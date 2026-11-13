"""Image loading shared by the pages (EXIF orientation from phone cameras)."""
import io
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageOps


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
