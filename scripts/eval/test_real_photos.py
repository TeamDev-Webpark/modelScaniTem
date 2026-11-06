"""Run the real scan pipeline on field photos and report what it finds.

For each photo it:
  - runs the quality gate (recorded only, the scan still runs)
  - tries every candidate tray template and keeps the one with the most alignment matches
    (so mixed folders of YA 1/2 and YA 2/2 trays are sorted automatically)
  - scans with the reference image the app uses today (data/tray_refs) and, if
    --photos is given, also with the clean tray photo, to compare the two
  - saves the annotated result and a report (json + csv)

Usage
  python scripts/test_real_photos.py --images <folder> --trays box1-template01_70-item,box1-template02_16-item
      [--photos <dir with <tray_id>.png / <tray_id>_full.png>] [--out reports/real_photo_test/86]
"""
import argparse
import csv
import json
import logging
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scan_workflow import ScanAggregator  # noqa: E402
from core.config import TRAY_REFS_DIR, TRAY_TEMPLATES_DIR  # noqa: E402

logging.disable(logging.WARNING)
MAX_SIDE = 2400  # phone photos are downscaled to this before scanning


def load_photo(path):
    data = np.fromfile(str(path), np.uint8)  # handles non-ASCII paths on Windows
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        return None
    s = MAX_SIDE / max(img.shape[:2])
    return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else img


def clean_photo(photo_dir, tray_id):
    for n in (f"{tray_id}_full.png", f"{tray_id}.png"):
        p = Path(photo_dir) / n
        if p.exists():
            return cv2.imread(str(p))
    return None


def make_scanner(tpl, ref):
    agg = ScanAggregator(tray_refs_dir=str(TRAY_REFS_DIR))
    agg.setup(tpl, reference_image=cv2.resize(ref, (tpl["image_width"], tpl["image_height"])))
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--trays", required=True)
    ap.add_argument("--photos")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    out = Path(args.out)
    (out / "results").mkdir(parents=True, exist_ok=True)
    templates = {t: json.loads((TRAY_TEMPLATES_DIR / f"{t}.json").read_text(encoding="utf-8"))
                 for t in args.trays.split(",")}
    scanners = {}
    for t, tpl in templates.items():
        scanners[(t, "current_ref")] = make_scanner(tpl, cv2.imread(str(TRAY_REFS_DIR / f"{t}.jpg")))
        if args.photos and (cp := clean_photo(args.photos, t)) is not None:
            scanners[(t, "clean_photo_ref")] = make_scanner(tpl, cp)

    files = sorted(p for p in Path(args.images).iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if args.limit:
        files = files[: args.limit]
    rows = []
    for i, f in enumerate(files):
        img = load_photo(f)
        if img is None:
            continue
        q = scanners[next(iter(scanners))].quality_gate.check(img)
        # pick the tray: full scan (with auto-crop fallback) per template, keep the most alignment matches
        first = {}
        for t in templates:
            t0 = time.time()
            s = scanners[(t, "current_ref")].scan(img, skip_quality=True)
            first[t] = (s, time.time() - t0)
        tray = max(first, key=lambda t: (first[t][0].align.match_count if first[t][0].align and first[t][0].align.success else 0))
        row = {"file": f.name, "tray": tray, "quality_ok": q.passed, "quality_issues": " | ".join(q.issues),
               "tray_votes": {t: (first[t][0].align.match_count if first[t][0].align else 0) for t in templates}}
        for label in ("current_ref", "clean_photo_ref"):
            agg = scanners.get((tray, label))
            if agg is None:
                continue
            t0 = time.time()
            s, dt0 = first[tray] if label == "current_ref" else (agg.scan(img, skip_quality=True), None)
            names = {r["slot_number"]: r.get("item_name", "") for r in s.slot_results}
            row[label] = {
                "aligned": bool(s.align and s.align.success),
                "matches": int(s.align.match_count) if s.align else 0,
                "correct": s.correct_count, "missing": s.missing_count,
                "misplaced": s.misplaced_count, "recheck": s.recheck_count,
                "missing_items": sorted({names[r["slot_number"]] for r in s.slot_results if r["status"] == "missing"}),
                "seconds": round(dt0 if dt0 is not None else time.time() - t0, 1),
                "error": s.error_message,
            }
            if s.annotated_image is not None:
                a = s.annotated_image
                k = 1600 / max(a.shape[:2])
                cv2.imencode(".jpg", cv2.resize(a, None, fx=min(1, k), fy=min(1, k)))[1].tofile(
                    str(out / "results" / f"{f.stem}_{label}.jpg"))
        rows.append(row)
        c = row["current_ref"]
        print(f"[{i + 1}/{len(files)}] {f.name} -> {tray} align={c['aligned']}({c['matches']}) "
              f"ok={c['correct']} miss={c['missing']} misplc={c['misplaced']} recheck={c['recheck']}"
              + (f" | clean ref: ok={row['clean_photo_ref']['correct']} miss={row['clean_photo_ref']['missing']} "
                 f"recheck={row['clean_photo_ref']['recheck']}" if "clean_photo_ref" in row else ""), flush=True)

    (out / "report.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "report.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "tray", "quality_ok", "quality_issues", "ref", "aligned", "matches",
                    "correct", "missing", "misplaced", "recheck", "missing_items"])
        for r in rows:
            for label in ("current_ref", "clean_photo_ref"):
                if label in r:
                    c = r[label]
                    w.writerow([r["file"], r["tray"], r["quality_ok"], r["quality_issues"], label, c["aligned"],
                                c["matches"], c["correct"], c["missing"], c["misplaced"], c["recheck"],
                                "; ".join(c["missing_items"])])
    print("saved", out)


if __name__ == "__main__":
    main()
