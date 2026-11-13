"""หน้า "สแกน" (หน้าหลัก): สแกนอุปกรณ์ในกล่อง หรืออุปกรณ์ชิ้นเดี่ยว

ซ้าย: ถ่าย/อัปโหลดภาพ แล้วดูผลสแกน · ขวา: รายการอุปกรณ์พร้อมรูป กดแก้ มี/ไม่มี ได้ แล้วบันทึกลงประวัติ
"""
import cv2
import streamlit as st

from core import inspections as I
from core import scan_items as S
from core.config import TRAY_REFS_DIR
from ui import theme
from ui.common import load_image_with_exif
from ui.components import camera_with_guide, history_ready, item_list, page_title, show_image

MODES = {"box": "อุปกรณ์ในกล่อง", "loose": "อุปกรณ์ชิ้นเดี่ยว"}
METHODS = ("ถ่ายภาพ", "อัปโหลดภาพ")


# ─────────────────────────────────────────── state

def _state(mode: str, target: str) -> dict:
    """The scan in progress. A new one starts when the mode or the box/set changes."""
    s = st.session_state.get("scan")
    if not s or s["mode"] != mode or s["target"] != target:
        s = {"mode": mode, "target": target, "round": (s or {}).get("round", 0) + 1,
             "items": S.box_items(target) if mode == "box" else S.loose_items(target),
             "photo": None, "annotated": None, "message": "", "photos": [], "seen_ids": set()}
        if mode == "box":
            for it in s["items"]:
                it["auto_status"] = it["status"] = "unchecked"
        st.session_state["scan"] = s
    return s


def _restart(s: dict):
    """Clear the photos and results, keep the mode and box/set."""
    st.session_state.pop("scan", None)
    _state(s["mode"], s["target"])


@st.cache_resource(show_spinner=False)
def _aggregator(tray_id: str):
    from scan_workflow import ScanAggregator
    from core.inspections import _load_template
    agg = ScanAggregator(tray_refs_dir=str(TRAY_REFS_DIR))
    agg.setup(_load_template(tray_id), reference_image=cv2.imread(str(TRAY_REFS_DIR / f"{tray_id}.jpg")))
    return agg


# ─────────────────────────────────────────── left: photo and result

def _box_left(s: dict):
    if s["annotated"] is not None or s["message"]:
        if s["message"]:
            st.warning(s["message"])
        t_res, t_orig = st.tabs(["ผลสแกน", "ภาพต้นฉบับ"])
        with t_res:
            st.image(s["annotated"] if s["annotated"] is not None else s["photo"], channels="BGR",
                     width="stretch")
        with t_orig:
            st.image(s["photo"], channels="BGR", width="stretch")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("ดูภาพใหญ่", width="stretch", key="scan_zoom"):
                show_image(cv2.cvtColor(s["annotated"] if s["annotated"] is not None else s["photo"],
                                        cv2.COLOR_BGR2RGB), I.tray_label(s["target"]))
        with c2:
            if st.button("ถ่ายภาพใหม่", width="stretch", key="scan_again"):
                _restart(s)
                st.rerun()
        return

    method = st.radio("วิธีรับภาพ", METHODS, horizontal=True, key="scan_box_method", label_visibility="collapsed")
    if method == "ถ่ายภาพ":
        st.caption("ถือมือถือหรือแท็บเล็ตแนวนอน ขนานกับกล่อง ให้เห็นขอบกล่องครบ 4 ด้าน")
        f = camera_with_guide("ถ่ายภาพกล่อง", key=f"scan_cam_{s['round']}", tray_id=s["target"])
    else:
        f = st.file_uploader("อัปโหลดภาพกล่อง", type=["jpg", "jpeg", "png"], key=f"scan_file_{s['round']}")
    if f is None:
        st.info("ถ่ายหรืออัปโหลดภาพกล่อง แล้วกดสแกน")
        return
    if st.button("สแกน", type="primary", width="stretch", key="scan_run"):
        img = load_image_with_exif(f, force_landscape=False)
        if img is None:
            st.error("เปิดไฟล์ภาพนี้ไม่ได้ ลองถ่ายหรืออัปโหลดใหม่")
            return
        try:
            with st.spinner("กำลังสแกนกล่อง..."):
                summary = _aggregator(s["target"]).scan(img, skip_quality=False)
        except Exception:  # noqa: BLE001 — show it and keep the page usable
            st.error("สแกนภาพนี้ไม่สำเร็จ ลองถ่ายหรืออัปโหลดใหม่ หรือกด มี / ไม่มี ในรายการเอง")
            return
        S.apply_box_scan(s["items"], summary.slot_results)
        s.update(photo=img, annotated=summary.annotated_image if summary.slot_results else None,
                 message=summary.error_message or "", round=s["round"] + 1)
        st.rerun()


def _loose_left(s: dict):
    st.info("ระบบยังจำเครื่องมือชิ้นเดี่ยวอัตโนมัติไม่ได้ ภาพที่ถ่ายจะเก็บเป็นหลักฐาน "
            "แล้วกด มี / ไม่มี ในรายการด้วยตนเอง")
    method = st.radio("วิธีรับภาพ", METHODS, horizontal=True, key="scan_loose_method", label_visibility="collapsed")
    if method == "ถ่ายภาพ":
        new = [camera_with_guide("ถ่ายภาพเครื่องมือ", key=f"loose_cam_{s['round']}_{len(s['photos'])}", tray_id="")]
    else:
        new = st.file_uploader("อัปโหลดภาพเครื่องมือ (หลายภาพได้)", type=["jpg", "jpeg", "png"],
                               accept_multiple_files=True, key=f"loose_files_{s['round']}") or []
    added = 0
    for f in new:
        if f is not None and f.file_id not in s["seen_ids"]:
            s["seen_ids"].add(f.file_id)  # a deleted photo stays in the uploader: never add it again
            img = load_image_with_exif(f, force_landscape=False)
            if img is not None:
                s["photos"].append(img)
                added += 1
    if added and method == "ถ่ายภาพ":
        st.rerun()  # a fresh camera for the next photo

    st.markdown(f'<div class="ui-meta">ภาพในรอบนี้ {len(s["photos"])} ภาพ</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, img in enumerate(s["photos"]):
        with cols[i % 3]:
            st.image(img, channels="BGR", width="stretch")
            if st.button("ลบ", key=f"loose_del_{s['round']}_{i}", width="stretch"):
                s["photos"].pop(i)
                st.rerun()


# ─────────────────────────────────────────── right: items and save

@st.fragment
def _right(s: dict):
    item_list(s["items"], key=f"scan_{s['round']}", editable=True, scan_type=s["mode"],
              prefer="slot" if s["mode"] == "box" else "product")
    with st.container(key="scan_save"):
        by = st.text_input("ชื่อผู้สแกน (ไม่บังคับ)", placeholder="พิมพ์ชื่อผู้สแกน", key="scan_by")
        if st.button("บันทึกผลการสแกน", type="primary", width="stretch", key="scan_save_btn"):
            _save(s, by)


def _save(s: dict, by: str):
    photo = s["photo"] if s["mode"] == "box" else (S.contact_sheet(s["photos"]) if s["photos"] else None)
    if photo is None:
        st.error("ถ่ายหรืออัปโหลดภาพก่อนบันทึก ภาพใช้เป็นหลักฐานในประวัติการสแกน")
        return
    ok, _ = I.ensure_tables()
    if not ok:
        st.error("บันทึกไม่ได้ เพราะเชื่อมต่อฐานข้อมูลประวัติไม่ได้ ผลสแกนยังอยู่ ลองบันทึกใหม่ภายหลัง")
        return
    sid = I.save_scan(s["mode"], s["target"], photo, s["items"], annotated=s["annotated"],
                      submitted_by=by, error=s["message"])
    c = S.count_statuses(s["items"])
    # a toast sent right before st.rerun() is lost: keep them for the next run (shown by render_scan)
    notices = [(f"บันทึกผลการสแกนแล้ว (#{sid}) ดูได้ในประวัติการสแกน", "💾")]
    if c["absent"] or c["misplaced"]:
        notices.append((f"{theme.label('absent')} {c['absent']} รายการ · {theme.label('misplaced')} {c['misplaced']} "
                        f"รายการ · {theme.label('needs_review')}", "⚠️"))
    st.session_state["scan_notices"] = notices
    _restart(s)
    st.rerun(scope="app")


# ─────────────────────────────────────────── page

def render_scan():
    page_title("สแกน", "ถ่ายภาพทางซ้าย ตรวจรายการอุปกรณ์ทางขวา กดแก้ มี / ไม่มี ได้ก่อนบันทึก")
    history_ready()  # a warning only: scanning still works without the history database
    for text, icon in st.session_state.pop("scan_notices", []):
        st.toast(text, icon=icon)
    mode = st.segmented_control("ประเภทการสแกน", list(MODES), format_func=MODES.get, default="box",
                                key="scan_mode", label_visibility="collapsed") or "box"
    left, right = st.columns([0.42, 0.58], gap="medium")
    with left:
        if mode == "box":
            target = st.selectbox("กล่อง", I.available_trays(), format_func=I.tray_label, key="scan_box")
        else:
            target = st.selectbox("ชุดเครื่องมือ", S.LOOSE_SETS, format_func=I.tray_label, key="scan_set")
        s = _state(mode, target)
        (_box_left if mode == "box" else _loose_left)(s)
    with right:
        _right(s)
