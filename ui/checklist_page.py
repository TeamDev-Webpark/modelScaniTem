"""หน้า "เช็คลิสต์": รายการเครื่องมือที่ตรวจพบจากการสแกน"""
import streamlit as st

from core.config import MASTER_DATA_DIR


def render_checklist():
    total_count = len(st.session_state.detected_list)
    checked_count = sum(1 for x in st.session_state.detected_list if x.get('checked', False))
    remaining_count = total_count - checked_count
    percent = int((checked_count / total_count * 100)) if total_count > 0 else 0

    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; border-left: 4px solid #E81D23; padding-left: 10px; margin-bottom: 10px;">
        <h3 style="margin: 0; color: #2C2C2C; font-size: 18px;">รายการตรวจสอบ</h3>
        <span style="background-color: #E81D23; color: #FFFFFF; padding: 2px 10px; border-radius: 12px; font-size: 13px; font-weight: 600;">{total_count} รายการ</span>
    </div>
    """, unsafe_allow_html=True)
    
    # --- ปุ่มจัดการขนาดใหญ่แตะสะดวก ---
    st.markdown("<div class='top-action-bar'>", unsafe_allow_html=True)
    c_btn1, c_btn2, c_btn3 = st.columns(3)
    
    def update_all_checked(value):
        for i in range(len(st.session_state.detected_list)):
            st.session_state.detected_list[i]['checked'] = value
            if f"chk_{i}" in st.session_state:
                st.session_state[f"chk_{i}"] = value

    with c_btn1:
        if st.button("ตรวจครบ", use_container_width=True):
            update_all_checked(True)
            st.rerun()
            
    with c_btn2:
        if st.button("ยกเลิก", use_container_width=True):
            update_all_checked(False)
            st.rerun()
            
    with c_btn3:
        if st.button("ล้างหมด", type="primary", use_container_width=True):
            st.session_state.detected_list = []
            for k in list(st.session_state.keys()):
                if str(k).startswith("chk_"):
                    del st.session_state[k]
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
            
    if total_count > 0:
        # แถบสรุปสถานะย่อ
        st.markdown(f"""
        <div style="display: flex; gap: 8px; margin: 8px 0;">
            <div style="flex: 1; background: #2C2C2C; color: #FFFFFF; border-radius: 6px; padding: 6px 8px; text-align: center;">
                <div style="font-size: 11px; color: #C7C7C7;">ทั้งหมด</div>
                <div style="font-size: 16px; font-weight: 700;">{total_count}</div>
            </div>
            <div style="flex: 1; background: #E5E5E5; color: #2C2C2C; border: 1px solid #C7C7C7; border-radius: 6px; padding: 6px 8px; text-align: center;">
                <div style="font-size: 11px; color: #525252;">ยังไม่ตรวจ</div>
                <div style="font-size: 16px; font-weight: 700; color: #E81D23;">{remaining_count}</div>
            </div>
            <div style="flex: 1; background: #E5E5E5; color: #2C2C2C; border: 1px solid #C7C7C7; border-radius: 6px; padding: 6px 8px; text-align: center;">
                <div style="font-size: 11px; color: #525252;">ตรวจแล้ว</div>
                <div style="font-size: 16px; font-weight: 700; color: #2C2C2C;">{checked_count} ({percent}%)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Progress Bar
        st.progress(percent / 100)
        
        # แจ้งเตือนเมื่อตรวจครบ 100%
        if checked_count == total_count and total_count > 0:
            st.markdown("""
            <div style="background-color: #FFFFFF; border: 2px solid #E81D23; border-radius: 8px; padding: 10px; margin: 8px 0; text-align: center;">
                <strong style="color: #2C2C2C; font-size: 15px;">ตรวจสอบอุปกรณ์ครบทุกชิ้นเรียบร้อย 100% (Ready for Handover)</strong>
            </div>
            """, unsafe_allow_html=True)
        
        # ฟิลเตอร์และค้นหา
        c_filter, c_view = st.columns([1.3, 1])
        with c_filter:
            filter_mode = st.radio(
                "กรองสถานะ:",
                options=["all", "unchecked", "checked"],
                format_func=lambda x: f"ทั้งหมด ({total_count})" if x == "all" else (f"ยังไม่ตรวจ ({remaining_count})" if x == "unchecked" else f"ตรวจแล้ว ({checked_count})"),
                horizontal=True,
                label_visibility="collapsed",
                key="chk_filter_radio"
            )
        with c_view:
            view_mode = st.radio(
                "รูปแบบ:",
                ["กะทัดรัด (Compact)", "การ์ด 2 คอลัมน์ (Grid)"],
                horizontal=True,
                label_visibility="collapsed",
                key="chk_view_radio"
            )
            
        search_kw = st.text_input("ค้นหา", placeholder="พิมพ์ชื่อ หรือหมวดหมู่...", label_visibility="collapsed", key="chk_search_input")
    else:
        filter_mode = "all"
        view_mode = "กะทัดรัด (Compact)"
        search_kw = ""

    st.markdown("<div style='margin-bottom: 6px;'></div>", unsafe_allow_html=True)

    # --- ส่วนแสดงรายการ (Scrollable Box) ---
    with st.container(height=480):
        if not st.session_state.detected_list:
            st.info("ยังไม่มีรายการ... กรุณาถ่ายภาพหรืออัปโหลดทางฝั่งสแกน")
        else:
            filtered_indices = []
            for i, item in enumerate(st.session_state.detected_list):
                if search_kw:
                    kw = search_kw.lower()
                    if kw not in item['name'].lower() and kw not in item.get('category', '').lower():
                        continue
                if filter_mode == "unchecked" and item.get('checked', False):
                    continue
                if filter_mode == "checked" and not item.get('checked', False):
                    continue
                filtered_indices.append(i)

            if not filtered_indices:
                st.markdown("<p style='text-align: center; color: #525252; padding: 20px 0;'>ไม่พบรายการที่ตรงกับเงื่อนไข</p>", unsafe_allow_html=True)
            elif "2 คอลัมน์" in view_mode:
                for row_idx in range(0, len(filtered_indices), 2):
                    pair_cols = st.columns(2)
                    for col_idx, pair_col in enumerate(pair_cols):
                        item_sub_idx = row_idx + col_idx
                        if item_sub_idx < len(filtered_indices):
                            orig_i = filtered_indices[item_sub_idx]
                            item = st.session_state.detected_list[orig_i]
                            is_item_checked = item.get('checked', False)
                            
                            with pair_col:
                                with st.container(border=True):
                                    gc1, gc2, gc3 = st.columns([0.15, 0.71, 0.14])
                                    with gc1:
                                        is_checked = st.checkbox(
                                            label=f"เลือก {item['name']}",
                                            value=is_item_checked,
                                            key=f"chk_{orig_i}",
                                            label_visibility="collapsed"
                                        )
                                        st.session_state.detected_list[orig_i]['checked'] = is_checked
                                    with gc2:
                                        name_style = "color: #525252; text-decoration: line-through;" if is_item_checked else "color: #2C2C2C; font-weight: 600;"
                                        st.markdown(f"""
                                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                            <div style="font-size: 0.88rem; {name_style} line-height: 1.2;">
                                                {item['name']}
                                            </div>
                                            <span class='badge-score'>★ {item['score']}</span>
                                        </div>
                                        <div style="margin-top: 3px;">
                                            <span class='badge-category' style="font-size: 0.70rem; padding: 1px 6px;">{item['category']}</span>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    with gc3:
                                        if st.button("✕", key=f"del_grid_{orig_i}", help="ลบรายการนี้"):
                                            st.session_state.detected_list.pop(orig_i)
                                            for k in list(st.session_state.keys()):
                                                if str(k).startswith("chk_"):
                                                    del st.session_state[k]
                                            st.rerun()
            else:
                for orig_i in filtered_indices:
                    item = st.session_state.detected_list[orig_i]
                    is_item_checked = item.get('checked', False)
                    
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([0.10, 0.14, 0.66, 0.10])
                        
                        with c1:
                            is_checked = st.checkbox(
                                label=f"เลือก {item['name']}", 
                                value=is_item_checked, 
                                key=f"chk_{orig_i}",
                                label_visibility="collapsed"
                            )
                            st.session_state.detected_list[orig_i]['checked'] = is_checked
                        
                        with c2:
                            try:
                                st.image(str(MASTER_DATA_DIR / item['filename']), width=40)
                            except: 
                                st.write("")
                        
                        with c3:
                            name_color = "color: #525252; text-decoration: line-through;" if is_item_checked else "color: #2C2C2C; font-weight: 600;"
                            st.markdown(f"""
                            <div style="display: flex; justify-content: space-between; align-items: baseline; gap: 4px; overflow: hidden;">
                                <span style="font-size: 0.88rem; {name_color} white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                    {item['name']}
                                </span>
                                <span class='badge-score' style="font-size: 0.74rem; flex-shrink: 0;">★ {item['score']}</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 6px; margin-top: 2px; overflow: hidden;">
                                <span class='badge-category' style="font-size: 0.68rem; padding: 1px 6px; flex-shrink: 0;">{item['category']}</span>
                                <span class='item-desc' style="font-size: 0.74rem; color: #525252; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                    {item['description']}
                                </span>
                            </div>
                            """, unsafe_allow_html=True)
                            
                        with c4:
                            if st.button("✕", key=f"del_{orig_i}", help="ลบรายการนี้"):
                                st.session_state.detected_list.pop(orig_i)
                                for k in list(st.session_state.keys()):
                                    if str(k).startswith("chk_"):
                                        del st.session_state[k]
                                st.rerun()
