"""
Image Collector module for Admin backend.
Handles uploading training/validation images, storing them in filesystem,
preventing duplicates using SHA-256 content hashing,
and registering images into PostgreSQL training_images table.
"""
import hashlib
import io
import uuid
from pathlib import Path
from PIL import Image
import streamlit as st
from core.config import IMAGES_DIR
from core.db import get_db
from core.models_db import TrainingImage, ImageLabel, ToolClass


SUPPORTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".cr2"]
RAW_EXTENSIONS = [".cr2"]


def calculate_image_hash(image_bytes: bytes) -> str:
    """Calculates SHA-256 hash of image file content."""
    return hashlib.sha256(image_bytes).hexdigest()


def decode_image_file(file_bytes: bytes, ext: str) -> tuple[Image.Image, str]:
    """
    Decodes image bytes from various formats (including Canon RAW .cr2 and .bmp) into a PIL Image.
    Returns (pil_img, save_extension).
    For RAW files (.cr2), converts to .jpg for YOLO training, Roboflow, and web display compatibility.
    """
    ext_lower = ext.lower()
    if ext_lower in RAW_EXTENSIONS:
        import rawpy
        with rawpy.imread(io.BytesIO(file_bytes)) as raw:
            rgb_array = raw.postprocess(use_camera_wb=True)
            pil_img = Image.fromarray(rgb_array)
        return pil_img, ".jpg"
    else:
        pil_img = Image.open(io.BytesIO(file_bytes))
        return pil_img, ext_lower


def save_uploaded_image(
    file,
    split: str = "train",
    user_id: int = None,
    allow_duplicate: bool = False
) -> tuple[str, str]:
    """
    Saves uploaded image file to IMAGES_DIR and registers in PostgreSQL.
    Supports JPG, JPEG, PNG, WEBP, BMP, and Canon RAW (CR2).
    Returns:
        (status, message)
        where status is 'success', 'duplicate', or 'error'
    """
    try:
        # Check file extension
        ext = Path(file.name).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return "error", f"สกุลไฟล์ไม่รองรับ: {ext} (รองรับ: {', '.join(SUPPORTED_EXTENSIONS)})"

        # Read bytes and compute SHA-256 hash
        file_bytes = file.getvalue()
        file_hash = calculate_image_hash(file_bytes)

        # Check for duplicates in PostgreSQL by hash
        if not allow_duplicate:
            with get_db() as db:
                existing = db.query(TrainingImage).filter(TrainingImage.file_hash == file_hash).first()
                if existing:
                    return "duplicate", existing.filename

        # Decode image content (handles CR2, BMP, WEBP, PNG, JPG)
        pil_img, save_ext = decode_image_file(file_bytes, ext)
        width, height = pil_img.size

        # Generate safe unique filename
        safe_filename = f"{Path(file.name).stem}_{uuid.uuid4().hex[:8]}{save_ext}"
        target_path = IMAGES_DIR / safe_filename

        # Save to filesystem with appropriate format encoding
        if save_ext in [".jpg", ".jpeg"]:
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
            pil_img.save(target_path, "JPEG", quality=95)
        elif save_ext == ".bmp":
            if pil_img.mode not in ("RGB", "L"):
                pil_img = pil_img.convert("RGB")
            pil_img.save(target_path, "BMP")
        elif save_ext == ".webp":
            pil_img.save(target_path, "WEBP", quality=95)
        elif save_ext == ".png":
            pil_img.save(target_path, "PNG")
        else:
            pil_img.save(target_path)

        # Register into DB
        with get_db() as db:
            img_record = TrainingImage(
                filename=safe_filename,
                file_path=str(target_path.as_posix()),
                split=split,
                file_hash=file_hash,
                width=width,
                height=height,
                source="upload",
                uploaded_by=user_id
            )
            db.add(img_record)

        return "success", safe_filename
    except Exception as e:
        return "error", str(e)


def render_image_collector(current_user: dict):
    """Renders the Image Collector UI."""
    st.markdown("### 📸 อัปโหลดและจัดการภาพ Training (Image Collector)")
    st.caption("รวบรวมรูปภาพเครื่องมือและถาดอุปกรณ์เพื่อใช้เทรนโมเดล YOLO (มีระบบตรวจสอบภาพซ้ำอัตโนมัติ)")

    tab_upload, tab_gallery = st.tabs(["📤 อัปโหลดภาพใหม่", "🖼️ แกลเลอรีภาพในระบบ"])

    # TAB 1: Upload Images
    with tab_upload:
        st.markdown("#### 1. อัปโหลดรูปภาพ (รองรับทีละหลายรูป)")
        col_split, col_dup = st.columns(2)
        with col_split:
            split_choice = st.selectbox("กำหนด Dataset Split", ["train", "val", "test"], index=0)
        with col_dup:
            prevent_dup = st.checkbox("🛡️ ป้องกันการอัปโหลดภาพซ้ำ (ตรวจสอบ SHA-256)", value=True)
            if prevent_dup:
                st.caption("ระบบจะตรวจสอบเนื้อหาไฟล์ภาพ หากมีภาพนี้ในระบบแล้วจะข้ามให้อัตโนมัติ")

        uploaded_files = st.file_uploader(
            "เลือกไฟล์รูปภาพ (JPG, PNG, WEBP, BMP, CR2)",
            type=["jpg", "jpeg", "png", "webp", "bmp", "cr2"],
            accept_multiple_files=True
        )

        if uploaded_files:
            st.write(f"เลือกภาพทั้งหมด **{len(uploaded_files)}** ไฟล์")
            if st.button("🚀 บันทึกภาพทั้งหมดเข้าสู่ระบบ", use_container_width=True):
                success_count = 0
                duplicates = []
                errors = []
                progress_bar = st.progress(0)
                
                for idx, f in enumerate(uploaded_files):
                    user_id = current_user.get("id") if current_user else None
                    status, res = save_uploaded_image(
                        f,
                        split=split_choice,
                        user_id=user_id,
                        allow_duplicate=not prevent_dup
                    )
                    
                    if status == "success":
                        success_count += 1
                    elif status == "duplicate":
                        duplicates.append(f"{f.name} (ตรงกับ {res})")
                    else:
                        errors.append(f"{f.name}: {res}")
                        
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                
                # Feedback to user
                if success_count > 0:
                    st.success(f"✅ บันทึกภาพใหม่สำเร็จ {success_count} ภาพ!")
                if duplicates:
                    st.warning(f"⚠️ ข้าม {len(duplicates)} ภาพ เนื่องจากเป็นภาพซ้ำที่มีอยู่ในระบบแล้ว:\n- " + "\n- ".join(duplicates[:10]))
                    if len(duplicates) > 10:
                        st.caption(f"...และอีก {len(duplicates) - 10} ภาพ")
                if errors:
                    st.error(f"❌ พบข้อผิดพลาด {len(errors)} ภาพ:\n- " + "\n- ".join(errors[:5]))

                if success_count > 0:
                    st.rerun()

    # TAB 2: Image Gallery
    with tab_gallery:
        st.markdown("#### 2. รายการภาพที่บันทึกแล้ว")
        try:
            with get_db() as db:
                raw_images = db.query(TrainingImage).order_by(TrainingImage.id.desc()).all()
                images = [
                    {
                        "id": img.id,
                        "filename": img.filename,
                        "file_path": img.file_path,
                        "split": img.split,
                        "width": img.width,
                        "height": img.height
                    }
                    for img in raw_images
                ]
                total = len(images)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("จำนวนรูปทั้งหมด", f"{total} รูป")
            with c2:
                train_count = sum(1 for img in images if img["split"] == "train")
                st.metric("Train Set", f"{train_count} รูป")
            with c3:
                val_count = sum(1 for img in images if img["split"] == "val")
                st.metric("Validation Set", f"{val_count} รูป")

            if total == 0:
                st.info("ยังไม่มีรูปภาพในระบบ กรุณาอัปโหลดรูปภาพในแท็บแรก")
            else:
                # Filter by split
                filter_split = st.selectbox("กรองตาม Split", ["ทั้งหมด", "train", "val", "test"])
                filtered_images = images if filter_split == "ทั้งหมด" else [i for i in images if i["split"] == filter_split]

                # Pagination
                items_per_page = 12
                page = st.number_input("หน้า", min_value=1, max_value=max(1, (len(filtered_images) + items_per_page - 1) // items_per_page), value=1)
                start_idx = (page - 1) * items_per_page
                paged = filtered_images[start_idx:start_idx + items_per_page]

                # Grid display
                cols = st.columns(4)
                for idx, img_record in enumerate(paged):
                    col = cols[idx % 4]
                    with col:
                        img_path = Path(img_record["file_path"])
                        if img_path.exists():
                            st.image(str(img_path), caption=f"{img_record['filename']} ({img_record['split']})", use_container_width=True)
                            st.caption(f"📐 {img_record['width']}x{img_record['height']} px")
                        else:
                            st.warning(f"ไม่พบไฟล์: {img_record['filename']}")
        except Exception as e:
            st.error(f"ไม่สามารถโหลดภาพจากฐานข้อมูล: {e}")
