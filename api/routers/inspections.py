"""Endpoints for viewing and querying inspection records and history."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from api.dependencies import get_tray_display_name, require_db
from api.schemas import InspectionHistoryResponse, InspectionSubmissionItem
from core.config import DATA_DIR
from core.inspections import (
    abs_path,
    count_submissions,
    delete_submission,
    fmt_time,
    get_submission,
    list_submissions as db_list_submissions,
)

logger = logging.getLogger(__name__)

# Every history endpoint answers 503 while the database is unreachable (checked per request).
router = APIRouter(prefix="/inspections", tags=["Inspection Records & History"],
                   dependencies=[Depends(require_db)])


@router.get("", response_model=InspectionHistoryResponse, summary="List inspection submissions")
def list_submissions(
    status: Optional[Literal["pending", "processing", "done", "needs_review", "failed"]] = Query(
        None, description="Filter by status: pending, processing, done, needs_review, failed"),
    tray_id: Optional[str] = Query(None, description="Filter by tray ID"),
    search: Optional[str] = Query(None, description="Keyword search in note, submitter, or tool name"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> InspectionHistoryResponse:
    """Retrieve history of tray scan submissions."""
    try:
        total = count_submissions(status=status, tray_id=tray_id, search=search or "")
        page_records = db_list_submissions(status=status, tray_id=tray_id, search=search or "",
                                           limit=page_size, offset=(page - 1) * page_size)

        items = []
        for r in page_records:
            tot = r.get("total") or 0
            correct = r.get("correct") or 0
            acc = round((correct / max(1, tot)) * 100.0, 1)

            photo_rel = r.get("image_path")
            annotated_rel = r.get("annotated_path")

            items.append(
                InspectionSubmissionItem(
                    id=r["id"],
                    tray_id=r.get("tray_id") or "",
                    tray_name=get_tray_display_name(r.get("tray_id")),
                    status=r.get("status") or "unknown",
                    total_slots=tot,
                    correct=correct,
                    missing=r.get("missing") or 0,
                    misplaced=r.get("misplaced") or 0,
                    recheck=r.get("recheck") or 0,
                    accuracy_pct=acc,
                    created_at=fmt_time(r.get("submitted_at")),
                    photo_url=f"/api/v1/inspections/{r['id']}/image?type=original" if photo_rel else None,
                    annotated_url=f"/api/v1/inspections/{r['id']}/image?type=annotated" if annotated_rel else None,
                )
            )

        return InspectionHistoryResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=items,
        )
    except Exception as e:
        logger.error(f"Error querying inspection submissions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database query error: {e}")


@router.get("/{submission_id}", summary="Get detailed inspection submission")
def get_submission_detail(submission_id: int):
    """Retrieve full inspection details including slot-by-slot detection outputs."""
    sub = get_submission(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail=f"Submission #{submission_id} not found")
    
    sub["tray_name"] = get_tray_display_name(sub.get("tray_id"))
    sub["submitted_at_formatted"] = fmt_time(sub.get("submitted_at"))
    return sub


@router.get("/{submission_id}/image", summary="Download submission photo (original or annotated)")
def get_submission_image(
    submission_id: int,
    type: str = Query("annotated", pattern="^(original|annotated)$", description="'original' or 'annotated'"),
):
    """Serve the JPEG image of the inspection submission."""
    sub = get_submission(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail=f"Submission #{submission_id} not found")

    rel_path = sub.get("annotated_path") if type == "annotated" else sub.get("image_path")
    if not rel_path and type == "annotated":
        # Fall back to original if annotated was not saved
        rel_path = sub.get("image_path")

    if not rel_path:
        raise HTTPException(status_code=404, detail="No image file associated with this submission")

    file_path = abs_path(rel_path)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Image file missing from storage")

    return FileResponse(
        path=str(file_path),
        media_type="image/jpeg",
        filename=f"inspection_{submission_id}_{type}.jpg",
    )


@router.delete("/{submission_id}", summary="Delete an inspection submission")
def remove_submission(submission_id: int):
    """Delete submission record and associated image files from disk."""
    sub = get_submission(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail=f"Submission #{submission_id} not found")

    delete_submission(submission_id)
    return {"status": "ok", "message": f"Deleted submission #{submission_id}"}
