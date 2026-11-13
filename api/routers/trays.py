"""Endpoints for managing and querying tray templates and camera guides."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Query, Response

from api.dependencies import get_tray_display_name, get_tray_template
from api.schemas import SlotInfo, TrayDetailResponse, TraySummaryItem
from core.config import TRAY_REFS_DIR, TRAY_TEMPLATES_DIR
from core.inspections import available_trays
from scan_workflow import generate_camera_guide, generate_tray_guide_overlay

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trays", tags=["Trays & Templates"])


def _fit(img: np.ndarray, width: int, height: int) -> np.ndarray:
    """Scale img to fit inside width x height keeping its shape, centred on a blank canvas."""
    h, w = img.shape[:2]
    s = min(width / w, height / h)
    nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
    canvas = np.zeros((height, width, img.shape[2]), dtype=img.dtype)
    if img.shape[2] == 3:
        canvas[:] = img[0, 0]  # blueprint background colour
    x, y = (width - nw) // 2, (height - nh) // 2
    canvas[y:y + nh, x:x + nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    return canvas


@router.get("", response_model=List[TraySummaryItem], summary="List all available tray templates")
def list_trays() -> List[TraySummaryItem]:
    """Retrieve all available tray templates registered in the system."""
    tray_ids = available_trays()
    items = []

    for tid in tray_ids:
        try:
            tpl = get_tray_template(tid)
            has_ref = any((Path(TRAY_REFS_DIR) / f"{tid}{ext}").exists() for ext in (".jpg", ".png"))
            has_empty = any((Path(TRAY_REFS_DIR) / f"{tid}_empty{ext}").exists() for ext in (".jpg", ".png"))
            slots = tpl.get("slots", [])

            items.append(
                TraySummaryItem(
                    tray_id=tid,
                    tray_name=get_tray_display_name(tid),
                    total_slots=len(slots),
                    has_reference_image=has_ref,
                    has_empty_image=has_empty,
                )
            )
        except Exception as e:
            logger.warning(f"Error loading summary for tray {tid}: {e}")

    return items


@router.get("/{tray_id}", response_model=TrayDetailResponse, summary="Get full tray template details")
def get_tray_details(tray_id: str) -> TrayDetailResponse:
    """Retrieve full details of a specific tray, including all tool slot positions and checklist mappings."""
    tpl = get_tray_template(tray_id)
    resolved_id = tpl.get("tray_id", tray_id)

    has_ref = any((Path(TRAY_REFS_DIR) / f"{resolved_id}{ext}").exists() for ext in (".jpg", ".png"))
    has_empty = any((Path(TRAY_REFS_DIR) / f"{resolved_id}_empty{ext}").exists() for ext in (".jpg", ".png"))

    slots_raw = tpl.get("slots", [])
    slots = []
    for s in slots_raw:
        slots.append(
            SlotInfo(
                slot_number=s.get("slot_number", 0),
                tool_code=s.get("tool_code") or s.get("part_number"),
                tool_name=s.get("tool_name") or s.get("name"),
                checklist_no=s.get("checklist_no"),
                checklist_sheet=s.get("checklist_sheet"),
                category=s.get("category"),
                bbox_norm=s.get("bbox_norm"),
                polygon=s.get("polygon"),
            )
        )

    w = tpl.get("image_width") or (tpl.get("image_size") or [1448, 1086])[0]
    h = tpl.get("image_height") or (tpl.get("image_size") or [1448, 1086])[1]

    return TrayDetailResponse(
        tray_id=resolved_id,
        tray_name=get_tray_display_name(resolved_id),
        description=tpl.get("description"),
        total_slots=len(slots),
        image_size=[int(w), int(h)],
        has_reference_image=has_ref,
        has_empty_image=has_empty,
        slots=slots,
    )


@router.get("/{tray_id}/guide", summary="Get transparent camera overlay guide PNG")
def get_tray_guide(
    tray_id: str,
    width: int = Query(1280, ge=320, le=3840, description="Overlay canvas width in pixels"),
    height: Optional[int] = Query(
        None, ge=240, le=2160,
        description="Canvas height. Omit to use the tray's own shape; if given, the guide is fitted "
                    "(centred, never stretched) inside width x height, like a camera viewport"),
    transparent: bool = Query(True, description="true: see-through PNG (same guide the app shows on the camera); "
                                                "false: dark blueprint JPEG with slot numbers"),
) -> Response:
    """Generate a live alignment camera guide wireframe for mobile/web apps.

    Can be loaded directly as an `<img>` tag or overlaid onto HTML5 / Flutter / React Native camera viewports.
    """
    tpl = get_tray_template(tray_id)
    tw = float(tpl.get("image_width") or (tpl.get("image_size") or [1448, 1086])[0])
    th = float(tpl.get("image_height") or (tpl.get("image_size") or [1448, 1086])[1])

    try:
        if transparent:
            guide = generate_camera_guide(tpl, width=width)
        else:
            guide = generate_tray_guide_overlay(tpl, width=width, height=int(round(width * th / tw)))
        overlay = _fit(guide, width, height) if height else guide

        ext = ".png" if transparent else ".jpg"
        media_type = "image/png" if transparent else "image/jpeg"

        ok, buffer = cv2.imencode(ext, overlay)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to encode overlay image")

        return Response(
            content=buffer.tobytes(),
            media_type=media_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f"inline; filename={tray_id}_guide{ext}",
            },
        )
    except Exception as e:
        logger.error(f"Error rendering guide for tray {tray_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to render guide: {e}")

