"""
Tray Template Manager module for Admin backend.
Manages Tray layout templates and slot positions in PostgreSQL.
Supports importing existing JSON tray templates (Y31, Y, etc.)
and setting up Tray 3 (16 items).
"""
import json
from pathlib import Path
import streamlit as st
from db import get_db
from models_db import TrayTemplate, TraySlot, ToolClass
from config import TRAY_TEMPLATES_DIR


def import_existing_json_trays(custom_json_data=None):
    """Imports existing tray JSON files from mock_database/tray_templates or custom dict into PostgreSQL."""
    data_list = []
    if custom_json_data is not None:
        data_list = [(custom_json_data, "uploaded_file.json")]
    else:
        templates_dir = TRAY_TEMPLATES_DIR
        if not templates_dir.exists():
            return 0
        for json_file in templates_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data_list.append((data, json_file.name))
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการอ่าน {json_file.name}: {e}")

    count = 0
    with get_db() as db:
        for data, filename in data_list:
            try:
                tray_id = data.get("tray_id") or Path(filename).stem
                tray_name = data.get("tray_name", tray_id)
                image_size = data.get("image_size", [1920, 1080])

                # Check if template already exists
                existing = db.query(TrayTemplate).filter(TrayTemplate.tray_id == tray_id).first()
                if not existing:
                    template = TrayTemplate(
                        tray_id=tray_id,
                        tray_name=tray_name,
                        description=data.get("description", f"Imported from {filename}"),
                        image_width=image_size[0] if len(image_size) > 0 else 1920,
                        image_height=image_size[1] if len(image_size) > 1 else 1080,
                        is_active=True
                    )
                    db.add(template)
                    db.flush()  # to obtain template.id

                    slots = data.get("slots", [])
                    for idx, s in enumerate(slots):
                        bbox = s.get("bbox_norm", [0, 0, 1, 1])
                        # Normalize 4 coordinates
                        x1 = bbox[0] if len(bbox) > 0 else 0.0
                        y1 = bbox[1] if len(bbox) > 1 else 0.0
                        x2 = bbox[2] if len(bbox) > 2 else 1.0
                        y2 = bbox[3] if len(bbox) > 3 else 1.0

                        # Resolve item_code: prefer class_key (matches YOLO class names),
                        # then fall back to code, then filename-derived key
                        resolved_item_code = (
                            s.get("class_key")
                            or s.get("code", "")
                            or s.get("filename", "").replace(".jpg", "").replace(".png", "")
                        )
                        slot_obj = TraySlot(
                            tray_template_id=template.id,
                            slot_number=s.get("slot_number", idx + 1),
                            item_name=s.get("name", f"Slot {idx + 1}"),
                            item_code=resolved_item_code,
                            bbox_x1_norm=float(x1),
                            bbox_y1_norm=float(y1),
                            bbox_x2_norm=float(x2),
                            bbox_y2_norm=float(y2),
                            is_required=s.get("is_required", True)
                        )
                        db.add(slot_obj)

                    template.slot_count = len(slots)
                    count += 1
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการนำเข้า {filename}: {e}")

    return count


def render_tray_manager(current_user: dict):
    """Renders the Tray Template Manager UI."""
    st.markdown("### 🍱 จัดการถาดอุปกรณ์ (Tray Template Manager)")
    st.caption("กำหนดโครงสร้างถาด ตำแหน่งช่อง (Slots) และรายการอุปกรณ์ประจำแต่ละช่อง")

    tab_list, tab_tray3, tab_import = st.tabs(["📋 รายการถาดในระบบ", "🎯 ตั้งค่าถาดที่ 3 (16 ชิ้น)", "📥 นำเข้าจาก JSON เดิม"])

    # TAB 1: List Trays
    with tab_list:
        try:
            with get_db() as db:
                raw_trays = db.query(TrayTemplate).all()
                trays = []
                for t in raw_trays:
                    slots_info = [
                        {
                            "ช่องที่": s.slot_number,
                            "ชื่ออุปกรณ์": s.item_name,
                            "รหัส": s.item_code or "-",
                            "BBox [x1, y1, x2, y2]": f"[{s.bbox_x1_norm:.2f}, {s.bbox_y1_norm:.2f}, {s.bbox_x2_norm:.2f}, {s.bbox_y2_norm:.2f}]",
                            "จำเป็นต้องมี": "✅" if s.is_required else "❌"
                        }
                        for s in t.slots
                    ]
                    trays.append({
                        "tray_id": t.tray_id,
                        "tray_name": t.tray_name,
                        "description": t.description,
                        "is_active": t.is_active,
                        "slots": slots_info
                    })

            if not trays:
                st.info("ยังไม่มีข้อมูลถาดในระบบ กรุณานำเข้าจากแท็บ 'นำเข้าจาก JSON เดิม'")
            else:
                for t in trays:
                    with st.expander(f"🍱 {t['tray_name']} (ID: {t['tray_id']}) - {len(t['slots'])} ช่อง"):
                        st.write(f"คำอธิบาย: {t['description'] or '-'}")
                        st.write(f"สถานะ: {'🟢 ใช้งาน' if t['is_active'] else '🔴 ปิดใช้งาน'}")

                        if t['slots']:
                            st.table(t['slots'])
        except Exception as e:
            st.error(f"ไม่สามารถโหลดข้อมูลถาด: {e}")

    # TAB 2: Setup Tray 3
    with tab_tray3:
        st.markdown("#### 🎯 ลงทะเบียนถาดที่ 3 (ถาดเริ่มต้น 16 รายการ)")
        st.info("ถาดที่ 3 มีอุปกรณ์หลัก 16 รายการพร้อมหมายเลขกำกับ (ลูกบ๊อกซ์, คีม, ด้ามฟรี ฯลฯ)")
        
        with st.form("create_tray3_form"):
            t3_name = st.text_input("ชื่อถาด", value="ถาดเครื่องมือชุดที่ 3 (Tray 03)")
            t3_id = st.text_input("Tray ID", value="TRAY_03")
            t3_desc = st.text_area("รายละเอียด", value="ถาดเครื่องมือมาตรฐาน 16 ช่อง พร้อมมาร์กเกอร์และตำแหน่งชัดเจน")
            btn_create_t3 = st.form_submit_button("สร้างถาดที่ 3 เข้าระบบ", use_container_width=True)

            if btn_create_t3:
                try:
                    with get_db() as db:
                        exist = db.query(TrayTemplate).filter(TrayTemplate.tray_id == t3_id).first()
                        if exist:
                            st.warning(f"ถาด ID '{t3_id}' มีอยู่ในระบบแล้ว")
                        else:
                            t3 = TrayTemplate(
                                tray_id=t3_id,
                                tray_name=t3_name,
                                description=t3_desc,
                                slot_count=16,
                                is_active=True
                            )
                            db.add(t3)
                            db.flush()

                            # Create 16 initial slots
                            for slot_i in range(1, 17):
                                slot = TraySlot(
                                    tray_template_id=t3.id,
                                    slot_number=slot_i,
                                    item_name=f"อุปกรณ์ช่องที่ {slot_i}",
                                    bbox_x1_norm=0.0,
                                    bbox_y1_norm=0.0,
                                    bbox_x2_norm=1.0,
                                    bbox_y2_norm=1.0,
                                    is_required=True
                                )
                                db.add(slot)
                            st.success("สร้างถาดที่ 3 พร้อม 16 ช่อง เรียบร้อยแล้ว!")
                            st.rerun()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

    # TAB 3: Import from JSON
    with tab_import:
        st.markdown("#### 📥 นำเข้าแม่แบบถาด (Import Tray Templates)")
        st.write("นำเข้าแม่แบบถาดจากโฟลเดอร์ `mock_database/tray_templates` หรืออัปโหลดไฟล์ JSON ถาดเครื่องมือใหม่")

        col_t_def, col_t_up = st.columns(2)
        with col_t_def:
            st.markdown("##### ⚡ นำเข้าจากโฟลเดอร์ระบบ")
            st.caption("ระบบพบแม่แบบ เช่น `box2-template01_31-item.json` (41 ช่อง)")
            if st.button("🚀 นำเข้าแม่แบบถาดทั้งหมดจากโฟลเดอร์", use_container_width=True):
                imported = import_existing_json_trays()
                if imported > 0:
                    st.success(f"นำเข้าถาดสำเร็จ {imported} แบบ!")
                    st.rerun()
                else:
                    st.info("ไม่มีถาดใหม่ที่ต้องนำเข้า (หรือนำเข้าไว้แล้ว)")

        with col_t_up:
            st.markdown("##### 📁 อัปโหลดไฟล์ Template JSON")
            uploaded_tray = st.file_uploader("เลือกไฟล์ JSON แม่แบบถาด", type=["json"], key="upload_custom_tray_json")
            if uploaded_tray is not None:
                if st.button("📥 นำเข้าถาดจากไฟล์ที่อัปโหลด", use_container_width=True):
                    try:
                        content = json.loads(uploaded_tray.getvalue().decode("utf-8"))
                        imported = import_existing_json_trays(custom_json_data=content)
                        if imported > 0:
                            st.success(f"นำเข้าถาดจากไฟล์อัปโหลดสำเร็จ!")
                            st.rerun()
                        else:
                            st.info("ถาดนี้มีอยู่ในระบบแล้ว")
                    except Exception as e:
                        st.error(f"รูปแบบไฟล์ JSON ไม่ถูกต้อง: {e}")
