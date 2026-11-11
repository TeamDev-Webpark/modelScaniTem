"""
scan_workflow — Tray Inspection Pipeline

Modules:
    quality_gate  : Step 0 — ตรวจคุณภาพภาพก่อนเข้า workflow
    aligner       : Step 1 — ปรับแนวภาพด้วย Homography (SIFT/ORB + reference image)
    slot_checker  : Step 2–4 — ตรวจ presence, shape และ placement ของแต่ละช่อง
    aggregator    : Step 5 — รวมผล, กำหนดสถานะ 4 แบบ, วาดกรอบสี

Slot Status:
    "correct"   🟢  มีวัตถุ + รูปทรงตรง + ตำแหน่งดี
    "missing"   🔴  ช่องว่างชัดเจน
    "misplaced" 🟡  มีวัตถุ แต่ผิดตำแหน่ง/ทิศทาง/รูปทรง
    "recheck"   ↩️  ตัดสินไม่ได้ (แสง, สิ่งบัง, confidence ต่ำ)
"""

from .quality_gate import ImageQualityGate
from .tray_cropper import TrayBoxCropper, TrayCropResult
from .aligner import TrayAligner
from .slot_checker import SlotChecker
from .aggregator import ScanAggregator, generate_camera_guide, generate_tray_guide_overlay

__all__ = [
    "ImageQualityGate",
    "TrayBoxCropper",
    "TrayCropResult",
    "TrayAligner",
    "SlotChecker",
    "ScanAggregator",
    "generate_camera_guide",
    "generate_tray_guide_overlay",
]
