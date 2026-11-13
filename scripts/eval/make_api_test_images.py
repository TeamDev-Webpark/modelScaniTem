"""สร้างชุดภาพทดสอบ API พร้อมผลที่คาดหวัง (สำหรับ Software tester)

สร้างจากภาพต้นแบบใน data/tray_refs/ แล้วรันผ่าน /api/v1/scan/tray เพื่อบันทึกผลจริงลง manifest.json

    python scripts/eval/make_api_test_images.py            # สร้างภาพ + manifest
    python scripts/eval/make_api_test_images.py --check    # ตรวจภาพที่มีอยู่กับ manifest อีกครั้ง

ผลลัพธ์: data/test_images/api/*.jpg และ data/test_images/api/manifest.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
logging.disable(logging.CRITICAL)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from core.config import TRAY_REFS_DIR, TRAY_TEMPLATES_DIR  # noqa: E402

OUT = ROOT / "data" / "test_images" / "api"
MAX_W = 1920  # ย่อภาพเพื่อให้ไฟล์เล็ก (ภาพต้นแบบ 3840px)
REMOVE = {  # ช่องที่ "เอาเครื่องมือออก" ในภาพทดสอบ
    "box1-template01_70-item": [3, 40],
    "box1-template02_16-item": [5],
    "box2-template01_31-item": [1, 12],
}


def _resize(img):
    if img.shape[1] <= MAX_W:
        return img
    s = MAX_W / img.shape[1]
    return cv2.resize(img, (MAX_W, int(round(img.shape[0] * s))), interpolation=cv2.INTER_AREA)


def _remove_slots(full, empty, tpl, slot_nos):
    """วางพื้นที่ช่องจากภาพถาดว่างทับภาพถาดเต็ม = จำลองเครื่องมือหาย"""
    out = full.copy()
    sx, sy = full.shape[1] / tpl["image_width"], full.shape[0] / tpl["image_height"]
    for s in tpl["slots"]:
        if s["slot_number"] in slot_nos:
            mask = np.zeros(full.shape[:2], np.uint8)
            pts = np.array([[x * sx, y * sy] for x, y in s["polygon"]], np.int32)
            cv2.fillPoly(mask, [pts], 255)
            mask = cv2.dilate(mask, np.ones((9, 9), np.uint8))
            out[mask > 0] = empty[mask > 0]
    return out


def build_cases():
    cases = []
    for tray, removed in REMOVE.items():
        tpl = json.loads((TRAY_TEMPLATES_DIR / f"{tray}.json").read_text(encoding="utf-8"))
        full = cv2.imread(str(TRAY_REFS_DIR / f"{tray}.jpg"))
        empty = cv2.imread(str(TRAY_REFS_DIR / f"{tray}_empty.jpg"))
        short = tray.split("-")[0] + "_" + tray.split("_")[-1]  # box1_70-item
        imgs = {
            f"{short}_01_full.jpg": (full, "ถาดครบทุกช่อง"),
            f"{short}_02_missing.jpg": (_remove_slots(full, empty, tpl, removed), f"เอาเครื่องมือออก ช่อง {removed}"),
            f"{short}_03_empty.jpg": (empty, "ถาดว่าง ไม่มีเครื่องมือ"),
            f"{short}_04_portrait.jpg": (cv2.rotate(full, cv2.ROTATE_90_CLOCKWISE), "ถาดครบ ถ่ายแนวตั้ง (หมุน 90°)"),
        }
        if tray == "box2-template01_31-item":
            imgs[f"{short}_05_upside_down.jpg"] = (cv2.rotate(full, cv2.ROTATE_180), "ถาดครบ กลับหัว (หมุน 180°)")
            imgs[f"{short}_06_blurred.jpg"] = (cv2.GaussianBlur(full, (0, 0), 25), "ภาพเบลอมาก")
            imgs[f"{short}_07_dark.jpg"] = ((full * 0.08).astype(np.uint8), "ภาพมืดมาก")
            imgs[f"{short}_08_far.jpg"] = (_far(full), "ถ่ายไกล ถาดเล็กในภาพ")
        for name, (img, desc) in imgs.items():
            cases.append({"file": name, "tray_id": tray, "description": desc, "img": _resize(img),
                          "removed_slots": removed if "missing" in name else []})
    return cases


def _far(full):
    h, w = full.shape[:2]
    canvas = np.full((h, w, 3), (90, 95, 100), np.uint8)
    small = cv2.resize(full, (w // 2, h // 2))
    canvas[h // 4: h // 4 + h // 2, w // 4: w // 4 + w // 2] = small
    return canvas


async def scan_all(items):
    import httpx
    from api.main import app
    tr = httpx.ASGITransport(app=app)
    out = []
    async with httpx.AsyncClient(transport=tr, base_url="http://t", timeout=600) as c:
        for it in items:
            data = (OUT / it["file"]).read_bytes()
            r = await c.post("/api/v1/scan/tray", data={"tray_id": it["tray_id"], "return_annotated": "false"},
                             files={"image": (it["file"], data, "image/jpeg")})
            d = r.json()
            k = d["counters"]
            out.append({
                "http_status": r.status_code, "success": d["success"],
                "total_slots": k["total_slots"], "correct": k["correct"], "missing": k["missing"],
                "misplaced": k["misplaced"], "recheck": k["recheck"], "is_complete": k["is_complete"],
                "quality_passed": (d.get("quality") or {}).get("passed"),
                "not_correct_slots": sorted(s["slot_number"] for s in d["slots"] if s["status"] != "correct"),
                "error_message": d.get("error_message"),
            })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="scan existing images and compare with manifest")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    man_path = OUT / "manifest.json"

    if args.check:
        man = json.loads(man_path.read_text(encoding="utf-8"))
        got = asyncio.run(scan_all(man["cases"]))
        fails = 0
        for case, g in zip(man["cases"], got):
            exp = case["expected"]
            same = all(g[k] == exp[k] for k in ("http_status", "success", "correct", "missing", "misplaced", "recheck"))
            fails += not same
            print(f"{'PASS' if same else 'FAIL'} | {case['file']} | ครบ {g['correct']}/{g['total_slots']} หาย {g['missing']} ตรวจซ้ำ {g['recheck']}")
        print(f"\n{len(got) - fails}/{len(got)} ตรงกับ manifest")
        sys.exit(1 if fails else 0)

    OUT.mkdir(parents=True, exist_ok=True)
    cases = build_cases()
    for c in cases:
        cv2.imwrite(str(OUT / c["file"]), c.pop("img"), [cv2.IMWRITE_JPEG_QUALITY, 88])
    (OUT / "not_an_image.jpg").write_bytes(b"this is not an image")
    (OUT / "empty_file.jpg").write_bytes(b"")
    got = asyncio.run(scan_all(cases))
    for c, g in zip(cases, got):
        c["expected"] = g
        print(f"{c['file']:32} ครบ {g['correct']}/{g['total_slots']} หาย {g['missing']} ผิดที่ {g['misplaced']} "
              f"ตรวจซ้ำ {g['recheck']} | {(g['error_message'] or '')[:50]}")
    man = {
        "note": "expected = ผลจริงจาก API ตอนสร้างชุดภาพ ใช้เป็นค่าคาดหวังสำหรับ regression test",
        "extra_files": {"not_an_image.jpg": "ต้องได้ HTTP 400", "empty_file.jpg": "ต้องได้ HTTP 400"},
        "cases": cases,
    }
    man_path.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nเขียน {len(cases)} ภาพ + manifest ที่ {OUT}")


if __name__ == "__main__":
    main()
