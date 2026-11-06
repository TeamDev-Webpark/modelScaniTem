import sys
import json
import time
import cv2
import numpy as np
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scan_workflow import ScanAggregator
from core.config import BENCHMARK_PATH, SAMPLE_IMAGES_DIR, TRAY_REFS_DIR, TRAY_TEMPLATES_DIR  # noqa: E402

def benchmark_trays():
    trays = [
        ("box1-template01_70-item", TRAY_TEMPLATES_DIR / "box1-template01_70-item.json"),
        ("box1-template02_16-item", TRAY_TEMPLATES_DIR / "box1-template02_16-item.json"),
        ("box2-template01_31-item", TRAY_TEMPLATES_DIR / "box2-template01_31-item.json"),
    ]

    results = []

    print("=" * 80)
    print("           BENCHMARKING ALL 3 TRAY TEMPLATES (FULL PIPELINE)")
    print("=" * 80)

    for tray_id, tmpl_file in trays:
        print(f"\n>>> TESTING: {tray_id} <<<")
        with open(tmpl_file, "r", encoding="utf-8") as f:
            tray_data = json.load(f)

        ref_img_path = TRAY_REFS_DIR / f"{tray_id}.jpg"
        ref_img = cv2.imread(str(ref_img_path))
        assert ref_img is not None, f"Cannot load image {ref_img_path}"

        agg = ScanAggregator(tray_refs_dir=str(TRAY_REFS_DIR))
        agg.setup(tray_data, reference_image=ref_img)

        # 1. Landscape Test
        t0 = time.time()
        res_land = agg.scan(ref_img.copy(), skip_quality=True)
        dur_land = time.time() - t0

        pct_land = (res_land.correct_count / res_land.total_slots * 100) if res_land.total_slots else 0
        print(f"  [Landscape] Matches: {res_land.align.match_count:<4} | Rot: {res_land.align.rotation_applied} deg | "
              f"Correct: {res_land.correct_count}/{res_land.total_slots} ({pct_land:.1f}%) | "
              f"Missing: {res_land.missing_count} | Misplaced: {res_land.misplaced_count} | "
              f"Recheck: {res_land.recheck_count} | Time: {dur_land:.2f}s")

        # 2. Portrait Test (90 deg CW)
        portrait_img = cv2.rotate(ref_img, cv2.ROTATE_90_CLOCKWISE)
        t0 = time.time()
        res_port = agg.scan(portrait_img, skip_quality=True)
        dur_port = time.time() - t0

        pct_port = (res_port.correct_count / res_port.total_slots * 100) if res_port.total_slots else 0
        print(f"  [Portrait ] Matches: {res_port.align.match_count:<4} | Rot: {res_port.align.rotation_applied} deg | "
              f"Correct: {res_port.correct_count}/{res_port.total_slots} ({pct_port:.1f}%) | "
              f"Missing: {res_port.missing_count} | Misplaced: {res_port.misplaced_count} | "
              f"Recheck: {res_port.recheck_count} | Time: {dur_port:.2f}s")

        results.append({
            "tray_id": tray_id,
            "total_slots": res_land.total_slots,
            "landscape": {
                "matches": res_land.align.match_count,
                "rotation": res_land.align.rotation_applied,
                "correct": res_land.correct_count,
                "missing": res_land.missing_count,
                "misplaced": res_land.misplaced_count,
                "recheck": res_land.recheck_count,
                "pct": pct_land,
                "time_sec": round(dur_land, 2)
            },
            "portrait": {
                "matches": res_port.align.match_count,
                "rotation": res_port.align.rotation_applied,
                "correct": res_port.correct_count,
                "missing": res_port.missing_count,
                "misplaced": res_port.misplaced_count,
                "recheck": res_port.recheck_count,
                "pct": pct_port,
                "time_sec": round(dur_port, 2)
            }
        })

    # Save summary json
    out_summary = BENCHMARK_PATH
    with open(out_summary, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print("                          FINAL SUMMARY TABLE")
    print("=" * 80)
    print(f"{'Tray ID':<25} | {'Orientation':<10} | {'Matches':<8} | {'Rot':<5} | {'Correct':<12} | {'Time'}")
    print("-" * 80)
    for r in results:
        tid = r["tray_id"]
        tot = r["total_slots"]
        l = r["landscape"]
        p = r["portrait"]
        print(f"{tid:<25} | {'Landscape':<10} | {l['matches']:<8} | {l['rotation']} deg | {l['correct']}/{tot} ({l['pct']:.0f}%)   | {l['time_sec']}s")
        print(f"{'':<25} | {'Portrait':<10} | {p['matches']:<8} | {p['rotation']} deg | {p['correct']}/{tot} ({p['pct']:.0f}%)   | {p['time_sec']}s")
        print("-" * 80)

if __name__ == "__main__":
    benchmark_trays()
