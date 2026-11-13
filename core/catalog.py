"""Tool catalog lookup (data/data.json), shared by the scanner page and the API."""
from __future__ import annotations

import json
import os
from typing import Optional

from core.config import CATALOG_PATH


def product_info(filename: str) -> Optional[dict]:
    """Find the catalog entry for a ShapeScanner result filename (by file name, code, English name or class key)."""
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    base = os.path.basename(filename)
    stem = os.path.splitext(base)[0]
    for item in data:
        if (item.get("filename") == base or item.get("code") in (base, stem)
                or item.get("name_en") == stem or item.get("class_key") == stem):
            return item
    return None
