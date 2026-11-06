"""
Step 5: Scan Aggregator
รวมผลการตรวจแต่ละช่อง → สรุป + วาดกรอบสี + สร้าง annotated image

สถานะ 4 แบบ:
    🟢 correct   — มีวัตถุ + รูปทรงตรง + ตำแหน่งดี
    🔴 missing   — ช่องว่างชัดเจน
    🟡 misplaced — มีวัตถุ แต่ผิดตำแหน่ง/ทิศทาง/รูปทรง
    ↩️ recheck   — ตัดสินไม่ได้

Pipeline สมบูรณ์:
    image + tray_id
        → Quality Gate
        → TrayAligner (Homography)
        → SlotChecker (presence + shape)
        → ScanAggregator (summarize + draw)
        → ScanSummary
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .quality_gate import ImageQualityGate, QualityResult
from .tray_cropper import TrayBoxCropper, TrayCropResult
from .aligner import TrayAligner, AlignResult
from .slot_checker import SlotChecker, SlotResult

logger = logging.getLogger(__name__)

# Thai/Unicode font paths (Windows → Linux fallback)
_FONT_PATHS = [
    "C:/Windows/Fonts/tahoma.ttf",
    "C:/Windows/Fonts/leelawad.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/thai/Loma.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

# ─────────────────────────────────────────────────────────────────────────────
# สถานะสี 4 แบบ
# ─────────────────────────────────────────────────────────────────────────────
STATUS_CONFIG = {
    "correct": {
        "color_bgr": (30, 200, 50),
        "color_rgb": (30, 200, 50),
        "label_th": "ครบ",
        "emoji": "🟢",
        "thickness": 2,
    },
    "missing": {
        "color_bgr": (30, 30, 220),
        "color_rgb": (220, 30, 30),
        "label_th": "ขาดหาย",
        "emoji": "🔴",
        "thickness": 3,
    },
    "misplaced": {
        "color_bgr": (0, 200, 240),
        "color_rgb": (220, 180, 0),
        "label_th": "ผิดตำแหน่ง",
        "emoji": "🟡",
        "thickness": 2,
    },
    "recheck": {
        "color_bgr": (130, 130, 130),
        "color_rgb": (130, 130, 130),
        "label_th": "ตรวจซ้ำ",
        "emoji": "↩️",
        "thickness": 2,
    },
}


@dataclass
class ScanSummary:
    """ผลสรุปการสแกนทั้งถาด"""
    tray_id: str
    is_complete: bool
    total_slots: int
    correct_count: int
    missing_count: int
    misplaced_count: int
    recheck_count: int
    slot_results: list[dict]        # list ของ SlotResult.to_dict()
    annotated_image: Optional[np.ndarray]  # ภาพพร้อมกรอบสี
    quality: Optional[QualityResult]
    align: Optional[AlignResult]
    crop: Optional[TrayCropResult] = None   # ผลการตรวจจับขอบเขตและตัดถาด
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tray_id": self.tray_id,
            "is_complete": self.is_complete,
            "total_slots": self.total_slots,
            "correct": self.correct_count,
            "missing": self.missing_count,
            "misplaced": self.misplaced_count,
            "recheck": self.recheck_count,
            "slot_results": self.slot_results,
            "error_message": self.error_message,
        }


def _get_font(size: int = 13) -> ImageFont.FreeTypeFont:
    for p in _FONT_PATHS:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


class ScanAggregator:
    """
    Orchestrates ทั้ง pipeline และรวมผลสุดท้าย

    Usage:
        aggregator = ScanAggregator()
        aggregator.setup(tray_id, slots, ref_image)   # ทำครั้งเดียวต่อ tray
        summary = aggregator.scan(image)              # ทำทุกครั้งที่สแกน
    """

    def __init__(
        self,
        tray_refs_dir: Optional[str] = None,
        quality_gate: Optional[ImageQualityGate] = None,
        cropper: Optional[TrayBoxCropper] = None,
    ):
        self.quality_gate = quality_gate or ImageQualityGate()
        self.cropper = cropper or TrayBoxCropper()
        self.aligner = TrayAligner(tray_refs_dir=tray_refs_dir)
        self.checker = SlotChecker()

        self._tray_id: Optional[str] = None
        self._slots: list[dict] = []
        self._ready = False

    def setup(
        self,
        tray_template_or_id: Any,
        slots: Optional[list[dict]] = None,
        reference_image: Optional[np.ndarray] = None,
        empty_reference_image: Optional[np.ndarray] = None,
        use_empty_ref: bool = True,
    ) -> bool:
        """
        เตรียม pipeline สำหรับ tray
        เรียกครั้งเดียวก่อน scan()

        Args:
            tray_template_or_id   : เช่น "TRAY_YA_1_2" หรือ dict template ที่มี tray_id และ slots
            slots                 : จาก JSON template["slots"] (ถ้า tray_template_or_id เป็น str)
            reference_image       : ถ้า None จะโหลดจาก tray_refs_dir อัตโนมัติ
            empty_reference_image : ภาพถาดว่างที่จัดระนาบตรงกับ reference แล้ว
                                    ถ้า None จะลองโหลด <tray_refs_dir>/<tray_id>_empty.jpg
            use_empty_ref         : False = ไม่ใช้ภาพถาดว่าง (เทียบกับต้นแบบอย่างเดียว)

        Returns:
            True ถ้าพร้อมใช้งาน
        """
        template_size = None
        if isinstance(tray_template_or_id, dict):
            tray_id = tray_template_or_id.get("tray_id", "unknown")
            slots = slots if slots is not None else tray_template_or_id.get("slots", [])
            tw = tray_template_or_id.get("image_width") or (tray_template_or_id.get("image_size") or [None, None])[0]
            th = tray_template_or_id.get("image_height") or (tray_template_or_id.get("image_size") or [None, None])[1]
            if tw and th:
                template_size = (int(tw), int(th))
        else:
            tray_id = str(tray_template_or_id)
            slots = slots if slots is not None else []

        self._tray_id = tray_id
        self._slots = slots

        # กำหนดหรือโหลด reference image
        if reference_image is not None:
            self.aligner.set_reference_image(tray_id, reference_image)
            ok = True
        else:
            ok = self.aligner.load_reference(tray_id)

        if not ok and reference_image is None:
            logger.warning(
                f"ScanAggregator: ไม่มี reference image สำหรับ '{tray_id}' — "
                "align จะใช้ภาพต้นแบบไม่ได้ แต่ยังสามารถตรวจสอบบนภาพปัจจุบันได้"
            )

        # โหลด empty_refs จาก reference image
        ref_img = reference_image if reference_image is not None else self.aligner.get_reference_image(tray_id)
        if ref_img is not None and slots:
            empty_img = empty_reference_image if use_empty_ref else None
            if empty_img is None and use_empty_ref:
                for ext in (".jpg", ".png"):
                    p = self.aligner.tray_refs_dir / f"{tray_id}_empty{ext}"
                    if p.exists():
                        empty_img = cv2.imread(str(p))
                        break
                # <tray_id>_empty.jpg ถูกจัดให้ตรงกับ <tray_id>.jpg เท่านั้น
                # ถ้าส่งภาพต้นแบบอื่นเข้ามา (มุมกล้องต่างกัน) จะเทียบกันไม่ได้ → ไม่ใช้ภาพถาดว่าง
                if empty_img is not None and reference_image is not None:
                    stored = self.aligner._find_ref_image(tray_id)
                    stored_img = cv2.imread(str(stored)) if stored else None
                    if stored_img is None or not self._same_image(reference_image, stored_img):
                        logger.info(
                            f"ScanAggregator: ภาพต้นแบบที่ส่งมาไม่ใช่ {tray_id}.jpg ใน tray_refs "
                            "— ไม่ใช้ภาพถาดว่าง (เทียบกับต้นแบบอย่างเดียว)"
                        )
                        empty_img = None
            if empty_img is not None and empty_img.shape[:2] != ref_img.shape[:2]:
                empty_img = cv2.resize(empty_img, (ref_img.shape[1], ref_img.shape[0]))
            loaded = self.checker.load_empty_refs(
                ref_img, slots, template_size=template_size, empty_image=empty_img
            )
            logger.info(f"ScanAggregator: setup '{tray_id}' — {loaded} empty_refs โหลดแล้ว")

        self._ready = True
        return True

    @staticmethod
    def _same_image(a: np.ndarray, b: np.ndarray, max_diff: float = 8.0) -> bool:
        """ภาพสองภาพเป็นภาพเดียวกันไหม (ยอมให้ต่างจากการบีบอัด/ย่อขนาดเล็กน้อย)"""
        def small(im):
            g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) if len(im.shape) == 3 else im
            return cv2.resize(g, (256, 192), interpolation=cv2.INTER_AREA).astype(np.float32)
        return float(np.abs(small(a) - small(b)).mean()) <= max_diff

    def scan(
        self,
        image: np.ndarray,
        skip_quality: bool = False,
        skip_crop: bool = False,
        crop_mode: str = "smart",
    ) -> ScanSummary:
        """
        รัน full pipeline และส่งคืน ScanSummary

        Args:
            image        : ภาพจากกล้องมือถือหรืออัปโหลด (BGR)
            skip_quality : ถ้า True จะข้าม quality gate (สำหรับ debug/ทดสอบ)
            skip_crop    : ถ้า True จะข้าม auto-crop
            crop_mode    : "smart" (SIFT-First Hybrid: ไม่ตัดขอบถ้าจัดระนาบได้โดยตรง), 
                           "off" (ปิดการตัดขอบ ใช้ภาพเต็ม 100%), 
                           "force" (บังคับตัดขอบ auto-crop ก่อนเสมอ)

        Returns:
            ScanSummary — ผลสรุปพร้อม annotated_image
        """
        tray_id = self._tray_id or "unknown"

        def _empty_summary(msg: str, q=None, a=None, c=None) -> ScanSummary:
            return ScanSummary(
                tray_id=tray_id,
                is_complete=False,
                total_slots=len(self._slots),
                correct_count=0,
                missing_count=0,
                misplaced_count=0,
                recheck_count=0,
                slot_results=[],
                annotated_image=image.copy() if image is not None else None,
                quality=q,
                align=a,
                crop=c,
                error_message=msg,
            )

        # ── Step 0: Auto-Rotate to Landscape if Portrait ────────────────────
        was_portrait = False
        if image is not None and image.shape[0] > image.shape[1]:
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
            was_portrait = True
            logger.info(f"ScanAggregator: ตรวจพบภาพแนวตั้ง ({image.shape[1]}x{image.shape[0]}) -> ปรับหมุนเป็นแนวนอน 90° อัตโนมัติ")

        # ── Step 0.2: Quality Gate ──────────────────────────────────────────
        quality_result = None
        if not skip_quality:
            quality_result = self.quality_gate.check(image)
            if not quality_result.passed:
                issues_str = " | ".join(quality_result.issues)
                return _empty_summary(f"คุณภาพภาพไม่ผ่าน: {issues_str}", q=quality_result)

        # ── Step 0.5 & 1: SIFT-First Hybrid Alignment & Smart Cropping ────────
        crop_result = None
        align_result = None
        working_image = image

        if skip_crop or crop_mode == "off":
            # ปิดการตัดขอบ — ทำ SIFT Alignment บนภาพเต็มเฟรม 100%
            crop_result = TrayCropResult(
                success=True,
                cropped_image=image,
                area_ratio=1.0,
                is_too_far=False,
                message="ปิดการตัดขอบ (ใช้งานภาพเต็มเฟรม 100%)",
            )
            if self._ready and self._tray_id:
                align_result = self.aligner.align(image, self._tray_id)
                if align_result.success and align_result.aligned_image is not None:
                    working_image = align_result.aligned_image
                    logger.info(f"Align (Full Image): {align_result.message}")
                else:
                    logger.warning(f"Align ไม่สำเร็จ: {align_result.message}")

        elif crop_mode == "force":
            # บังคับตัดขอบ Auto-Crop ก่อนเสมอ
            crop_result = self.cropper.detect_and_crop(image)
            if crop_result.is_too_far:
                return _empty_summary(crop_result.message, q=quality_result, c=crop_result)
            if crop_result.success and crop_result.cropped_image is not None:
                working_image = crop_result.cropped_image
                logger.info(f"Force Auto-Crop: {crop_result.message}")
            if self._ready and self._tray_id:
                align_result = self.aligner.align(working_image, self._tray_id)
                if align_result.success and align_result.aligned_image is not None:
                    working_image = align_result.aligned_image

        else:
            # 🌟 SMART MODE (SIFT-First Hybrid): แนะนำเป็นอันดับ 1
            # 1. กรณีภาพถ่ายในตู้/ลิ้นชักสีแดง (Red Chest Enclosure):
            # มีขอบตู้เหล็กและรางข้าง (เช่น ปืนลม DG-10, เหล็กงัด) ที่ไม่ใช่ส่วนของถาด
            # ให้ตัดขอบตู้และแยกเฉพาะถาดโฟมดำทันทีก่อนจัดระนาบ เพื่อให้ระนาบแม่นยำสูงสุด
            if self.cropper.is_red_chest_enclosure(image):
                logger.info("SIFT-First: ตรวจพบภาพในตู้/ลิ้นชักสีแดง -> แยกถาดโฟมดำและตัดสิ่งแปลกปลอมในรางข้างออกโดยอัตโนมัติ")
                crop_result = self.cropper.detect_and_crop(image)
                if crop_result.is_too_far:
                    return _empty_summary(crop_result.message, q=quality_result, c=crop_result)
                if crop_result.success and crop_result.cropped_image is not None:
                    working_image = crop_result.cropped_image
                if self._ready and self._tray_id:
                    align_result = self.aligner.align(working_image, self._tray_id)
                    if align_result.success and align_result.aligned_image is not None:
                        working_image = align_result.aligned_image
            else:
                # 2. กรณีถาดทั่วไปบนโต๊ะ: ทดสอบ SIFT Alignment บนภาพจริงโดยตรงก่อน
                direct_align = None
                if self._ready and self._tray_id:
                    direct_align = self.aligner.align(image, self._tray_id)

                if direct_align and direct_align.success and direct_align.match_count >= 15:
                    align_result = direct_align
                    working_image = direct_align.aligned_image
                    crop_result = TrayCropResult(
                        success=True,
                        cropped_image=image,
                        area_ratio=1.0,
                        is_too_far=False,
                        message=f"จัดระนาบสำเร็จโดยตรงด้วย SIFT Homography ({direct_align.match_count} จุดตรงกัน — คมชัดสูงสุดโดยไม่ตัดขอบ)",
                    )
                    logger.info(f"SIFT-First: Direct alignment succeeded ({direct_align.match_count} matches). Bypassing cropper.")
                else:
                    # กรณี SIFT บนภาพเต็มไม่ผ่าน (เช่น ถ่ายไกลมาก ถาดเล็ก หรือฉากหลังรบกวน) -> Fallback ไปใช้ Auto-Crop เพื่อช่วยซูมหาถาด
                    logger.info("SIFT-First: Direct alignment insufficient. Triggering fallback Auto-Crop...")
                    crop_result = self.cropper.detect_and_crop(image)
                    if crop_result.is_too_far:
                        return _empty_summary(crop_result.message, q=quality_result, c=crop_result, a=direct_align)

                    if crop_result.success and crop_result.cropped_image is not None:
                        working_image = crop_result.cropped_image
                        logger.info(f"Fallback Auto-Crop: {crop_result.message}")

                    # ลอง Align ซ้ำบนภาพที่ครอปแล้ว
                    if self._ready and self._tray_id:
                        retry_align = self.aligner.align(working_image, self._tray_id)
                        if retry_align.success and retry_align.aligned_image is not None:
                            working_image = retry_align.aligned_image
                            align_result = retry_align
                            logger.info(f"Align (After Crop): {retry_align.message}")
                        else:
                            align_result = direct_align if (direct_align and direct_align.match_count > retry_align.match_count) else retry_align

        # ── Step 2–4: ตรวจแต่ละช่อง ─────────────────────────────────────────
        has_ref = self.aligner.get_reference_image(tray_id) is not None
        if has_ref and not (align_result and align_result.success):
            # จัดระนาบไม่ได้ → กรอบช่องจะวางผิดที่ ผลจึงเชื่อไม่ได้: ให้ทุกช่องเป็น "ตรวจซ้ำ" และขอให้ถ่ายใหม่
            slot_results = []
            for s in self._slots:
                r = SlotResult(s.get("slot_number", 0))
                r.status, r.confidence = "recheck", 0.0
                r.reason = "จัดระนาบภาพไม่สำเร็จ — ตรวจช่องนี้ไม่ได้"
                slot_results.append(r)
            names = {s.get("slot_number", 0): s.get("name", "") for s in self._slots}
            results_dicts = [{**r.to_dict(), "item_name": names.get(r.slot_number, "")} for r in slot_results]
            n = len(slot_results)
            return ScanSummary(
                tray_id=tray_id, is_complete=False, total_slots=len(self._slots),
                correct_count=0, missing_count=0, misplaced_count=0, recheck_count=n,
                slot_results=results_dicts, annotated_image=working_image.copy(),
                quality=quality_result, align=align_result, crop=crop_result,
                error_message=(
                    "จัดระนาบภาพให้ตรงกับถาดต้นแบบไม่สำเร็จ "
                    f"({align_result.match_count if align_result else 0} จุดตรงกัน) — "
                    "ถ่ายใหม่ให้เห็นถาดเต็มเฟรม ตรงหน้า และไม่มีแสงสะท้อน"
                ),
            )

        slot_results: list[SlotResult] = self.checker.check_all_slots(working_image, self._slots)

        # ── Step 5: รวมผลและวาดกรอบ ─────────────────────────────────────────
        annotated = self._draw_results(working_image, slot_results, self._slots)

        correct = sum(1 for r in slot_results if r.status == "correct")
        missing = sum(1 for r in slot_results if r.status == "missing")
        misplaced = sum(1 for r in slot_results if r.status == "misplaced")
        recheck = sum(1 for r in slot_results if r.status == "recheck")

        # เพิ่มชื่อเครื่องมือจาก slot template
        slot_name_map = {s.get("slot_number", 0): s.get("name", "") for s in self._slots}
        results_dicts = []
        for r in slot_results:
            d = r.to_dict()
            d["item_name"] = slot_name_map.get(r.slot_number, "")
            results_dicts.append(d)

        return ScanSummary(
            tray_id=tray_id,
            is_complete=(missing == 0 and misplaced == 0 and recheck == 0),
            total_slots=len(self._slots),
            correct_count=correct,
            missing_count=missing,
            misplaced_count=misplaced,
            recheck_count=recheck,
            slot_results=results_dicts,
            annotated_image=annotated,
            quality=quality_result,
            align=align_result,
            crop=crop_result,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Drawing
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_results(
        self,
        image: np.ndarray,
        results: list[SlotResult],
        slots: list[dict],
    ) -> np.ndarray:
        """วาดกรอบสีและ badge label บนภาพ"""
        annotated = image.copy()
        slot_name_map = {s.get("slot_number", 0): s.get("name", "") for s in slots}

        # ── วาดกรอบ (OpenCV) ─────────────────────────────────────────────────
        for r in results:
            if not r.slot_bbox_px or len(r.slot_bbox_px) < 4:
                continue
            x1, y1, x2, y2 = r.slot_bbox_px
            cfg = STATUS_CONFIG.get(r.status, STATUS_CONFIG["recheck"])
            cv2.rectangle(annotated, (x1, y1), (x2, y2), cfg["color_bgr"], cfg["thickness"])

            # วาดจุดกึ่งกลาง contour ถ้ามี
            if r.contour_center and r.status == "misplaced":
                cx, cy = r.contour_center
                cx_abs = x1 + cx
                cy_abs = y1 + cy
                cv2.circle(annotated, (cx_abs, cy_abs), 4, cfg["color_bgr"], -1)

        # ── วาด label (PIL → Thai font) ───────────────────────────────────────
        img_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        draw = ImageDraw.Draw(pil_img)
        font_sm = _get_font(12)

        for r in results:
            if not r.slot_bbox_px or len(r.slot_bbox_px) < 4:
                continue
            x1, y1, x2, y2 = r.slot_bbox_px
            cfg = STATUS_CONFIG.get(r.status, STATUS_CONFIG["recheck"])
            color_rgb = cfg["color_rgb"]

            badge_text = f"#{r.slot_number}"

            try:
                bbox = draw.textbbox((x1, y1), badge_text, font=font_sm)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
            except Exception:
                tw, th = 30, 14

            badge_y1 = max(0, y1 - th - 4)
            badge_y2 = y1
            draw.rectangle([x1, badge_y1, x1 + tw + 6, badge_y2], fill=color_rgb)
            draw.text((x1 + 3, badge_y1 + 1), badge_text, font=font_sm, fill=(255, 255, 255))

        annotated_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return annotated_bgr

    # ──────────────────────────────────────────────────────────────────────────
    # Convenience: สร้างและ setup จาก tray template dict
    # ──────────────────────────────────────────────────────────────────────────

    @classmethod
    def from_template(
        cls,
        tray_template: dict,
        tray_refs_dir: Optional[str] = None,
    ) -> "ScanAggregator":
        """
        สร้าง ScanAggregator จาก tray template dict โดยตรง

        Args:
            tray_template : dict ที่โหลดจาก TRAY_YA_1_2.json
            tray_refs_dir : โฟลเดอร์ที่เก็บ reference images

        Returns:
            ScanAggregator ที่ setup() แล้ว
        """
        agg = cls(tray_refs_dir=tray_refs_dir)
        tray_id = tray_template.get("tray_id", "unknown")
        slots = tray_template.get("slots", [])
        agg.setup(tray_id, slots)
        return agg


def generate_tray_guide_overlay(
    tray_template: dict,
    width: int = 1024,
    height: int = 768,
    transparent_bg: bool = False,
) -> np.ndarray:
    """
    สร้างภาพร่างนำทางการเล็ง (Camera Alignment Guide Overlay)
    แสดงกรอบถาด, จุดมุม 4 ด้าน, เส้นประแต่ละช่อง และหมายเลขเครื่องมือ
    เพื่อให้ผู้ใช้จัดตำแหน่งกล้องบนมือถือ/iPad ให้ตรงกับถาดจริงได้อย่างแม่นยำ

    Args:
        tray_template  : dict template เช่น TRAY_YA_1_2.json
        width, height  : ขนาดภาพไกด์ที่ต้องการ
        transparent_bg : ถ้า True ส่งคืน RGBA โปร่งใส, ถ้า False ส่งคืน BGR พื้นหลัง blueprint สีเข้ม

    Returns:
        np.ndarray (BGR หรือ RGBA)
    """
    slots = tray_template.get("slots", [])
    tray_name = tray_template.get("tray_name", "ถาดเครื่องมือ")

    if transparent_bg:
        canvas = np.zeros((height, width, 4), dtype=np.uint8)
        border_color = (0, 220, 255, 230)      # Cyan
        slot_color = (0, 255, 128, 180)        # Green
        corner_color = (0, 230, 255, 255)
    else:
        # Dark blueprint background (#1A1E24)
        canvas = np.full((height, width, 3), (36, 30, 26), dtype=np.uint8)
        border_color = (0, 220, 255)
        slot_color = (0, 255, 128)
        corner_color = (0, 230, 255)

    # 1. กรอบขอบถาด (Outer Margin 3%)
    margin_x = int(width * 0.03)
    margin_y = int(height * 0.03)
    x1_tray = margin_x
    y1_tray = margin_y
    x2_tray = width - margin_x
    y2_tray = height - margin_y

    cv2.rectangle(canvas, (x1_tray, y1_tray), (x2_tray, y2_tray), border_color, 2)

    # 2. เครื่องหมายมุม 4 ด้าน (Corner L-marks)
    arm = int(min(width, height) * 0.06)
    # บนซ้าย
    cv2.line(canvas, (x1_tray, y1_tray), (x1_tray + arm, y1_tray), corner_color, 4)
    cv2.line(canvas, (x1_tray, y1_tray), (x1_tray, y1_tray + arm), corner_color, 4)
    # บนขวา
    cv2.line(canvas, (x2_tray, y1_tray), (x2_tray - arm, y1_tray), corner_color, 4)
    cv2.line(canvas, (x2_tray, y1_tray), (x2_tray, y1_tray + arm), corner_color, 4)
    # ล่างซ้าย
    cv2.line(canvas, (x1_tray, y2_tray), (x1_tray + arm, y2_tray), corner_color, 4)
    cv2.line(canvas, (x1_tray, y2_tray), (x1_tray, y2_tray - arm), corner_color, 4)
    # ล่างขวา
    cv2.line(canvas, (x2_tray, y2_tray), (x2_tray - arm, y2_tray), corner_color, 4)
    cv2.line(canvas, (x2_tray, y2_tray), (x2_tray, y2_tray - arm), corner_color, 4)

    # 3. เป้ากึ่งกลาง (Center Crosshair)
    cx, cy = width // 2, height // 2
    c_color = (100, 100, 100, 150) if transparent_bg else (80, 80, 80)
    cv2.line(canvas, (cx - 20, cy), (cx + 20, cy), c_color, 1)
    cv2.line(canvas, (cx, cy - 20), (cx, cy + 20), c_color, 1)
    cv2.circle(canvas, (cx, cy), 15, c_color, 1)

    # 4. วาดช่องเครื่องมือตาม polygon (หรือ bbox_norm ถ้าไม่มี polygon)
    orig_w = tray_template.get("image_width") or tray_template.get("image_size", [1448, 1086])[0] or 1448
    orig_h = tray_template.get("image_height") or tray_template.get("image_size", [1448, 1086])[1] or 1086
    scale_x = width / float(orig_w)
    scale_y = height / float(orig_h)

    for s in slots:
        polygon = s.get("polygon")
        if polygon and len(polygon) >= 3:
            poly_scaled = []
            for pt in polygon:
                poly_scaled.append([int(pt[0] * scale_x), int(pt[1] * scale_y)])
            pts_arr = np.array(poly_scaled, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [pts_arr], isClosed=True, color=slot_color, thickness=1, lineType=cv2.LINE_AA)
        else:
            b = s.get("bbox_norm")
            if not b or len(b) < 4:
                continue
            sx1 = int(b[0] * width)
            sy1 = int(b[1] * height)
            sx2 = int(b[2] * width)
            sy2 = int(b[3] * height)
            cv2.rectangle(canvas, (sx1, sy1), (sx2, sy2), slot_color, 1)

    # 5. วาดข้อความกำกับด้วย PIL
    if transparent_bg:
        img_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGRA2RGBA)
        pil_img = Image.fromarray(img_rgb)
    else:
        img_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

    draw = ImageDraw.Draw(pil_img)
    font_title = _get_font(15)
    font_sm = _get_font(11)

    # Title & Instructions
    title_text = f"📐 ไกด์เล็งถ่ายภาพ: {tray_name} ({len(slots)} ช่อง)"
    sub_text = "จัดขอบถาดจริงให้ตรงกับเส้นกรอบสีเขียว/ฟ้าด้านบน แล้วกดถ่ายภาพ"
    draw.text((x1_tray + 10, y1_tray + 8), title_text, font=font_title, fill=(0, 230, 255))
    draw.text((x1_tray + 10, y1_tray + 28), sub_text, font=font_sm, fill=(200, 200, 200))

    # Slot Numbers
    for s in slots:
        b = s.get("bbox_norm")
        if not b or len(b) < 4:
            continue
        sx1 = int(b[0] * width)
        sy1 = int(b[1] * height)
        num_str = f"#{s.get('slot_number', 0)}"
        draw.text((sx1 + 2, sy1 + 1), num_str, font=font_sm, fill=(0, 255, 128))

    if transparent_bg:
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGBA2BGRA)
    else:
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
