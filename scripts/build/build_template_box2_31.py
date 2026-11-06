import json
import base64
import zlib
import numpy as np
import cv2
import os
from pathlib import Path

# Paths
json_source = r"C:\Users\polwa\.gemini\antigravity-ide\brain\e94903e8-e625-4570-b6b1-d9946b7ac04a\.user_uploaded\media_1793037046330.txt"
user_img_path = r"C:\Users\polwa\.gemini\antigravity-ide\brain\e94903e8-e625-4570-b6b1-d9946b7ac04a\.user_uploaded\media_1793037021990.png"
tray_id = "box2-template01_31-item"

with open(json_source, "r", encoding="utf-8") as f:
    upload_data = json.load(f)

# Load existing 31 tools database
with open("mock_database/tray_templates/tray_special_tools_31.json", "r", encoding="utf-8") as f:
    old_31_data = json.load(f)

old_slots = old_31_data.get("slots", [])
boxes = upload_data.get("boxes", [])
w_canvas = int(upload_data.get("width", 3840))
h_canvas = int(upload_data.get("height", 2880))

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

# Resize user reference image to canvas size
orig_img = cv2.imread(user_img_path)
if orig_img is None:
    raise FileNotFoundError(f"Cannot load user image: {user_img_path}")
ref_image = cv2.resize(orig_img, (w_canvas, h_canvas), interpolation=cv2.INTER_LANCZOS4)

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

    # Find nearest tool from old 31 tools for name matching
    best_old = None
    best_dist = 999.0
    ncx = (x1_norm + x2_norm) / 2.0
    ncy = (y1_norm + y2_norm) / 2.0
    for os_slot in old_slots:
        ob = os_slot["bbox_norm"]
        ocx = (ob[0] + ob[2]) / 2.0
        ocy = (ob[1] + ob[3]) / 2.0
        dist = np.hypot(ocx - ncx, ocy - ncy)
        if dist < best_dist:
            best_dist = dist
            best_old = os_slot

    category = get_section_info(cx, cy)
    if best_dist < 0.12 and best_old:
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

# Save images
out_dir = Path("admin_data/tray_refs")
out_dir.mkdir(parents=True, exist_ok=True)

ref_path = out_dir / f"{tray_id}.jpg"
sketch_path = out_dir / f"{tray_id}_sketch.png"
overlay_path = Path(f"admin_data/blueprint_overlay_{tray_id}.jpg")

cv2.imwrite(str(ref_path), ref_image)
cv2.imwrite(str(sketch_path), blueprint)
overlay = cv2.addWeighted(ref_image, 0.65, blueprint, 0.35, 0)
cv2.imwrite(str(overlay_path), overlay)

# Save template JSON
template_dict = {
    "tray_id": tray_id,
    "tray_name": tray_id,
    "description": f"แผงแขวนเครื่องมือพิเศษ Yamaha ชุด {tray_id} ({len(slots)} รายการ) พร้อมตำแหน่งและพิกัด Polygon จาก Mask แม่นยำ",
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

out_json = Path(f"mock_database/tray_templates/{tray_id}.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(template_dict, f, ensure_ascii=False, indent=2)

print(f"[SUCCESS] Created {out_json} with {len(slots)} slots!")
print(f"[SUCCESS] Saved reference image: {ref_path}")
print(f"[SUCCESS] Saved sketch image: {sketch_path}")
