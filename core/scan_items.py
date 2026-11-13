"""Item lists for the scan page: what to check, its picture, and its status.

Item status (one vocabulary for both scan types and the history):
    present    มี            absent     ไม่มี
    misplaced  ผิดที่ (box)   recheck    ตรวจซ้ำ (box: the scan could not decide)
    unchecked  ยังไม่ตรวจ (loose: nobody has checked it yet)

An item is a plain dict, so it can be kept in session state and saved as JSON:
    {key, no, slot, name, part_number, tray_id, auto_status, status, manual, reason}
`auto_status` is what the scan said, `status` what is saved; `manual` is True when a person changed it.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from core.config import DATA_DIR, IMAGES_DIR, TRAY_REFS_DIR, TRAY_TEMPLATES_DIR

ITEM_STATUSES = ("present", "absent", "misplaced", "recheck", "unchecked")
SLOT_TO_ITEM = {"correct": "present", "missing": "absent", "misplaced": "misplaced", "recheck": "recheck"}
LOOSE_SETS = ("standard_new_86", "special_new_31")
THUMBS_DIR = DATA_DIR / "thumbs"
THUMB_SIDE = 160  # px: shown at about 64px, sharp on phones


def _norm_pn(pn: Optional[str]) -> str:
    return (pn or "").replace(" ", "")


@lru_cache(maxsize=8)
def _template(tray_id: str) -> dict:
    return json.loads((Path(TRAY_TEMPLATES_DIR) / f"{tray_id}.json").read_text(encoding="utf-8"))


def _item(key, no, slot, name, part_number, tray_id, auto_status, reason="") -> dict:
    return {"key": key, "no": no, "slot": slot, "name": name, "part_number": _norm_pn(part_number),
            "tray_id": tray_id, "auto_status": auto_status, "status": auto_status, "manual": False,
            "reason": reason}


def box_items(tray_id: str) -> list[dict]:
    """Every slot of a box, not scanned yet (status recheck until a scan sets it)."""
    return [_item(f"{tray_id}:{s['slot_number']}", s.get("checklist_no"), s["slot_number"], s.get("name", ""),
                  s.get("part_number"), tray_id, "recheck")
            for s in sorted(_template(tray_id)["slots"], key=lambda s: s["slot_number"])]


def apply_box_scan(items: list[dict], slot_results: list[dict]) -> list[dict]:
    """Set each slot's status from a ScanAggregator result; a person's changes are kept."""
    by_slot = {r.get("slot_number"): r for r in slot_results}
    for it in items:
        r = by_slot.get(it["slot"])
        auto = SLOT_TO_ITEM.get(r.get("status"), "recheck") if r else "recheck"
        it["auto_status"], it["reason"] = auto, (r or {}).get("reason") or ""
        if not it["manual"]:
            it["status"] = auto
    return items


def loose_items(sheet_key: str) -> list[dict]:
    """Every item of a checklist set, unchecked."""
    from core.inspections import equipment_catalog
    return [_item(c["key"], c["no"], _slot_of(c["tray_id"], c["sheet_name"], c["no"]), c["name"],
                  c["part_number"], c["tray_id"], "unchecked")
            for c in equipment_catalog() if c["sheet_key"] == sheet_key]


def _slot_of(tray_id: Optional[str], sheet_name: str, no: int) -> Optional[int]:
    if not tray_id:
        return None
    for s in _template(tray_id)["slots"]:
        nos = [s.get("checklist_no")] + [e.get("checklist_no") for e in s.get("extra_items") or []]
        if s.get("checklist_sheet") == sheet_name and no in nos:
            return s["slot_number"]
    return None


def set_status(item: dict, status: str) -> dict:
    """A person's choice. Choosing what the scan said again clears the manual mark."""
    item["status"] = status
    item["manual"] = status != item["auto_status"]
    return item


def count_statuses(items: list[dict]) -> Counter:
    c = Counter({k: 0 for k in ITEM_STATUSES})
    c.update(i["status"] for i in items)
    c["manual"] = sum(1 for i in items if i.get("manual"))
    return c


def items_from_record(rec: dict) -> list[dict]:
    """Items of a saved history record. Records saved before the scan page used ScanAggregator slot results."""
    rows = rec.get("slots") or []
    if rows and "auto_status" in rows[0]:
        return rows
    tray_id = rec.get("tray_id")
    names = {}
    if tray_id and (Path(TRAY_TEMPLATES_DIR) / f"{tray_id}.json").exists():
        names = {s["slot_number"]: s for s in _template(tray_id)["slots"]}
    out = []
    for r in rows:
        s = names.get(r.get("slot_number"), {})
        status = SLOT_TO_ITEM.get(r.get("status"), "recheck")
        out.append(_item(f"{tray_id}:{r.get('slot_number')}", s.get("checklist_no"), r.get("slot_number"),
                         r.get("item_name") or s.get("name", ""), s.get("part_number"), tray_id, status,
                         r.get("reason") or ""))
    return out


# ─────────────────────────────────────────────────────────────── pictures

@lru_cache(maxsize=1)
def _product_photos() -> dict:
    """part number -> product photo path (admin_data/images/<part number>_<id>.jpg)."""
    out = {}
    if IMAGES_DIR.exists():
        for f in sorted(os.listdir(IMAGES_DIR)):
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                out.setdefault(_norm_pn(f.split("_")[0].split(".")[0]), IMAGES_DIR / f)
    return out


def _square(img: np.ndarray, side: int = THUMB_SIDE, fill=(255, 255, 255)) -> np.ndarray:
    h, w = img.shape[:2]
    s = side / max(h, w)
    small = cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA)
    canvas = np.full((side, side, 3), fill, np.uint8)
    y, x = (side - small.shape[0]) // 2, (side - small.shape[1]) // 2
    canvas[y:y + small.shape[0], x:x + small.shape[1]] = small
    return canvas


def _crop_from_reference(tray_id: str, slot: int) -> Optional[np.ndarray]:
    ref = cv2.imread(str(TRAY_REFS_DIR / f"{tray_id}.jpg"))
    s = next((x for x in _template(tray_id)["slots"] if x["slot_number"] == slot), None)
    if ref is None or s is None or not s.get("polygon"):
        return None
    tpl = _template(tray_id)
    pts = np.array(s["polygon"], float) * [ref.shape[1] / tpl["image_width"], ref.shape[0] / tpl["image_height"]]
    pad = int(0.04 * max(ref.shape[:2]) / 10)
    x1, y1 = np.maximum(pts.min(0).astype(int) - pad, 0)
    x2, y2 = pts.max(0).astype(int) + pad
    crop = ref[y1:y2, x1:x2]
    return crop if crop.size else None


def thumbnail(item: dict, prefer: str = "product") -> Optional[str]:
    """Path of a small square picture of the item, made once and kept in admin_data/thumbs/.

    prefer="slot": the slot cut from the box's reference photo (shows exactly what sits in that slot,
    used by the box scan); prefer="product": the product photo (loose scan). Either falls back to the other.
    """
    pn = _norm_pn(item.get("part_number"))
    name = f"{prefer}_{pn or 'x'}_{item.get('tray_id') or 'none'}_{item.get('slot') or 0}.jpg"
    out = THUMBS_DIR / name
    if out.exists():
        return str(out)

    def from_slot():
        return _crop_from_reference(item["tray_id"], item["slot"]) if item.get("tray_id") and item.get("slot") else None

    def from_product():
        if pn and pn in _product_photos():
            return cv2.imdecode(np.fromfile(str(_product_photos()[pn]), np.uint8), cv2.IMREAD_COLOR)
        return None

    first, second = (from_slot, from_product) if prefer == "slot" else (from_product, from_slot)
    img = first()
    if img is None:
        img = second()
    if img is None:
        return None
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    cv2.imencode(".jpg", _square(img), [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tofile(str(out))
    return str(out)


def contact_sheet(images: list[np.ndarray], width: int = 1600) -> np.ndarray:
    """Several loose-tool photos side by side in one image (2 per row), for the history record."""
    if len(images) == 1:
        return images[0]
    cols = 2
    cell = width // cols
    tiles = [_square(im, cell, fill=(245, 245, 245)) for im in images]
    while len(tiles) % cols:
        tiles.append(np.full((cell, cell, 3), 245, np.uint8))
    rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    return np.vstack(rows)
