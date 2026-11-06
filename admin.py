"""
Admin Backend Dashboard for YOLO Tool Scanner.
Run with: streamlit run admin.py
"""
import streamlit as st

# Configure page layout
st.set_page_config(
    page_title="YOLO Tool Scanner — Admin Backend",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

from core.config import DATABASE_URL, ADMIN_DEFAULT_USER
from core.db import check_connection, init_db, get_db
from core.models_db import ToolClass, TrainingImage, TrainedModel, TrayTemplate
from admin_modules.auth import (
    init_auth_session,
    ensure_default_admin,
    render_login_form,
    logout_user
)
from admin_modules.class_manager import render_class_manager
from admin_modules.image_collector import render_image_collector
from admin_modules.dataset_exporter import render_dataset_exporter
from admin_modules.model_manager import render_model_manager
from admin_modules.tray_manager import render_tray_manager
from admin_modules.scanner_tester import render_scanner_tester


def render_dashboard():
    """Renders main overview metrics and quick actions."""
    st.markdown("## 📊 ภาพรวมระบบ (System Overview)")
    st.write("สถานะชุดข้อมูล โมเดลการเรียนรู้ และข้อมูลถาดอุปกรณ์ปัจจุบัน")

    try:
        with get_db() as db:
            class_count = db.query(ToolClass).count()
            img_count = db.query(TrainingImage).count()
            model_count = db.query(TrainedModel).count()
            tray_count = db.query(TrayTemplate).count()
            active_model = db.query(TrainedModel).filter(TrainedModel.is_active == True).first()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🏷️ Tool Classes", f"{class_count} คลาส")
        with col2:
            st.metric("📸 Training Images", f"{img_count} รูป")
        with col3:
            st.metric("🧠 โมเดลในระบบ", f"{model_count} โมเดล")
        with col4:
            st.metric("🍱 แบบถาดอุปกรณ์", f"{tray_count} แบบ")

        st.markdown("---")
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown("### 🏆 โมเดล Active ปัจจุบัน")
            if active_model:
                st.success(f"**เวอร์ชัน:** {active_model.version} ({active_model.model_type})")
                st.write(f"**Path:** `{active_model.model_path}`")
                if active_model.notes:
                    st.caption(f"หมายเหตุ: {active_model.notes}")
            else:
                st.warning("ยังไม่มีโมเดลที่เปิดใช้งาน (สามารถเปิดใช้งานได้ที่เมนู 'จัดการโมเดล')")

        with c_right:
            st.markdown("### ⚡ ขั้นตอนการทำงาน (Workflow)")
            st.markdown(
                """
                1. **กำหนด Class**: เพิ่มหรือนำเข้าประเภทเครื่องมือในเมนู *จัดการ Class*
                2. **รวบรวมภาพ**: อัปโหลดรูปภาพเครื่องมือและถาดในเมนู *เก็บรูปภาพ Training*
                3. **Label & Augment**: ใช้ Roboflow จัดการ Label และสร้าง Augmentation
                4. **เทรนบน Colab**: ใช้ไฟล์ Notebook รันเทรน YOLOv8
                5. **อัปโหลดโมเดล**: นำไฟล์ `best.pt` มาใส่ในเมนู *จัดการโมเดล*
                """
            )
    except Exception as e:
        st.error(f"ไม่สามารถโหลดสถิติภาพรวม: {e}")


def main():
    # Initialize authentication state
    init_auth_session()

    # Sidebar: DB Status & Branding
    st.sidebar.title("🛠️ YOLO Admin")
    st.sidebar.caption("Tool Scanner Backend System")

    # DB Connection Status Check
    is_connected, db_msg = check_connection()
    if is_connected:
        st.sidebar.success("🟢 PostgreSQL เชื่อมต่อสำเร็จ")
        # Ensure database tables and default admin exist
        try:
            init_db()
            ensure_default_admin()
        except Exception as e:
            st.sidebar.warning(f"DB Init note: {e}")
    else:
        st.sidebar.error("🔴 ไม่สามารถเชื่อมต่อ PostgreSQL")
        with st.sidebar.expander("รายละเอียดข้อผิดพลาด"):
            st.caption(db_msg)
            st.caption(f"URL: `{DATABASE_URL}`")

    # Authentication guard
    if not st.session_state.authenticated:
        if not is_connected:
            st.warning("⚠️ ไม่สามารถเชื่อมต่อ PostgreSQL ได้ในขณะนี้ กรุณาตรวจสอบว่า PostgreSQL Service กำลังทำงานอยู่ และการตั้งค่าในไฟล์ `.env` ถูกต้อง")
        render_login_form()
        return

    # User Profile & Logout in Sidebar
    user = st.session_state.user
    st.sidebar.markdown(f"👤 ผู้ใช้: **{user['username']}** ({user['role']})")
    if st.sidebar.button("🚪 ออกจากระบบ (Logout)", use_container_width=True):
        logout_user()

    st.sidebar.markdown("---")
    menu_choice = st.sidebar.radio(
        "เมนูหลัก",
        [
            "📊 ภาพรวมระบบ (Overview)",
            "🔍 ทดสอบการสแกน (Playground)",
            "🏷️ จัดการ Class เครื่องมือ (Classes)",
            "📸 เก็บรูปภาพ Training (Images)",
            "📦 ส่งออกชุดข้อมูล (Export)",
            "🧠 จัดการโมเดล (Models)",
            "🍱 จัดการถาดอุปกรณ์ (Trays)",
            "⚙️ การเชื่อมต่อฐานข้อมูล (Settings)"
        ]
    )

    # Route based on menu selection
    if menu_choice.startswith("📊"):
        render_dashboard()
    elif menu_choice.startswith("🔍"):
        render_scanner_tester()
    elif menu_choice.startswith("🏷️"):
        render_class_manager()
    elif menu_choice.startswith("📸"):
        render_image_collector(user)
    elif menu_choice.startswith("📦"):
        render_dataset_exporter()
    elif menu_choice.startswith("🧠"):
        render_model_manager(user)
    elif menu_choice.startswith("🍱"):
        render_tray_manager(user)
    elif menu_choice.startswith("⚙️"):
        st.markdown("### ⚙️ การตั้งค่าและฐานข้อมูล (Database Settings)")
        st.write(f"**Database URL ปัจจุบัน:** `{DATABASE_URL}`")
        st.write(f"**สถานะ:** {'🟢 ปกติ' if is_connected else '🔴 ขัดข้อง'}")
        if is_connected:
            st.success("ฐานข้อมูลพร้อมใช้งานและ Schema ตารางทั้ง 7 ถูกตรวจสอบเรียบร้อย")
        else:
            st.error(f"ข้อความจาก Driver: {db_msg}")


if __name__ == "__main__":
    main()
