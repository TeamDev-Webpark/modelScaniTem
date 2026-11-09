"""Tool checklist scanner (Streamlit). Run: streamlit run app.py

Pages live in ui/ and are grouped in the top menu by ui/nav.py:
  ติดตามผล  ภาพรวม (dashboard_page), รายการภาพ (submissions_page)
  ตรวจสอบ   ส่งภาพตรวจถาด (submit_page), ตรวจรายอุปกรณ์ (manual_check_page)
  จัดการ    ถาดเครื่องมือ (tray_page), สแกนเครื่องมือ (scanner_page), เช็คลิสต์ (checklist_page)
"""
import streamlit as st

st.set_page_config(layout="wide", page_title="ระบบเช็คลิสต์เครื่องมือ", page_icon=":material/handyman:")

from ui import nav  # noqa: E402
from ui.common import init_session_state  # noqa: E402
from ui.style import apply_theme, render_header  # noqa: E402

apply_theme()
init_session_state()
page = st.navigation(nav.build(), position="top")
render_header()
page.run()
