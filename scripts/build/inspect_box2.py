import json
from pathlib import Path

DATA_PATH = Path(r"c:\MyProject\Webpark\dataYamaha\Merchecklist\Tools\ตำแหน่งอุปกรณ์\31\new data2.txt")
if not DATA_PATH.exists():
    DATA_PATH = Path(r"c:\MyProject\Webpark\dataYamaha\Merchecklist\Tools\ตำแหน่งอุปกรณ์\31\Annotation Data.txt")

with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

boxes = data.get("boxes", [])
print(f"Total boxes: {len(boxes)} from {DATA_PATH.name}")
for i, b in enumerate(boxes, 1):
    print(f"{i:2d}. id={b.get('id')} label={b.get('label'):<12} x={float(b.get('x')):6.1f} y={float(b.get('y')):6.1f} w={float(b.get('width')):5.1f} h={float(b.get('height')):5.1f}")
