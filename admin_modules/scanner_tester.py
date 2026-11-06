"""
Scanner Test & Verification Playground for Admin backend.
Allows testing both:
Part 1: General Object Detection (tools on table / freely placed)
Part 2: Tray Block Verification (checking slots against tray template)
"""
from pathlib import Path
from PIL import Image
import cv2
import numpy as np
import streamlit as st
from core.config import MODELS_DIR
from core.db import get_db
from core.models_db import TrainedModel, TrayTemplate
from scanners.yolo_scanner import YOLOToolScanner, ULTRALYTICS_AVAILABLE
from admin_modules.image_collector import decode_image_file


def load_active_scanner() -> tuple[YOLOToolScanner, str]:
    """Loads scanner with active model from DB or fallback default."""
    try:
        with get_db() as db:
            active_m = db.query(TrainedModel).filter(TrainedModel.is_active == True).first()
            if active_m and Path(active_m.model_path).exists():
                scanner = YOLOToolScanner(active_m.model_path)
                return scanner, f"โมเดล {active_m.version} ({Path(active_m.model_path).name})"
    except Exception as e:
        pass

    # Fallback to any .pt file in MODELS_DIR if exists
    pt_files = list(MODELS_DIR.glob("*.pt"))
    if pt_files:
        scanner = YOLOToolScanner(str(pt_files[0]))
        return scanner, f"โมเดล {pt_files[0].name} (จากโฟลเดอร์)"

    return YOLOToolScanner(), "ยังไม่มีโมเดลในระบบ (โหมดจำลอง/Simulation)"


def render_scanner_tester():
    """Renders the interactive Scanner Testing & Verification Playground."""
    st.markdown("### 🔍 ทดสอบการตรวจจับ & เช็คผลลัพธ์ (Scanner Playground)")
    st.caption("ทดสอบประสิทธิภาพการสแกนอุปกรณ์และการตรวจสอบความครบถ้วนของถาด")

    scanner, model_info = load_active_scanner()

    # Model status card
    c_m1, c_m2 = st.columns([3, 1])
    with c_m1:
        st.info(f"🧠 **สถานะโมเดลที่ใช้อยู่:** `{model_info}`")
    with c_m2:
        if not ULTRALYTICS_AVAILABLE:
            st.warning("⚠️ ยังไม่ได้ติดตั้ง ultralytics")

    test_mode = st.radio(
        "เลือกโหมดการทดสอบ",
        [
            "🎯 โหมด 1: ตรวจจับอุปกรณ์อิสระ (Object Detection)",
            "🍱 โหมด 2: ตรวจสอบความถูกต้องของถาด (Tray Block Verification)"
        ],
        horizontal=True
    )

    st.markdown("---")

    # =========================================================================
    # MODE 1: Object Detection
    # =========================================================================
    if test_mode.startswith("🎯"):
        st.markdown("#### 🎯 สแกนอุปกรณ์ที่วางเรียงหรือวางอิสระ")
        st.write("ตรวจจับ Bounding Box, ระบุชื่ออุปกรณ์ และแสดง Confidence Score")

        c_file, c_conf = st.columns([2, 1])
        with c_file:
            uploaded_img = st.file_uploader(
                "อัปโหลดภาพสำหรับสแกน",
                type=["jpg", "jpeg", "png", "webp", "bmp", "cr2"],
                key="test_obj_upload"
            )
        with c_conf:
            conf_th = st.slider("เกณฑ์ความมั่นใจ (Confidence Threshold)", 0.10, 0.95, 0.35, 0.05)

        if uploaded_img:
            # Read image (supports CR2, BMP, WEBP, PNG, JPG)
            ext = Path(uploaded_img.name).suffix.lower()
            pil_img, _ = decode_image_file(uploaded_img.getvalue(), ext)
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
            img_np = np.array(pil_img)
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

            col_btn, _ = st.columns([1, 3])
            with col_btn:
                start_scan = st.button("🚀 สแกนค้นหาอุปกรณ์", use_container_width=True)

            if start_scan or "last_obj_detections" in st.session_state:
                with st.spinner("กำลังประมวลผลการตรวจจับ..."):
                    detections = scanner.detect_tools(img_bgr, conf_threshold=conf_th)
                    st.session_state.last_obj_detections = detections

                # If no model is active, show simulation example if requested
                if scanner.model is None and not detections:
                    st.warning("ℹ️ ขณะนี้ยังไม่มีโมเดล YOLO `.pt` ที่เปิดใช้งานในระบบ")
                    st.info("💡 เมื่อคุณนำโมเดลที่เทรนจาก Google Colab มาอัปโหลดในหน้า 'จัดการโมเดล' ระบบจะตรวจจับและวาดกรอบ Bounding Box พร้อมระบุชื่ออุปกรณ์ให้อัตโนมัติ")

                col_res_img, col_res_tbl = st.columns([3, 2])
                with col_res_img:
                    annotated_bgr = scanner.draw_detections(img_bgr, detections)
                    annotated_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
                    st.image(annotated_rgb, caption=f"ผลการสแกน (พบ {len(detections)} ชิ้น)", use_container_width=True)

                with col_res_tbl:
                    st.markdown(f"##### 📋 รายการอุปกรณ์ที่พบ ({len(detections)} ชิ้น)")
                    if detections:
                        summary_rows = []
                        for idx, det in enumerate(detections):
                            summary_rows.append({
                                "#": idx + 1,
                                "ชื่ออุปกรณ์": det["class_name"],
                                "ความมั่นใจ": f"{det['confidence']:.1%}",
                                "พิกัด BBox": f"[{det['bbox'][0]}, {det['bbox'][1]}, {det['bbox'][2]}, {det['bbox'][3]}]"
                            })
                        st.dataframe(summary_rows, use_container_width=True)
                    else:
                        st.caption("ไม่พบอุปกรณ์ที่ระดับความมั่นใจนี้")

    # =========================================================================
    # MODE 2: Tray Verification
    # =========================================================================
    else:
        st.markdown("#### 🍱 ตรวจสอบอุปกรณ์บนบล็อกถาด (ความครบถ้วน & ตำแหน่ง)")
        st.write("เปรียบเทียบตำแหน่งอุปกรณ์ที่ตรวจจับได้กับช่อง (Slots) ในแม่แบบถาด")

        # Select tray template from DB
        try:
            with get_db() as db:
                trays = db.query(TrayTemplate).all()
                tray_options = {f"{t.tray_name} (ID: {t.tray_id})": t.id for t in trays}
        except Exception:
            tray_options = {}

        if not tray_options:
            st.warning("⚠️ ยังไม่มีแม่แบบถาดในระบบ กรุณาไปที่เมนู '🍱 จัดการถาดอุปกรณ์' เพื่อกด 'ตั้งค่าถาดที่ 3' หรือนำเข้าถาดเดิม")
            return

        c_tray_sel, c_tray_img = st.columns(2)
        with c_tray_sel:
            selected_tray_name = st.selectbox("เลือกแม่แบบถาดที่ต้องการตรวจ", list(tray_options.keys()))
            selected_tray_id = tray_options[selected_tray_name]
        with c_tray_img:
            uploaded_tray_img = st.file_uploader(
                "อัปโหลดภาพถ่ายถาดที่ต้องการตรวจสอบ",
                type=["jpg", "jpeg", "png", "webp", "bmp", "cr2"],
                key="test_tray_upload"
            )

        if uploaded_tray_img:
            ext = Path(uploaded_tray_img.name).suffix.lower()
            pil_img, _ = decode_image_file(uploaded_tray_img.getvalue(), ext)
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
            img_np = np.array(pil_img)
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

            # Fetch tray template details
            with get_db() as db:
                target_tray = db.query(TrayTemplate).filter(TrayTemplate.id == selected_tray_id).first()
                tray_data = {
                    "tray_id": target_tray.tray_id,
                    "tray_name": target_tray.tray_name,
                    "slots": [
                        {
                            "slot_number": s.slot_number,
                            "item_name": s.item_name,
                            "item_code": s.item_code,
                            "bbox_norm": [s.bbox_x1_norm, s.bbox_y1_norm, s.bbox_x2_norm, s.bbox_y2_norm],
                            "is_required": s.is_required
                        }
                        for s in target_tray.slots
                    ]
                }

            if st.button("🚀 ตรวจสอบความถูกต้องของถาด", use_container_width=True):
                with st.spinner("กำลังตรวจสอบแต่ละช่องของถาด..."):
                    verification = scanner.verify_tray(img_bgr, tray_data)

                # Show status summary
                st.markdown("---")
                s1, s2, s3, s4 = st.columns(4)
                with s1:
                    if verification["is_complete"]:
                        st.success("✅ **ผลสรุป: ครบถ้วนถูกต้อง**")
                    else:
                        st.error("⚠️ **ผลสรุป: อุปกรณ์ไม่สมบูรณ์**")
                with s2:
                    st.metric("ช่องทั้งหมด", f"{verification['total_slots']} ช่อง")
                with s3:
                    st.metric("🟢 ครบ/ถูกต้อง", f"{verification['correct_count']} ชิ้น")
                with s4:
                    st.metric("🔴 ขาดหาย", f"{verification['missing_count']} ชิ้น")

                # Show visual and table
                c_vis, c_table = st.columns([3, 2])
                with c_vis:
                    annotated_bgr = scanner.draw_tray_verification(img_bgr, verification)
                    annotated_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
                    st.image(annotated_rgb, caption="ผลการตรวจเช็คถาด (เขียว=ครบ, แดง=ขาด, ส้ม=ผิดช่อง)", use_container_width=True)

                with c_table:
                    st.markdown("##### 📝 รายละเอียดการตรวจเช็คแต่ละช่อง")
                    table_rows = []
                    for s in verification["slot_results"]:
                        status_badge = "🟢 ครบ" if s["status"] == "correct" else ("🔴 ขาด" if s["status"] == "missing" else "🟠 ผิดช่อง")
                        table_rows.append({
                            "ช่อง": s["slot_number"],
                            "รายการที่ต้องมี": s["expected_name"],
                            "ผลการตรวจ": status_badge,
                            "ตรวจพบ": s["detected_item"] or "-"
                        })
                    st.dataframe(table_rows, use_container_width=True)
