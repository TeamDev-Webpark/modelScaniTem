"""หน้า "ตรวจรายอุปกรณ์": เลือกอุปกรณ์จาก checklist ตรวจเอง บันทึกผล แนบภาพ และดูประวัติ"""
from html import escape

import streamlit as st

from core import inspections as I
from ui import theme
from ui.common import load_image_with_exif
from ui.components import history_ready, no_match, page_title, stat_tiles, status_badge

RESULT_FILTERS = ["all", "unchecked", "ok", "damaged", "lost"]
RESULT_CHOICES = ["ok", "damaged", "lost"]


@st.dialog("ประวัติการตรวจ", width="large")
def _history_dialog(item: dict):
    st.markdown(f'<div class="ui-item-name">{escape(item["name"])}</div>'
                f'<div class="ui-meta">{escape(item["part_number"])} · {escape(I.tray_label(item["tray_id"]))}</div>',
                unsafe_allow_html=True)
    rows = I.list_manual(item_key=item["key"])
    if not rows:
        st.info("ยังไม่เคยตรวจอุปกรณ์นี้")
        return
    for r in rows:
        with st.container(border=True):
            c1, c2 = st.columns([0.7, 0.3], vertical_alignment="center")
            with c1:
                who = f" · {escape(r['inspected_by'])}" if r["inspected_by"] else ""
                note = f'<div class="ui-meta">📝 {escape(r["note"])}</div>' if r["note"] else ""
                st.markdown(f'{status_badge(r["result"])}<div class="ui-meta">{I.fmt_time(r["inspected_at"])}{who}</div>{note}',
                            unsafe_allow_html=True)
            with c2:
                p = I.abs_path(r["attachment_path"])
                if p and p.exists():
                    st.image(str(p), use_container_width=True)


def _selected() -> set:
    return st.session_state.setdefault("manual_selected", set())


def _toggle(key: str):
    sel = _selected()
    if st.session_state.get(f"man_chk_{key}"):
        sel.add(key)
    else:
        sel.discard(key)


def _render_form(catalog_by_key: dict):
    keys = [k for k in st.session_state["manual_working"] if k in catalog_by_key]
    page_title("กรอกผลการตรวจ", "เลือกผลของแต่ละอุปกรณ์ เพิ่มหมายเหตุหรือแนบภาพได้", count=f"{len(keys)} รายการ")
    by = st.text_input("ชื่อผู้ตรวจ (ไม่บังคับ)", placeholder="พิมพ์ชื่อผู้ตรวจ", key="manual_by")
    with st.form("manual_form", border=False):
        for k in keys:
            it = catalog_by_key[k]
            with st.container(border=True, key=f"man_form_{k.replace(':', '_')}"):
                st.markdown(f'<div class="ui-item-name">{it["no"]}. {escape(it["name"])}</div>'
                            f'<div class="ui-meta">{escape(it["part_number"])} · {escape(I.tray_label(it["tray_id"]))}</div>',
                            unsafe_allow_html=True)
                st.radio("ผลการตรวจ", RESULT_CHOICES, horizontal=True, label_visibility="collapsed",
                         key=f"man_res_{k}", format_func=lambda r: f"{theme.status(r)['icon']} {theme.status(r)['label']}")
                st.text_input("หมายเหตุ", placeholder="พิมพ์หมายเหตุ (ไม่บังคับ)", label_visibility="collapsed",
                              key=f"man_note_{k}")
                st.file_uploader("แนบภาพ (ไม่บังคับ)", type=["jpg", "jpeg", "png"], key=f"man_file_{k}")
        c_save, c_cancel = st.columns(2)
        with c_save:
            save = st.form_submit_button("บันทึกผลทั้งหมด", type="primary", use_container_width=True)
        with c_cancel:
            cancel = st.form_submit_button("ยกเลิก", use_container_width=True)
    if cancel:
        st.session_state.pop("manual_working", None)
        st.rerun()
    if save:
        problems = 0
        for k in keys:
            res = st.session_state.get(f"man_res_{k}", "ok")
            f = st.session_state.get(f"man_file_{k}")
            img = load_image_with_exif(f, force_landscape=False) if f else None
            I.save_manual(catalog_by_key[k], res, note=st.session_state.get(f"man_note_{k}", ""),
                          attachment=img, inspected_by=by)
            problems += res != "ok"
        st.session_state.pop("manual_working", None)
        _selected().clear()
        for k in list(st.session_state):
            if str(k).startswith("man_chk_"):
                del st.session_state[k]
        st.toast(f"บันทึกผลตรวจ {len(keys)} รายการแล้ว", icon="✅")
        if problems:
            st.toast(f"พบ {problems} รายการชำรุด/สูญหาย ต้องดำเนินการเพิ่มเติม", icon="⚠️")
        st.rerun()


def render_manual_check():
    catalog = I.equipment_catalog()
    page_title("ตรวจรายอุปกรณ์", "เลือกอุปกรณ์ที่ต้องการตรวจเอง แล้วกดเริ่มตรวจ", count=f"{len(catalog)} รายการ")
    if not history_ready():
        return
    by_key = {c["key"]: c for c in catalog}

    if st.session_state.get("manual_working"):
        _render_form(by_key)
        return

    latest = I.latest_manual_by_item()
    today = I.manual_counts_today()
    res_of = {c["key"]: (latest[c["key"]]["result"] if c["key"] in latest else "unchecked") for c in catalog}
    n = {k: sum(1 for v in res_of.values() if v == k) for k in RESULT_FILTERS[1:]}
    stat_tiles([
        ("ทั้งหมด", len(catalog)),
        ("ตรวจวันนี้", today["total"]),
        ("ปกติ (ล่าสุด)", n["ok"], "ok"),
        ("ชำรุด/สูญหาย", n["damaged"] + n["lost"], "lost"),
    ])

    f_res = st.radio(
        "กรองสถานะ:", RESULT_FILTERS, horizontal=True, label_visibility="collapsed", key="manual_filter",
        format_func=lambda k: f"ทั้งหมด ({len(catalog)})" if k == "all"
        else f"{theme.status(k)['icon']} {theme.status(k)['label']} ({n[k]})",
    )
    trays = [""] + sorted({c["tray_id"] or "-" for c in catalog})
    f_tray = st.selectbox("ประเภทอุปกรณ์ / ถาด", trays, key="manual_tray",
                          format_func=lambda t: "ทุกถาด" if not t else ("ไม่มีช่องในถาด" if t == "-" else I.tray_label(t)))
    kw = st.text_input("ค้นหา", placeholder="พิมพ์ชื่อ รหัสอะไหล่ หรือลำดับ...", label_visibility="collapsed",
                       key="manual_search").strip().lower()

    rows = []
    for c in catalog:
        if f_res != "all" and res_of[c["key"]] != f_res:
            continue
        if f_tray and (c["tray_id"] or "-") != f_tray:
            continue
        if kw and kw not in c["name"].lower() and kw not in c["part_number"].lower() and kw != str(c["no"]):
            continue
        rows.append(c)

    sel = _selected()
    if st.button(f"เริ่มตรวจ {len(sel)} รายการ", type="primary", use_container_width=True,
                 disabled=not sel, key="manual_start"):
        st.session_state["manual_working"] = [c["key"] for c in catalog if c["key"] in sel]
        st.rerun()
    c_all, c_none = st.columns(2)
    with c_all:
        if st.button(f"เลือกที่แสดง ({len(rows)})", use_container_width=True, key="manual_sel_all"):
            for c in rows:
                sel.add(c["key"])
                st.session_state[f"man_chk_{c['key']}"] = True
            st.rerun()
    with c_none:
        if st.button("ล้างที่เลือก", use_container_width=True, key="manual_sel_none", disabled=not sel):
            sel.clear()
            for k in list(st.session_state):
                if str(k).startswith("man_chk_"):
                    del st.session_state[k]
            st.rerun()

    with st.container(height=560, key="manual_list"):
        if not catalog:
            st.info("ยังไม่มีรายการอุปกรณ์ใน checklist")
        elif not rows:
            no_match()
        for c in rows:
            k = c["key"]
            with st.container(border=True, key=f"uiman_{k.replace(':', '_')}"):
                c1, c2, c3 = st.columns([0.1, 0.65, 0.25], vertical_alignment="center")
                with c1:
                    st.session_state.setdefault(f"man_chk_{k}", k in sel)
                    st.checkbox(f"เลือก {c['name']}", key=f"man_chk_{k}", label_visibility="collapsed",
                                on_change=_toggle, args=(k,))
                with c2:
                    last = latest.get(k)
                    when = f" · ตรวจล่าสุด {I.fmt_time(last['inspected_at'])}" if last else ""
                    st.markdown(
                        f'<div class="ui-item-name">{c["no"]}. {escape(c["name"])}</div>'
                        f'<div class="ui-meta">{escape(c["part_number"])} · {escape(I.tray_label(c["tray_id"]) if c["tray_id"] else "ไม่มีช่องในถาด")}{when}</div>'
                        f'<div style="margin:3px 0;">{status_badge(res_of[k])}</div>',
                        unsafe_allow_html=True)
                with c3:
                    if st.button("ประวัติ", key=f"man_hist_{k}", use_container_width=True):
                        _history_dialog(c)
