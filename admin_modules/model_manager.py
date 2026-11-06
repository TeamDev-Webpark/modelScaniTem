"""
Model Manager module for Admin backend.
Manages trained YOLO weights (.pt), model versioning, performance metrics (mAP50),
and activating the production model for the scanner.
"""
from datetime import datetime
from pathlib import Path
import streamlit as st
from core.config import MODELS_DIR
from core.db import get_db
from core.models_db import TrainedModel


def save_trained_model_file(uploaded_file, version: str, notes: str, user_id: int = None) -> tuple[bool, str]:
    """Saves uploaded .pt model file to MODELS_DIR and registers in DB."""
    try:
        filename = f"{version}_{uploaded_file.name}"
        dest_path = MODELS_DIR / filename
        
        with open(dest_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        with get_db() as db:
            model_record = TrainedModel(
                version=version,
                model_path=str(dest_path.as_posix()),
                model_type="yolov8m",
                notes=notes,
                is_active=False,
                trained_by=user_id,
                trained_at=datetime.utcnow()
            )
            db.add(model_record)

        return True, "อัปโหลดโมเดลเรียบร้อย"
    except Exception as e:
        return False, str(e)


def initialize_base_pretrained_model(model_name: str = "yolov8m.pt") -> tuple[bool, str]:
    """Downloads and registers base pretrained YOLOv8 model for immediate testing."""
    try:
        from ultralytics import YOLO
        
        # Download or load base model
        model = YOLO(model_name)
        target_path = MODELS_DIR / f"base_{model_name}"
        
        # Save weights to MODELS_DIR
        import shutil
        if Path(model_name).exists():
            shutil.copy2(model_name, target_path)
        else:
            # Fallback path if ultralytics saved in current dir
            found = list(Path(".").glob(f"*{model_name}"))
            if found:
                shutil.copy2(found[0], target_path)

        with get_db() as db:
            # Deactivate others
            db.query(TrainedModel).update({TrainedModel.is_active: False})
            
            base_record = TrainedModel(
                version=f"Base-{model_name.replace('.pt', '')}",
                model_path=str(target_path.as_posix()),
                model_type=model_name.replace(".pt", ""),
                notes="โมเดลเริ่มต้น Pre-trained จาก Ultralytics (พร้อมใช้งานสำหรับทดสอบทันที)",
                is_active=True,
                trained_at=datetime.utcnow()
            )
            db.add(base_record)

        return True, f"ติดตั้งและเปิดใช้งาน {model_name} สำเร็จ!"
    except Exception as e:
        return False, str(e)


def set_active_model(model_id: int):
    """Sets the designated model as the active model and deactivates others."""
    with get_db() as db:
        # Deactivate all
        db.query(TrainedModel).update({TrainedModel.is_active: False})
        # Activate chosen
        target = db.query(TrainedModel).filter(TrainedModel.id == model_id).first()
        if target:
            target.is_active = True
            db.add(target)


def render_model_manager(current_user: dict):
    """Renders the Model Management UI."""
    st.markdown("### 🧠 จัดการโมเดลตรวจจับ (Trained Model Manager)")
    st.caption("อัปโหลดและสลับโมเดล YOLO (.pt) ที่เทรนจาก Google Colab เพื่อนำมาใช้ตรวจจับจริง")

    tab_list, tab_upload, tab_base = st.tabs([
        "🏆 โมเดลในระบบ & การเปิดใช้งาน",
        "⬆️ อัปโหลดโมเดล (.pt)",
        "⚡ โหลดโมเดลเริ่มต้น (Quick Start)"
    ])

    # TAB 1: List models
    with tab_list:
        try:
            with get_db() as db:
                raw_models = db.query(TrainedModel).order_by(TrainedModel.id.desc()).all()
                models = [
                    {
                        "id": m.id,
                        "version": m.version,
                        "model_path": m.model_path,
                        "model_type": m.model_type,
                        "is_active": m.is_active,
                        "notes": m.notes,
                        "created_at": m.created_at
                    }
                    for m in raw_models
                ]

            if not models:
                st.info("💡 ยังไม่มีโมเดลในระบบ คุณสามารถเลือกได้ 2 ทาง:\n1. กดแท็บ **'⚡ โหลดโมเดลเริ่มต้น'** เพื่อดาวน์โหลดโมเดลพื้นฐานมาทดสอบได้ทันที\n2. หรืออัปโหลดไฟล์ `best.pt` ที่เทรนจาก Google Colab ในแท็บ **'อัปโหลดโมเดล'**")
            else:
                for m in models:
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
                        with c1:
                            st.markdown(f"**เวอร์ชัน: {m['version']}**")
                            st.caption(f"ไฟล์: {Path(m['model_path']).name}")
                        with c2:
                            st.markdown(f"ชนิด: `{m['model_type']}`")
                            date_str = m['created_at'].strftime('%Y-%m-%d %H:%M') if m['created_at'] else '-'
                            st.caption(f"วันที่: {date_str}")
                        with c3:
                            if m['is_active']:
                                st.success("🟢 ใช้งานอยู่ (Active)")
                            else:
                                st.info("⚪ ไม่ได้ใช้งาน")
                        with c4:
                            if not m['is_active']:
                                if st.button("🚀 เปิดใช้งานโมเดลนี้", key=f"act_{m['id']}", use_container_width=True):
                                    set_active_model(m['id'])
                                    st.success(f"เปิดใช้งานโมเดล {m['version']} เรียบร้อย!")
                                    st.rerun()
                            else:
                                st.write("⭐ โมเดลหลัก")
                        
                        if m['notes']:
                            st.markdown(f"📝 *บันทึก:* {m['notes']}")
        except Exception as e:
            st.error(f"ไม่สามารถโหลดข้อมูลโมเดล: {e}")

    # TAB 2: Upload model
    with tab_upload:
        st.markdown("#### อัปโหลดโมเดล PyTorch (.pt) ที่เทรนเสร็จแล้ว (จาก Google Colab)")
        st.caption("เมื่อคุณรัน Notebook บน Google Colab เสร็จแล้ว ให้ดาวน์โหลดไฟล์ `best.pt` มาอัปโหลดที่นี่")
        with st.form("upload_model_form"):
            ver_input = st.text_input("เวอร์ชันโมเดล (เช่น v1.0, v2.0-tray3)", placeholder="v1.0")
            notes_input = st.text_area("หมายเหตุการเทรน (เช่น เทรน 16 รายการถาดที่ 3 บน Google Colab 50 epochs)")
            model_file = st.file_uploader("เลือกไฟล์โมเดล (.pt)", type=["pt"])
            submit_upload = st.form_submit_button("บันทึกและลงทะเบียนโมเดล", use_container_width=True)

            if submit_upload:
                if not ver_input or not model_file:
                    st.error("กรุณากรอกเวอร์ชันและเลือกไฟล์ .pt")
                else:
                    uid = current_user.get("id") if current_user else None
                    ok, msg = save_trained_model_file(model_file, ver_input.strip(), notes_input.strip(), uid)
                    if ok:
                        st.success("อัปโหลดและบันทึกโมเดลสำเร็จ! คุณสามารถกด '🚀 เปิดใช้งานโมเดลนี้' ได้ในแท็บแรก")
                        st.rerun()
                    else:
                        st.error(f"เกิดข้อผิดพลาด: {msg}")

    # TAB 3: Base Quick Start Model
    with tab_base:
        st.markdown("#### ⚡ โหลดโมเดลเริ่มต้นเพื่อทดสอบทันที (ไม่ต้องรอเทรน)")
        st.write("หากคุณยังไม่ได้เทรนโมเดลบน Colab สามารถโหลดโมเดล Pre-trained พื้นฐานของ YOLOv8 มาเปิดใช้งานเพื่อทดสอบระบบการสแกนและ UI ได้ทันที")
        
        c_choice, c_btn = st.columns([2, 1])
        with c_choice:
            base_choice = st.selectbox(
                "เลือกรุ่นโมเดล",
                ["yolov8m.pt (แนะนำ - แม่นยำดี)", "yolov8n.pt (ขนาดเล็ก - เร็วมาก)"]
            )
        with c_btn:
            st.write("")
            st.write("")
            if st.button("🚀 ดาวน์โหลด & เปิดใช้งานทันที", use_container_width=True):
                target_model_file = "yolov8m.pt" if "yolov8m" in base_choice else "yolov8n.pt"
                with st.spinner(f"กำลังดาวน์โหลดและตั้งค่า {target_model_file}..."):
                    ok, msg = initialize_base_pretrained_model(target_model_file)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(f"เกิดข้อผิดพลาด: {msg}")
