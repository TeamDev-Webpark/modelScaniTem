"""หน้า "รายการภาพ": ภาพที่ส่งตรวจและผลการตรวจ พร้อมตัวกรองสถานะ ถาด วันที่ และค้นหา"""
from datetime import date, timedelta

import streamlit as st

from core import inspections as I
from ui import theme
from ui.components import history_ready, no_match, page_title, stat_tiles, submission_card

PAGE_SIZE = 20
STATUS_FILTERS = ["all", "pending", "processing", "done", "needs_review", "failed"]


def render_submissions():
    title = st.empty()
    with title:
        page_title("รายการภาพ", "ภาพที่ส่งเข้าระบบ ผลการตรวจ และเวลาที่ส่ง/ตรวจเสร็จ")
    if not history_ready():
        return

    counts = I.submission_counts()
    stat_tiles([
        ("ทั้งหมด", counts["total"]),
        ("รอตรวจสอบ", counts["pending"], "pending"),
        ("กำลังตรวจสอบ", counts["processing"], "processing"),
        ("ตรวจสอบแล้ว", counts["done"], "done"),
        ("ต้องตรวจสอบเพิ่มเติม", counts["needs_review"] + counts["failed"], "needs_review"),
    ])

    status = st.radio(
        "กรองสถานะ:", STATUS_FILTERS, horizontal=True, label_visibility="collapsed", key="subs_status",
        format_func=lambda k: f"ทั้งหมด ({counts['total']})" if k == "all"
        else f"{theme.status(k)['icon']} {theme.status(k)['label']} ({counts.get(k, 0)})",
    )

    c_tray, c_date = st.columns(2)
    with c_tray:
        trays = [""] + I.available_trays()
        tray = st.selectbox("ประเภทอุปกรณ์ / ถาด", trays, key="subs_tray",
                            format_func=lambda t: "ทุกถาด" if not t else I.tray_label(t))
    with c_date:
        today = date.today()
        rng = st.date_input("ช่วงวันที่ส่ง", value=(today - timedelta(days=30), today), key="subs_dates",
                            format="DD/MM/YYYY")
    d_from, d_to = (rng if isinstance(rng, (tuple, list)) and len(rng) == 2 else (rng[0] if rng else None, None))

    search = st.text_input("ค้นหา", placeholder="พิมพ์หมายเหตุ ชื่อผู้ส่ง หรือชื่อเครื่องมือ...",
                           label_visibility="collapsed", key="subs_search")

    rows = I.list_submissions(status=None if status == "all" else status, tray_id=tray or None,
                              date_from=d_from, date_to=d_to, search=search)

    shown = st.session_state.get("subs_shown", PAGE_SIZE)
    with title:
        page_title("รายการภาพ", "ภาพที่ส่งเข้าระบบ ผลการตรวจ และเวลาที่ส่ง/ตรวจเสร็จ", count=f"{len(rows)} รายการ")
    with st.container(height=620, key="subs_list"):
        if counts["total"] == 0:
            st.info("ยังไม่มีภาพที่ส่งตรวจ ไปที่เมนู ตรวจสอบ > ส่งภาพตรวจถาด เพื่อเริ่ม")
        elif not rows:
            no_match()
        for s in rows[:shown]:
            submission_card(s, key_prefix="list")
        if len(rows) > shown:
            if st.button(f"แสดงเพิ่ม ({len(rows) - shown} รายการ)", use_container_width=True, key="subs_more"):
                st.session_state["subs_shown"] = shown + PAGE_SIZE
                st.rerun()
