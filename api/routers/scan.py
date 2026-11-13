"""Scanning endpoints for tray inspection and tool recognition."""
from __future__ import annotations

import base64
import logging
from functools import lru_cache
from typing import Literal, Optional

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.dependencies import get_aggregator, get_tray_display_name, get_tray_template
from core.catalog import product_info
from api.schemas import (
    AlignResponse,
    QualityGateResponse,
    ScanCounters,
    SingleToolScanResponse,
    SlotScanResult,
    TrayScanResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan", tags=["Scanning & Inspection"])

STATUS_META = {
    "correct": ("ครบ", "🟢"),
    "missing": ("ขาดหาย", "🔴"),
    "misplaced": ("ผิดตำแหน่ง", "🟡"),
    "recheck": ("ตรวจซ้ำ", "↩️"),
}


async def _decode_upload_image(file: UploadFile) -> np.ndarray:
    """Read and decode uploaded image into OpenCV BGR numpy array."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded image file is empty")

    nparr = np.frombuffer(content, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(
            status_code=400,
            detail="Could not decode image. Supported formats: JPEG, PNG, WEBP.",
        )
    return image


def _encode_base64_jpg(image: np.ndarray, quality: int = 85) -> str:
    """Encode OpenCV BGR image as base64 JPEG string."""
    ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        return ""
    return base64.b64encode(buf.tobytes()).decode("utf-8")


@router.post(
    "/tray",
    response_model=TrayScanResponse,
    summary="Scan and inspect an entire tool tray",
)
async def scan_tray(
    tray_id: str = Form(..., description="Target tray ID (e.g. box1-template01_70-item, box2-template01_31-item)"),
    image: UploadFile = File(..., description="Tray photo from camera or gallery (JPEG/PNG)"),
    skip_quality: bool = Form(False, description="Bypass image blur/glare check for testing"),
    crop_mode: Literal["smart", "off", "force"] = Form("smart", description="Auto-crop strategy: 'smart', 'off', or 'force'"),
    return_annotated: bool = Form(True, description="Return color-coded annotated image as base64 JPEG"),
    save_history: bool = Form(False, description="Persist inspection result to inspection history database"),
    note: str = Form("", description="Optional inspection remark or operator note"),
    operator_name: str = Form("", description="Optional technician/inspector name"),
) -> TrayScanResponse:
    """Run full tray inspection workflow:
    
    1. Quality Gate: checks blur, brightness, glare, resolution.
    2. Alignment & Homography: aligns image against golden reference template.
    3. Slot Checking: checks presence, contour, orientation, and shape against empty & golden models.
    4. Aggregator: produces status 🟢 correct, 🔴 missing, 🟡 misplaced, ↩️ recheck.
    5. Returns structured JSON + optional color-annotated image.
    """
    img_bgr = await _decode_upload_image(image)

    # Load template to get slot metadata (names, part numbers)
    template = get_tray_template(tray_id)
    resolved_id = template.get("tray_id", tray_id)
    tray_name = get_tray_display_name(resolved_id)
    slot_defs = {s.get("slot_number", i + 1): s for i, s in enumerate(template.get("slots", []))}

    # Get cached aggregator
    aggregator = get_aggregator(resolved_id)

    # Run inspection
    try:
        summary = aggregator.scan(
            image=img_bgr,
            skip_quality=skip_quality,
            crop_mode=crop_mode,
        )
    except Exception as e:
        logger.error(f"Scan pipeline failed for tray {tray_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inspection pipeline failure: {e}")

    # Build Quality Response
    quality_resp = None
    if summary.quality is not None:
        quality_resp = QualityGateResponse(
            passed=summary.quality.passed,
            issues=summary.quality.issues or [],
            blur_score=round(summary.quality.blur_score, 2),
            brightness=round(summary.quality.brightness, 2),
            resolution=list(summary.quality.resolution),
            score=round(summary.quality.score, 3),
        )

    # Build Align Response
    align_resp = None
    if summary.align is not None:
        align_resp = AlignResponse(
            success=summary.align.success,
            match_count=summary.align.match_count,
            inlier_ratio=round(summary.align.inlier_ratio, 3),
            rotation_applied=summary.align.rotation_applied,
            message=summary.align.message or "",
            has_homography=summary.align.homography is not None,
        )

    # Build Slot Scan Results with enriched metadata
    slots_out: list[SlotScanResult] = []
    for s_res in summary.slot_results:
        s_num = s_res.get("slot_number", 0)
        s_def = slot_defs.get(s_num, {})
        status = s_res.get("status", "recheck")
        label_th, emoji = STATUS_META.get(status, ("ตรวจซ้ำ", "↩️"))

        slots_out.append(
            SlotScanResult(
                slot_number=s_num,
                tool_code=s_def.get("tool_code") or s_def.get("part_number"),
                tool_name=s_def.get("tool_name") or s_def.get("name"),
                status=status,
                status_label_th=label_th,
                emoji=emoji,
                confidence=float(s_res.get("confidence", 0.0)),
                slot_bbox=s_res.get("slot_bbox"),
                reason=s_res.get("reason"),
                center_offset_px=s_res.get("center_offset_px"),
                angle_deg=s_res.get("angle_deg"),
                iou_score=s_res.get("iou_score"),
                golden_score=s_res.get("golden_score"),
                empty_score=s_res.get("empty_score"),
            )
        )

    # Calculate overall stats
    tot = summary.total_slots or len(slots_out)
    acc = round((summary.correct_count / max(1, tot)) * 100.0, 1)

    counters = ScanCounters(
        total_slots=tot,
        correct=summary.correct_count,
        missing=summary.missing_count,
        misplaced=summary.misplaced_count,
        recheck=summary.recheck_count,
        accuracy_pct=acc,
        is_complete=summary.is_complete,
    )

    # Optionally encode annotated image
    annotated_b64 = None
    if return_annotated and summary.annotated_image is not None:
        annotated_b64 = _encode_base64_jpg(summary.annotated_image)

    # Optionally save to database
    if save_history:
        try:
            from core.inspections import ensure_tables, record_tray_check
            ensure_tables()
            sub_id = record_tray_check(resolved_id, img_bgr, summary, submitted_by=operator_name,
                                       note=note, source="api")
            logger.info(f"Recorded inspection submission #{sub_id} for tray {resolved_id}")
        except Exception as e:
            logger.warning(f"Could not save inspection history to DB: {e}")

    return TrayScanResponse(
        success=(summary.error_message == ""),
        tray_id=resolved_id,
        tray_name=tray_name,
        counters=counters,
        slots=slots_out,
        quality=quality_resp,
        alignment=align_resp,
        error_message=summary.error_message or None,
        annotated_image_base64=annotated_b64,
    )


@router.post(
    "/tool",
    response_model=SingleToolScanResponse,
    summary="Scan and identify a single tool item",
)
async def scan_single_tool(
    image: UploadFile = File(..., description="Single tool photo (JPEG/PNG)"),
) -> SingleToolScanResponse:
    """Identify a single tool with the SIFT ShapeScanner (same method as the app's scan page).

    status: `found`, `not_found`, or `no_references` when no tool reference images are loaded
    (put them in `data/` as .png/.jpg named like the catalog `filename`).
    """
    img_bgr = await _decode_upload_image(image)
    scanner = _shape_scanner()
    if not scanner.templates:
        return SingleToolScanResponse(
            success=False, status="no_references",
            message="No tool reference images loaded: add .png/.jpg tool images to the data/ folder",
        )
    try:
        matches = scanner.scan_with_tiling(img_bgr, threshold=8)
    except Exception as e:
        logger.error(f"ShapeScanner failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tool recognition failure: {e}")
    if not matches:
        return SingleToolScanResponse(success=False, status="not_found",
                                      message="No matching tool shape detected in image")

    best = matches[0]  # sorted by score, highest first
    info = product_info(best["filename"]) or {}
    score = int(best["score"])
    return SingleToolScanResponse(
        success=True,
        tool_code=info.get("code") or best["filename"],
        tool_name=info.get("name") or best["filename"],
        # score = matching SIFT keypoints; 40+ is treated as certain (same rule as the tray aligner)
        confidence=round(min(1.0, score / 40.0), 3),
        status="found",
        message=f"Matched {best['filename']} with {score} keypoints",
    )


@lru_cache(maxsize=1)
def _shape_scanner():
    """Load tool reference images once per process (loading reads every image in data/)."""
    from core.config import MASTER_DATA_DIR
    from scanners.scanner_module import ShapeScanner
    return ShapeScanner(db_folder=str(MASTER_DATA_DIR))

