"""
Builds the box2-template01_31-item template, wireframe sketch, and overlay
using the latest mask annotations and reference image.
"""
import json
import base64
import zlib
import numpy as np
import cv2
import os
from pathlib import Path

# Paths to data
PRIMARY_JSON_SOURCE = Path(r"c:\MyProject\Webpark\dataYamaha\Merchecklist\Tools\ตำแหน่งอุปกรณ์\31\new data2.txt")
FALLBACK_JSON_SOURCE = Path(r"c:\MyProject\Webpark\dataYamaha\Merchecklist\Tools\ตำแหน่งอุปกรณ์\31\new data.txt")
REF_IMG_PATH = Path("data/tray_refs/box2-template01_31-item.jpg")
TRAY_ID = "box2-template01_31-item"

# Load annotation data
if PRIMARY_JSON_SOURCE.exists():
    with open(PRIMARY_JSON_SOURCE, "r", encoding="utf-8") as f:
        upload_data = json.load(f)
elif FALLBACK_JSON_SOURCE.exists():
    with open(FALLBACK_JSON_SOURCE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    converted_str = raw_data["annotations"]["hand-tool-board-detection"]["converted"]
    upload_data = json.loads(converted_str)
else:
    raise FileNotFoundError(f"Could not find annotation data at {PRIMARY_JSON_SOURCE}")

# Reference database of the 31 special tools for Yamaha
REFERENCE_31_TOOLS = [
    {"slot_number": 1, "code": "timing_hole_cap_tool", "name": "เครื่องมือถอดฝาปิดช่องตั้งมาร์ค", "bbox_norm": [0.73, 0.24, 0.76, 0.39]},
    {"slot_number": 2, "code": "valve_guide_installer", "name": "ชุดใส่ปลอกวาล์ว", "bbox_norm": [0.67, 0.15, 0.69, 0.38]},
    {"slot_number": 3, "code": "clutch_holding_tool", "name": "เครื่องมือจับคลัทช์", "bbox_norm": [0.63, 0.14, 0.67, 0.48]},
    {"slot_number": 4, "code": "rocker_arm_shaft_puller", "name": "ตัวถอดเพลากระเดื่องวาล์ว", "bbox_norm": [0.69, 0.15, 0.73, 0.45]},
    {"slot_number": 5, "code": "valve_spring_compressor", "name": "เครื่องมือถอดสปริงวาล์ว", "bbox_norm": [0.76, 0.16, 0.89, 0.49]},
    {"slot_number": 6, "code": "chain_cutter_tool", "name": "ตัวตัดโซ่ พร้อมแกนตัดสำรอง", "bbox_norm": [0.25, 0.29, 0.33, 0.46]},
    {"slot_number": 7, "code": "front_fork_t_wrench_10", "name": "ตัว T ถอด–ประกอบโช๊คอัพหน้า #10", "bbox_norm": [0.31, 0.19, 0.39, 0.77]},
    {"slot_number": 8, "code": "vernier_caliper_150mm", "name": "เวอร์เนียร์ 150 มม.", "bbox_norm": [0.47, 0.51, 0.6, 0.6]},
    {"slot_number": 9, "code": "wheel_aligner_nouvo_mio", "name": "เครื่องมือตั้งศูนย์ล้อ Nouvo/Mio", "bbox_norm": [0.26, 0.12, 0.31, 0.29]},
    {"slot_number": 10, "code": "adjustable_wrench_300mm", "name": "ประแจเลื่อน 300 มม.", "bbox_norm": [0.57, 0.14, 0.61, 0.48]},
    {"slot_number": 11, "code": "impact_driver_ktc_sd6", "name": "ไขควงตอก KTC SD6", "bbox_norm": [0.43, 0.36, 0.52, 0.48]},
    {"slot_number": 12, "code": "punch_chisel_set", "name": "ชุดเหล็กสกัดและตอก", "bbox_norm": [0.48, 0.28, 0.53, 0.42]},
    {"slot_number": 13, "code": "digital_torque_wrench", "name": "ประแจปอนด์ดิจิตอล", "bbox_norm": [0.4, 0.75, 0.61, 0.82]},
    {"slot_number": 14, "code": "hex_impact_bit_socket_set", "name": "ชุดลูกบ๊อกซ์ลมเดือยหกเหลี่ยม", "bbox_norm": [0.4, 0.19, 0.56, 0.29]},
    {"slot_number": 15, "code": "preset_torque_wrench", "name": "ประแจปอนด์ออโตเมติก", "bbox_norm": [0.45, 0.6, 0.61, 0.7]},
    {"slot_number": 16, "code": "flywheel_puller_2way", "name": "ตัวดูดจานไฟ 2 ทาง", "bbox_norm": [0.68, 0.54, 0.75, 0.67]},
    {"slot_number": 17, "code": "flywheel_puller_round", "name": "ตัวดูดจานไฟแบบกลม", "bbox_norm": [0.11, 0.46, 0.27, 0.69]},
    {"slot_number": 18, "code": "clutch_spring_compressor", "name": "เครื่องมือจับสปริงชุดผ้าคลัทช์", "bbox_norm": [0.76, 0.46, 0.89, 0.76]},
    {"slot_number": 19, "code": "cam_sprocket_holder", "name": "ตัวล็อกเฟืองเพลาลูกเบี้ยว", "bbox_norm": [0.62, 0.48, 0.68, 0.82]},
    {"slot_number": 20, "code": "valve_adjuster_l_wrench", "name": "ประแจ L ล็อกสกรูปรับตั้งวาล์ว", "bbox_norm": [0.37, 0.24, 0.48, 0.38]},
    {"slot_number": 21, "code": "bearing_puller_internal_2leg", "name": "ชุดถอดลูกปืนรูในแบบ 2 ขา Mio/Nouvo", "bbox_norm": [0.11, 0.13, 0.25, 0.42]},
    {"slot_number": 22, "code": "oil_filter_wrench_64mm", "name": "บ๊อกซ์ถอดกรองน้ำมันเครื่อง 64 มม.", "bbox_norm": [0.53, 0.23, 0.58, 0.37]},
    {"slot_number": 23, "code": "flywheel_puller_r3", "name": "ตัวดูดจานไฟ R3", "bbox_norm": [0.68, 0.67, 0.75, 0.79]},
    {"slot_number": 24, "code": "rear_clutch_wrench_46", "name": "เครื่องมือถอดชุดคลัทช์หลัง เบอร์ 46", "bbox_norm": [0.83, 0.72, 0.89, 0.82]},
    {"slot_number": 25, "code": "crankshaft_bearing_installer", "name": "ชุดประกอบแบริ่งข้อเหวี่ยง X-MAX", "bbox_norm": [0.11, 0.67, 0.27, 0.83]},
    {"slot_number": 26, "code": "usd_fork_assembly_tool", "name": "ด้ามขันแกนโช๊คหน้า USD", "bbox_norm": [0.35, 0.36, 0.39, 0.77]},
    {"slot_number": 27, "code": "digital_multimeter", "name": "มัลติมิเตอร์แบบดิจิตอล", "bbox_norm": [0.4, 0.48, 0.46, 0.71]},
    {"slot_number": 28, "code": "pulley_socket", "name": "ลูกบ๊อกซ์ถอดพู่เลย์", "bbox_norm": [0.78, 0.7, 0.83, 0.82]},
    {"slot_number": 29, "code": "crankcase_splitter_separator", "name": "เครื่องมือแยกแคร้ง", "bbox_norm": [0.18, 0.57, 0.27, 0.76]},
    {"slot_number": 30, "code": "steering_stem_wrench", "name": "เครื่องมือขันคอรถ", "bbox_norm": [0.28, 0.4, 0.33, 0.58]},
    {"slot_number": 31, "code": "crankshaft_installer", "name": "เครื่องมือประกอบเพลาข้อเหวี่ยง", "bbox_norm": [0.28, 0.57, 0.37, 0.83]}
]

boxes = upload_data.get("boxes", [])
w_canvas = int(upload_data.get("width", 3840))
h_canvas = int(upload_data.get("height", 2880))

print(f"Loaded {len(boxes)} boxes for {TRAY_ID} (Canvas: {w_canvas}x{h_canvas})")

def decode_coco_rle(counts_str, h, w):
    m = len(counts_str)
    counts = []
    p = 0
    while p < m:
        x = 0
        k = 0
        more = 1
        while more:
            c = ord(counts_str[p]) - 48
            x |= (c & 0x1f) << (5 * k)
            more = c & 0x20
            p += 1
            k += 1
            if not more and (c & 0x10):
                x |= (-1 << (5 * k))
        if len(counts) > 2:
            x += counts[-2]
        counts.append(x)
    mask = np.zeros(h * w, dtype=np.uint8)
    cur = 0
    val = 0
    for cnt in counts:
        mask[cur:cur + cnt] = val
        cur += cnt
        val = 1 - val
    return mask.reshape((w, h)).T

# Load reference image
ref_image = cv2.imread(str(REF_IMG_PATH))
if ref_image is None:
    raise FileNotFoundError(f"Cannot load reference image: {REF_IMG_PATH}")
if ref_image.shape[1] != w_canvas or ref_image.shape[0] != h_canvas:
    ref_image = cv2.resize(ref_image, (w_canvas, h_canvas), interpolation=cv2.INTER_LANCZOS4)

# Map sections based on X, Y coordinates
def get_section_info(cx, cy):
    # Board width is 3840, height is 2880
    if cx < 1000:
        if cy < 1500:
            return "เครื่องมือถอดชุดลูกปืน (Bearing Puller)"
        else:
            return "เครื่องมือถอดชุดเพลาข้อเหวี่ยง (Crankshaft Tools)"
    elif cx < 1550:
        return "เครื่องมือถอดชุดโครงรถ (Chassis Tools)"
    elif cx < 2350:
        if cy < 1550:
            return "เครื่องมือชุดอเนกประสงค์ (Universal Tools)"
        else:
            return "เครื่องมือวัดทางกล และ ไฟฟ้า (Mechanical & Electrical)"
    elif cx < 3050:
        if cy < 1550:
            return "เครื่องมือชุดถอดฝาสูบ (Cylinder Head Tools)"
        else:
            return "เครื่องมือถอดล้อแม่เหล็ก (Magneto Puller)"
    else:
        return "เครื่องมือถอดชุดส่งกำลัง (Transmission Tools)"

# Sort boxes logically by section (X) then vertical position (Y)
sorted_boxes = sorted(boxes, key=lambda b: (round(float(b["x"]) / 600.0), float(b["y"])))

blueprint = np.full((h_canvas, w_canvas, 3), (28, 24, 22), dtype=np.uint8)

slots = []
for idx, b in enumerate(sorted_boxes, start=1):
    b_id = b["id"]
    label = b.get("label", "tool")
    cx = float(b["x"])
    cy = float(b["y"])
    bw = float(b["width"])
    bh = float(b["height"])

    # Decode mask
    rle_str = zlib.decompress(base64.b64decode(b["mask"])).decode("ascii", errors="ignore")
    bin_mask = decode_coco_rle(rle_str, h_canvas, w_canvas)

    cnts, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if cnts:
        c = max(cnts, key=cv2.contourArea)
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.005 * peri, True)
        polygon = [[round(float(pt[0][0]), 1), round(float(pt[0][1]), 1)] for pt in approx]

        rect = cv2.minAreaRect(c)
        angle = rect[2]
        rw, rh = rect[1]
        if rw < rh:
            angle = (angle + 90.0) % 180.0
    else:
        x1, y1 = cx - bw / 2.0, cy - bh / 2.0
        x2, y2 = cx + bw / 2.0, cy + bh / 2.0
        polygon = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
        angle = 0.0

    rad = np.radians(angle)
    orient_vec = [round(float(np.cos(rad)), 3), round(float(np.sin(rad)), 3)]

    # Normalized Bounding Box [x1, y1, x2, y2]
    x1_norm = max(0.0, round((cx - bw / 2.0) / w_canvas, 4))
    y1_norm = max(0.0, round((cy - bh / 2.0) / h_canvas, 4))
    x2_norm = min(1.0, round((cx + bw / 2.0) / w_canvas, 4))
    y2_norm = min(1.0, round((cy + bh / 2.0) / h_canvas, 4))
    bbox_norm = [x1_norm, y1_norm, x2_norm, y2_norm]

    # Find nearest tool from 31 reference tools
    best_old = None
    best_dist = 999.0
    ncx = (x1_norm + x2_norm) / 2.0
    ncy = (y1_norm + y2_norm) / 2.0
    for os_slot in REFERENCE_31_TOOLS:
        ob = os_slot["bbox_norm"]
        ocx = (ob[0] + ob[2]) / 2.0
        ocy = (ob[1] + ob[3]) / 2.0
        dist = np.hypot(ocx - ncx, ocy - ncy)
        if dist < best_dist:
            best_dist = dist
            best_old = os_slot

    category = get_section_info(cx, cy)
    if best_dist < 0.16 and best_old:
        tool_name = best_old["name"]
        tool_code = best_old["code"]
    else:
        tool_name = f"เครื่องมือพิเศษประจำตำแหน่ง {idx}"
        tool_code = f"special_tool_{idx:02d}"

    # Calculate tolerances based on tool size
    diag = np.hypot(bw, bh)
    center_tol = max(18.0, min(45.0, diag * 0.06))
    angle_tol = 20.0 if diag < 150 else 12.0
    iou_min = 0.45

    slot_entry = {
        "slot_number": idx,
        "box_id": b_id,
        "name": tool_name,
        "code": tool_code,
        "filename": f"{tool_code}.png",
        "category": category,
        "center": [round(cx, 1), round(cy, 1)],
        "size": [round(bw, 1), round(bh, 1)],
        "area": int(b.get("area", bw * bh)),
        "bbox_norm": bbox_norm,
        "polygon": polygon,
        "tolerance": {
            "center_px": round(center_tol, 1),
            "angle_deg": angle_tol,
            "iou_min": iou_min
        },
        "orientation_vec": orient_vec
    }
    slots.append(slot_entry)

    # Draw wireframe polygon on blueprint
    poly_pts = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))
    
    # Palette based on category
    if "ลูกปืน" in category:
        color = (255, 180, 0)       # Cyan/Blue
    elif "โครงรถ" in category:
        color = (0, 220, 255)       # Yellow
    elif "อเนกประสงค์" in category:
        color = (255, 100, 220)     # Magenta/Pink
    elif "ฝาสูบ" in category:
        color = (50, 255, 120)      # Green
    elif "เพลาข้อเหวี่ยง" in category:
        color = (0, 165, 255)       # Orange
    elif "ไฟฟ้า" in category:
        color = (180, 255, 50)      # Lime
    elif "ล้อแม่เหล็ก" in category:
        color = (255, 220, 100)     # Sky Blue
    else:
        color = (120, 150, 255)     # Coral Red

    cv2.polylines(blueprint, [poly_pts], isClosed=True, color=color, thickness=3, lineType=cv2.LINE_AA)
    cv2.circle(blueprint, (int(cx), int(cy)), 5, color, -1)
    
    # Slot number badge
    cv2.putText(blueprint, str(idx), (int(cx) - 14, int(cy) + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)

# Draw board border and corner markers
cv2.rectangle(blueprint, (50, 50), (w_canvas - 50, h_canvas - 50), (0, 210, 255), 4)
arm = 140
for (cx_c, cy_c, dx, dy) in [
    (50, 50, 1, 1),
    (w_canvas - 50, 50, -1, 1),
    (50, h_canvas - 50, 1, -1),
    (w_canvas - 50, h_canvas - 50, -1, -1)
]:
    cv2.line(blueprint, (cx_c, cy_c), (cx_c + dx * arm, cy_c), (0, 255, 255), 8)
    cv2.line(blueprint, (cx_c, cy_c), (cx_c, cy_c + dy * arm), (0, 255, 255), 8)

# Output paths
out_dir = Path("data/tray_refs")
out_dir.mkdir(parents=True, exist_ok=True)

sketch_path = out_dir / f"{TRAY_ID}_sketch.png"
overlay_path = Path(f"reports/blueprints/blueprint_overlay_{TRAY_ID}.jpg")

cv2.imwrite(str(sketch_path), blueprint)
overlay = cv2.addWeighted(ref_image, 0.65, blueprint, 0.35, 0)
cv2.imwrite(str(overlay_path), overlay)

# Save template JSON
template_dict = {
    "tray_id": TRAY_ID,
    "tray_name": TRAY_ID,
    "description": f"แผงแขวนเครื่องมือพิเศษ Yamaha ชุด {TRAY_ID} ({len(slots)} ช่องตำแหน่ง) พร้อมพิกัด Polygon จาก Mask แม่นยำ",
    "version": "1.0.1",
    "image_size": [w_canvas, h_canvas],
    "image_width": w_canvas,
    "image_height": h_canvas,
    "slot_count": len(slots),
    "total_slots": len(slots),
    "reference_image": f"data/tray_refs/{TRAY_ID}.jpg",
    "sketch_image": f"data/tray_refs/{TRAY_ID}_sketch.png",
    "slots": slots,
    "tools": slots
}

out_json = Path(f"data/tray_templates/{TRAY_ID}.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(template_dict, f, ensure_ascii=False, indent=2)

print(f"[SUCCESS] Updated {out_json} with {len(slots)} slots!")
print(f"[SUCCESS] Saved sketch image: {sketch_path}")
print(f"[SUCCESS] Saved overlay image: {overlay_path}")
