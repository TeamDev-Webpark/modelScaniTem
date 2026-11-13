"""วัดความแม่นยำของการจำเครื่องมือชิ้นเดี่ยว (core/tool_recognizer.py)

ตัดเครื่องมือแต่ละช่องออกจากภาพต้นแบบของกล่อง (data/tray_refs) ที่มีภาพสินค้าใน admin_data/images
แล้วดูว่าระบบจำรหัสอะไหล่ได้ถูกไหม

    python scripts/eval/test_tool_recognizer.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from core.config import REPORTS_DIR, TRAY_REFS_DIR, TRAY_TEMPLATES_DIR  # noqa: E402
from core import tool_recognizer as R  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    t = time.time()
    refs = {R.part_number_of(x["name"]) for x in R.get_scanner().templates}
    print(f"โหลดภาพสินค้า {len(R.get_scanner().templates)} ภาพ ({len(refs)} รหัส) ใน {time.time() - t:.1f} วินาที")
    rows = []
    for tpl_path in sorted(TRAY_TEMPLATES_DIR.glob("*.json")):
        tpl = json.loads(tpl_path.read_text(encoding="utf-8"))
        img = cv2.imread(str(TRAY_REFS_DIR / f"{tpl_path.stem}.jpg"))
        sx, sy = img.shape[1] / tpl["image_width"], img.shape[0] / tpl["image_height"]
        for s in tpl["slots"]:
            pn = (s.get("part_number") or "").replace(" ", "")
            if pn not in refs:
                continue
            pts = np.array(s["polygon"]) * [sx, sy]
            x1, y1 = np.maximum(pts.min(0).astype(int) - 20, 0)
            x2, y2 = pts.max(0).astype(int) + 20
            crop = img[y1:y2, x1:x2]
            t = time.time()
            found = R.recognize(crop, tiling=False)
            rows.append({"tray": tpl_path.stem, "slot": s["slot_number"], "part_number": pn,
                         "top": found[0]["part_number"] if found else None,
                         "top_score": found[0]["score"] if found else 0,
                         "in_results": pn in [f["part_number"] for f in found],
                         "n_results": len(found), "sec": round(time.time() - t, 2)})
    n = len(rows)
    top1 = sum(r["top"] == r["part_number"] for r in rows)
    anywhere = sum(r["in_results"] for r in rows)
    none = sum(r["top"] is None for r in rows)
    print(f"ทดสอบ {n} ช่อง: ถูกเป็นอันดับ 1 = {top1} ({top1 / n:.0%}), อยู่ในผลลัพธ์ = {anywhere} ({anywhere / n:.0%}), "
          f"ไม่พบอะไรเลย = {none}, เวลาเฉลี่ย {sum(r['sec'] for r in rows) / n:.2f} วินาที/ภาพ")
    out = REPORTS_DIR / "tool_recognizer_accuracy.json"
    out.write_text(json.dumps({"tested": n, "top1": top1, "in_results": anywhere, "none": none, "rows": rows},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"บันทึกผลที่ {out}")


if __name__ == "__main__":
    main()
