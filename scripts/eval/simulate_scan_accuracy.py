"""Simulated accuracy test for checklist matching + tray image detection.

What it does
  1. Data matching test: every template slot's name / part number must equal the
     Excel checklist row it points to (checklist_no).
  2. Detection test: builds synthetic scans with a known answer.
       - starts from a clean photo of the full tray
       - "removes" random checklist items by pasting the matching pixels of the
         real empty-tray photo (aligned to the full photo with SIFT homography)
       - applies camera effects (tilt, zoom, perspective, light, blur, noise, JPEG)
       - runs the real ScanAggregator pipeline and compares every slot with the truth
     It also checks that the names the scanner reports for missing slots are the
     Excel names of the removed items (end-to-end data matching).

Usage
  python scripts/simulate_scan_accuracy.py --photos <dir with tray photos> [--trials 12] [--seed 7]

  <dir> must contain, per tray: <tray_id>.png or <tray_id>_full.png (full tray)
  and <tray_id>_empty.png (empty tray), e.g. dataYamaha/Merchecklist/Tools/tian
"""
import argparse
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
from core.config import CHECKLIST_PATH, SCAN_SIMULATION_DIR, TRAY_PHOTOS_DIR, TRAY_REFS_DIR, TRAY_TEMPLATES_DIR  # noqa: E402

logging.disable(logging.WARNING)

TRAYS = ["box1-template01_70-item", "box1-template02_16-item", "box2-template01_31-item"]
OUT_DIR = SCAN_SIMULATION_DIR

LEVELS = {
    # name: (max tilt deg, min zoom, perspective jitter, light change, max blur kernel, noise sigma, min jpeg quality)
    "clean": (0, 1.0, 0.0, 0.0, 0, 0, 95),
    "mild": (3, 0.92, 0.02, 0.10, 3, 3, 85),
    "hard": (8, 0.80, 0.05, 0.25, 5, 6, 60),
}


# --------------------------------------------------------------------------- helpers

def load_template(tray_id):
    return json.loads((TRAY_TEMPLATES_DIR / f"{tray_id}.json").read_text(encoding="utf-8"))


def find_photo(photo_dir, tray_id, kind):
    names = [f"{tray_id}_empty.png"] if kind == "empty" else [f"{tray_id}_full.png", f"{tray_id}.png"]
    for n in names:
        p = Path(photo_dir) / n
        if p.exists():
            return cv2.imread(str(p))
    raise FileNotFoundError(f"{kind} photo for {tray_id} not found in {photo_dir}")


def align_empty_to_full(empty, full):
    """Warp the empty-tray photo onto the full-tray photo (they are shot/cropped differently)."""
    h, w = full.shape[:2]
    scale = 1600 / max(h, w)
    small = lambda im: cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), None, fx=scale, fy=scale)
    e_s = small(cv2.resize(empty, (w, h)))
    f_s = small(full)
    sift = cv2.SIFT_create(6000)
    k1, d1 = sift.detectAndCompute(e_s, None)
    k2, d2 = sift.detectAndCompute(f_s, None)
    good = [m for m, n in cv2.BFMatcher().knnMatch(d1, d2, k=2) if m.distance < 0.75 * n.distance]
    src = np.float32([k1[m.queryIdx].pt for m in good]) / scale
    dst = np.float32([k2[m.trainIdx].pt for m in good]) / scale
    H, inl = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
    warped = cv2.warpPerspective(cv2.resize(empty, (w, h)), H, (w, h), borderMode=cv2.BORDER_REPLICATE)
    return warped, int(inl.sum()), len(good)


def slot_mask(slot, shape, grow):
    m = np.zeros(shape[:2], np.uint8)
    poly = np.array(slot.get("polygon") or [], np.int32)
    if len(poly) >= 3:
        cv2.fillPoly(m, [poly], 255)
    else:
        b = slot["bbox_norm"]; H, W = shape[:2]
        cv2.rectangle(m, (int(b[0] * W), int(b[1] * H)), (int(b[2] * W), int(b[3] * H)), 255, -1)
    if grow:
        m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grow * 2 + 1, grow * 2 + 1)))
    return m


def remove_items(full, empty_aligned, slots, item_nos, grow):
    img = full.copy()
    removed_slots = []
    for s in slots:
        if s.get("checklist_no") in item_nos:
            m = slot_mask(s, img.shape, grow)
            m = cv2.GaussianBlur(m, (0, 0), max(1, grow / 2)).astype(np.float32)[..., None] / 255.0
            img = (img * (1 - m) + empty_aligned * m).astype(np.uint8)
            removed_slots.append(s["slot_number"])
    return img, removed_slots


def camera(img, rng, level):
    tilt, zmin, persp, light, blur, noise, jq = LEVELS[level]
    h, w = img.shape[:2]
    if level != "clean":
        z = rng.uniform(zmin, 1.0)
        ang = np.radians(rng.uniform(-tilt, tilt))
        c = np.array([w / 2, h / 2])
        corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        R = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
        dst = (corners - c) @ R.T * z + c + rng.uniform(-persp, persp, (4, 2)) * [w, h]
        M = cv2.getPerspectiveTransform(corners, dst.astype(np.float32))
        bg = [int(v) for v in rng.integers(90, 200, 3)]
        img = cv2.warpPerspective(img, M, (w, h), borderValue=bg)
        a = 1 + rng.uniform(-light, light)
        b = rng.uniform(-light, light) * 60
        img = np.clip(img.astype(np.float32) * a + b, 0, 255).astype(np.uint8)
        k = int(rng.choice([0, 3, 5][: (blur // 2) + 1]))
        if k:
            img = cv2.GaussianBlur(img, (k, k), 0)
        if noise:
            img = np.clip(img + rng.normal(0, rng.uniform(0, noise), img.shape), 0, 255).astype(np.uint8)
    ok, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, int(rng.integers(jq, 96))])
    return cv2.imdecode(enc, cv2.IMREAD_COLOR)


# --------------------------------------------------------------------------- tests

def data_matching_test(templates, checklist):
    sheets = {s["key"]: {i["no"]: i for i in s["items"]} for s in checklist["sheets"]}
    sheet_for = {"box1-template01_70-item": "standard_new_86", "box1-template02_16-item": "standard_new_86",
                 "box2-template01_31-item": "special_new_31"}
    out = {}
    for tid, tpl in templates.items():
        items = sheets[sheet_for[tid]]
        bad = []
        for s in tpl["slots"]:
            it = items.get(s.get("checklist_no"))
            if not it or it["name"] != s.get("name") or it["part_number"] != s.get("part_number"):
                bad.append(s["slot_number"])
        covered = {s.get("checklist_no") for s in tpl["slots"]} | {
            e["checklist_no"] for s in tpl["slots"] for e in s.get("extra_items", [])}
        out[tid] = {"slots": len(tpl["slots"]), "slots_matching_excel": len(tpl["slots"]) - len(bad),
                    "mismatched_slots": bad, "excel_items_with_slot": len(covered)}
    return out


def run_detection(tray_id, tpl, full, empty_aligned, ref_img, ref_label, levels, trials, rng, sample_dir,
                  use_empty_ref=True):
    agg = ScanAggregator(tray_refs_dir=str(TRAY_REFS_DIR))
    agg.setup(tpl, reference_image=ref_img, use_empty_ref=use_empty_ref)
    slots = tpl["slots"]
    names = {s["slot_number"]: s["name"] for s in slots}
    no_of = {s["slot_number"]: s.get("checklist_no") for s in slots}
    # items you can remove on their own (a shelf holding two items is removed with its primary item)
    items = sorted({s["checklist_no"] for s in slots})
    grow = max(3, full.shape[1] // 400)
    rows = []
    for level in levels:
        for t in range(trials):
            k = 0 if t == 0 else int(rng.integers(1, 4))
            removed = set(int(x) for x in rng.choice(items, k, replace=False)) if k else set()
            scene, removed_slots = remove_items(full, empty_aligned, slots, removed, grow)
            img = camera(scene, rng, level)
            t0 = time.time()
            summary = agg.scan(img, skip_quality=True)
            dt = time.time() - t0
            pred = {r["slot_number"]: r for r in summary.slot_results}
            row = {"tray": tray_id, "ref": ref_label, "level": level, "trial": t, "removed_items": sorted(removed),
                   "aligned": bool(summary.align and summary.align.success), "seconds": round(dt, 2),
                   "matches": getattr(summary.align, "match_count", 0) if summary.align else 0,
                   "slots": []}
            for s in slots:
                sn = s["slot_number"]
                truth = "missing" if sn in removed_slots else "present"
                status = pred.get(sn, {}).get("status", "none")
                row["slots"].append((sn, truth, status))
            pred_missing_items = {no_of[sn] for sn, tr, st in row["slots"] if st == "missing"}
            row["pred_missing_items"] = sorted(pred_missing_items)
            row["item_exact"] = pred_missing_items == removed
            # names shown to the user for missing slots must be the Excel names of those items
            row["name_errors"] = [sn for sn, tr, st in row["slots"]
                                  if st == "missing" and pred[sn].get("item_name") != names[sn]]
            rows.append(row)
            if sample_dir and t == 1:
                cv2.imwrite(str(sample_dir / f"{tray_id}_{ref_label}_{level}_input.jpg"),
                            cv2.resize(img, None, fx=0.5, fy=0.5) if img.shape[1] > 2000 else img)
                if summary.annotated_image is not None:
                    a = summary.annotated_image
                    cv2.imwrite(str(sample_dir / f"{tray_id}_{ref_label}_{level}_result.jpg"),
                                cv2.resize(a, None, fx=0.5, fy=0.5) if a.shape[1] > 2000 else a)
            print(f"  {tray_id} [{ref_label}/{level}] #{t}: removed {sorted(removed)} -> missing "
                  f"{sorted(pred_missing_items)} {'OK' if row['item_exact'] else 'DIFF'} ({dt:.1f}s)", flush=True)
    return rows


def summarize(rows):
    groups = {}
    for r in rows:
        groups.setdefault((r["tray"], r["ref"], r["level"]), []).append(r)
    out = []
    for (tray, ref, level), rs in groups.items():
        c = {"tp": 0, "fn_present": 0, "fn_recheck": 0, "fn_other": 0,
             "tn": 0, "fp_missing": 0, "fp_misplaced": 0, "fp_recheck": 0}
        for r in rs:
            for sn, truth, st in r["slots"]:
                if truth == "missing":
                    key = {"missing": "tp", "correct": "fn_present", "recheck": "fn_recheck"}.get(st, "fn_other")
                else:
                    key = {"correct": "tn", "missing": "fp_missing", "misplaced": "fp_misplaced",
                           "recheck": "fp_recheck"}.get(st, "fp_recheck")
                c[key] += 1
        gt_missing = c["tp"] + c["fn_present"] + c["fn_recheck"] + c["fn_other"]
        gt_present = c["tn"] + c["fp_missing"] + c["fp_misplaced"] + c["fp_recheck"]
        pred_missing = c["tp"] + c["fp_missing"]
        out.append({
            "tray": tray, "ref": ref, "level": level, "trials": len(rs),
            "align_ok": sum(r["aligned"] for r in rs) / len(rs),
            "missing_recall": c["tp"] / gt_missing if gt_missing else None,
            "missing_precision": c["tp"] / pred_missing if pred_missing else None,
            "present_ok_rate": c["tn"] / gt_present if gt_present else None,
            "false_missing_rate": c["fp_missing"] / gt_present if gt_present else None,
            "false_misplaced_rate": c["fp_misplaced"] / gt_present if gt_present else None,
            "recheck_rate": (c["fp_recheck"] + c["fn_recheck"]) / (gt_missing + gt_present),
            "slot_accuracy": (c["tp"] + c["tn"]) / (gt_missing + gt_present),
            "item_exact_rate": sum(r["item_exact"] for r in rs) / len(rs),
            "name_errors": sum(len(r["name_errors"]) for r in rs),
            "avg_seconds": round(sum(r["seconds"] for r in rs) / len(rs), 2),
            "counts": c,
        })
    return out


def pct(v):
    return "-" if v is None else f"{v * 100:.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos", default=TRAY_PHOTOS_DIR, required=TRAY_PHOTOS_DIR is None,
                    help="default: <YAMAHA_DATA_DIR>/Merchecklist/Tools/tian from .env")
    ap.add_argument("--trials", type=int, default=12)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--levels", default="clean,mild,hard")
    ap.add_argument("--trays", default=",".join(TRAYS))
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sample_dir = OUT_DIR / "samples"
    sample_dir.mkdir(exist_ok=True)
    rng = np.random.default_rng(args.seed)
    trays = args.trays.split(",")
    templates = {t: load_template(t) for t in trays}
    checklist = json.loads((CHECKLIST_PATH).read_text(encoding="utf-8"))

    print("== 1) Data matching test ==")
    dm = data_matching_test(templates, checklist)
    for t, r in dm.items():
        print(f"  {t}: {r['slots_matching_excel']}/{r['slots']} slots match Excel, "
              f"{r['excel_items_with_slot']} Excel items have a slot, mismatched={r['mismatched_slots']}")

    print("== 2) Detection simulation ==")
    rows, prep = [], {}
    for t in trays:
        tpl = templates[t]
        W, H = tpl["image_width"], tpl["image_height"]
        full = cv2.resize(find_photo(args.photos, t, "full"), (W, H))
        empty_aligned, inliers, matches = align_empty_to_full(find_photo(args.photos, t, "empty"), full)
        cv2.imwrite(str(sample_dir / f"{t}_empty_aligned_check.jpg"),
                    cv2.resize(cv2.addWeighted(full, 0.5, empty_aligned, 0.5, 0), (1448, 1086)))
        prep[t] = {"empty_align_inliers": inliers, "empty_align_matches": matches}
        print(f"  {t}: empty->full homography inliers {inliers}/{matches}")
        # the app's reference (data/tray_refs/<tray>.jpg), with and without the empty-tray reference
        ref = cv2.resize(cv2.imread(str(TRAY_REFS_DIR / f"{t}.jpg")), (W, H))
        for label, use_empty in (("golden+empty", True), ("golden_only", False)):
            rows += run_detection(t, tpl, full, empty_aligned, ref, label,
                                  args.levels.split(","), args.trials, rng, sample_dir, use_empty_ref=use_empty)

    summary = summarize(rows)
    report = {"seed": args.seed, "trials_per_case": args.trials, "levels": {k: LEVELS[k] for k in args.levels.split(",")},
              "data_matching": dm, "empty_alignment": prep, "summary": summary, "trials": rows}
    (OUT_DIR / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n== Summary ==")
    print(f"{'tray':26} {'ref':16} {'level':6} {'align':>6} {'recall':>7} {'precis':>7} {'presOK':>7} "
          f"{'falseMiss':>9} {'misplc':>7} {'recheck':>7} {'slotAcc':>7} {'itemExact':>9} {'sec':>5}")
    for s in summary:
        print(f"{s['tray']:26} {s['ref']:16} {s['level']:6} {pct(s['align_ok']):>6} {pct(s['missing_recall']):>7} "
              f"{pct(s['missing_precision']):>7} {pct(s['present_ok_rate']):>7} {pct(s['false_missing_rate']):>9} "
              f"{pct(s['false_misplaced_rate']):>7} {pct(s['recheck_rate']):>7} {pct(s['slot_accuracy']):>7} "
              f"{pct(s['item_exact_rate']):>9} {s['avg_seconds']:>5}")
    print("name errors in missing reports:", sum(s["name_errors"] for s in summary))


if __name__ == "__main__":
    main()
