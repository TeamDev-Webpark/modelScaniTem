"""หน้า "ส่งภาพตรวจถาด": ถ่าย/อัปโหลดภาพถาด ส่งเข้าคิว (รอตรวจสอบ) แล้วกดตรวจ"""
import streamlit as st

from core import inspections as I
from ui.common import load_image_with_exif
from ui.components import camera_with_guide, history_ready, page_title, run_queue, stat_tiles, submission_card
from ui.nav import go


def _uploader_key() -> str:
    return f"submit_files_{st.session_state.get('submit_uploader_n', 0)}"


def _clear_inputs():
    st.session_state["submit_uploader_n"] = st.session_state.get("submit_uploader_n", 0) + 1


def render_submit():
    page_title("ส่งภาพตรวจถาด", "ถ่ายหรืออัปโหลดภาพถาด ส่งเข้าคิว แล้วกดตรวจ ผลจะเก็บไว้ในรายการภาพ")
    if not history_ready():
        return

    trays = I.available_trays()
    tray_id = st.selectbox("เลือกถาด", trays, format_func=I.tray_label, key="submit_tray")

    input_method = st.radio("เลือกวิธี:", ["ถ่ายภาพ", "อัปโหลดภาพ (หลายภาพได้)"], horizontal=True, key="submit_method")
    images = []
    if input_method == "ถ่ายภาพ":
        st.caption("ถือมือถือหรือแท็บเล็ตแนวนอน ขนานกับถาด ให้เห็นขอบถาดครบ 4 ด้าน")
        shot = camera_with_guide("ถ่ายภาพถาด", key=f"submit_cam_{st.session_state.get('submit_uploader_n', 0)}",
                                 tray_id=tray_id)
        if shot:
            images = [(shot.name or "camera.jpg", shot)]
    else:
        files = st.file_uploader("อัปโหลดภาพถาด", type=["jpg", "jpeg", "png"], accept_multiple_files=True,
                                 key=_uploader_key())
        images = [(f.name, f) for f in files or []]

    c_note, c_by = st.columns(2)
    with c_note:
        note = st.text_input("หมายเหตุ (ไม่บังคับ)", placeholder="พิมพ์หมายเหตุ เช่น สาขา หรือเลขตู้", key="submit_note")
    with c_by:
        by = st.text_input("ชื่อผู้ส่ง (ไม่บังคับ)", placeholder="พิมพ์ชื่อผู้ส่ง", key="submit_by")

    if st.button(f"ส่งเข้าคิว ({len(images)} ภาพ)", type="primary", use_container_width=True,
                 disabled=not images, key="submit_send_btn"):
        sent = 0
        for _, f in images:
            img = load_image_with_exif(f, force_landscape=False)
            if img is not None:
                I.create_submission(tray_id, img, note=note, submitted_by=by)
                sent += 1
        st.toast(f"ส่ง {sent} ภาพเข้าคิวแล้ว (สถานะ: รอตรวจสอบ)", icon="📥")
        st.session_state.pop("_queue_last_result", None)
        _clear_inputs()
        st.rerun()

    st.divider()

    # ── คิวที่รอตรวจ ────────────────────────────────────────────
    pending = I.list_submissions(status="pending") + I.list_submissions(status="failed")
    counts = I.submission_counts()
    page_title("คิวรอตรวจสอบ", count=f"{len(pending)} ภาพ")
    stat_tiles([
        ("ทั้งหมด", counts["total"]),
        ("รอตรวจสอบ", counts["pending"], "pending"),
        ("ตรวจสอบแล้ว", counts["done"], "done"),
        ("ต้องตรวจสอบเพิ่มเติม", counts["needs_review"] + counts["failed"], "needs_review"),
    ])

    last = st.session_state.get("_queue_last_result")
    if last:
        if last["review"]:
            st.warning(f"ตรวจเสร็จ {last['total']} ภาพ: ครบ {last['done']} ภาพ, ต้องตรวจสอบเพิ่มเติม {last['review']} ภาพ")
        else:
            st.success(f"ตรวจเสร็จ {last['total']} ภาพ: ครบทุกภาพ")
        if st.button("ดูผลในรายการภาพ", use_container_width=True, key="submit_goto_list"):
            st.session_state.pop("_queue_last_result", None)
            go("submissions")

    if pending:
        if st.button(f"ตรวจทั้งหมด ({len(pending)} ภาพ)", type="primary", use_container_width=True, key="submit_run_all"):
            run_queue([s["id"] for s in reversed(pending)])  # oldest first
            st.rerun()

    with st.container(height=520, key="submit_queue_list"):
        if not pending:
            st.info("ไม่มีภาพในคิว ส่งภาพด้านบนเพื่อเริ่มตรวจ")
        for s in pending:
            submission_card(s, key_prefix="q")
