"""หน้า "จัดการกล่อง": กล่องที่มีในระบบ ภาพต้นแบบ เส้นไกด์ และรายการช่อง พร้อมวิธีเพิ่มกล่องใหม่"""
import base64
from pathlib import Path

import streamlit as st

from core import inspections as I
from core import scan_items as S
from core.config import TRAY_REFS_DIR
from scan_workflow import generate_tray_guide_overlay
from ui.components import no_match, page_title, stat_tiles


@st.cache_data(show_spinner=False)
def _data_uri(path: str) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(Path(path).read_bytes()).decode()


def _box(tray_id: str):
    items = S.box_items(tray_id)
    tpl = I._load_template(tray_id)
    ref, empty = TRAY_REFS_DIR / f"{tray_id}.jpg", TRAY_REFS_DIR / f"{tray_id}_empty.jpg"
    with st.expander(f"{I.tray_label(tray_id)} · {len(items)} ช่อง", expanded=False):
        st.markdown(f'<div class="ui-meta">รหัสกล่อง {tray_id} · ภาพต้นแบบ {"มี" if ref.exists() else "ไม่มี"}'
                    f' · ภาพกล่องว่าง {"มี" if empty.exists() else "ไม่มี"}</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if ref.exists():
                st.image(str(ref), caption="ภาพต้นแบบ (ใช้จัดภาพและตรวจช่อง)", width="stretch")
        with c2:
            st.image(generate_tray_guide_overlay(tpl, width=960, height=720), channels="BGR",
                     caption="ภาพร่างช่องเครื่องมือ", width="stretch")
        st.dataframe(
            [{"รูป": _data_uri(p) if (p := S.thumbnail(it, "slot")) else None, "ช่อง": it["slot"],
              "ลำดับในเช็คลิสต์": it["no"], "ชื่อ": it["name"], "รหัสอะไหล่": it["part_number"]} for it in items],
            column_config={"รูป": st.column_config.ImageColumn("รูป", width="small")},
            hide_index=True, width="stretch", row_height=56, height=420)


def render_manage():
    page_title("จัดการกล่อง", "กล่องที่ใช้สแกนได้ ภาพต้นแบบ และรายการช่องของแต่ละกล่อง")
    trays = I.available_trays()
    stat_tiles([("กล่องในระบบ", len(trays)),
                ("ช่องทั้งหมด", sum(len(S.box_items(t)) for t in trays))])
    if not trays:
        no_match("ยังไม่มีกล่องในระบบ ดูวิธีเพิ่มกล่องด้านล่าง")
    for t in trays:
        _box(t)

    page_title("เพิ่มกล่องใหม่")
    st.markdown(
        "กล่องใหม่ต้องมีเทมเพลต (ตำแหน่งช่อง) และภาพต้นแบบ ผู้ดูแลระบบสร้างด้วยสคริปต์ในโฟลเดอร์ `scripts/build/` "
        "ตามขั้นตอนใน README หัวข้อ *เพิ่มหรืออัปเดตถาด*:\n"
        "1. สร้างเทมเพลต `data/tray_templates/<รหัสกล่อง>.json` ที่ระบุขอบเขตของทุกช่อง\n"
        "2. จับคู่ช่องกับ checklist: `python scripts/build/apply_checklist_mapping.py --apply --photos <โฟลเดอร์ภาพ>`\n"
        "3. ถ่ายภาพกล่องครบและกล่องว่างจากมุมเดียวกัน แล้วรัน `python scripts/build/build_tray_refs.py --photos <โฟลเดอร์ภาพ>`\n\n"
        "กล่องใหม่จะขึ้นในหน้านี้และในหน้าสแกนเองหลังรีสตาร์ตแอป")
