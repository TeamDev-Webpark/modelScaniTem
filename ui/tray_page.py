"""หน้า "ถาด": ลงทะเบียนถาด และตรวจสอบถาดเครื่องมือด้วย scan_workflow"""
import json

import cv2
import streamlit as st

from core.config import SAMPLE_IMAGES_DIR, TRAY_REFS_DIR, TRAY_TEMPLATES_DIR
from scan_workflow import ImageQualityGate, ScanAggregator, generate_tray_guide_overlay
from ui.common import load_image_with_exif, load_scanner, reset_tray_check_state


def render_tray_register():
    """รับลงทะเบียน Template ถาด: ถ่ายภาพถาดเต็ม → บันทึกตำแหน่งและ Brightness"""
    scanner = load_scanner()
    st.markdown("""
    <div style="background:#E5E5E5;border:1px solid #C7C7C7;border-left:4px solid #2C2C2C;
                border-radius:8px;padding:10px 12px;margin-bottom:12px;">
        <p style="margin:0;color:#2C2C2C;font-size:0.88rem;font-weight:600;">\U0001f4cb วิธีใช้:</p>
        <p style="margin:4px 0 0 0;color:#525252;font-size:0.82rem;">
            1. ใส่เครื่องมือในถาดให้ครบทุกชิ้น<br>
            2. ถ่ายภาพจากมุมตั้งฉากกับถาด (Top-down) ให้เห็นถาดทั้งใบ<br>
            3. ใส่ชื่อถาด แล้วกด “ลงทะเบียน”
        </p>
    </div>
    """, unsafe_allow_html=True)

    tray_name = st.text_input(
        "ชื่อถาด",
        placeholder="เช่น YA 1/2, YA 2/2, BA",
        key="tray_reg_name"
    )

    input_method = st.radio("เลือกวิธี:", ["Camera", "Upload Image"],
                            horizontal=True, key="tray_reg_method")
    opencv_img = None
    if input_method == "Camera":
        img_file = st.camera_input("ถ่ายภาพถาดเต็ม", key="tray_reg_cam")
    else:
        img_file = st.file_uploader("อัปโหลดภาพถาด", type=['jpg', 'png', 'jpeg'],
                                    key="tray_reg_file")

    if img_file:
        opencv_img = load_image_with_exif(img_file)
        st.image(opencv_img, channels="BGR", caption="ภาพถาดที่จะลงทะเบียน", use_container_width=True)

    if opencv_img is not None:
        if not tray_name.strip():
            st.warning("⚠️ กรุณาใส่ชื่อถาดก่อนลงทะเบียน")
        else:
            if st.button("\U0001f5c2️ ลงทะเบียน Template",
                         type="primary", use_container_width=True, key="tray_reg_btn"):
                tray_id = (tray_name.strip()
                           .replace(" ", "_").replace("/", "_").replace(".", "_"))
                with st.spinner(f"กำลังวิเคราะห์ตำแหน่งเครื่องมือในถาด '{tray_name}'..."):
                    tray_data = scanner.register_tray_template(
                        opencv_img, tray_id, tray_name.strip()
                    )

                slots = tray_data.get('slots', [])
                if slots:
                    st.markdown(f"""
                    <div style="background:#FFFFFF;border:2px solid #E81D23;border-radius:8px;
                                padding:10px 14px;margin:8px 0;text-align:center;">
                        <strong style="color:#2C2C2C;font-size:1rem;">
                            ลงทะเบียนถาด '{tray_name}' สำเร็จ!
                        </strong>
                        <span style="color:#525252;font-size:0.84rem;display:block;margin-top:2px;">
                            พบและบันทึก {len(slots)} รายการ
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                    with st.container(height=200):
                        for slot in slots:
                            st.markdown(f"""
                            <div style="display:flex;align-items:center;gap:8px;
                                        padding:4px 0;border-bottom:1px solid #E5E5E5;">
                                <span style="color:#2C2C2C;font-size:0.85rem;">
                                    \u2705 <strong>{slot['name']}</strong>
                                </span>
                                <span style="background:#E5E5E5;color:#525252;font-size:0.72rem;
                                             padding:1px 6px;border-radius:8px;">
                                    {slot.get('category', 'เครื่องมือ')}
                                </span>
                                <span style="color:#C7C7C7;font-size:0.70rem;margin-left:auto;">
                                    ☉ {slot.get('mean_brightness', 110.0):.0f}
                                </span>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.error("ไม่พบเครื่องมือในภาพ กรุณาปรับแสงและลองใหม่")


def render_tray_check():
    """ตรวจสอบถาดเครื่องมือด้วย Slot-Reference Workflow (4 สถานะ, Quality Gate, Alignment Guide)"""
    scanner = load_scanner()
    templates = scanner.list_tray_templates()
    if not templates:
        st.info("ยังไม่มีถาดที่ลงทะเบียน กรุณาไปที่แท็บ 'ลงทะเบียนถาด' ก่อน")
        return

    # Dropdown เลือกถาด
    tray_options = {
        f"{t['tray_name']} ({t['slot_count']} รายการ)": t['tray_id']
        for t in templates
    }
    selected_label = st.selectbox("เลือกถาด",
                                   options=list(tray_options.keys()),
                                   key="tray_check_select",
                                   on_change=reset_tray_check_state)
    selected_id = tray_options[selected_label]

    # โหลดไฟล์ Template JSON ของถาดที่เลือก
    from pathlib import Path
    template_dir = TRAY_TEMPLATES_DIR
    template_file = template_dir / f"{selected_id}.json"
    if not template_file.exists():
        for f in template_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as jf:
                    td = json.load(jf)
                if td.get("tray_id") == selected_id:
                    template_file = f
                    break
            except Exception:
                continue

    tray_data = {}
    if template_file.exists():
        try:
            with open(template_file, "r", encoding="utf-8") as f:
                tray_data = json.load(f)
        except Exception as e:
            st.error(f"ไม่สามารถโหลดข้อมูลถาด {selected_id}: {e}")

    slots = tray_data.get("slots", [])

    # โหลด Template Reference Image (Golden Sample)
    ref_img_path = TRAY_REFS_DIR / f"{selected_id}.jpg"
    if not ref_img_path.exists():
        ref_img_path = TRAY_REFS_DIR / f"{selected_id}.png"
    if not ref_img_path.exists():
        for fallback in [SAMPLE_IMAGES_DIR / "test_verified.jpg"]:
            if fallback.exists():
                ref_img_path = fallback
                break

    ref_img = cv2.imread(str(ref_img_path)) if ref_img_path.exists() else None

    # ภาพร่างนำทางการเล็ง (Camera Alignment Guide Overlay)
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #242A33 0%, #171B21 100%); border: 1.5px solid #00D2FF;
                border-radius: 8px; padding: 10px 14px; margin: 10px 0 14px 0; color: #FFFFFF;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.15rem;">📐</span>
                <span style="font-weight: 700; font-size: 0.95rem; color: #00E6FF;">ภาพร่างนำทางการถ่ายภาพ (Alignment Guide)</span>
            </div>
            <span style="background: rgba(0, 210, 255, 0.15); color: #00E6FF; border: 1px solid #00D2FF;
                         padding: 2px 8px; border-radius: 6px; font-size: 0.74rem; font-weight: 600;">
                Top-Down Inspection
            </span>
        </div>
        <p style="margin: 6px 0 0 0; color: #C7C7C7; font-size: 0.82rem; line-height: 1.4;">
            เล็งกล้องมือถือ/iPad จากมุมมองด้านบน ให้เห็นขอบถาดครบทั้ง 4 ด้าน เพื่อให้ระบบวิเคราะห์ช่องเครื่องมือทั้ง {len(slots)} ช่องได้อย่างแม่นยำ
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🖼️ ดูภาพร่างโครงสร้างถาดต้นแบบ (Template Blueprint Guide)", expanded=False):
        if tray_data and slots:
            guide_img = generate_tray_guide_overlay(tray_data, width=1024, height=768)
            st.image(guide_img, channels="BGR", use_container_width=True,
                     caption=f"โครงร่างตำแหน่ง {len(slots)} ช่องของ {tray_data.get('tray_name')}")

    # แนะนำการถ่ายภาพสำหรับมือถือ / iPad
    st.markdown("""
    <div style="background: #F0F4FF; border: 1.5px solid #2B6CB0; border-radius: 6px; padding: 8px 12px; margin-bottom: 8px; font-size: 0.84rem; color: #1A365D; display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 1.25rem;">📱</span>
        <div>
            <strong>คำแนะนำการถ่ายภาพ:</strong> ควรถือมือถือหรือ iPad <strong>แนวนอน (Landscape)</strong> ขนานกับถาด โดยให้เห็นขอบถาดครบทั้ง 4 ด้าน <em>(ระบบมี AI ตรวจจับทิศทางและหมุนปรับองศาอัตโนมัติหากถ่ายแนวตั้ง)</em>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # วิธีการนำเข้าภาพ
    input_method = st.radio("เลือกวิธีถ่าย/ทดสอบ:",
                            ["Camera (ถ่ายจากกล้องมือถือ/iPad)", "Upload Image (ทดสอบระบบด้วยไฟล์)"],
                            horizontal=True, key="tray_check_method",
                            on_change=reset_tray_check_state)
    opencv_img = None
    if "Camera" in input_method:
        img_file = st.camera_input("ถ่ายภาพถาดปัจจุบัน (จัดมุมมองให้ตรงกับภาพร่าง)",
                                   key="tray_check_cam",
                                   on_change=reset_tray_check_state)
    else:
        img_file = st.file_uploader("อัปโหลดภาพถาดปัจจุบัน (สำหรับทดสอบ)",
                                    type=['jpg', 'png', 'jpeg'],
                                    key="tray_check_file",
                                    on_change=reset_tray_check_state)

    if img_file:
        opencv_img = load_image_with_exif(img_file)

    # Quality Gate & ปุ่มตรวจสอบ
    if opencv_img is not None:
        q_gate = ImageQualityGate()
        q_res = q_gate.check(opencv_img)

        if q_res.passed:
            st.markdown(f"""
            <div style="background: #FFFFFF; border: 1.5px solid #1E9E40; border-left: 5px solid #1E9E40;
                        border-radius: 6px; padding: 8px 12px; margin: 10px 0; display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <strong style="color: #1E9E40; font-size: 0.90rem;">✅ คุณภาพภาพถ่ายพร้อมตรวจ (Quality Gate Passed)</strong>
                    <div style="color: #525252; font-size: 0.78rem; margin-top: 2px;">
                        ความคมชัด: {q_res.blur_score:.1f} (เกณฑ์ ≥ 80) | ความสว่าง: {q_res.brightness:.1f}
                    </div>
                </div>
                <span style="background: #EAF7ED; color: #1E9E40; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">พร้อมสแกน</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            issues_text = " • ".join(q_res.issues)
            st.markdown(f"""
            <div style="background: #FFF8E6; border: 1.5px solid #E59800; border-left: 5px solid #E59800;
                        border-radius: 6px; padding: 8px 12px; margin: 10px 0;">
                <strong style="color: #B57000; font-size: 0.90rem;">⚠️ ข้อสังเกตคุณภาพภาพ (Quality Warning):</strong>
                <div style="color: #7A4B00; font-size: 0.80rem; margin-top: 2px;">{issues_text}</div>
                <div style="color: #8C8C8C; font-size: 0.74rem; margin-top: 2px;">ความคมชัด: {q_res.blur_score:.1f} | ความสว่าง: {q_res.brightness:.1f}</div>
            </div>
            """, unsafe_allow_html=True)

        crop_sel = st.radio(
            "โหมดการตัดขอบถาด (Crop Mode):",
            [
                "🤖 อัตโนมัติ (Smart SIFT-First: ไม่ตัดขอบถ้าภาพชัดเจน)",
                "🔒 ปิดการตัดขอบ (Original 100% Full Frame)",
                "✂️ บังคับตัดขอบ (Force Auto-Crop)"
            ],
            index=0,
            horizontal=True,
            key="tray_crop_mode_radio",
            on_change=reset_tray_check_state
        )
        crop_mode_param = "smart"
        if "ปิดการตัดขอบ" in crop_sel:
            crop_mode_param = "off"
        elif "บังคับตัดขอบ" in crop_sel:
            crop_mode_param = "force"

        c_scan_btn1, c_scan_btn2 = st.columns([3, 1])
        with c_scan_btn1:
            inspect_clicked = st.button(
                f"🔍 ตรวจสอบถาดเครื่องมือครบ {len(slots)} ช่อง (Inspect Tray)",
                type="primary", use_container_width=True, key="tray_check_btn"
            )
        with c_scan_btn2:
            reset_clicked = st.button("🔄 ล้างผลสแกน", use_container_width=True, key="tray_check_reset_top_btn", help="ล้างผลการตรวจและเริ่มใหม่")

        if reset_clicked:
            reset_tray_check_state()
            st.rerun()

        if inspect_clicked:
            with st.spinner(f"กำลังปรับแนวภาพและตรวจสอบช่องเครื่องมือทั้ง {len(slots)} รายการ..."):
                agg = ScanAggregator(tray_refs_dir=str(TRAY_REFS_DIR))
                agg.setup(tray_data, reference_image=ref_img)
                summary = agg.scan(opencv_img, skip_quality=False, crop_mode=crop_mode_param)

                st.session_state.tray_check_summary = summary
                st.session_state.tray_check_selected_id = selected_id
                st.session_state.tray_check_input_img = opencv_img
                st.rerun()

    # แสดงผลสรุป 4 สถานะ (แสดงเมื่อมีรูปภาพปัจจุบันและผลการตรวจตรงกับถาดที่เลือก)
    summary = st.session_state.get('tray_check_summary')
    cached_id = st.session_state.get('tray_check_selected_id')

    if summary and cached_id == selected_id and opencv_img is not None:
        total = summary.total_slots
        correct = summary.correct_count
        missing = summary.missing_count
        misplaced = summary.misplaced_count
        recheck = summary.recheck_count
        pct = int((correct / total * 100)) if total > 0 else 0

        # แถบปุ่มจัดการผลลัพธ์ (สแกนซ้ำ / ล้างเพื่อถ่ายใหม่)
        c_res_act1, c_res_act2 = st.columns([2.5, 1.5])
        with c_res_act1:
            if st.button("🔄 ตรวจสอบซ้ำอีกครั้ง (Re-Scan Current Image)", key="tray_rescan_top_btn", type="primary", use_container_width=True):
                with st.spinner(f"กำลังประมวลผลการตรวจสอบซ้ำทั้ง {len(slots)} ช่อง..."):
                    agg = ScanAggregator(tray_refs_dir=str(TRAY_REFS_DIR))
                    agg.setup(tray_data, reference_image=ref_img)
                    new_summary = agg.scan(opencv_img, skip_quality=False, crop_mode=crop_mode_param)
                    st.session_state.tray_check_summary = new_summary
                    st.session_state.tray_check_selected_id = selected_id
                    st.session_state.tray_check_input_img = opencv_img
                    st.rerun()
        with c_res_act2:
            if st.button("🗑️ ล้างผลการตรวจนี้", key="tray_clear_top_btn", use_container_width=True):
                reset_tray_check_state()
                st.rerun()

        # แผง 4 สถานะ
        st.markdown(f"""
        <div style="display: flex; gap: 6px; margin: 14px 0 8px 0; flex-wrap: wrap;">
            <div style="flex: 1; min-width: 70px; background: #2C2C2C; color: #FFFFFF; border-radius: 6px; padding: 6px 8px; text-align: center;">
                <div style="font-size: 10px; color: #C7C7C7;">ทั้งหมด</div>
                <div style="font-size: 18px; font-weight: 700;">{total}</div>
            </div>
            <div style="flex: 1; min-width: 70px; background: #E8F7ED; border: 1.5px solid #1E9E40; color: #1E9E40; border-radius: 6px; padding: 6px 8px; text-align: center;">
                <div style="font-size: 10px; font-weight: 600;">🟢 ครบ</div>
                <div style="font-size: 18px; font-weight: 700;">{correct}</div>
            </div>
            <div style="flex: 1; min-width: 70px; background: {'#FFF0F0' if missing else '#E5E5E5'}; border: 1.5px solid {'#E81D23' if missing else '#C7C7C7'}; color: {'#E81D23' if missing else '#525252'}; border-radius: 6px; padding: 6px 8px; text-align: center;">
                <div style="font-size: 10px; font-weight: 600;">🔴 ขาดหาย</div>
                <div style="font-size: 18px; font-weight: 700;">{missing}</div>
            </div>
            <div style="flex: 1; min-width: 70px; background: {'#FFF9E6' if misplaced else '#E5E5E5'}; border: 1.5px solid {'#D4A000' if misplaced else '#C7C7C7'}; color: {'#B57000' if misplaced else '#525252'}; border-radius: 6px; padding: 6px 8px; text-align: center;">
                <div style="font-size: 10px; font-weight: 600;">🟡 ผิดตำแหน่ง</div>
                <div style="font-size: 18px; font-weight: 700;">{misplaced}</div>
            </div>
            <div style="flex: 1; min-width: 70px; background: {'#F0F0F0' if recheck else '#E5E5E5'}; border: 1.5px solid {'#808080' if recheck else '#C7C7C7'}; color: #525252; border-radius: 6px; padding: 6px 8px; text-align: center;">
                <div style="font-size: 10px; font-weight: 600;">↩️ ตรวจซ้ำ</div>
                <div style="font-size: 18px; font-weight: 700;">{recheck}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.progress(pct / 100)

        # แจ้งเตือนข้อผิดพลาดหรือถ่ายไกลเกินไป (Distance Guard)
        if summary.error_message:
            st.markdown(f"""
            <div style="background: #FFF2F2; border: 2px solid #E81D23; border-radius: 8px;
                        padding: 12px 16px; margin: 12px 0;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.4rem;">⚠️</span>
                    <strong style="color: #E81D23; font-size: 1rem;">ไม่สามารถตรวจสอบถาดได้:</strong>
                </div>
                <p style="color: #2C2C2C; margin: 6px 0 0 32px; font-size: 0.90rem;">{summary.error_message}</p>
            </div>
            """, unsafe_allow_html=True)
            return

        # แสดงกล่องสถานะ Auto-Crop & Distance
        if summary.crop:
            crop_info = summary.crop
            c_ratio = crop_info.area_ratio
            if c_ratio >= 0.50:
                c_badge_bg = "#E8F7ED"
                c_badge_border = "#1E9E40"
                c_badge_color = "#1E9E40"
                c_status_text = f"✅ ระยะถ่ายดีเยี่ยม: ตัวถาดกินพื้นที่ {c_ratio:.0%} ของภาพ (Auto-Crop สำเร็จ)"
            else:
                c_badge_bg = "#FFF9E6"
                c_badge_border = "#D4A000"
                c_badge_color = "#B57000"
                c_status_text = f"ℹ️ ถ่ายค่อนข้างห่าง: ตัวถาดกินพื้นที่ {c_ratio:.0%} (ระบบทำการ Auto-Crop ซูมระนาบ 90° ให้อัตโนมัติ)"

            st.markdown(f"""
            <div style="background: {c_badge_bg}; border: 1.5px solid {c_badge_border}; border-radius: 6px;
                        padding: 6px 12px; margin: 8px 0; font-size: 0.82rem; color: {c_badge_color};">
                <strong>✂️ การตรวจจับและตัดขอบถาด:</strong> {c_status_text}
            </div>
            """, unsafe_allow_html=True)

        # แสดงกล่องสถานะ Auto-Orientation (ถ้ามีการหมุนภาพ)
        if summary.align and getattr(summary.align, "rotation_applied", 0) > 0:
            deg = summary.align.rotation_applied
            st.markdown(f"""
            <div style="background: #EBF8FF; border: 1.5px solid #3182CE; border-radius: 6px;
                        padding: 6px 12px; margin: 8px 0; font-size: 0.82rem; color: #2B6CB0;">
                <strong>🔄 ปรับทิศทางภาพอัตโนมัติ:</strong> ตรวจพบภาพถ่ายแนวตั้ง/หมุน ระบบหมุนปรับระนาบ {deg}° ให้อัตโนมัติเพื่อให้ตรงกับโครงสร้างถาดต้นแบบ
            </div>
            """, unsafe_allow_html=True)

        if summary.is_complete:
            st.markdown("""
            <div style="background: #E8F7ED; border: 2px solid #1E9E40; border-radius: 8px;
                        padding: 10px; text-align: center; margin: 8px 0;">
                <strong style="color: #1E9E40; font-size: 1.02rem;">✅ ตรวจสอบเครื่องมือครบทุกช่อง 100% เรียบร้อย!</strong>
            </div>
            """, unsafe_allow_html=True)
        else:
            status_desc = []
            if missing > 0: status_desc.append(f"ขาด {missing} ชิ้น")
            if misplaced > 0: status_desc.append(f"ผิดตำแหน่ง {misplaced} ชิ้น")
            if recheck > 0: status_desc.append(f"ตรวจซ้ำ {recheck} ชิ้น")
            st.markdown(f"""
            <div style="background: #FFF2F2; border: 1.5px solid #E81D23; border-radius: 8px;
                        padding: 8px 12px; text-align: center; margin: 8px 0;">
                <strong style="color: #E81D23; font-size: 0.94rem;">⚠️ ถาดไม่สมบูรณ์: {', '.join(status_desc)}</strong>
            </div>
            """, unsafe_allow_html=True)

        # ภาพผลลัพธ์แบบสลับ 4 แท็บ (เพิ่มแท็บภาพหลัง Crop)
        tab_anno, tab_crop, tab_orig, tab_wire = st.tabs([
            "🖼️ ภาพพร้อมผลการตรวจ (Annotated)",
            "✂️ ภาพตัดขอบถาด (Cropped & Rectified)",
            "📷 ภาพถ่ายต้นฉบับ (Original)",
            "📐 ภาพร่างไกด์ (Template Blueprint)"
        ])

        with tab_anno:
            if summary.annotated_image is not None:
                st.image(summary.annotated_image, channels="BGR", use_container_width=True,
                         caption=f"ผลการตรวจสอบถาด: 🟢 {correct}  🔴 {missing}  🟡 {misplaced}  ↩️ {recheck}")

        with tab_crop:
            if summary.crop and summary.crop.cropped_image is not None:
                st.image(summary.crop.cropped_image, channels="BGR", use_container_width=True,
                         caption=f"ภาพตัดขอบถาดและปรับระนาบ (Perspective Rectified): ขนาด {summary.crop.cropped_image.shape[1]}x{summary.crop.cropped_image.shape[0]} px")
            else:
                st.info("ใช้ภาพเต็มเฟรมโดยตรง (ไม่มีการตัดขอบ)")

        with tab_orig:
            orig_img = st.session_state.get('tray_check_input_img')
            if orig_img is not None:
                st.image(orig_img, channels="BGR", use_container_width=True, caption="ภาพถ่ายต้นฉบับก่อนตัดขอบ")

        with tab_wire:
            if tray_data and slots:
                wire = generate_tray_guide_overlay(tray_data, width=1024, height=768)
                st.image(wire, channels="BGR", use_container_width=True, caption="โครงสร้างช่องต้นแบบ")

        # รายการแยกแต่ละช่องพร้อมฟิลเตอร์
        st.markdown("<h4 style='font-size: 15px; margin: 14px 0 6px 0; color: #2C2C2C;'>รายละเอียดแต่ละช่อง:</h4>", unsafe_allow_html=True)

        filter_choice = st.radio(
            "กรองสถานะ:",
            options=["ทั้งหมด", "🔴 ขาดหาย", "🟡 ผิดตำแหน่ง", "↩️ ตรวจซ้ำ", "🟢 ครบ"],
            format_func=lambda x: {
                "ทั้งหมด": f"ทั้งหมด ({total})",
                "🔴 ขาดหาย": f"🔴 ขาดหาย ({missing})",
                "🟡 ผิดตำแหน่ง": f"🟡 ผิดตำแหน่ง ({misplaced})",
                "↩️ ตรวจซ้ำ": f"↩️ ตรวจซ้ำ ({recheck})",
                "🟢 ครบ": f"🟢 ครบ ({correct})"
            }[x],
            horizontal=True,
            label_visibility="collapsed",
            key="tray_slot_filter_radio"
        )

        target_status = {
            "ทั้งหมด": None,
            "🔴 ขาดหาย": "missing",
            "🟡 ผิดตำแหน่ง": "misplaced",
            "↩️ ตรวจซ้ำ": "recheck",
            "🟢 ครบ": "correct"
        }[filter_choice]

        filtered_slots = summary.slot_results
        if target_status is not None:
            filtered_slots = [s for s in filtered_slots if s["status"] == target_status]

        with st.container(height=340):
            if not filtered_slots:
                st.markdown("<p style='text-align: center; color: #888; padding: 20px 0;'>ไม่พบรายการในสถานะนี้</p>", unsafe_allow_html=True)
            else:
                for s in filtered_slots:
                    st_val = s["status"]
                    sn = s["slot_number"]
                    name = s.get("item_name") or f"ช่องที่ {sn}"
                    reason = s.get("reason", "")
                    conf = s.get("confidence", 0.0)

                    if st_val == "correct":
                        icon, bg, bdr, tag_color = "🟢", "#FFFFFF", "#1E9E40", "#1E9E40"
                    elif st_val == "missing":
                        icon, bg, bdr, tag_color = "🔴", "#FFF2F2", "#E81D23", "#E81D23"
                    elif st_val == "misplaced":
                        icon, bg, bdr, tag_color = "🟡", "#FFFBE6", "#E5A000", "#B57000"
                    else:
                        icon, bg, bdr, tag_color = "↩️", "#F7F7F7", "#888888", "#525252"

                    st.markdown(f"""
                    <div style="background: {bg}; border: 1px solid {bdr}; border-radius: 6px;
                                padding: 6px 10px; margin-bottom: 5px; display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                        <div style="display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0;">
                            <span style="font-size: 1.1rem; flex-shrink: 0;">{icon}</span>
                            <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                <strong style="color: #2C2C2C; font-size: 0.86rem;">#{sn} {name}</strong>
                                <div style="color: #525252; font-size: 0.74rem;">{reason}</div>
                            </div>
                        </div>
                        <div style="text-align: right; flex-shrink: 0;">
                            <span style="background: #E5E5E5; color: {tag_color}; font-size: 0.72rem; font-weight: 600; padding: 2px 6px; border-radius: 4px;">
                                {conf:.0%}
                            </span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # ปุ่มเพิ่มรายการขาด / ผิดตำแหน่งเข้า Checklist
        problem_slots = [s for s in summary.slot_results if s["status"] in ("missing", "misplaced", "recheck")]
        if problem_slots:
            btn_label = f"➕ เพิ่ม {len(problem_slots)} รายการที่พบปัญหาเข้า Checklist"
            if st.button(btn_label, use_container_width=True, type="primary", key="tray_add_problems_btn"):
                existing_names = [x['name'] for x in st.session_state.detected_list]
                added = 0
                for s in problem_slots:
                    item_name = s.get("item_name") or f"ช่อง #{s['slot_number']}"
                    if item_name not in existing_names:
                        st.session_state.detected_list.append({
                            "filename": f"{s['slot_number']}.png",
                            "name": item_name,
                            "category": "ถาด 70 รายการ",
                            "description": f"สถานะจากถาด: {s['status']} ({s.get('reason', '')})",
                            "score": int(s.get("confidence", 0.0) * 100),
                            "checked": False
                        })
                        added += 1

                st.session_state.active_view = "checklist"
                st.rerun()

        # ตัวเลือกเพิ่มเติม
        with st.expander("⚙️ ตัวเลือกเพิ่มเติม"):
            c_del1, c_del2 = st.columns(2)
            with c_del1:
                if st.button("ล้างผลการสแกนนี้", use_container_width=True):
                    st.session_state.tray_check_summary = None
                    st.rerun()
            with c_del2:
                if st.button("ลบ Template ถาดนี้", key="tray_delete_btn", type="secondary", use_container_width=True):
                    scanner.delete_tray_template(selected_id)
                    st.session_state.tray_check_summary = None
                    st.success("ลบ Template สำเร็จ")
                    st.rerun()


def render_tray():
    """หน้าจัดการถาด Template"""
    st.markdown("""
    <div style="border-left:4px solid #E81D23;padding-left:10px;margin-bottom:10px;">
        <h3 style="margin:0;color:#2C2C2C;font-size:18px;">จัดการถาดเครื่องมือ</h3>
        <p style="margin:2px 0 0 0;color:#525252;font-size:12px;">
            ระบบตรวจนับและสแกนถาดเครื่องมืออัตโนมัติด้วย AI (Auto-Orientation, Auto-Crop & Homography Alignment)
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_reg, tab_check = st.tabs(["ลงทะเบียนถาด", "ตรวจสอบถาด"])
    with tab_reg:
        render_tray_register()
    with tab_check:
        render_tray_check()
