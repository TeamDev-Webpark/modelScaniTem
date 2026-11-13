"""Shared UI pieces for the scanner app pages.

page_title    หัวข้อหน้า (เส้นแดงด้านซ้าย + คำอธิบาย)
stat_tiles    แถวกล่องตัวเลขสรุป (ขึ้นบรรทัดใหม่เองบนจอเล็ก)
status_badge  ป้ายสถานะสี/ไอคอนตาม ui.theme.STATUS (คืนค่า HTML)
no_match      ข้อความเมื่อตัวกรองไม่เหลือรายการ
show_image    หน้าต่างดูภาพใหญ่
camera_with_guide  กล้องพร้อมเส้นไกด์ของกล่อง
item_list     รายการอุปกรณ์ (รูป ชื่อ สถานะ ปุ่ม มี/ไม่มี) ใช้ทั้งหน้าสแกนและหน้าประวัติ
"""
from html import escape
from typing import Iterable, Optional

import streamlit as st

from ui import theme


def page_title(title: str, subtitle: str = "", count: Optional[str] = None):
    sub = f'<p class="ui-page-sub">{escape(subtitle)}</p>' if subtitle else ""
    pill = f'<span class="ui-pill">{escape(count)}</span>' if count else ""
    st.markdown(
        f'<div class="ui-page-title"><div><h3>{escape(title)}</h3>{sub}</div>{pill}</div>',
        unsafe_allow_html=True,
    )


def stat_tiles(tiles: Iterable[tuple]):
    """tiles: (label, value) or (label, value, status_key). The first tile without a status is dark."""
    parts = []
    for i, t in enumerate(tiles):
        label, value = t[0], t[1]
        key = t[2] if len(t) > 2 else None
        if key:
            s = theme.status(key)
            style = f"background:{s['bg']};border:1.5px solid {s['border']};color:{s['fg']};"
            label = f"{s['icon']} {label}"
        elif i == 0:
            style = f"background:{theme.TEXT};color:{theme.BACKGROUND};border:1.5px solid {theme.TEXT};"
        else:
            style = f"background:{theme.SURFACE};color:{theme.TEXT};border:1.5px solid {theme.BORDER};"
        parts.append(
            f'<div class="ui-tile" style="{style}"><div class="ui-tile-label">{escape(str(label))}</div>'
            f'<div class="ui-tile-value">{escape(str(value))}</div></div>'
        )
    st.markdown(f'<div class="ui-tiles">{"".join(parts)}</div>', unsafe_allow_html=True)


def status_badge(key: str, text: Optional[str] = None) -> str:
    s = theme.status(key)
    return (f'<span class="ui-badge" style="background:{s["bg"]};color:{s["fg"]};border:1px solid {s["border"]};">'
            f'{s["icon"]} {escape(text or s["label"])}</span>')


def no_match(text: str = "ไม่พบรายการที่ตรงกับเงื่อนไข"):
    st.markdown(f'<p class="ui-no-match">{escape(text)}</p>', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _camera_guide_uri(tray_id: str) -> str:
    """เส้นไกด์ของถาด (PNG โปร่งใส) เป็น data URI สำหรับวางทับภาพกล้อง; คืน "" ถ้าไม่มีเทมเพลต"""
    import base64
    import json

    import cv2

    from core.config import TRAY_TEMPLATES_DIR
    from scan_workflow import generate_camera_guide

    path = TRAY_TEMPLATES_DIR / f"{tray_id}.json"
    if not path.exists():
        return ""
    guide = generate_camera_guide(json.loads(path.read_text(encoding="utf-8")))
    ok, buf = cv2.imencode(".png", guide)
    return f"data:image/png;base64,{base64.b64encode(buf.tobytes()).decode()}" if ok else ""


def camera_with_guide(label: str, key: str, tray_id: str):
    """st.camera_input ที่มีเส้นไกด์ช่องเครื่องมือของถาดวางทับภาพกล้องสดขณะเล็ง (ไม่ติดไปในภาพที่ถ่าย)"""
    uri = _camera_guide_uri(tray_id) if tray_id else ""
    show = bool(uri) and st.toggle("แสดงเส้นไกด์บนกล้อง", value=True, key=f"{key}_guide")
    with st.container(key=f"uicam_{key}"):
        if show:
            box = f'.st-key-uicam_{key} [data-testid="stCameraInputWebcamStyledBox"]'
            st.markdown(
                f'<style>{box}{{position:relative;}}'
                f'{box}:has(video)::after{{content:"";position:absolute;inset:0;pointer-events:none;'
                f'background:url("{uri}") center / contain no-repeat;}}</style>',
                unsafe_allow_html=True)
            st.caption("จัดขอบกล่องและเครื่องมือให้ตรงกับเส้นไกด์ แล้วกดถ่ายภาพ")
        return st.camera_input(label, key=key)


@st.dialog("ดูภาพขนาดใหญ่", width="large")
def show_image(image, caption: str = ""):
    st.image(image, caption=caption or None, width="stretch")


# ─────────────────────────────────────────── inspection history pieces

def history_ready() -> bool:
    """Show a warning and return False when the inspection history database is unavailable."""
    from core import inspections as I
    ok, msg = I.ensure_tables()
    if not ok:
        st.warning("เชื่อมต่อฐานข้อมูลประวัติการสแกนไม่ได้ จึงบันทึกและแสดงประวัติไม่ได้ในตอนนี้ ลองใหม่ภายหลัง")
    return ok


# ─────────────────────────────────────────── item list (scan page and history)

CHOICES = ("present", "absent")
FILTERS = {
    "all": "ทั้งหมด",
    "absent": theme.label("absent"),
    "misplaced": theme.label("misplaced"),
    "pending": f'{theme.label("recheck")} / {theme.label("unchecked")}',
    "manual": theme.label("manual"),
}


def item_summary(items: list[dict], scan_type: str):
    """Tiles with the count of each status (misplaced only exists in a box scan)."""
    from core.scan_items import count_statuses
    c = count_statuses(items)
    L = theme.label
    tiles = [(L("present"), c["present"], "present"), (L("absent"), c["absent"], "absent")]
    if scan_type == "box":
        waiting = "unchecked" if c["unchecked"] else "recheck"  # before a scan nothing is checked yet
        tiles += [(L("misplaced"), c["misplaced"], "misplaced"), (L(waiting), c["recheck"] + c["unchecked"], waiting)]
    else:
        tiles += [(L("unchecked"), c["unchecked"] + c["recheck"], "unchecked")]
    tiles.append((L("manual"), c["manual"], "manual"))
    stat_tiles(tiles)


def _matches(item: dict, flt: str, kw: str) -> bool:
    if flt == "absent" and item["status"] != "absent":
        return False
    if flt == "misplaced" and item["status"] != "misplaced":
        return False
    if flt == "pending" and item["status"] not in ("recheck", "unchecked"):
        return False
    if flt == "manual" and not item.get("manual"):
        return False
    if kw:
        hay = f'{item.get("no") or ""} {item.get("name") or ""} {item.get("part_number") or ""}'.lower()
        return kw in hay
    return True


def _on_choice(items: list[dict], idx: int, widget_key: str):
    from core.scan_items import set_status
    value = st.session_state.get(widget_key)
    item = items[idx]
    set_status(item, value if value in CHOICES else item["auto_status"])


def item_list(items: list[dict], key: str, editable: bool = True, prefer: str = "product",
              scan_type: str = "box", height: int = 520):
    """Every item with its picture, name, part number, status and (editable) the มี / ไม่มี choice.

    `items` is changed in place when a person picks มี / ไม่มี; picking the same again clears the
    choice and the item goes back to what the scan said.
    """
    from core.scan_items import thumbnail
    item_summary(items, scan_type)
    filters = [f for f in FILTERS if scan_type == "box" or f != "misplaced"]
    c_f, c_s = st.columns([0.6, 0.4], vertical_alignment="bottom")
    with c_f:
        flt = st.pills("แสดง", filters, format_func=FILTERS.get, default="all", key=f"{key}_filter",
                       label_visibility="collapsed") or "all"
    with c_s:
        kw = st.text_input("ค้นหา", placeholder="ชื่อ รหัสอะไหล่ หรือลำดับ", key=f"{key}_search",
                           label_visibility="collapsed").strip().lower()
    shown = [(i, it) for i, it in enumerate(items) if _matches(it, flt, kw)]
    with st.container(height=height, key=f"{key}_rows"):
        if not shown:
            no_match()
        for i, it in shown:
            with st.container(border=True, key=f"uiitem_{key}_{i}"):
                c_img, c_body, c_act = st.columns([0.16, 0.54, 0.30] if editable else [0.16, 0.84, 0.001],
                                                  vertical_alignment="center")
                with c_img:
                    pic = thumbnail(it, prefer)
                    if pic:
                        st.image(pic, width="stretch")
                with c_body:
                    no = f'{it["no"]}. ' if it.get("no") else ""
                    where = f' · ช่อง {it["slot"]}' if scan_type == "box" and it.get("slot") else ""
                    badges = status_badge(it["status"]) + (" " + status_badge("manual") if it.get("manual") else "")
                    note = ""
                    if it.get("manual"):
                        note = f'<div class="ui-meta">ระบบสแกนได้: {theme.label(it["auto_status"])}</div>'
                    st.markdown(
                        f'<div class="ui-item-name">{escape(no + (it.get("name") or ""))}</div>'
                        f'<div class="ui-meta">{escape(it.get("part_number") or "")}{where}</div>'
                        f'<div style="margin-top:3px;">{badges}</div>{note}',
                        unsafe_allow_html=True)
                if editable:
                    with c_act:
                        wkey = f"{key}_pick_{i}"
                        st.segmented_control(
                            f"ผลของ {it.get('name')}", CHOICES, format_func=theme.label,
                            default=it["status"] if it["status"] in CHOICES else None, key=wkey,
                            label_visibility="collapsed", on_change=_on_choice, args=(items, i, wkey))
