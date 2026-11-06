"""
Dataset Exporter module for YOLOv8 & Roboflow integration.
Packages images and labels into standard YOLOv8 folder structure with data.yaml,
and bundles them into a downloadable ZIP file.
"""
import shutil
import zipfile
from pathlib import Path
import streamlit as st
from core.config import EXPORTS_DIR, IMAGES_DIR
from core.db import get_db
from core.models_db import ToolClass, TrainingImage, ImageLabel


def build_yolo_dataset_zip() -> tuple[bool, str, Path | None]:
    """
    Constructs YOLOv8 directory structure and zips it:
    dataset/
      ├── data.yaml
      ├── images/
      │   ├── train/
      │   └── val/
      └── labels/
          ├── train/
          └── val/
    """
    try:
        export_build_dir = EXPORTS_DIR / "yolo_dataset_build"
        if export_build_dir.exists():
            shutil.rmtree(export_build_dir)
        
        # Create directories
        for split in ["train", "val"]:
            (export_build_dir / "images" / split).mkdir(parents=True, exist_ok=True)
            (export_build_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

        with get_db() as db:
            # Fetch active classes
            classes = db.query(ToolClass).filter(ToolClass.is_active == True).order_by(ToolClass.id).all()
            if not classes:
                return False, "ไม่มี Tool Class ที่เปิดใช้งานในระบบ", None
            
            class_id_to_idx = {c.id: idx for idx, c in enumerate(classes)}
            class_names = [c.class_key for c in classes]

            # Fetch all training images
            images = db.query(TrainingImage).all()
            if not images:
                return False, "ยังไม่มีรูปภาพในระบบสำหรับ Export", None

            copied_img_count = 0
            for img in images:
                src_path = Path(img.file_path)
                if not src_path.exists():
                    continue

                split = img.split if img.split in ["train", "val"] else "train"
                dest_img_path = export_build_dir / "images" / split / img.filename
                shutil.copy2(src_path, dest_img_path)
                copied_img_count += 1

                # Generate label file
                label_txt_path = export_build_dir / "labels" / split / f"{src_path.stem}.txt"
                labels = db.query(ImageLabel).filter(ImageLabel.image_id == img.id).all()
                lines = []
                for lbl in labels:
                    if lbl.class_id in class_id_to_idx:
                        c_idx = class_id_to_idx[lbl.class_id]
                        lines.append(lbl.to_yolo_str(c_idx))
                
                with open(label_txt_path, "w", encoding="utf-8") as lf:
                    lf.write("\n".join(lines))

        # Generate data.yaml
        yaml_content = f"""# YOLOv8 Dataset Configuration
path: ./dataset
train: images/train
val: images/val

# Classes
nc: {len(class_names)}
names: {class_names}
"""
        with open(export_build_dir / "data.yaml", "w", encoding="utf-8") as yf:
            yf.write(yaml_content)

        # Create ZIP archive
        zip_path = EXPORTS_DIR / "yolo_dataset.zip"
        if zip_path.exists():
            zip_path.unlink()

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_f:
            for file_path in export_build_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(export_build_dir)
                    zip_f.write(file_path, arcname)

        return True, f"สร้าง Dataset สำเร็จ (รวม {copied_img_count} รูป)", zip_path
    except Exception as e:
        return False, str(e), None


def render_dataset_exporter():
    """Renders the Dataset Exporter UI."""
    st.markdown("### 📦 ส่งออกชุดข้อมูล (Dataset Exporter for YOLO & Roboflow)")
    st.caption("จัดเตรียมและดาวน์โหลดข้อมูลภาพพร้อม Label เพื่อนำไปเทรนบน Google Colab หรืออัปโหลดเข้า Roboflow")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            #### 🚀 วิธีที่เลือก: Roboflow + Colab (Option B)
            1. **ส่งออกรูปภาพ**: ดาวน์โหลดไฟล์รูปภาพจากระบบนี้
            2. **อัปโหลดเข้า Roboflow**: วาด Bounding Box + ทำ Data Augmentation
            3. **Export จาก Roboflow**: เลือก format `YOLOv8 PyTorch`
            4. **เทรนบน Google Colab**: รันโค้ดสั้นๆ เพียงไม่กี่เซลล์
            5. **นำโมเดล .pt กลับมา**: อัปโหลดในหน้า Model Manager
            """
        )

    with col2:
        st.markdown("#### 📥 ดาวน์โหลด Dataset จากระบบปัจจุบัน")
        if st.button("🔨 สร้างและดาวน์โหลด YOLO Dataset ZIP", use_container_width=True):
            with st.spinner("กำลังรวบรวมไฟล์และสร้าง ZIP..."):
                ok, msg, zip_file = build_yolo_dataset_zip()
                if ok and zip_file and zip_file.exists():
                    st.success(msg)
                    with open(zip_file, "rb") as f:
                        st.download_button(
                            label="⬇️ คลิกเพื่อบันทึก yolo_dataset.zip",
                            data=f.read(),
                            file_name="yolo_dataset.zip",
                            mime="application/zip",
                            use_container_width=True
                        )
                else:
                    st.error(f"เกิดข้อผิดพลาด: {msg}")
