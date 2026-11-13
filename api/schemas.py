"""Pydantic schemas for the modelScaniTem REST API."""
from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Base & Health
# ─────────────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = Field("ok", description="Server status")
    version: str = Field("1.0.0", description="API version")
    timestamp: str = Field(..., description="Server timestamp (ISO format)")
    available_trays: List[str] = Field(default_factory=list, description="List of registered tray IDs")


# ─────────────────────────────────────────────────────────────────────────────
# Tray Catalog & Templates
# ─────────────────────────────────────────────────────────────────────────────

class SlotInfo(BaseModel):
    slot_number: int = Field(..., description="Slot index/number")
    tool_code: Optional[str] = Field(None, description="Tool code or part number")
    tool_name: Optional[str] = Field(None, description="Tool name in Thai/English")
    checklist_no: Optional[int] = Field(None, description="Checklist item number")
    checklist_sheet: Optional[str] = Field(None, description="Checklist sheet name")
    category: Optional[str] = Field(None, description="Tool category")
    bbox_norm: Optional[List[float]] = Field(None, description="Normalized bounding box [x1, y1, x2, y2]")
    polygon: Optional[List[List[float]]] = Field(None, description="Polygon contour points if defined")


class TraySummaryItem(BaseModel):
    tray_id: str = Field(..., description="Unique tray template identifier")
    tray_name: str = Field(..., description="Human-readable Thai label")
    total_slots: int = Field(..., description="Total number of tool slots in tray")
    has_reference_image: bool = Field(..., description="True if golden reference image exists")
    has_empty_image: bool = Field(..., description="True if empty tray reference image exists")


class TrayDetailResponse(BaseModel):
    tray_id: str
    tray_name: str
    description: Optional[str] = None
    total_slots: int
    image_size: Optional[List[int]] = None
    has_reference_image: bool = False
    has_empty_image: bool = False
    slots: List[SlotInfo] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Scanning & Inspection Results
# ─────────────────────────────────────────────────────────────────────────────

class QualityGateResponse(BaseModel):
    passed: bool
    issues: List[str] = Field(default_factory=list)
    blur_score: float
    brightness: float
    resolution: List[int]
    score: float


class AlignResponse(BaseModel):
    success: bool
    match_count: int
    inlier_ratio: float
    rotation_applied: int
    message: str
    has_homography: bool


class SlotScanResult(BaseModel):
    slot_number: int
    tool_code: Optional[str] = None
    tool_name: Optional[str] = None
    status: str = Field(..., description="'correct' | 'missing' | 'misplaced' | 'recheck'")
    status_label_th: str = Field(..., description="'ครบ' | 'ขาดหาย' | 'ผิดตำแหน่ง' | 'ตรวจซ้ำ'")
    emoji: str = Field(..., description="'🟢' | '🔴' | '🟡' | '↩️'")
    confidence: float
    slot_bbox: Optional[List[int]] = None
    reason: Optional[str] = None
    center_offset_px: Optional[float] = None
    angle_deg: Optional[float] = None
    iou_score: Optional[float] = None
    golden_score: Optional[float] = None
    empty_score: Optional[float] = None


class ScanCounters(BaseModel):
    total_slots: int
    correct: int
    missing: int
    misplaced: int
    recheck: int
    accuracy_pct: float
    is_complete: bool


class TrayScanResponse(BaseModel):
    success: bool
    tray_id: str
    tray_name: str
    counters: ScanCounters
    slots: List[SlotScanResult]
    quality: Optional[QualityGateResponse] = None
    alignment: Optional[AlignResponse] = None
    error_message: Optional[str] = None
    annotated_image_base64: Optional[str] = Field(None, description="JPEG image with color-coded bounding boxes encoded as base64 string")


class SingleToolScanResponse(BaseModel):
    success: bool
    tool_code: Optional[str] = None
    tool_name: Optional[str] = None
    confidence: float = 0.0
    status: str = "unknown"
    message: str = ""
    bbox: Optional[List[int]] = None


# ─────────────────────────────────────────────────────────────────────────────
# Inspection Submissions (Database)
# ─────────────────────────────────────────────────────────────────────────────

class InspectionSubmissionItem(BaseModel):
    id: int
    tray_id: str
    tray_name: str
    status: str
    total_slots: int
    correct: int
    missing: int
    misplaced: int
    recheck: int
    accuracy_pct: float
    created_at: str
    photo_url: Optional[str] = None
    annotated_url: Optional[str] = None


class InspectionHistoryResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[InspectionSubmissionItem]

