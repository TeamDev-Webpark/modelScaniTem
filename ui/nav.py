"""Grouped top navigation for the scanner app (st.navigation).

Pages call go("<key>") to move to another page instead of setting session state.
"""
import streamlit as st

_PAGES: dict = {}


def build():
    from ui.checklist_page import render_checklist
    from ui.dashboard_page import render_dashboard
    from ui.manual_check_page import render_manual_check
    from ui.scanner_page import render_scanner
    from ui.submissions_page import render_submissions
    from ui.submit_page import render_submit
    from ui.tray_page import render_tray

    _PAGES.update({
        "dashboard": st.Page(render_dashboard, title="ภาพรวม", icon=":material/dashboard:", url_path="dashboard", default=True),
        "submissions": st.Page(render_submissions, title="รายการภาพ", icon=":material/photo_library:", url_path="images"),
        "submit": st.Page(render_submit, title="ส่งภาพตรวจถาด", icon=":material/add_a_photo:", url_path="submit"),
        "manual": st.Page(render_manual_check, title="ตรวจรายอุปกรณ์", icon=":material/fact_check:", url_path="manual"),
        "tray": st.Page(render_tray, title="ถาดเครื่องมือ", icon=":material/inventory_2:", url_path="trays"),
        "scanner": st.Page(render_scanner, title="สแกนเครื่องมือ", icon=":material/center_focus_strong:", url_path="scan"),
        "checklist": st.Page(render_checklist, title="เช็คลิสต์", icon=":material/checklist:", url_path="checklist"),
    })
    return {
        "ติดตามผล": [_PAGES["dashboard"], _PAGES["submissions"]],
        "ตรวจสอบ": [_PAGES["submit"], _PAGES["manual"]],
        "จัดการ": [_PAGES["tray"], _PAGES["scanner"], _PAGES["checklist"]],
    }


def go(key: str):
    st.switch_page(_PAGES[key])
