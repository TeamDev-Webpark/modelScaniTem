"""Top navigation for the scanner app (st.navigation): สแกน, ประวัติการสแกน, จัดการกล่อง.
"""
import streamlit as st

_PAGES: dict = {}


def build():
    from ui.history_page import render_history
    from ui.manage_page import render_manage
    from ui.scan_page import render_scan

    _PAGES.update({
        "scan": st.Page(render_scan, title="สแกน", icon=":material/document_scanner:", url_path="scan", default=True),
        "history": st.Page(render_history, title="ประวัติการสแกน", icon=":material/history:", url_path="history"),
        "manage": st.Page(render_manage, title="จัดการกล่อง", icon=":material/inventory_2:", url_path="boxes"),
    })
    return [_PAGES["scan"], _PAGES["history"], _PAGES["manage"]]

