import sys
import json
import cv2
import numpy as np
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scan_workflow import ScanAggregator
from config import DATA_DIR, SAMPLE_IMAGES_DIR, TRAY_REFS_DIR, TRAY_TEMPLATES_DIR  # noqa: E402

def test_box2():
    print("=== Testing box2-template01_31-item Scanning Pipeline ===")
    
    tmpl_path = TRAY_TEMPLATES_DIR / "box2-template01_31-item.json"
    with open(tmpl_path, "r", encoding="utf-8") as f:
        tray_data = json.load(f)
        
    ref_img_path = TRAY_REFS_DIR / "box2-template01_31-item.jpg"
    ref_img = cv2.imread(str(ref_img_path))
    assert ref_img is not None, "Failed to load reference image"
    
    agg = ScanAggregator(tray_refs_dir=str(TRAY_REFS_DIR))
    agg.setup(tray_data, reference_image=ref_img)
    
    # 1. Landscape scan
    print("\n1. Testing normal landscape scan...")
    res_land = agg.scan(ref_img.copy(), skip_quality=True)
    print(f"Landscape scan: Success={res_land.align.success}, "
          f"Matches={res_land.align.match_count}, "
          f"Rotation={res_land.align.rotation_applied} deg, "
          f"Correct={res_land.correct_count}/{res_land.total_slots}")
    assert res_land.align.success is True
    assert res_land.align.rotation_applied == 0
    assert res_land.correct_count == res_land.total_slots

    # 2. Portrait scan (rotate 90 deg CW)
    print("\n2. Testing rotated portrait photo (90 deg CW)...")
    portrait_img = cv2.rotate(ref_img, cv2.ROTATE_90_CLOCKWISE)
    res_port = agg.scan(portrait_img, skip_quality=True)
    print(f"Portrait scan (90 deg CW): Success={res_port.align.success}, "
          f"Matches={res_port.align.match_count}, "
          f"Rotation={res_port.align.rotation_applied} deg, "
          f"Correct={res_port.correct_count}/{res_port.total_slots}")
    assert res_port.align.success is True
    assert res_port.align.rotation_applied in (90, 270)
    assert res_port.correct_count == res_port.total_slots

    print("\n>>> ALL TESTS PASSED FOR box2-template01_31-item: 100% ACCURACY <<<")

if __name__ == "__main__":
    test_box2()
