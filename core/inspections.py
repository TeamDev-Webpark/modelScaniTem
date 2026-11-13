"""Inspection history for the scanner app (PostgreSQL via core.db).

- scans (table inspection_submissions): one row per scan from the scan page (save_scan), the API
  (record_tray_check, source="api") or older versions of the app; scan_type is "box" or "loose"
- equipment catalog: the items of the current checklist sheets, with their tray
- the manual_inspections table holds results from an older page; nothing writes to it any more

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
from sqlalchemy import or_, text

from core.config import CHECKLIST_PATH, DATA_DIR, TRAY_TEMPLATES_DIR
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
    # ชุดเครื่องมือของการสแกนชิ้นเดี่ยว (เก็บใน tray_id ของประวัติ)
    "standard_new_86": "ชุดมาตรฐาน (86 รายการ)",
    "special_new_31": "ชุดเครื่องมือพิเศษ (31 รายการ)",
}

SCAN_TYPES = {"box": "อุปกรณ์ในกล่อง", "loose": "อุปกรณ์ชิ้นเดี่ยว"}


_tables_ready = False


# ─────────────────────────────────────────────────────────────── setup

def ensure_tables() -> tuple[bool, str]:
    """Check the database is reachable now (and create the inspection tables the first time).

    Returns (ok, message) and never raises. It checks on every call, so a database that goes
    down after start-up is reported here instead of failing later inside a page or request.
    """
    global _tables_ready
    try:
        if _tables_ready:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, ""
        from core import models_db
        Base.metadata.create_all(bind=get_engine(), tables=[
            models_db.InspectionSubmission.__table__, models_db.ManualInspection.__table__])
        _add_missing_columns()
        _tables_ready = True
        return True, ""
    except Exception as e:  # database down or not configured
        logger.warning(f"inspection database unavailable: {e}")
        return False, str(e)


def _add_missing_columns():
    """create_all() never alters an existing table: add the columns newer code needs (PostgreSQL)."""
    if get_engine().dialect.name != "postgresql":
        return
    with get_engine().begin() as conn:
        conn.execute(text("ALTER TABLE inspection_submissions "
                          "ADD COLUMN IF NOT EXISTS scan_type VARCHAR(20) NOT NULL DEFAULT 'box'"))
        conn.execute(text("ALTER TABLE inspection_submissions "
                          "ADD COLUMN IF NOT EXISTS manual_count INTEGER NOT NULL DEFAULT 0"))


def to_local(dt: Optional[datetime]) -> Optional[datetime]:
    return dt + LOCAL_UTC_OFFSET if dt else None


def fmt_time(dt: Optional[datetime]) -> str:
    return to_local(dt).strftime("%d/%m/%Y %H:%M") if dt else "-"


def tray_label(tray_id: Optional[str]) -> str:
    return TRAY_LABELS.get(tray_id or "", tray_id or "-")


def abs_path(rel: Optional[str]) -> Optional[Path]:
    return (DATA_DIR / rel) if rel else None


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
        "scan_type": r.scan_type or "box", "manual_count": r.manual_count or 0,
        "image_path": r.image_path, "annotated_path": r.annotated_path, "note": r.note,
        "submitted_by": r.submitted_by, "submitted_at": r.submitted_at, "started_at": r.started_at,
        "finished_at": r.finished_at, "total": r.total_slots, "correct": r.correct_count,
        "missing": r.missing_count, "misplaced": r.misplaced_count, "recheck": r.recheck_count,
        "error": r.error_message, "slots": json.loads(r.slot_results) if r.slot_results else [],
    }


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


def record_tray_check(tray_id: str, image: np.ndarray, summary, submitted_by: str = "",
                      note: str = "", source: str = "tray_check") -> int:
    """Store a result that was already processed (tray check page, or source="api")."""
    from core.models_db import InspectionSubmission
    rel = _save_image(image, "sub")
    now = datetime.utcnow()
    with get_db() as db:
        r = InspectionSubmission(tray_id=tray_id, source=source, image_path=rel, note=note or None,
                                 submitted_by=submitted_by or None, submitted_at=now, started_at=now)
        _apply_summary(r, summary)
        db.add(r)
        db.flush()
        return r.id


def _submission_query(db, status=None, tray_id=None, date_from=None, date_to=None, search="", scan_type=None):
    from core.models_db import InspectionSubmission as S
    q = db.query(S)
    if scan_type:
        q = q.filter(S.scan_type == scan_type)
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
    return q


def list_submissions(status: Optional[str] = None, tray_id: Optional[str] = None,
                     date_from=None, date_to=None, search: str = "", limit: int = 300,
                     offset: int = 0, scan_type: Optional[str] = None) -> list[dict]:
    """date_from/date_to are local dates (inclusive)."""
    from core.models_db import InspectionSubmission as S
    with get_db() as db:
        q = _submission_query(db, status, tray_id, date_from, date_to, search, scan_type)
        return [_sub_dict(r) for r in q.order_by(S.submitted_at.desc(), S.id.desc()).offset(offset).limit(limit).all()]


def count_submissions(status: Optional[str] = None, tray_id: Optional[str] = None,
                      date_from=None, date_to=None, search: str = "", scan_type: Optional[str] = None) -> int:
    with get_db() as db:
        return _submission_query(db, status, tray_id, date_from, date_to, search, scan_type).count()


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


def save_scan(scan_type: str, target: str, image: np.ndarray, items: list[dict],
              annotated: Optional[np.ndarray] = None, submitted_by: str = "", note: str = "",
              error: str = "") -> int:
    """Store one scan from the scan page: the photo, the result photo and every item's final status.

    items: from core.scan_items (status present/absent/misplaced/recheck/unchecked, auto_status, manual).
    """
    from core.models_db import InspectionSubmission
    from core.scan_items import count_statuses
    c = count_statuses(items)
    bad = c["absent"] + c["misplaced"] + (c["recheck"] + c["unchecked"] if scan_type == "box" else 0)
    now = datetime.utcnow()
    with get_db() as db:
        r = InspectionSubmission(
            tray_id=target, scan_type=scan_type, source="scan", status="needs_review" if bad else "done",
            image_path=_save_image(image, "sub"),
            annotated_path=_save_image(annotated, "res") if annotated is not None else None,
            note=note or None, submitted_by=submitted_by or None, submitted_at=now, started_at=now, finished_at=now,
            total_slots=len(items), correct_count=c["present"], missing_count=c["absent"],
            misplaced_count=c["misplaced"], recheck_count=c["recheck"] + c["unchecked"],
            manual_count=c["manual"], error_message=error or None,
            slot_results=json.dumps(items, ensure_ascii=False, default=str))
        db.add(r)
        db.flush()
        return r.id


def history_stats() -> dict:
    """Numbers for the history page: scans today, and all-time scans by result."""
    from core.models_db import InspectionSubmission as S
    start = datetime.combine(to_local(datetime.utcnow()).date(), datetime.min.time()) - LOCAL_UTC_OFFSET
    with get_db() as db:
        q = db.query(S)
        return {
            "today": q.filter(S.submitted_at >= start).count(),
            "total": q.count(),
            "complete": q.filter(S.status == "done").count(),
            "with_absent": q.filter(S.missing_count > 0).count(),
            "with_misplaced": q.filter(S.misplaced_count > 0).count(),
        }
