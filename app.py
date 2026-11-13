"""Tool checklist scanner (Streamlit). Run: streamlit run app.py

Pages live in ui/, menu in ui/nav.py:
  สแกน            scan_page    (หน้าหลัก: อุปกรณ์ในกล่อง / อุปกรณ์ชิ้นเดี่ยว)
  ประวัติการสแกน    history_page
  จัดการกล่อง       manage_page
"""
import streamlit as st

st.set_page_config(layout="wide", page_title="ระบบเช็คลิสต์เครื่องมือ", page_icon=":material/handyman:")

from ui import nav  # noqa: E402
from ui.style import apply_theme, render_header  # noqa: E402

apply_theme()
page = st.navigation(nav.build(), position="top")
render_header()
page.run()
