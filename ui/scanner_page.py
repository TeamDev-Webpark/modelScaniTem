"""หน้า "สแกน": ถ่าย/อัปโหลดภาพแล้วตรวจจับเครื่องมือด้วย ShapeScanner"""
import time

import streamlit as st

from ui.common import get_product_info, keep_only_checked_items, load_image_with_exif, load_scanner
from ui.components import page_title
from ui.nav import go


@st.dialog("กำลังประมวลผลสแกนเครื่องมือ", width="small")
def scan_processing_dialog(opencv_img):
    scanner = load_scanner()
    st.markdown("""
    <div style="text-align: center; padding: 4px 0 8px 0;">
        <div class="radar-scan-anim">
            <div class="radar-beam"></div>
            <div class="radar-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#E81D23" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m4.93 4.93 4.24 4.24"/><path d="m14.83 9.17 4.24-4.24"/><path d="m14.83 14.83 4.24 4.24"/><path d="m9.17 14.83-4.24 4.24"/></svg>
            </div>
        </div>
        <h4 style="color: #2C2C2C; margin: 12px 0 4px 0; font-size: 1.06rem; font-weight: 700;">กำลังวิเคราะห์และตรวจจับเครื่องมือ</h4>
        <p style="color: #525252; font-size: 0.82rem; margin-bottom: 6px;">ระบบกำลังใช้ SIFT Feature Matching & Tiling Inspection</p>
    </div>
    """, unsafe_allow_html=True)
    
    status_text = st.empty()
    prog_bar = st.progress(20)
    
    status_text.markdown("<p style='text-align: center; color: #525252; font-size: 0.85rem;'>ขั้นที่ 1/3: ค้นหาจุดเด่นในภาพ (Extracting Keypoints)...</p>", unsafe_allow_html=True)
    time.sleep(0.35)
    
    prog_bar.progress(55)
    status_text.markdown("<p style='text-align: center; color: #525252; font-size: 0.85rem;'>ขั้นที่ 2/3: เปรียบเทียบกับฐานข้อมูลอุปกรณ์ (Feature Matching)...</p>", unsafe_allow_html=True)
    
    # รันการค้นหาอุปกรณ์จริง
    results = scanner.scan_with_tiling(opencv_img, threshold=8)
    
    prog_bar.progress(90)
    status_text.markdown("<p style='text-align: center; color: #525252; font-size: 0.85rem;'>ขั้นที่ 3/3: ประมวลผลและสรุปรายการ...</p>", unsafe_allow_html=True)
    time.sleep(0.25)
    prog_bar.progress(100)
    
    if results:
        count_new = 0
        existing_files = [x['filename'] for x in st.session_state.detected_list]
        
        for res in results:
            if res['filename'] not in existing_files:
                info = get_product_info(res['filename'])
                display_name = info['name'] if info else res['filename']
                category = info['category'] if info else "Unknown"
                description = info['description'] if info else "-"
                
                st.session_state.detected_list.append({
                    "filename": res['filename'],
                    "name": display_name,
                    "category": category,
                    "description": description,
                    "score": res['score'],
                    "checked": False
                })
                count_new += 1
        
        if count_new > 0:
            status_text.markdown(f"""
            <div style="background-color: #FFFFFF; border: 2px solid #E81D23; border-radius: 8px; padding: 12px; margin: 10px 0; text-align: center;">
                <strong style="color: #2C2C2C; font-size: 1.02rem; display: block; margin-top: 4px;">ตรวจพบอุปกรณ์ {count_new} รายการใหม่</strong>
                <span style="color: #525252; font-size: 0.84rem; display: block; margin-top: 2px;">กำลังนำคุณไปยังหน้าแสดงผลรายการตรวจสอบ...</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            status_text.markdown(f"""
            <div style="background-color: #E5E5E5; border: 1px solid #C7C7C7; border-left: 4px solid #525252; border-radius: 8px; padding: 12px; margin: 10px 0; text-align: center;">
                <strong style="color: #2C2C2C; font-size: 0.96rem; display: block;">ตรวจพบ {len(results)} รายการ (มีอยู่ในรายการแล้ว)</strong>
                <span style="color: #525252; font-size: 0.84rem; display: block; margin-top: 2px;">กำลังนำคุณไปยังหน้าแสดงผลรายการตรวจสอบ...</span>
            </div>
            """, unsafe_allow_html=True)
            
        time.sleep(1.0)
        go("checklist")
    else:
        status_text.markdown("""
        <div style="background-color: #FFFFFF; border: 1px solid #E81D23; border-radius: 8px; padding: 12px; margin: 10px 0; text-align: center;">
            <strong style="color: #E81D23; font-size: 0.95rem; display: block;">ไม่พบอุปกรณ์ที่ตรงกับฐานข้อมูล</strong>
            <span style="color: #525252; font-size: 0.82rem; display: block; margin-top: 4px;">คำแนะนำ: ปรับแสงสว่าง หรือวางอุปกรณ์ให้เห็นลายเส้นชัดเจน</span>
        </div>
        """, unsafe_allow_html=True)
        
        c_dlg1, c_dlg2 = st.columns(2)
        with c_dlg1:
            if st.button("ลองสแกนใหม่", use_container_width=True):
                st.rerun()
        with c_dlg2:
            if st.button("ไปยังรายการ", use_container_width=True):
                go("checklist")


def render_scanner():
    scanner = load_scanner()
    page_title("สแกนเครื่องมือ", "ถ่ายหรืออัปโหลดภาพเครื่องมือ ระบบจะหาเครื่องมือที่ตรงกับฐานข้อมูล")
    
    input_method = st.radio("เลือกวิธี:", ["ถ่ายภาพ", "อัปโหลดภาพ"], horizontal=True, key="scan_input_method")
    
    opencv_img = None
    
    if input_method == "ถ่ายภาพ":
        st.caption("คำแนะนำ: ถือ iPad หรือมือถือขนานกับโต๊ะ วางเครื่องมือไม่ซ้อนทับกัน")
        img_file = st.camera_input("ถ่ายภาพเครื่องมือ", key="cam_input", on_change=keep_only_checked_items)
        if img_file:
            opencv_img = load_image_with_exif(img_file)
    elif input_method == "อัปโหลดภาพ":
        img_file = st.file_uploader("อัปโหลดภาพเครื่องมือ", type=['jpg','png'], key="file_input", on_change=keep_only_checked_items)
        if img_file:
            opencv_img = load_image_with_exif(img_file)

    if opencv_img is not None:
        viz_img = None
        kp_count = 0
        try:
            viz_img, kp_count = scanner.visualize_keypoints(opencv_img.copy())
        except AttributeError:
            viz_img = opencv_img
            kp_count = "N/A"

        st.write("---") 
        img_col1, img_col2 = st.columns(2) 

        with img_col1:
            st.image(opencv_img, channels="BGR", caption="ภาพถ่าย", use_container_width=True)

        with img_col2:
            caption_text = f"จุดสแกน (พบ {kp_count} จุด)"
            st.image(viz_img, channels="BGR", caption=caption_text, use_container_width=True)
        
        if isinstance(kp_count, int) and kp_count < 500:
             st.warning(f"พบจุดเด่นน้อย ({kp_count}) แนะนำให้ปรับแสงหรือขยับเข้าใกล้เครื่องมือ")
        
        st.divider()

        if st.button("สแกนหาอุปกรณ์ทั้งหมด", type="primary", use_container_width=True):
            scan_processing_dialog(opencv_img)
