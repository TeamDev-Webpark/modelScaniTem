import sys as _sys
if "--i-know-this-overwrites-data" not in _sys.argv:
    _sys.exit("Legacy script, disabled: it overwrites the 16-item reference photo with an annotated image from a deleted upload folder. "
              "See scripts/legacy/README.md. Pass --i-know-this-overwrites-data to run it anyway.")

import json
import base64
import zlib
import numpy as np
import cv2
import os

# Path to the uploaded raw annotation JSON
json_source = r"C:\Users\polwa\.gemini\antigravity-ide\brain\e94903e8-e625-4570-b6b1-d9946b7ac04a\.user_uploaded\media_1792608588941.txt"
with open(json_source, "r", encoding="utf-8") as f:
    data = json.load(f)

boxes = data["boxes"]
w_canvas = int(data.get("width", 3840))
h_canvas = int(data.get("height", 2880))
tray_id = "box1-template02_16-item"

print(f"Loaded {len(boxes)} boxes for {tray_id} (Canvas: {w_canvas}x{h_canvas})")

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

# Reference image from user upload
user_img_path = r"C:\Users\polwa\.gemini\antigravity-ide\brain\e94903e8-e625-4570-b6b1-d9946b7ac04a\.user_uploaded\media_1792608675737.jpg"
orig_img = cv2.imread(user_img_path)
ref_image = cv2.resize(orig_img, (w_canvas, h_canvas), interpolation=cv2.INTER_LANCZOS4)

# Create blueprint wireframe sketch
blueprint = np.full((h_canvas, w_canvas, 3), (32, 28, 24), dtype=np.uint8)

# Map labels to readable Thai & English names
tool_label_map = {
    "hammer": "ค้อน (Hammer)",
    "pliers": "คีม (Pliers)",
    "wrench": "ด้ามขัน/ประแจ (Wrench)",
    "screwdriver": "ไขควง (Screwdriver)",
    "hex key": "ชุดประแจหกเหลี่ยม (Hex Key Set)"
}

# Sort boxes logically by row (y) then column (x)
sorted_boxes = sorted(boxes, key=lambda b: (round(float(b["y"]) / 150.0), float(b["x"])))

slots = []
for idx, b in enumerate(sorted_boxes, start=1):
    b_id = b["id"]
    label = b["label"]
    cx = float(b["x"])
    cy = float(b["y"])
    bw = float(b["width"])
    bh = float(b["height"])

    # Decode mask
    rle_str = zlib.decompress(base64.b64decode(b["mask"])).decode('ascii', errors='ignore')
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

    # Normalized BBox
    x1_px = max(0.0, cx - bw / 2.0)
    y1_px = max(0.0, cy - bh / 2.0)
    x2_px = min(float(w_canvas), cx + bw / 2.0)
    y2_px = min(float(h_canvas), cy + bh / 2.0)
    bbox_norm = [
        round(x1_px / w_canvas, 4),
        round(y1_px / h_canvas, 4),
        round(x2_px / w_canvas, 4),
        round(y2_px / h_canvas, 4),
    ]

    # Name and tolerances
    readable_name = tool_label_map.get(label, label.capitalize())
    name_th = f"{readable_name} #{idx} ({b_id})"
    part_no = f"TRAY2-{idx:02d}"

    if label == "hex key":
        center_tol = max(25.0, min(bw, bh) * 0.15)
        angle_tol = 12.0
        iou_min = 0.40
    elif label == "hammer":
        center_tol = max(30.0, min(bw, bh) * 0.12)
        angle_tol = 15.0
        iou_min = 0.42
    elif label == "pliers":
        center_tol = max(25.0, min(bw, bh) * 0.15)
        angle_tol = 16.0
        iou_min = 0.40
    elif label == "screwdriver":
        center_tol = max(20.0, min(bw, bh) * 0.15)
        angle_tol = 15.0
        iou_min = 0.38
    else:
        center_tol = max(25.0, min(bw, bh) * 0.15)
        angle_tol = 15.0
        iou_min = 0.40

    slot_entry = {
        "slot_number": idx,
        "part_number": part_no,
        "name": name_th,
        "code": part_no,
        "class_key": label,
        "code_id": b_id,
        "category": label,
        "expected_class": label,
        "filename": f"{part_no}.png",
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
    if label == "hammer":
        color = (0, 180, 255)       # Orange
    elif label == "pliers":
        color = (0, 255, 180)       # Cyan/Green
    elif label == "hex key":
        color = (255, 200, 0)       # Blue/Cyan
    elif label == "screwdriver":
        color = (255, 100, 255)     # Magenta
    else:
        color = (0, 255, 100)       # Green

    cv2.polylines(blueprint, [poly_pts], isClosed=True, color=color, thickness=4, lineType=cv2.LINE_AA)
    cv2.circle(blueprint, (int(cx), int(cy)), 6, color, -1)
    cv2.putText(blueprint, str(idx), (int(cx) - 16, int(cy) + 12), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 3, cv2.LINE_AA)

# Draw alignment border
cv2.rectangle(blueprint, (40, 40), (w_canvas - 40, h_canvas - 40), (0, 220, 255), 4)
arm = 120
cv2.line(blueprint, (40, 40), (40 + arm, 40), (0, 255, 255), 8)
cv2.line(blueprint, (40, 40), (40, 40 + arm), (0, 255, 255), 8)
cv2.line(blueprint, (w_canvas - 40, 40), (w_canvas - 40 - arm, 40), (0, 255, 255), 8)
cv2.line(blueprint, (w_canvas - 40, 40), (w_canvas - 40, 40 + arm), (0, 255, 255), 8)
cv2.line(blueprint, (40, h_canvas - 40), (40 + arm, h_canvas - 40), (0, 255, 255), 8)
cv2.line(blueprint, (40, h_canvas - 40), (40, h_canvas - 40 - arm), (0, 255, 255), 8)
cv2.line(blueprint, (w_canvas - 40, h_canvas - 40), (w_canvas - 40 - arm, h_canvas - 40), (0, 255, 255), 8)
cv2.line(blueprint, (w_canvas - 40, h_canvas - 40), (w_canvas - 40, h_canvas - 40 - arm), (0, 255, 255), 8)

# Save images
os.makedirs("admin_data/tray_refs", exist_ok=True)
cv2.imwrite(f"admin_data/tray_refs/{tray_id}.jpg", ref_image)
cv2.imwrite(f"admin_data/tray_refs/{tray_id}_sketch.png", blueprint)
overlay = cv2.addWeighted(ref_image, 0.65, blueprint, 0.35, 0)
cv2.imwrite(f"admin_data/blueprint_overlay_{tray_id}.jpg", overlay)

# Save template JSON
template_dict = {
    "tray_id": tray_id,
    "tray_name": tray_id,
    "description": f"ถาดโฟมเครื่องมือชุด {tray_id} ({len(slots)} รายการ) พร้อมตำแหน่งและพิกัด Polygon จาก Mask แม่นยำ",
    "version": "1.0.0",
    "image_size": [w_canvas, h_canvas],
    "image_width": w_canvas,
    "image_height": h_canvas,
    "slot_count": len(slots),
    "total_slots": len(slots),
    "reference_image": f"admin_data/tray_refs/{tray_id}.jpg",
    "sketch_image": f"admin_data/tray_refs/{tray_id}_sketch.png",
    "slots": slots,
    "tools": slots
}

out_json = f"mock_database/tray_templates/{tray_id}.json"
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(template_dict, f, ensure_ascii=False, indent=2)

print(f"Generated {tray_id}.json with {len(slots)} slots successfully!")
