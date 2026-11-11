"""Shared UI pieces for the scanner app pages.

page_title    หัวข้อหน้า (เส้นแดงด้านซ้าย + คำอธิบาย)
stat_tiles    แถวกล่องตัวเลขสรุป (ขึ้นบรรทัดใหม่เองบนจอเล็ก)
status_badge  ป้ายสถานะสี/ไอคอนตาม ui.theme.STATUS (คืนค่า HTML)
no_match      ข้อความเมื่อตัวกรองไม่เหลือรายการ
show_image / show_compare  หน้าต่างดูภาพใหญ่ / เปรียบเทียบภาพก่อน-หลัง
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


def camera_with_guide(label: str, key: str, tray_id: str, on_change=None):
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
            st.caption("จัดขอบถาดและเครื่องมือให้ตรงกับเส้นไกด์ แล้วกดถ่ายภาพ")
        return st.camera_input(label, key=key, on_change=on_change)


@st.dialog("ดูภาพขนาดใหญ่", width="large")
def show_image(image, caption: str = ""):
    st.image(image, caption=caption or None, use_container_width=True)


@st.dialog("เปรียบเทียบภาพก่อนและหลังตรวจสอบ", width="large")
def show_compare(before, after, caption_before: str = "ก่อนตรวจ (ภาพที่ส่ง)", caption_after: str = "หลังตรวจ (ผลการตรวจ)"):
    mode = st.radio("รูปแบบ", ["คู่กัน", "สลับดู"], horizontal=True, label_visibility="collapsed", key="cmp_mode")
    if mode == "คู่กัน":
        c1, c2 = st.columns(2)
        with c1:
            st.image(before, caption=caption_before, use_container_width=True)
        with c2:
            if after is not None:
                st.image(after, caption=caption_after, use_container_width=True)
            else:
                st.info("ยังไม่มีภาพผลการตรวจ")
    else:
        t1, t2 = st.tabs([caption_before, caption_after])
        with t1:
            st.image(before, use_container_width=True)
        with t2:
            if after is not None:
                st.image(after, use_container_width=True)
            else:
                st.info("ยังไม่มีภาพผลการตรวจ")


# ─────────────────────────────────────────── inspection history pieces

def history_ready() -> bool:
    """Show a warning and return False when the inspection history database is unavailable."""
    from core import inspections as I
    ok, msg = I.ensure_tables()
    if not ok:
        st.warning(f"ยังเชื่อมต่อฐานข้อมูลประวัติการตรวจไม่ได้ จึงบันทึก/แสดงประวัติไม่ได้ในตอนนี้ ({msg[:120]})")
    return ok


def card(key: str, widths=(0.22, 0.53, 0.25)):
    """A bordered card row; returns its columns (thumbnail, body, actions)."""
    box = st.container(border=True, key=f"uicard_{key}")
    with box:
        return st.columns(list(widths), vertical_alignment="center")


def slot_counts_html(s: dict) -> str:
    if s.get("total") is None:
        return ""
    parts = [f'{theme.status(k)["icon"]} {s.get(k) or 0}' for k in ("correct", "missing", "misplaced", "recheck")]
    return f'<div class="ui-meta">{" &nbsp; ".join(parts)} &nbsp;/ {s["total"]} ช่อง</div>'


def run_queue(sub_ids: list[int]):
    """Process queued submissions one by one with progress, then notify."""
    from core import inspections as I
    if not sub_ids:
        return
    bar = st.progress(0.0, text="กำลังตรวจสอบ...")
    results = []
    for i, sid in enumerate(sub_ids, 1):
        bar.progress((i - 1) / len(sub_ids), text=f"กำลังตรวจสอบภาพที่ {i}/{len(sub_ids)} (#{sid})")
        results.append(I.process_submission(sid))
    bar.progress(1.0, text="ตรวจสอบเสร็จแล้ว")
    done = sum(r["status"] == "done" for r in results)
    review = sum(r["status"] in ("needs_review", "failed") for r in results)
    st.toast(f"ตรวจสอบเสร็จ {len(results)} ภาพ: ครบ {done} ภาพ", icon="✅")
    if review:
        st.toast(f"มี {review} ภาพต้องตรวจสอบเพิ่มเติม", icon="⚠️")
    st.session_state["_queue_last_result"] = {"total": len(results), "done": done, "review": review}


def submission_card(s: dict, key_prefix: str = "sub", show_process: bool = True):
    """One submitted tray photo: thumbnail, status, times, counts, its actions and its problem slots."""
    from core import inspections as I
    box = st.container(border=True, key=f"uisub_{key_prefix}_{s['id']}")
    with box:
        c_img, c_body, c_act = st.columns([0.22, 0.53, 0.25], vertical_alignment="center")
        thumb = I.abs_path(s["annotated_path"] or s["image_path"])
        with c_img:
            if thumb and thumb.exists():
                st.image(str(thumb), use_container_width=True)
        with c_body:
            meta = f"ส่ง {I.fmt_time(s['submitted_at'])}"
            if s["finished_at"]:
                meta += f" · เสร็จ {I.fmt_time(s['finished_at'])}"
            extra = ""
            if s.get("error"):
                extra += f'<div class="ui-meta">{escape(s["error"][:160])}</div>'
            if s.get("note"):
                extra += f'<div class="ui-meta">📝 {escape(s["note"])}</div>'
            st.markdown(
                f'<div class="ui-item-name">#{s["id"]} {escape(I.tray_label(s["tray_id"]))}</div>'
                f'<div style="margin:3px 0;">{status_badge(s["status"])}</div>'
                f'<div class="ui-meta">{meta}</div>{slot_counts_html(s)}{extra}',
                unsafe_allow_html=True,
            )
        with c_act:
            if st.button("ดูภาพ", key=f"{key_prefix}_view_{s['id']}", use_container_width=True):
                show_image(str(thumb), f"#{s['id']} {I.tray_label(s['tray_id'])}")
            if s["annotated_path"] and st.button("ก่อน/หลัง", key=f"{key_prefix}_cmp_{s['id']}",
                                                 use_container_width=True, help="เปรียบเทียบภาพก่อนและหลังตรวจ"):
                show_compare(str(I.abs_path(s["image_path"])), str(I.abs_path(s["annotated_path"])))
            if show_process and s["status"] in ("pending", "failed"):
                if st.button("ตรวจ", key=f"{key_prefix}_run_{s['id']}", use_container_width=True):
                    run_queue([s["id"]])
                    st.rerun()
        problems = [x for x in s.get("slots", []) if x.get("status") != "correct"]
        if problems:
            with st.expander(f"รายละเอียดช่องที่พบปัญหา ({len(problems)})"):
                st.markdown("".join(
                    f'<div class="ui-slot-row">{status_badge(x["status"])} '
                    f'<span class="ui-item-name">#{x["slot_number"]} {escape(x.get("item_name") or "")}</span>'
                    f'<div class="ui-meta">{escape(x.get("reason") or "")}</div></div>'
                    for x in problems), unsafe_allow_html=True)
