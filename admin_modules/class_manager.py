"""
Tool Class Manager module for the Admin backend.
Manages YOLO tool classes (classes defined for detection).
Includes 1-click import from data/data.json.
"""
import json
from pathlib import Path
import streamlit as st
from core.db import get_db
from core.models_db import ToolClass, ImageLabel
from core.config import CATALOG_PATH


def import_classes_from_legacy_data(custom_data=None):
    """Imports tool classes from existing data/data.json or passed data."""
    if custom_data is None:
        json_path = CATALOG_PATH
        if not json_path.exists():
            st.error("ไม่พบไฟล์ data/data.json")
            return 0
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์ JSON: {e}")
            return 0
    else:
        data = custom_data

    try:
        imported_count = 0
        with get_db() as db:
            for item in data:
                # Prefer class_key (matches YOLO detection class name), then identifier name_en, then code
                class_key = (
                    item.get("class_key")
                    or (item.get("name_en") if item.get("name_en") and ("_" in item.get("name_en") or " " not in item.get("name_en")) else "")
                    or item.get("code", "")
                ).strip()
                code = item.get("code", class_key).strip()
                name_th = (item.get("name") or item.get("name_th") or code).strip()
                name_en = (item.get("name_en") or class_key or code).strip()
                category = item.get("category", "Special Tools").strip()
                desc = item.get("description", f"Auto-imported (Code: {code})").strip()
                if not class_key:
                    continue

                # Check if already exists
                existing = db.query(ToolClass).filter(
                    (ToolClass.class_key == class_key) | (ToolClass.name_th == name_th)
                ).first()

                if not existing:
                    new_class = ToolClass(
                        class_key=class_key,
                        name_en=name_en,
                        name_th=name_th,
                        category=category,
                        description=desc,
                        is_active=True
                    )
                    db.add(new_class)
                    imported_count += 1

        return imported_count
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการนำเข้าข้อมูล: {e}")
        return 0


def render_class_manager():
    """Renders the Tool Class Management UI."""
    st.markdown("### 🏷️ จัดการประเภทเครื่องมือ (Tool Classes for YOLO)")
    st.caption("กำหนด Class ที่โมเดล YOLO จะต้องตรวจจับและแยกแยะ")

    tab_list, tab_add, tab_import = st.tabs(["📋 รายการ Class ทั้งหมด", "➕ เพิ่ม Class ใหม่", "📥 นำเข้าจากข้อมูลเดิม"])

    # TAB 1: List Classes
    with tab_list:
        try:
            with get_db() as db:
                classes = db.query(ToolClass).order_by(ToolClass.id).all()
                total_classes = len(classes)
                table_data = [
                    {
                        "ID": c.id,
                        "Key (YOLO)": c.class_key,
                        "ชื่อภาษาอังกฤษ": c.name_en,
                        "ชื่อภาษาไทย": c.name_th or "-",
                        "หมวดหมู่": c.category or "-",
                        "สถานะ": "🟢 ใช้งาน" if c.is_active else "🔴 ปิดใช้งาน",
                    }
                    for c in classes
                ]
                class_options = [f"{c.id}: {c.class_key} ({c.name_th or c.name_en})" for c in classes]
            
            st.metric("จำนวน Class ในระบบ", f"{total_classes} คลาส")

            if total_classes == 0:
                st.info("ยังไม่มี Tool Class ในระบบ กรุณาเพิ่มใหม่ หรือใช้แท็บ 'นำเข้าจากข้อมูลเดิม'")
            else:
                st.dataframe(table_data, use_container_width=True)

                # Edit or Delete section
                st.markdown("#### ✏️ แก้ไข / ลบ Class")
                selected_key = st.selectbox(
                    "เลือก Class ที่ต้องการจัดการ",
                    options=class_options
                )
                
                if selected_key:
                    sel_id = int(selected_key.split(":")[0])
                    with get_db() as db:
                        target = db.query(ToolClass).filter(ToolClass.id == sel_id).first()
                        if target:
                            with st.form("edit_class_form"):
                                e_key = st.text_input("Class Key", value=target.class_key)
                                e_name_en = st.text_input("Name (EN)", value=target.name_en)
                                e_name_th = st.text_input("Name (TH)", value=target.name_th or "")
                                e_cat = st.text_input("Category", value=target.category or "Hand Tools")
                                e_desc = st.text_area("Description", value=target.description or "")
                                e_active = st.checkbox("เปิดใช้งาน (Active)", value=target.is_active)
                                
                                c1, c2 = st.columns(2)
                                with c1:
                                    save_btn = st.form_submit_button("💾 บันทึกการแก้ไข", use_container_width=True)
                                with c2:
                                    del_btn = st.form_submit_button("🗑️ ลบ Class นี้", use_container_width=True)
                                
                                if save_btn:
                                    target.class_key = e_key.strip()
                                    target.name_en = e_name_en.strip()
                                    target.name_th = e_name_th.strip()
                                    target.category = e_cat.strip()
                                    target.description = e_desc.strip()
                                    target.is_active = e_active
                                    db.add(target)
                                    st.success("บันทึกข้อมูลเรียบร้อย!")
                                    st.rerun()

                                if del_btn:
                                    # Check if used in labels
                                    used_count = db.query(ImageLabel).filter(ImageLabel.class_id == target.id).count()
                                    if used_count > 0:
                                        st.error(f"ไม่สามารถลบได้เนื่องจาก Class นี้ถูกใช้ใน Label ไปแล้ว {used_count} จุด")
                                    else:
                                        db.delete(target)
                                        st.warning("ลบ Class เรียบร้อย")
                                        st.rerun()

        except Exception as e:
            st.error(f"ไม่สามารถโหลดข้อมูล Tool Classes: {e}")

    # TAB 2: Add New Class
    with tab_add:
        st.markdown("#### ➕ เพิ่ม Class ใหม่สำหรับโมเดล")
        with st.form("add_class_form"):
            new_key = st.text_input("Class Key (ภาษาอังกฤษ ตัวพิมพ์เล็ก ไม่มีเว้นวรรค เช่น combination_pliers, socket_10mm)")
            new_name_en = st.text_input("ชื่อภาษาอังกฤษ (เช่น Combination Pliers 8-inch)")
            new_name_th = st.text_input("ชื่อภาษาไทย (เช่น คีมปากจระเข้ 8 นิ้ว)")
            new_category = st.selectbox("หมวดหมู่", ["Hand Tools", "Sockets & Wrenches", "Pliers", "Screwdrivers", "Measuring Tools", "Special Tools"])
            new_desc = st.text_area("คำอธิบายเพิ่มเติม")
            
            submit_add = st.form_submit_button("บันทึก Class ใหม่", use_container_width=True)
            if submit_add:
                if not new_key or not new_name_en:
                    st.error("กรุณากรอก Class Key และ ชื่อภาษาอังกฤษ")
                else:
                    try:
                        with get_db() as db:
                            exist = db.query(ToolClass).filter(ToolClass.class_key == new_key.strip()).first()
                            if exist:
                                st.error(f"Class Key '{new_key}' มีอยู่แล้วในระบบ")
                            else:
                                item = ToolClass(
                                    class_key=new_key.strip(),
                                    name_en=new_name_en.strip(),
                                    name_th=new_name_th.strip(),
                                    category=new_category,
                                    description=new_desc.strip(),
                                    is_active=True
                                )
                                db.add(item)
                                st.success(f"เพิ่ม Class '{new_key}' สำเร็จ!")
                                st.rerun()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")

    # TAB 3: Import from Legacy Data
    with tab_import:
        st.markdown("#### 📥 นำเข้ารายการเครื่องมือ (Import Classes)")
        st.write("ระบบจะแปลงรายการอุปกรณ์ 31 รายการจาก `data/data.json` หรือจากไฟล์ JSON ที่อัปโหลด เข้าสู่ตาราง `tool_classes` ใน PostgreSQL อัตโนมัติ")
        
        col_def, col_up = st.columns(2)
        with col_def:
            st.markdown("##### ⚡ นำเข้าจากไฟล์ค่าเริ่มต้น")
            st.caption("อ่านไฟล์ `data/data.json` ที่ระบบเตรียมไว้ (31 รายการเครื่องมือพิเศษ)")
            if st.button("🚀 เริ่มนำเข้าจาก data.json (31 รายการ)", use_container_width=True):
                count = import_classes_from_legacy_data()
                if count > 0:
                    st.success(f"นำเข้าข้อมูลสำเร็จทั้งหมด {count} รายการ!")
                    st.rerun()
                else:
                    st.info("ไม่มีรายการใหม่ที่ต้องนำเข้า (มีครบแล้วในระบบ)")

        with col_up:
            st.markdown("##### 📁 อัปโหลดไฟล์ JSON กำหนดเอง")
            uploaded_json = st.file_uploader("เลือกไฟล์ JSON ที่มีรายการคลาส", type=["json"], key="upload_custom_class_json")
            if uploaded_json is not None:
                if st.button("📥 นำเข้าจากไฟล์ที่อัปโหลด", use_container_width=True):
                    try:
                        content = json.loads(uploaded_json.getvalue().decode("utf-8"))
                        count = import_classes_from_legacy_data(custom_data=content)
                        if count > 0:
                            st.success(f"นำเข้าจากไฟล์อัปโหลดสำเร็จ {count} รายการ!")
                            st.rerun()
                        else:
                            st.info("ไม่มีรายการใหม่ที่ต้องนำเข้า")
                    except Exception as e:
                        st.error(f"รูปแบบไฟล์ JSON ไม่ถูกต้อง: {e}")
