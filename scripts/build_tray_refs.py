"""Build the scan reference images in admin_data/tray_refs from the clean tray photos.

For each tray it writes:
  <tray_id>.jpg        the full tray photo (no annotation boxes), at the template size
  <tray_id>_empty.jpg  the empty tray photo, warped onto the full photo so every slot lines up
and a check image (admin_data/tray_refs/check/<tray_id>.jpg) with the template polygons drawn on both.

The photos folder needs <tray_id>_full.png or <tray_id>.png, plus <tray_id>_empty.png,
e.g. dataYamaha/Merchecklist/Tools/tian.

Usage
  python scripts/build_tray_refs.py --photos <dir> [--trays a,b,c]
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
TRAYS = ["box1-template01_70-item", "box1-template02_16-item", "box2-template01_31-item"]
REFS = ROOT / "admin_data" / "tray_refs"


def read(path):
    data = np.fromfile(str(path), np.uint8)  # handles non-ASCII paths on Windows
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def find_photo(photo_dir, tray_id, kind):
    names = [f"{tray_id}_empty.png"] if kind == "empty" else [f"{tray_id}_full.png", f"{tray_id}.png"]
    for n in names:
        p = Path(photo_dir) / n
        if p.exists():
            return read(p)
    raise FileNotFoundError(f"{kind} photo for {tray_id} not found in {photo_dir}")


def align_to(src, dst):
    """Warp src onto dst with a SIFT homography. Returns (warped, inliers, matches)."""
    h, w = dst.shape[:2]
    scale = 1600 / max(h, w)
    small = lambda im: cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), None, fx=scale, fy=scale)
    src = cv2.resize(src, (w, h))
    sift = cv2.SIFT_create(6000)
    k1, d1 = sift.detectAndCompute(small(src), None)
    k2, d2 = sift.detectAndCompute(small(dst), None)
    good = [m for m, n in cv2.BFMatcher().knnMatch(d1, d2, k=2) if m.distance < 0.75 * n.distance]
    p1 = np.float32([k1[m.queryIdx].pt for m in good]) / scale
    p2 = np.float32([k2[m.trainIdx].pt for m in good]) / scale
    H, inl = cv2.findHomography(p1, p2, cv2.RANSAC, 4.0)
    return cv2.warpPerspective(src, H, (w, h), borderMode=cv2.BORDER_REPLICATE), int(inl.sum()), len(good)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos", required=True)
    ap.add_argument("--trays", default=",".join(TRAYS))
    args = ap.parse_args()
    (REFS / "check").mkdir(parents=True, exist_ok=True)

    for tid in args.trays.split(","):
        tpl = json.loads((ROOT / "mock_database" / "tray_templates" / f"{tid}.json").read_text(encoding="utf-8"))
        W, H = tpl["image_width"], tpl["image_height"]
        full = cv2.resize(find_photo(args.photos, tid, "full"), (W, H), interpolation=cv2.INTER_AREA)
        empty, inliers, matches = align_to(find_photo(args.photos, tid, "empty"), full)
        if inliers < 50:
            sys.exit(f"{tid}: empty photo could not be aligned ({inliers}/{matches} inliers)")
        cv2.imwrite(str(REFS / f"{tid}.jpg"), full, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(str(REFS / f"{tid}_empty.jpg"), empty, [cv2.IMWRITE_JPEG_QUALITY, 95])

        check = [full.copy(), empty.copy()]
        for im in check:
            for s in tpl["slots"]:
                cv2.polylines(im, [np.array(s["polygon"], np.int32)], True, (0, 0, 255), max(1, W // 900))
        k = 1448 / W
        cv2.imwrite(str(REFS / "check" / f"{tid}.jpg"),
                    cv2.resize(np.hstack(check), None, fx=k, fy=k, interpolation=cv2.INTER_AREA))
        print(f"{tid}: {W}x{H}, empty aligned with {inliers}/{matches} inliers")


if __name__ == "__main__":
    main()
