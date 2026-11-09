"""หน้า "ภาพรวม" (Dashboard): ตัวเลขสรุป รายการที่ต้องดำเนินการ และประวัติล่าสุด"""
from html import escape

import streamlit as st

from core import inspections as I
from ui.components import history_ready, page_title, stat_tiles, status_badge, submission_card
from ui.nav import go


def render_dashboard():
    page_title("ภาพรวม", "จำนวนรายการที่ส่งตรวจ ตรวจแล้ว และรอดำเนินการ")
    if not history_ready():
        return

    c = I.submission_counts()
    latest = I.latest_manual_by_item()
    today = I.manual_counts_today()
    broken = [m for m in latest.values() if m["result"] in ("damaged", "lost")]

    stat_tiles([
        ("ส่งตรวจทั้งหมด", c["total"]),
        ("ตรวจสอบแล้ว", c["done"], "done"),
        ("รอดำเนินการ", c["pending"] + c["processing"], "pending"),
        ("ต้องตรวจสอบเพิ่มเติม", c["needs_review"] + c["failed"], "needs_review"),
    ])
    stat_tiles([
        ("ตรวจรายอุปกรณ์วันนี้", today["total"]),
        ("อุปกรณ์ปกติ (ล่าสุด)", sum(1 for m in latest.values() if m["result"] == "ok"), "ok"),
        ("อุปกรณ์ชำรุด/สูญหาย", len(broken), "lost"),
    ])

    c1, c2 = st.columns(2)
    with c1:
        if st.button("ส่งภาพตรวจถาด", type="primary", use_container_width=True, key="dash_go_submit"):
            go("submit")
    with c2:
        if st.button("ตรวจรายอุปกรณ์", use_container_width=True, key="dash_go_manual"):
            go("manual")

    # ── ต้องดำเนินการ ────────────────────────────────────────────
    todo = (I.list_submissions(status="needs_review", limit=20) + I.list_submissions(status="failed", limit=20)
            + I.list_submissions(status="pending", limit=20))
    page_title("ต้องดำเนินการ", count=f"{len(todo) + len(broken)} รายการ")
    with st.container(height=460, key="dash_todo"):
        if not todo and not broken:
            st.info("ไม่มีรายการที่ต้องดำเนินการ")
        for s in todo:
            submission_card(s, key_prefix="dash")
        for m in sorted(broken, key=lambda m: m["inspected_at"], reverse=True):
            note = f'<div class="ui-meta">📝 {escape(m["note"])}</div>' if m["note"] else ""
            with st.container(border=True, key=f"uicard_dash_man_{m['id']}"):
                st.markdown(
                    f'<div class="ui-item-name">{m["no"]}. {escape(m["name"])}</div>'
                    f'<div style="margin:3px 0;">{status_badge(m["result"])}</div>'
                    f'<div class="ui-meta">{escape(m["part_number"] or "")} · {escape(I.tray_label(m["tray_id"]))}'
                    f' · ตรวจเมื่อ {I.fmt_time(m["inspected_at"])}</div>{note}',
                    unsafe_allow_html=True)

    # ── ประวัติล่าสุด ───────────────────────────────────────────
    page_title("ประวัติการตรวจล่าสุด")
    events = [("sub", s["finished_at"] or s["submitted_at"], s) for s in I.list_submissions(limit=15)]
    events += [("man", m["inspected_at"], m) for m in I.list_manual(limit=15)]
    events.sort(key=lambda e: e[1], reverse=True)
    if not events:
        st.info("ยังไม่มีประวัติการตรวจ")
        return
    rows = []
    for kind, when, x in events[:15]:
        if kind == "sub":
            title = f"ภาพ #{x['id']} · {escape(I.tray_label(x['tray_id']))}"
            badge = status_badge(x["status"])
        else:
            title = f"ตรวจรายอุปกรณ์ · {escape(x['name'])}"
            badge = status_badge(x["result"])
        rows.append(f'<div class="ui-slot-row">{badge} <span class="ui-item-name">{title}</span>'
                    f'<div class="ui-meta">{I.fmt_time(when)}</div></div>')
    with st.container(height=360, key="dash_history"):
        st.markdown("".join(rows), unsafe_allow_html=True)
    if st.button("ดูรายการภาพทั้งหมด", use_container_width=True, key="dash_go_list"):
        go("submissions")
