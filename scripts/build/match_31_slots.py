import json
import numpy as np
from pathlib import Path

# Load raw upload
DATA_PATH = Path(r"c:\MyProject\Webpark\dataYamaha\Merchecklist\Tools\ตำแหน่งอุปกรณ์\31\new data2.txt")
if not DATA_PATH.exists():
    DATA_PATH = Path(r"c:\MyProject\Webpark\dataYamaha\Merchecklist\Tools\ตำแหน่งอุปกรณ์\31\Annotation Data.txt")

with open(DATA_PATH, "r", encoding="utf-8") as f:
    upload_data = json.load(f)

# Load existing 31 template
TEMPLATE_PATH = Path("mock_database/tray_templates/box2-template01_31-item.json")
with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    template_data = json.load(f)

template_slots = template_data.get("slots", [])
new_boxes = upload_data.get("boxes", [])

print(f"Template slots count: {len(template_slots)}")
print(f"Uploaded boxes count: {len(new_boxes)}")

# Calculate normalized boxes for new boxes
w_canvas = float(upload_data.get("width", 3840.0))
h_canvas = float(upload_data.get("height", 2880.0))

new_parsed = []
for b in new_boxes:
    cx = float(b["x"])
    cy = float(b["y"])
    bw = float(b["width"])
    bh = float(b["height"])
    x1 = (cx - bw / 2.0) / w_canvas
    y1 = (cy - bh / 2.0) / h_canvas
    x2 = (cx + bw / 2.0) / w_canvas
    y2 = (cy + bh / 2.0) / h_canvas
    new_parsed.append({
        "id": b["id"],
        "label": b["label"],
        "bbox_norm": [round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4)],
        "cx": cx, "cy": cy, "bw": bw, "bh": bh
    })

# Check IoU or center distance between new boxes and template slots
matches = []
for nb in new_parsed:
    best_slot = None
    best_dist = 999.0
    for ts in template_slots:
        ob = ts["bbox_norm"]
        ocx = (ob[0] + ob[2]) / 2.0
        ocy = (ob[1] + ob[3]) / 2.0
        ncx = (nb["bbox_norm"][0] + nb["bbox_norm"][2]) / 2.0
        ncy = (nb["bbox_norm"][1] + nb["bbox_norm"][3]) / 2.0
        dist = np.hypot(ocx - ncx, ocy - ncy)
        if dist < best_dist:
            best_dist = dist
            best_slot = ts
    if best_dist < 0.05:
        matches.append((nb["id"], best_slot["slot_number"], best_slot["name"], best_slot["code"], best_dist))
    else:
        matches.append((nb["id"], None, "New Tool / Subpart", "new_tool", best_dist))

for m in matches:
    print(f"Box {m[0]:>3}: matched slot {str(m[1]):>2} - {m[3]:<30} (dist={m[4]:.4f})")
