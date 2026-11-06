import json

with open(r'C:\Users\polwa\.gemini\antigravity-ide\brain\e94903e8-e625-4570-b6b1-d9946b7ac04a\.user_uploaded\media_1793037046330.txt', 'r', encoding='utf-8') as f:
    data = json.load(f)

boxes = data.get("boxes", [])
print(f"Total boxes: {len(boxes)}")
for i, b in enumerate(boxes, 1):
    print(f"{i:2d}. id={b.get('id')} label={b.get('label'):<12} x={float(b.get('x')):6.1f} y={float(b.get('y')):6.1f} w={float(b.get('width')):5.1f} h={float(b.get('height')):5.1f}")
