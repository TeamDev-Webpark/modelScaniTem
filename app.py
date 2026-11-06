"""Tool checklist scanner (Streamlit). Run: streamlit run app.py

Pages live in ui/: scanner_page (สแกน), checklist_page (เช็คลิสต์), tray_page (ถาด).
"""
import streamlit as st

st.set_page_config(layout="wide", page_title="ระบบเช็คลิสต์เครื่องมือ")

from ui.checklist_page import render_checklist  # noqa: E402
from ui.common import init_session_state, load_scanner  # noqa: E402
from ui.scanner_page import render_scanner  # noqa: E402
from ui.style import apply_theme, render_header  # noqa: E402
from ui.tray_page import render_tray  # noqa: E402

apply_theme()
init_session_state()
scanner = load_scanner()
render_header()

# ==========================================
# เมนูนำทางแบบแท็บ (Interactive Navigation Tabs)
# ==========================================
total_items = len(st.session_state.detected_list)

st.markdown("<div class='custom-nav-bar'>", unsafe_allow_html=True)
c_nav1, c_nav2, c_nav3 = st.columns(3)

with c_nav1:
    is_scan_active = (st.session_state.get('active_view', 'scan') == 'scan')
    btn_type1 = "primary" if is_scan_active else "secondary"
    if st.button("สแกน", key="nav_btn_scan", type=btn_type1, use_container_width=True):
        st.session_state.active_view = "scan"
        st.rerun()

with c_nav2:
    is_check_active = (st.session_state.get('active_view', 'scan') == 'checklist')
    btn_type2 = "primary" if is_check_active else "secondary"
    label_check = f"เช็คลิสต์ ({total_items})"
    if st.button(label_check, key="nav_btn_check", type=btn_type2, use_container_width=True):
        st.session_state.active_view = "checklist"
        st.rerun()

with c_nav3:
    is_tray_active = (st.session_state.get('active_view', 'scan') == 'tray')
    btn_type3 = "primary" if is_tray_active else "secondary"
    tray_count = len(scanner.list_tray_templates())
    label_tray = f"ถาด ({tray_count})"
    if st.button(label_tray, key="nav_btn_tray", type=btn_type3, use_container_width=True):
        st.session_state.active_view = "tray"
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

active_view = st.session_state.get('active_view', 'scan')
if active_view == 'scan':
    render_scanner()
elif active_view == 'checklist':
    render_checklist()
else:
    render_tray()