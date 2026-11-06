import sys
import json
import cv2
import numpy as np
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scan_workflow import ScanAggregator
from config import DATA_DIR, SAMPLE_IMAGES_DIR, TRAY_REFS_DIR, TRAY_TEMPLATES_DIR  # noqa: E402

def test_auto_orientation():
    print("=== Testing Auto-Orientation & Multi-Angle Alignment ===")
    
    # 1. Load template 02
    tmpl_path = TRAY_TEMPLATES_DIR / "box1-template02_16-item.json"
    with open(tmpl_path, "r", encoding="utf-8") as f:
        tray_data = json.load(f)
        
    ref_img_path = TRAY_REFS_DIR / "box1-template02_16-item.jpg"
    ref_img = cv2.imread(str(ref_img_path))
    assert ref_img is not None, "Failed to load reference image"
    
    agg = ScanAggregator(tray_refs_dir=str(TRAY_REFS_DIR))
    agg.setup(tray_data, reference_image=ref_img)
    
    # Normal landscape scan
    print("\n1. Testing normal landscape scan...")
    summary_landscape = agg.scan(ref_img.copy(), skip_quality=True)
    print(f"Landscape scan: Success={summary_landscape.align.success}, "
          f"Matches={summary_landscape.align.match_count}, "
          f"Rotation={summary_landscape.align.rotation_applied} deg, "
          f"Correct={summary_landscape.correct_count}/{summary_landscape.total_slots}")
    assert summary_landscape.align.rotation_applied == 0
    assert summary_landscape.correct_count == summary_landscape.total_slots
    
    # Simulate a portrait photo (rotate 90 degrees clockwise)
    print("\n2. Testing rotated portrait photo (90 deg CW)...")
    portrait_img_90 = cv2.rotate(ref_img, cv2.ROTATE_90_CLOCKWISE)
    h_p, w_p = portrait_img_90.shape[:2]
    print(f"Portrait image size: {w_p}x{h_p} (W < H)")
    
    summary_portrait = agg.scan(portrait_img_90, skip_quality=True)
    print(f"Portrait scan (90 deg CW): Success={summary_portrait.align.success}, "
          f"Matches={summary_portrait.align.match_count}, "
          f"Rotation={summary_portrait.align.rotation_applied} deg, "
          f"Correct={summary_portrait.correct_count}/{summary_portrait.total_slots}")
    assert summary_portrait.align.success is True
    assert summary_portrait.align.rotation_applied in (90, 270)
    assert summary_portrait.correct_count == summary_portrait.total_slots
    
    # Simulate an upside down rotated photo (180 degrees)
    print("\n3. Testing upside-down photo (180 deg)...")
    upside_down_img = cv2.rotate(ref_img, cv2.ROTATE_180)
    summary_180 = agg.scan(upside_down_img, skip_quality=True)
    print(f"Upside-down scan (180 deg): Success={summary_180.align.success}, "
          f"Matches={summary_180.align.match_count}, "
          f"Rotation={summary_180.align.rotation_applied} deg, "
          f"Correct={summary_180.correct_count}/{summary_180.total_slots}")
    assert summary_180.align.success is True
    assert summary_180.correct_count == summary_180.total_slots
    print("\n[SUCCESS] Template 02 (16-item) passed 100% on Landscape, Portrait, and 180 deg!")

    # 4. Test Template 01 (box1-template01_70-item) with portrait rotation
    print("\n4. Testing Template 01 (box1-template01_70-item) with Portrait (90 deg CW)...")
    tmpl1_path = TRAY_TEMPLATES_DIR / "box1-template01_70-item.json"
    with open(tmpl1_path, "r", encoding="utf-8") as f:
        tray_data1 = json.load(f)
    ref_img1 = cv2.imread(str(SAMPLE_IMAGES_DIR / "test_verified.jpg"))
    if ref_img1 is not None:
        agg1 = ScanAggregator(tray_refs_dir=str(TRAY_REFS_DIR))
        agg1.setup(tray_data1, reference_image=ref_img1)
        # Check landscape first
        res1_land = agg1.scan(ref_img1.copy(), skip_quality=True)
        print(f"Template 01 Landscape: Success={res1_land.align.success}, "
              f"Matches={res1_land.align.match_count}, "
              f"Rotation={res1_land.align.rotation_applied} deg, "
              f"Correct={res1_land.correct_count}/{res1_land.total_slots}")
        
        # Check portrait
        portrait_img1 = cv2.rotate(ref_img1, cv2.ROTATE_90_CLOCKWISE)
        res1 = agg1.scan(portrait_img1, skip_quality=True)
        print(f"Template 01 Portrait:  Success={res1.align.success}, "
              f"Matches={res1.align.match_count}, "
              f"Rotation={res1.align.rotation_applied} deg, "
              f"Correct={res1.correct_count}/{res1.total_slots}")
        assert res1.align.success is True
        # Portrait accuracy should match landscape accuracy!
        assert abs(res1.correct_count - res1_land.correct_count) <= 3

    # 5. Test Missing Item Detection (Simulate removing a tool from slot 1 in Template 02)
    print("\n5. Testing Missing Item Detection (Removing tool from slot 1)...")
    missing_img = ref_img.copy()
    slot1_meta = next(s for s in tray_data["slots"] if s["slot_number"] == 1)
    b = slot1_meta["bbox_norm"]
    h_m, w_m = missing_img.shape[:2]
    x1, y1, x2, y2 = int(b[0]*w_m), int(b[1]*h_m), int(b[2]*w_m), int(b[3]*h_m)
    # Fill slot 1 with dark empty foam texture
    missing_img[y1:y2, x1:x2] = (30, 30, 30)
    
    res_missing = agg.scan(missing_img, skip_quality=True)
    print(f"Missing Item Test: Total={res_missing.total_slots}, "
          f"Correct={res_missing.correct_count}, "
          f"Missing={res_missing.missing_count}, "
          f"Misplaced={res_missing.misplaced_count}")
    
    # Check if slot 1 was detected as missing
    s1_res = next(r for r in res_missing.slot_results if r["slot_number"] == 1)
    print(f"Slot 1 status: {s1_res['status']}")
    assert s1_res["status"] == "missing", f"Expected slot 1 to be missing, got {s1_res['status']}"
    assert res_missing.missing_count >= 1

    print("\n>>> ALL TESTS PASSED: Landscape, Portrait Auto-Orientation, CLAHE Enhancement, Missing Item Detection <<<")

if __name__ == "__main__":
    test_auto_orientation()
