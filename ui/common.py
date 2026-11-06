"""Session state, image loading and catalog helpers shared by the pages."""
import io
import json
import os
from typing import Optional

import cv2
import numpy as np
import streamlit as st
from PIL import Image, ImageOps

from core.config import CATALOG_PATH, MASTER_DATA_DIR
from scanners.scanner_module import ShapeScanner


def init_session_state():
    if 'detected_list' not in st.session_state:
        st.session_state.detected_list = []

    if 'active_view' not in st.session_state:
        st.session_state.active_view = "scan"

    if 'tray_check_results' not in st.session_state:
        st.session_state.tray_check_results = None

    if 'tray_check_data' not in st.session_state:
        st.session_state.tray_check_data = None

    if 'tray_check_summary' not in st.session_state:
        st.session_state.tray_check_summary = None

    if 'tray_check_selected_id' not in st.session_state:
        st.session_state.tray_check_selected_id = None

    if 'tray_check_input_img' not in st.session_state:
        st.session_state.tray_check_input_img = None


def reset_tray_check_state():
    """ล้างผลการตรวจสอบถาดเดิมเมื่อมีการเปลี่ยนรูปภาพ ถ่ายใหม่ หรือเปลี่ยนถาด เพื่อไม่ให้ข้อมูลค้าง"""
    st.session_state.tray_check_summary = None
    st.session_state.tray_check_input_img = None


def keep_only_checked_items():
    kept_items = [item for item in st.session_state.detected_list if item.get('checked', False)]
    st.session_state.detected_list = kept_items
    
    keys_to_del = [k for k in st.session_state.keys() if str(k).startswith("chk_")]
    for k in keys_to_del:
        del st.session_state[k]


def load_image_with_exif(img_file, force_landscape: bool = True) -> Optional[np.ndarray]:
    """
    อ่านภาพจาก Streamlit UploadedFile / CameraInput พร้อมปรับ EXIF orientation อัตโนมัติ
    และหากภาพเป็นแนวตั้ง (Portrait) จะปรับหมุนเป็นแนวนอน (Landscape) ให้อัตโนมัติ
    """
    if img_file is None:
        return None
    try:
        raw_bytes = img_file.getvalue()
        pil_img = Image.open(io.BytesIO(raw_bytes))
        pil_img = ImageOps.exif_transpose(pil_img)
        rgb_arr = np.array(pil_img.convert("RGB"))
        img_bgr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
    except Exception:
        img_bgr = cv2.imdecode(np.frombuffer(img_file.getvalue(), np.uint8), cv2.IMREAD_COLOR)

    if img_bgr is not None and force_landscape:
        h, w = img_bgr.shape[:2]
        if h > w:
            img_bgr = cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)

    return img_bgr


@st.cache_resource
def load_scanner():
    MASTER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return ShapeScanner(db_folder=str(MASTER_DATA_DIR))


def get_product_info(filename):
    try:
        with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            base = os.path.basename(filename)
            base_no_ext = os.path.splitext(base)[0]
            for item in data:
                if (item.get('filename') == base or 
                    item.get('code') == base or 
                    item.get('code') == base_no_ext or
                    item.get('name_en') == base_no_ext or
                    item.get('class_key') == base_no_ext):
                    return item
    except: return None
    return None
