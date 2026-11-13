"""หน้า "ประวัติการสแกน": วันเวลา ประเภทการสแกน ผล และรายละเอียดย้อนหลังของทุกการสแกน"""
from datetime import date, timedelta
from html import escape

import streamlit as st

from core import inspections as I
from core import scan_items as S
from ui import theme
from ui.components import history_ready, item_list, no_match, page_title, stat_tiles, status_badge

PAGE_SIZE = 20


def _counts_html(rec: dict) -> str:
    def badge(key, n):
        return status_badge(key, f"{theme.label(key)} {n or 0}")
    parts = [badge("present", rec["correct"]), badge("absent", rec["missing"])]
    if rec["scan_type"] == "box":
        parts.append(badge("misplaced", rec["misplaced"]))
    if rec["recheck"]:
        parts.append(badge("recheck" if rec["scan_type"] == "box" else "unchecked", rec["recheck"]))
    if rec["manual_count"]:
        parts.append(badge("manual", rec["manual_count"]))
    return " ".join(parts)


@st.dialog("รายละเอียดการสแกน", width="large")
def _detail(rec: dict):
    st.markdown(
        f'<div class="ui-item-name">{escape(I.SCAN_TYPES.get(rec["scan_type"], ""))} · {escape(I.tray_label(rec["tray_id"]))}</div>'
        f'<div class="ui-meta">สแกนเมื่อ {I.fmt_time(rec["submitted_at"])}'
        f'{" · โดย " + escape(rec["submitted_by"]) if rec["submitted_by"] else ""}</div>'
        f'<div style="margin:4px 0;">{status_badge(rec["status"])} {_counts_html(rec)}</div>',
        unsafe_allow_html=True)
    if rec.get("error"):
        st.warning(rec["error"])
    photo, result = I.abs_path(rec["image_path"]), I.abs_path(rec["annotated_path"])
    c1, c2 = st.columns(2)
    with c1:
        if photo and photo.exists():
            st.image(str(photo), caption="ภาพที่ถ่าย", width="stretch")
    with c2:
        if result and result.exists():
            st.image(str(result), caption="ผลสแกน", width="stretch")
    items = S.items_from_record(rec)
    if items:
        item_list(items, key=f"hist_{rec['id']}", editable=False, scan_type=rec["scan_type"],
                  prefer="slot" if rec["scan_type"] == "box" else "product", height=420)
    with st.expander("ลบการสแกนนี้"):
        st.caption("ลบทั้งข้อมูลและไฟล์ภาพ กู้คืนไม่ได้")
        if st.button("ลบถาวร", key=f"hist_del_{rec['id']}"):
            I.delete_submission(rec["id"])
            st.toast(f"ลบการสแกน #{rec['id']} แล้ว", icon="🗑️")
            st.rerun()


def _card(rec: dict):
    with st.container(border=True, key=f"uihist_{rec['id']}"):
        c_img, c_body, c_act = st.columns([0.2, 0.62, 0.18], vertical_alignment="center")
        pic = I.abs_path(rec["annotated_path"] or rec["image_path"])
        with c_img:
            if pic and pic.exists():
                st.image(str(pic), width="stretch")
        with c_body:
            by = f' · {escape(rec["submitted_by"])}' if rec["submitted_by"] else ""
            st.markdown(
                f'<div class="ui-item-name">{I.fmt_time(rec["submitted_at"])}</div>'
                f'<div class="ui-meta">{escape(I.SCAN_TYPES.get(rec["scan_type"], ""))} · '
                f'{escape(I.tray_label(rec["tray_id"]))}{by}</div>'
                f'<div style="margin-top:4px;">{status_badge(rec["status"])} {_counts_html(rec)}</div>',
                unsafe_allow_html=True)
        with c_act:
            if st.button("ดู", key=f"hist_view_{rec['id']}", width="stretch"):
                _detail(rec)


def _first_page():
    st.session_state["hist_shown"] = PAGE_SIZE


def render_history():
    title = st.empty()
    with title:
        page_title("ประวัติการสแกน", "วันเวลา ประเภทการสแกน และผลของทุกการสแกน")
    if not history_ready():
        return

    stats = I.history_stats()
    stat_tiles([
        ("สแกนวันนี้", stats["today"]),
        ("ทั้งหมด", stats["total"]),
        (theme.label("done"), stats["complete"], "done"),
        (f'มีรายการ{theme.label("absent")}', stats["with_absent"], "absent"),
        (f'มีรายการ{theme.label("misplaced")}', stats["with_misplaced"], "misplaced"),
    ])

    c_type, c_target, c_date = st.columns(3)
    with c_type:
        scan_type = st.selectbox("ประเภทการสแกน", ["", *I.SCAN_TYPES], key="hist_type", on_change=_first_page,
                                 format_func=lambda k: I.SCAN_TYPES.get(k, "ทุกประเภท"))
    with c_target:
        targets = [""] + (I.available_trays() if scan_type != "loose" else []) + \
                  (list(S.LOOSE_SETS) if scan_type != "box" else [])
        target = st.selectbox("กล่อง / ชุด", targets, key=f"hist_target_{scan_type}", on_change=_first_page,
                              format_func=lambda t: I.tray_label(t) if t else "ทั้งหมด")
    with c_date:
        today = date.today()
        rng = st.date_input("ช่วงวันที่", value=(today - timedelta(days=30), today), key="hist_dates",
                            format="DD/MM/YYYY", on_change=_first_page)
    d_from, d_to = (rng if isinstance(rng, (tuple, list)) and len(rng) == 2 else (rng[0] if rng else None, None))
    search = st.text_input("ค้นหา", placeholder="ชื่อผู้สแกน หรือชื่อเครื่องมือ", key="hist_search",
                           label_visibility="collapsed", on_change=_first_page)

    query = dict(scan_type=scan_type or None, tray_id=target or None, date_from=d_from, date_to=d_to, search=search)
    total = I.count_submissions(**query)
    shown = st.session_state.get("hist_shown", PAGE_SIZE)
    rows = I.list_submissions(limit=shown, **query)
    with title:
        page_title("ประวัติการสแกน", "วันเวลา ประเภทการสแกน และผลของทุกการสแกน", count=f"{total} ครั้ง")

    if stats["total"] == 0:
        st.info("ยังไม่มีประวัติการสแกน ไปที่เมนู สแกน เพื่อเริ่ม")
        return
    if not rows:
        no_match()
    for rec in rows:
        _card(rec)
    if total > shown and st.button(f"แสดงเพิ่ม ({total - shown} ครั้ง)", width="stretch", key="hist_more"):
        st.session_state["hist_shown"] = shown + PAGE_SIZE
        st.rerun()
