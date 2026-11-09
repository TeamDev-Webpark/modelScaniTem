"""Inspection history for the scanner app (PostgreSQL via core.db).

- submissions: tray photos sent for checking, queued as "pending" and processed by
  process_submission() (pending -> processing -> done / needs_review / failed)
- manual inspections: results a user records for single items of the checklist
- equipment catalog: the items of the current checklist sheets, with their tray

Images are stored under <DATA_DIR>/inspections/<YYYYMMDD>/ and referenced by a path
relative to DATA_DIR. Times are stored in UTC; to_local() converts them for display.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from sqlalchemy import func, or_

from core.config import CHECKLIST_PATH, DATA_DIR, TRAY_REFS_DIR, TRAY_TEMPLATES_DIR
from core.db import Base, get_db, get_engine

logger = logging.getLogger(__name__)

INSPECTIONS_DIR = DATA_DIR / "inspections"
LOCAL_UTC_OFFSET = timedelta(hours=7)  # เวลาประเทศไทย

# ชีต checklist ที่ใช้ตรวจ (รุ่นใหม่)
ACTIVE_SHEETS = ("standard_new_86", "special_new_31")

TRAY_LABELS = {
    "box1-template01_70-item": "ถาด YA 1/2 (70 รายการ)",
    "box1-template02_16-item": "ถาด YA 2/2 (16 รายการ)",
    "box2-template01_31-item": "แผงเครื่องมือพิเศษ (31 รายการ)",
}

QUEUE_STATUSES = ("pending", "processing", "done", "needs_review", "failed")
MANUAL_RESULTS = ("ok", "damaged", "lost")

_tables_ready = False


# ─────────────────────────────────────────────────────────────── setup

def ensure_tables() -> tuple[bool, str]:
    """Create the inspection tables if needed. Returns (ok, message) — never raises."""
    global _tables_ready
    if _tables_ready:
        return True, ""
    try:
        from core import models_db
        Base.metadata.create_all(bind=get_engine(), tables=[
            models_db.InspectionSubmission.__table__, models_db.ManualInspection.__table__])
        _tables_ready = True
        return True, ""
    except Exception as e:  # database down or not configured
        logger.warning(f"inspection tables unavailable: {e}")
        return False, str(e)


def to_local(dt: Optional[datetime]) -> Optional[datetime]:
    return dt + LOCAL_UTC_OFFSET if dt else None


def fmt_time(dt: Optional[datetime]) -> str:
    return to_local(dt).strftime("%d/%m/%Y %H:%M") if dt else "-"


def tray_label(tray_id: Optional[str]) -> str:
    return TRAY_LABELS.get(tray_id or "", tray_id or "-")


def abs_path(rel: Optional[str]) -> Optional[Path]:
    return (DATA_DIR / rel) if rel else None


def load_image(rel: Optional[str]) -> Optional[np.ndarray]:
    p = abs_path(rel)
    if not p or not p.exists():
        return None
    return cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR)


def _save_image(img: np.ndarray, prefix: str) -> str:
    day = datetime.utcnow().strftime("%Y%m%d")
    folder = INSPECTIONS_DIR / day
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{prefix}_{uuid.uuid4().hex[:12]}.jpg"
    ok, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise ValueError("cannot encode image")
    enc.tofile(str(folder / name))
    return f"inspections/{day}/{name}"


# ─────────────────────────────────────────────────────────────── catalog

@lru_cache(maxsize=1)
def equipment_catalog() -> list[dict]:
    """All items of the active checklist sheets, with the tray that holds them."""
    sheets = json.loads(Path(CHECKLIST_PATH).read_text(encoding="utf-8"))["sheets"]
    sheet_names = {s["key"]: s["sheet_name"] for s in sheets}
    where = {}  # (sheet_name, no) -> (tray_id, category)
    for tf in sorted(Path(TRAY_TEMPLATES_DIR).glob("*.json")):
        tpl = json.loads(tf.read_text(encoding="utf-8"))
        for s in tpl.get("slots", []):
            nos = [s.get("checklist_no")] + [e.get("checklist_no") for e in s.get("extra_items", []) or []]
            for no in nos:
                if no is not None:
                    where.setdefault((s.get("checklist_sheet"), no), (tpl.get("tray_id", tf.stem), s.get("category", "")))
    items = []
    for s in sheets:
        if s["key"] not in ACTIVE_SHEETS:
            continue
        for it in s["items"]:
            tray_id, category = where.get((sheet_names[s["key"]], it["no"]), (None, ""))
            items.append({
                "key": f"{s['key']}:{it['no']}", "sheet_key": s["key"], "sheet_name": s["sheet_name"],
                "no": it["no"], "part_number": it.get("part_number", ""), "name": it["name"],
                "tray_id": tray_id, "category": category,
            })
    return items


@lru_cache(maxsize=8)
def _load_template(tray_id: str) -> dict:
    return json.loads((Path(TRAY_TEMPLATES_DIR) / f"{tray_id}.json").read_text(encoding="utf-8"))


def available_trays() -> list[str]:
    return sorted(p.stem for p in Path(TRAY_TEMPLATES_DIR).glob("*.json"))


# ─────────────────────────────────────────────────────────────── submissions

def _sub_dict(r) -> dict:
    return {
        "id": r.id, "tray_id": r.tray_id, "status": r.status, "source": r.source,
        "image_path": r.image_path, "annotated_path": r.annotated_path, "note": r.note,
        "submitted_by": r.submitted_by, "submitted_at": r.submitted_at, "started_at": r.started_at,
        "finished_at": r.finished_at, "total": r.total_slots, "correct": r.correct_count,
        "missing": r.missing_count, "misplaced": r.misplaced_count, "recheck": r.recheck_count,
        "error": r.error_message, "slots": json.loads(r.slot_results) if r.slot_results else [],
    }


def create_submission(tray_id: str, image: np.ndarray, note: str = "", submitted_by: str = "") -> int:
    from core.models_db import InspectionSubmission
    rel = _save_image(image, "sub")
    with get_db() as db:
        r = InspectionSubmission(tray_id=tray_id, status="pending", source="queue", image_path=rel,
                                 note=note or None, submitted_by=submitted_by or None)
        db.add(r)
        db.flush()
        return r.id


def _status_of(summary) -> str:
    if summary.error_message:
        return "needs_review"
    return "done" if summary.is_complete else "needs_review"


def _apply_summary(r, summary):
    r.total_slots = summary.total_slots
    r.correct_count = summary.correct_count
    r.missing_count = summary.missing_count
    r.misplaced_count = summary.misplaced_count
    r.recheck_count = summary.recheck_count
    r.error_message = summary.error_message or None
    r.slot_results = json.dumps(summary.slot_results, ensure_ascii=False, default=str)
    if summary.annotated_image is not None:
        r.annotated_path = _save_image(summary.annotated_image, "res")
    r.status = _status_of(summary)
    r.finished_at = datetime.utcnow()


def set_processing(sub_id: int):
    from core.models_db import InspectionSubmission
    with get_db() as db:
        r = db.get(InspectionSubmission, sub_id)
        r.status, r.started_at = "processing", datetime.utcnow()


def process_submission(sub_id: int) -> dict:
    """Run the tray scan on a queued photo and store the result. Returns the updated submission."""
    from core.models_db import InspectionSubmission
    from scan_workflow import ScanAggregator

    set_processing(sub_id)
    with get_db() as db:
        r = db.get(InspectionSubmission, sub_id)
        try:
            img = load_image(r.image_path)
            if img is None:
                raise FileNotFoundError(f"ไม่พบไฟล์ภาพ {r.image_path}")
            tpl = _load_template(r.tray_id)
            ref = cv2.imread(str(Path(TRAY_REFS_DIR) / f"{r.tray_id}.jpg"))
            agg = ScanAggregator(tray_refs_dir=str(TRAY_REFS_DIR))
            agg.setup(tpl, reference_image=ref)
            _apply_summary(r, agg.scan(img, skip_quality=False))
        except Exception as e:
            logger.exception("process_submission failed")
            r.status, r.error_message, r.finished_at = "failed", str(e), datetime.utcnow()
        db.flush()
        return _sub_dict(r)


def record_tray_check(tray_id: str, image: np.ndarray, summary, submitted_by: str = "") -> int:
    """Store a result made on the tray check page (already processed)."""
    from core.models_db import InspectionSubmission
    rel = _save_image(image, "sub")
    now = datetime.utcnow()
    with get_db() as db:
        r = InspectionSubmission(tray_id=tray_id, source="tray_check", image_path=rel,
                                 submitted_by=submitted_by or None, submitted_at=now, started_at=now)
        _apply_summary(r, summary)
        db.add(r)
        db.flush()
        return r.id


def list_submissions(status: Optional[str] = None, tray_id: Optional[str] = None,
                     date_from=None, date_to=None, search: str = "", limit: int = 300) -> list[dict]:
    """date_from/date_to are local dates (inclusive)."""
    from core.models_db import InspectionSubmission as S
    with get_db() as db:
        q = db.query(S)
        if status:
            q = q.filter(S.status == status)
        if tray_id:
            q = q.filter(S.tray_id == tray_id)
        if date_from:
            q = q.filter(S.submitted_at >= datetime.combine(date_from, datetime.min.time()) - LOCAL_UTC_OFFSET)
        if date_to:
            q = q.filter(S.submitted_at < datetime.combine(date_to, datetime.min.time()) + timedelta(days=1) - LOCAL_UTC_OFFSET)
        if search:
            kw = f"%{search.strip()}%"
            q = q.filter(or_(S.note.ilike(kw), S.tray_id.ilike(kw), S.submitted_by.ilike(kw), S.slot_results.ilike(kw)))
        return [_sub_dict(r) for r in q.order_by(S.submitted_at.desc()).limit(limit).all()]


def get_submission(sub_id: int) -> Optional[dict]:
    from core.models_db import InspectionSubmission
    with get_db() as db:
        r = db.get(InspectionSubmission, sub_id)
        return _sub_dict(r) if r else None


def delete_submission(sub_id: int):
    from core.models_db import InspectionSubmission
    with get_db() as db:
        r = db.get(InspectionSubmission, sub_id)
        if r:
            for rel in (r.image_path, r.annotated_path):
                p = abs_path(rel)
                if p and p.exists():
                    p.unlink()
            db.delete(r)


def submission_counts() -> dict:
    from core.models_db import InspectionSubmission as S
    with get_db() as db:
        rows = db.query(S.status, func.count(S.id)).group_by(S.status).all()
    counts = {k: 0 for k in QUEUE_STATUSES}
    counts.update({k: n for k, n in rows})
    counts["total"] = sum(n for _, n in rows)
    return counts


# ─────────────────────────────────────────────────────────────── manual inspections

def _man_dict(r) -> dict:
    return {
        "id": r.id, "item_key": r.item_key, "sheet_key": r.sheet_key, "no": r.item_no,
        "part_number": r.part_number, "name": r.item_name, "tray_id": r.tray_id, "result": r.result,
        "note": r.note, "attachment_path": r.attachment_path, "inspected_by": r.inspected_by,
        "inspected_at": r.inspected_at,
    }


def save_manual(item: dict, result: str, note: str = "", attachment: Optional[np.ndarray] = None,
                inspected_by: str = "") -> int:
    from core.models_db import ManualInspection
    if result not in MANUAL_RESULTS:
        raise ValueError(result)
    rel = _save_image(attachment, "man") if attachment is not None else None
    with get_db() as db:
        r = ManualInspection(item_key=item["key"], sheet_key=item["sheet_key"], item_no=item["no"],
                             part_number=item.get("part_number"), item_name=item["name"],
                             tray_id=item.get("tray_id"), result=result, note=note or None,
                             attachment_path=rel, inspected_by=inspected_by or None)
        db.add(r)
        db.flush()
        return r.id


def list_manual(item_key: Optional[str] = None, result: Optional[str] = None, limit: int = 300) -> list[dict]:
    from core.models_db import ManualInspection as M
    with get_db() as db:
        q = db.query(M)
        if item_key:
            q = q.filter(M.item_key == item_key)
        if result:
            q = q.filter(M.result == result)
        return [_man_dict(r) for r in q.order_by(M.inspected_at.desc()).limit(limit).all()]


def latest_manual_by_item() -> dict:
    """item_key -> latest manual inspection."""
    from core.models_db import ManualInspection as M
    with get_db() as db:
        sub = db.query(M.item_key, func.max(M.inspected_at).label("t")).group_by(M.item_key).subquery()
        rows = db.query(M).join(sub, (M.item_key == sub.c.item_key) & (M.inspected_at == sub.c.t)).all()
        return {r.item_key: _man_dict(r) for r in rows}


def manual_counts_today() -> dict:
    from core.models_db import ManualInspection as M
    start = datetime.combine((datetime.utcnow() + LOCAL_UTC_OFFSET).date(), datetime.min.time()) - LOCAL_UTC_OFFSET
    with get_db() as db:
        rows = db.query(M.result, func.count(M.id)).filter(M.inspected_at >= start).group_by(M.result).all()
    out = {k: 0 for k in MANUAL_RESULTS}
    out.update({k: n for k, n in rows})
    out["total"] = sum(n for _, n in rows)
    return out
