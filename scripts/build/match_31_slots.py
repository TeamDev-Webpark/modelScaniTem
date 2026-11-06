import json
import numpy as np

# Load raw upload
with open(r'C:\Users\polwa\.gemini\antigravity-ide\brain\e94903e8-e625-4570-b6b1-d9946b7ac04a\.user_uploaded\media_1793037046330.txt', 'r', encoding='utf-8') as f:
    upload_data = json.load(f)

# Load existing 31 template
with open('mock_database/tray_templates/tray_special_tools_31.json', 'r', encoding='utf-8') as f:
    old_31_data = json.load(f)

old_slots = old_31_data.get('slots', [])
new_boxes = upload_data.get('boxes', [])

print(f"Old 31 slots count: {len(old_slots)}")
print(f"New uploaded boxes count: {len(new_boxes)}")

# Calculate normalized boxes for new boxes
w_canvas = 3840.0
h_canvas = 2880.0

new_parsed = []
for b in new_boxes:
    cx = float(b['x'])
    cy = float(b['y'])
    bw = float(b['width'])
    bh = float(b['height'])
    x1 = (cx - bw/2.0) / w_canvas
    y1 = (cy - bh/2.0) / h_canvas
    x2 = (cx + bw/2.0) / w_canvas
    y2 = (cy + bh/2.0) / h_canvas
    new_parsed.append({
        'id': b['id'],
        'label': b['label'],
        'bbox_norm': [round(x1, 3), round(y1, 3), round(x2, 3), round(y2, 3)],
        'cx': cx, 'cy': cy, 'bw': bw, 'bh': bh
    })

# Check IoU or center distance between new boxes and old 31 slots
matched = 0
matches = []
for nb in new_parsed:
    best_old = None
    best_dist = 999.0
    for os in old_slots:
        ob = os['bbox_norm']
        # center of old
        ocx = (ob[0] + ob[2]) / 2.0
        ocy = (ob[1] + ob[3]) / 2.0
        # center of new
        ncx = (nb['bbox_norm'][0] + nb['bbox_norm'][2]) / 2.0
        ncy = (nb['bbox_norm'][1] + nb['bbox_norm'][3]) / 2.0
        dist = np.hypot(ocx - ncx, ocy - ncy)
        if dist < best_dist:
            best_dist = dist
            best_old = os
    if best_dist < 0.10: # within 10% distance
        matches.append((nb['id'], best_old['slot_number'], best_old['name'], best_old['code'], best_dist))
    else:
        matches.append((nb['id'], None, "New Tool / Subpart", "new_tool", best_dist))

for m in matches:
    print(f"Box {m[0]:>3}: matched slot {str(m[1]):>2} - {m[3]:<30} (dist={m[4]:.3f})")
