"""Dependencies and singleton service providers for modelScaniTem API."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Generator, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.config import DATA_DIR, TRAY_REFS_DIR, TRAY_TEMPLATES_DIR
from core.db import get_db
from core.inspections import TRAY_LABELS, available_trays
from scan_workflow import ScanAggregator

logger = logging.getLogger(__name__)

# Cache of initialized aggregators keyed by tray_id
_AGGREGATORS: Dict[str, ScanAggregator] = {}
_TEMPLATES_CACHE: Dict[str, Dict[str, Any]] = {}


def get_tray_template(tray_id: str) -> Dict[str, Any]:
    """Retrieve tray template JSON from cache or disk."""
    if tray_id in _TEMPLATES_CACHE:
        return _TEMPLATES_CACHE[tray_id]

    # Exact match only: a partial id must never silently pick another tray.
    if tray_id.endswith(".json"):
        tray_id = tray_id[:-5]
    trays = available_trays()
    if tray_id not in trays:
        raise HTTPException(
            status_code=404,
            detail=f"Tray template '{tray_id}' not found. Available: {trays}"
        )
    path = Path(TRAY_TEMPLATES_DIR) / f"{tray_id}.json"

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("tray_id", tray_id)
        _TEMPLATES_CACHE[tray_id] = data
        return data
    except Exception as e:
        logger.error(f"Failed to read template {path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse template: {e}")


def get_aggregator(tray_id: str) -> ScanAggregator:
    """Get or initialize a cached ScanAggregator for the given tray_id."""
    if tray_id in _AGGREGATORS:
        return _AGGREGATORS[tray_id]

    template = get_tray_template(tray_id)
    resolved_id = template.get("tray_id", tray_id)

    agg = ScanAggregator(tray_refs_dir=str(TRAY_REFS_DIR))
    ok = agg.setup(template)
    if not ok:
        logger.warning(f"ScanAggregator setup for '{resolved_id}' returned False")

    _AGGREGATORS[resolved_id] = agg
    if resolved_id != tray_id:
        _AGGREGATORS[tray_id] = agg

    return agg


def require_db() -> None:
    """FastAPI dependency: 503 when the inspection database cannot be reached right now."""
    from core.inspections import ensure_tables
    ok, msg = ensure_tables()
    if not ok:
        raise HTTPException(status_code=503, detail=f"Inspection database unavailable: {msg[:200]}")


def get_tray_display_name(tray_id: str) -> str:
    """Return friendly Thai label for tray_id."""
    return TRAY_LABELS.get(tray_id, tray_id)


def get_db_session() -> Generator[Optional[Session], None, None]:
    """FastAPI database dependency yielding an active session or None if DB is down."""
    try:
        with get_db() as db:
            yield db
    except Exception as e:
        logger.warning(f"Database session unavailable: {e}")
        yield None

