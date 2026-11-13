"""Recognise single (loose) tools from a photo, using the product photos in admin_data/images as references.

Product photo file names start with the part number (`90843-08211_85aac931.jpg`), so a match gives
the part number directly. Shared by the scanner app (loose-tool scan) and the API (/scan/tool).
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

import cv2
import numpy as np

from core.config import IMAGES_DIR
from scanners.scanner_module import ShapeScanner

logger = logging.getLogger(__name__)

REF_MAX_SIDE = 800       # product photos are shrunk to this before SIFT (they are up to 2400px)
SCENE_MAX_SIDE = 1600    # scene photos too: SIFT time grows with pixels
MIN_SCORE = 8            # minimum RANSAC inliers to count as a match (ShapeScanner default)
CERTAIN_SCORE = 40       # inliers at which confidence reaches 1.0 (same rule as the tray aligner)


def part_number_of(filename: str) -> str:
    return os.path.basename(filename).split("_")[0].split(".")[0].replace(" ", "")


def _shrink(img: np.ndarray, max_side: int) -> np.ndarray:
    h, w = img.shape[:2]
    s = max_side / max(h, w)
    return cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA) if s < 1 else img


class ProductToolScanner(ShapeScanner):
    """ShapeScanner that loads shrunk product photos quietly."""

    def _load_template(self, path, filename, index, total):
        img = cv2.imread(path)
        if img is None:
            return
        gray = self._preprocess_image(_shrink(img, REF_MAX_SIDE))
        kp, des = self.sift.detectAndCompute(gray, self._create_mask(gray))
        if des is not None and len(kp) > 0:
            self.templates.append({"name": filename, "kp": kp, "des": des, "shape": gray.shape})


@lru_cache(maxsize=1)
def get_scanner() -> ProductToolScanner:
    """Load the product photos once per process (about 90 images)."""
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):  # ShapeScanner prints a line per image
        scanner = ProductToolScanner(db_folder=str(IMAGES_DIR))
    logger.info(f"tool recognizer: {len(scanner.templates)} product photos loaded")
    return scanner


def reference_count() -> int:
    return len(get_scanner().templates)


def recognize(image: np.ndarray, tiling: bool = True) -> list[dict]:
    """Tools found in the photo, best first: [{part_number, filename, score, confidence}], one per part number."""
    import contextlib
    import io
    scanner = get_scanner()
    if not scanner.templates:
        return []
    scene = _shrink(image, SCENE_MAX_SIDE)
    with contextlib.redirect_stdout(io.StringIO()):
        raw = (scanner.scan_with_tiling(scene, threshold=MIN_SCORE) if tiling
               else scanner.scan_multiple_items(scene, threshold=MIN_SCORE))
    best: dict[str, dict] = {}
    for r in raw:
        pn = part_number_of(r["filename"])
        if pn not in best or r["score"] > best[pn]["score"]:
            best[pn] = {"part_number": pn, "filename": r["filename"], "score": int(r["score"]),
                        "confidence": round(min(1.0, r["score"] / CERTAIN_SCORE), 2)}
    return sorted(best.values(), key=lambda x: x["score"], reverse=True)
