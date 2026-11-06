import sys as _sys
if "--i-know-this-overwrites-data" not in _sys.argv:
    _sys.exit("Legacy script, disabled: it builds the old TRAY_YA_1_2 tray and overwrites data/classes_ya1_2_70_tools.json. "
              "See scripts/legacy/README.md. Pass --i-know-this-overwrites-data to run it anyway.")

import json
import cv2
import numpy as np
from pathlib import Path

# Tool metadata: (seq, part_number, name_th, class_key)
tools_info = [
    (1, "90843-08202", "ลูกบ๊อกซ์ 6 เหลี่ยม 3/8\" No.8", "hex_socket_3_8_no8"),
    (2, "90843-08203", "ลูกบ๊อกซ์ 6 เหลี่ยม 3/8\" No.10", "hex_socket_3_8_no10"),
    (3, "90843-08204", "ลูกบ๊อกซ์ 6 เหลี่ยม 3/8\" No.12", "hex_socket_3_8_no12"),
    (4, "90843-08205", "ลูกบ๊อกซ์ 6 เหลี่ยม 3/8\" No.13", "hex_socket_3_8_no13"),
    (5, "90843-08206", "ลูกบ๊อกซ์ 6 เหลี่ยม 3/8\" No.14", "hex_socket_3_8_no14"),
    (6, "90843-08207", "ลูกบ๊อกซ์ 6 เหลี่ยม 3/8\" No.17", "hex_socket_3_8_no17"),
    (7, "90843-08208", "ลูกบ๊อกซ์ 6 เหลี่ยม 3/8\" No.19", "hex_socket_3_8_no19"),
    (8, "90843-08209", "ลูกบ๊อกซ์ 6 เหลี่ยม 3/8\" No.21", "hex_socket_3_8_no21"),
    (9, "90843-08210", "ลูกบ๊อกซ์ 6 เหลี่ยม 3/8\" No.22", "hex_socket_3_8_no22"),
    (10, "90843-08211", "ลูกบ๊อกซ์หัวเทียน 3/8\" ขนาด 16 มม.", "spark_plug_socket_16mm"),
    (11, "90843-08212", "ลูกบ๊อกซ์หัวเทียน 3/8\" ขนาด 18 มม.", "spark_plug_socket_18mm"),
    (12, "90843-08213", "ลูกบ๊อกซ์หัวเทียน 3/8\" ขนาด 20.8 มม.", "spark_plug_socket_20_8mm"),
    (13, "90843-08214", "ลูกบ๊อกซ์ 6 เหลี่ยม 3/8\" ตัวยาว No.8", "deep_socket_3_8_no8"),
    (14, "90843-08215", "ลูกบ๊อกซ์ 6 เหลี่ยม 3/8\" ตัวยาว No.10", "deep_socket_3_8_no10"),
    (15, "90843-08216", "ลูกบ๊อกซ์ 6 เหลี่ยม 3/8\" ตัวยาว No.12", "deep_socket_3_8_no12"),
    (16, "90843-08217", "ลูกบ๊อกซ์ 6 เหลี่ยม 3/8\" ตัวยาว No.14", "deep_socket_3_8_no14"),
    (17, "90843-08218", "ไขควงแบน (จิ๋ว) 75 mm.", "mini_slotted_screwdriver_75mm"),
    (18, "90843-08219", "ด้ามต่อบ๊อกซ์ 3/8\" x 50 มม.", "extension_bar_3_8_50mm"),
    (19, "90843-08220", "ด้ามต่อบ๊อกซ์ 3/8\" x 75 มม.", "extension_bar_3_8_75mm"),
    (20, "90843-08221", "ด้ามต่อบ๊อกซ์ 3/8\" x 150 มม.", "extension_bar_3_8_150mm"),
    (21, "90843-08222", "ด้ามต่อบ๊อกซ์ ขันเร็ว 3/8\"", "quick_spinner_3_8"),
    (22, "90843-08223", "ด้ามขันเลื่อน 3/8\"", "sliding_t_handle_3_8"),
    (23, "90843-08224", "ข้อต่ออ่อน 3/8\"", "universal_joint_3_8"),
    (24, "90843-08225", "ด้ามขันฟรี 3/8\" x 7\"", "ratchet_handle_3_8_7in"),
    (25, "90843-08226", "ด้ามขันบ๊อกซ์ 3/8\" x 300 มม.", "breaker_bar_3_8_300mm"),
    (26, "90843-08227", "ไขควงแบน ก้านเล็ก 200 มม.", "slotted_screwdriver_thin_200mm"),
    (27, "90843-08228", "ไขควงแบน 75 มม.", "slotted_screwdriver_75mm"),
    (28, "90843-08229", "ไขควงแบน 100 มม.", "slotted_screwdriver_100mm"),
    (29, "90843-08230", "ไขควงแบน 150 มม.", "slotted_screwdriver_150mm"),
    (30, "90843-08231", "ไขควงแบน ป้อม 25 มม.", "stubby_slotted_screwdriver_25mm"),
    (31, "90843-08232", "ไขควงแฉก 75 มม.", "phillips_screwdriver_75mm"),
    (32, "90843-08233", "ไขควงแฉก 100 มม.", "phillips_screwdriver_100mm"),
    (33, "90843-08234", "ไขควงแฉก 150 มม.", "phillips_screwdriver_150mm"),
    (34, "90843-08235", "ไขควงแฉก ป้อม 25 มม.", "stubby_phillips_screwdriver_25mm"),
    (35, "90843-110M3", "ไขควงปากแฉก ก้านเล็กด้ามนุ่ม 1x150 มม.", "soft_grip_phillips_screwdriver_150mm"),
    (36, "90843-08238", "ประแจแหวน 8 x 10", "double_offset_ring_wrench_8x10"),
    (37, "90843-08239", "ประแจแหวน 10 x 12", "double_offset_ring_wrench_10x12"),
    (38, "90843-08240", "ประแจแหวน 12 x 14", "double_offset_ring_wrench_12x14"),
    (39, "90843-08241", "ประแจแหวน 14 x 17", "double_offset_ring_wrench_14x17"),
    (40, "90843-08242", "ประแจแหวน 17 x 19", "double_offset_ring_wrench_17x19"),
    (41, "90843-08243", "ประแจแหวน 22 x 24", "double_offset_ring_wrench_22x24"),
    (42, "90843-08244", "ประแจรวม No. 08", "combination_wrench_no8"),
    (43, "90843-08245", "ประแจรวม No. 10", "combination_wrench_no10"),
    (44, "90843-08246", "ประแจรวม No. 12", "combination_wrench_no12"),
    (45, "90843-08247", "ประแจรวม No. 14", "combination_wrench_no14"),
    (46, "90843-08248", "ประแจรวม No. 17", "combination_wrench_no17"),
    (47, "90843-08252", "ประแจปากตาย 6 x 7", "open_end_wrench_6x7"),
    (48, "90843-08253", "ประแจปากตาย 8 x 10", "open_end_wrench_8x10"),
    (49, "90843-08256", "ถาดล้างชิ้นส่วน มีแม่เหล็ก", "magnetic_parts_tray"),
    (50, "90843-08F04", "ลูกบล๊อคลม 3/8\" # 8 (ดำ)", "impact_socket_3_8_no8"),
    (51, "90843-08F05", "ลูกบล๊อคลม 3/8\" # 10 (ดำ)", "impact_socket_3_8_no10"),
    (52, "90843-08F06", "ลูกบล๊อคลม 3/8\" # 12 (ดำ)", "impact_socket_3_8_no12"),
    (53, "90843-08F07", "ลูกบล๊อคลม 3/8\" # 14 (ดำ)", "impact_socket_3_8_no14"),
    (54, "90843-08F08", "ลูกบล๊อคลม 3/8\" # 17 (ดำ)", "impact_socket_3_8_no17"),
    (55, "90843-08F09", "ลูกบล๊อคลม 3/8\" # 19 (ดำ)", "impact_socket_3_8_no19"),
    (56, "90843-08F10", "ลูกบล๊อคลม 3/8\" # 21 (ดำ)", "impact_socket_3_8_no21"),
    (57, "90843-08F11", "ลูกบล๊อคลม 3/8\" # 22 (ดำ)", "impact_socket_3_8_no22"),
    (58, "90843-08F23", "ข้อต่อบ็อกซ์ลมสำหรับใส่ดอกไขควง", "impact_bit_adapter_3_8"),
    (59, "90843-08F54", "ลูกบ๊อกซ์ลมเดือย 6 เหลี่ยม 3/8 # 4", "impact_hex_bit_socket_3_8_no4"),
    (60, "90843-08F55", "ลูกบ๊อกซ์ลมเดือย 6 เหลี่ยม 3/8 # 5", "impact_hex_bit_socket_3_8_no5"),
    (61, "90843-08F56", "ลูกบ๊อกซ์ลมเดือย 6 เหลี่ยม 3/8 # 6", "impact_hex_bit_socket_3_8_no6"),
    (62, "90843-08F62", "ประแจแหวน 8 - 10", "double_offset_ring_wrench_8_10"),
    (63, "90843-11011", "ประแจแหวนรวม No. 5.5", "combination_wrench_no5_5"),
    (64, "90843-11012", "ประแจแหวนรวม No. 6", "combination_wrench_no6"),
    (65, "90843-11060", "ลูกบ๊อกซ์ดอกจีบ เดือยมีรู 3/8\" T30", "torx_bit_socket_3_8_t30"),
    (66, "90843-11074", "ข้อต่อบ๊อกซ์ เพิ่ม 3/8\" - 1/2\"", "socket_adapter_3_8_to_1_2"),
    (67, "90843-110C5", "ลูกบ๊อกซ์ดอกจีบ เดือยมีรู 42 มม.T50", "torx_bit_socket_42mm_t50"),
    (68, "90843-13009", "ลูกบล๊อคลม 1/2\" No. 24", "impact_socket_1_2_no24"),
    (69, "90843-13013", "ข้อต่อลด จาก 1/2 ลด 3/8\"", "socket_reducer_1_2_to_3_8"),
    (70, "90843-21021", "ลูกบ๊อกซ์เดือยโผล่หัวหกเหลี่ยม 3 x 128", "hex_long_bit_socket_3x128")
]

# Read polygons from check_coords.py
with open("check_coords.py", "r", encoding="utf-8") as f:
    text = f.read()

start = text.find('polygons_raw = """') + len('polygons_raw = """')
end = text.find('"""\n\npolys')
polygons_json = json.loads(text[start:end].strip())

poly_map = {item["sequence"]: item["polygon"] for item in polygons_json}

# Image resolution
IMG_W = 3840
IMG_H = 2880

slots = []
for seq, part_no, name_th, class_key in tools_info:
    polygon = poly_map.get(seq, [])
    if polygon:
        xs = [pt[0] for pt in polygon]
        ys = [pt[1] for pt in polygon]
        x1_norm = round(max(0.0, min(xs) / IMG_W), 4)
        y1_norm = round(max(0.0, min(ys) / IMG_H), 4)
        x2_norm = round(min(1.0, max(xs) / IMG_W), 4)
        y2_norm = round(min(1.0, max(ys) / IMG_H), 4)
    else:
        x1_norm, y1_norm, x2_norm, y2_norm = 0.0, 0.0, 1.0, 1.0

    # Calculate default orientation and tolerance based on tool geometry
    if polygon and len(polygon) >= 5:
        pts = np.array(polygon, dtype=np.float32)
        _, eigenvectors = cv2.PCACompute(pts, mean=None)
        pv = eigenvectors[0].tolist()
        orient_vec = [round(pv[0], 3), round(pv[1], 3)]
    else:
        orient_vec = [0.0, 1.0]

    # Assign tailored tolerance
    if "ลูกบ๊อกซ์" in name_th or "ลูกบล๊อค" in name_th:
        tol = {"center_px": 14, "angle_deg": 35.0, "iou_min": 0.40}
    elif "ประแจ" in name_th or "ไขควง" in name_th or "ด้าม" in name_th:
        tol = {"center_px": 16, "angle_deg": 18.0, "iou_min": 0.45}
    else:
        tol = {"center_px": 15, "angle_deg": 20.0, "iou_min": 0.42}

    slots.append({
        "slot_number": seq,
        "part_number": part_no,
        "name": name_th,
        "code": part_no,
        "class_key": class_key,
        "filename": f"{part_no}.png",
        "bbox_norm": [x1_norm, y1_norm, x2_norm, y2_norm],
        "polygon": polygon,
        "tolerance": tol,
        "orientation_vec": orient_vec
    })

tray_template = {
    "tray_id": "TRAY_YA_1_2",
    "tray_name": "ถาดเครื่องมือชุดที่ 1 (YA 1/2) 70 รายการ",
    "description": "ถาดโฟมเครื่องมือชุดที่ 1 (YA 1/2) ครบ 70 ช่อง พร้อมกรอบ Bounding Box และ Polygon",
    "image_size": [IMG_W, IMG_H],
    "slot_count": len(slots),
    "slots": slots
}

for fname in ["tray_ya1_2_70_tools.json", "TRAY_YA_1_2.json"]:
    out_tray_path = Path("mock_database/tray_templates") / fname
    out_tray_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_tray_path, "w", encoding="utf-8") as f:
        json.dump(tray_template, f, ensure_ascii=False, indent=2)
    print(f"Successfully generated {out_tray_path} with {len(slots)} slots!")

# Also generate a dataset/classes JSON file for these 70 tools
classes_70 = []
for seq, part_no, name_th, class_key in tools_info:
    category = "Hand Tools"
    if "ลูกบ๊อกซ์" in name_th or "ลูกบล๊อค" in name_th or "ด้ามต่อ" in name_th or "ด้ามขัน" in name_th or "ข้อต่อ" in name_th:
        category = "Sockets & Wrenches"
    elif "ไขควง" in name_th:
        category = "Screwdrivers"
    elif "ประแจ" in name_th:
        category = "Wrenches"
    elif "ถาด" in name_th:
        category = "Trays & Accessories"

    classes_70.append({
        "id": seq,
        "code": part_no,
        "name": name_th,
        "name_th": name_th,
        "name_en": class_key,
        "category": category,
        "description": f"ลำดับที่ {seq}: {name_th} (รหัส: {part_no})"
    })

out_classes_path = Path("mock_database/classes_ya1_2_70_tools.json")
with open(out_classes_path, "w", encoding="utf-8") as f:
    json.dump(classes_70, f, ensure_ascii=False, indent=2)

print(f"Successfully generated {out_classes_path} with {len(classes_70)} classes!")
