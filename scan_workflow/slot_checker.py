"""
Step 2–4: Slot Checker
ตรวจสอบแต่ละช่องของถาดหลังจาก align แล้ว

ลำดับการตรวจ:
    Step 2 — ตัด slot crop ตาม bbox_norm
    Step 3 — ตรวจว่ามีวัตถุในช่อง (เทียบกับ empty_ref)
    Step 4 — ตรวจรูปทรง ตำแหน่ง และทิศทาง (เทียบกับ polygon ต้นแบบ)

สถานะที่ส่งคืน:
    "correct"   — มีวัตถุ + shape ตรง + ตำแหน่งดี
    "missing"   — ช่องว่างชัดเจน
    "misplaced" — มีวัตถุ แต่ผิดตำแหน่ง/ทิศทาง/รูปทรง
    "recheck"   — ตัดสินไม่ได้ (confidence ต่ำ, แสงสะท้อน ฯลฯ)
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# ค่า default tolerance — ปรับหลังทดสอบภาพจริง
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_TOLERANCE = {
    "center_px": 14,    # จุดกึ่งกลางวัตถุเยื้องได้ไม่เกิน 14px
    "angle_deg": 20.0,  # มุมหมุนได้ไม่เกิน 20°
    "iou_min": 0.45,    # IoU กับ polygon ต้นแบบต้องไม่ต่ำกว่า 0.45
}

# Presence detection: ค่าขีดสำหรับแยก "มีของ" กับ "ช่องว่าง"
PRESENCE_STD_THRESHOLD = 16.0       # std ของ pixel ใน slot
PRESENCE_EDGE_THRESHOLD = 0.035     # สัดส่วน edge pixel
PRESENCE_SSIM_THRESHOLD = 0.82     # ถ้าคล้าย empty_ref มาก → ว่าง
RECHECK_CONFIDENCE_THRESHOLD = 0.55 # ถ้า confidence ต่ำกว่านี้ → recheck

# Masked reference comparison: เทียบภาพเฉพาะพื้นที่ polygon ของช่องกับภาพต้นแบบ (ถาดครบ)
# และภาพถาดว่าง (ถ้ามี) — ใช้แทนการดูความหยาบของภาพในกรอบสี่เหลี่ยม ซึ่งช่องโฟมว่างก็มีขอบรอยตัดชัด
WORK_MAX_SIDE = 1600        # ย่อภาพให้ด้านยาวไม่เกินนี้ก่อนเทียบ (เร็วขึ้น และลด noise)
MATCH_SEARCH_FRAC = 0.008   # เลื่อนหาตำแหน่งที่ตรงที่สุดได้ ± สัดส่วนนี้ของด้านยาว (ชดเชย align เพี้ยนเล็กน้อย)
MIN_MASK_AREA = 150         # polygon เล็กกว่านี้ (px ในภาพย่อ) จะถูกขยายออกก่อนเทียบ
GOLDEN_MATCH_OK = 0.55      # มีภาพถาดว่าง: คล้ายต้นแบบอย่างน้อยเท่านี้ → วางตรงตำแหน่ง (ต่ำกว่า → วางผิด)
EMPTY_MARGIN = 0.10         # มีภาพถาดว่าง: ต้องคล้ายภาพหนึ่งมากกว่าอีกภาพอย่างน้อยเท่านี้จึงตัดสิน
# ไม่มีภาพถาดว่าง: ช่องโฟมว่างยังมีขอบรอยตัดรูปทรงเดียวกับเครื่องมือ คะแนนต้นแบบจึงสูงได้ถึง ~0.85
# ใช้เกณฑ์เข้มและเผื่อช่วง "ตรวจซ้ำ" ไว้ตรงกลาง — ควรมี <tray_id>_empty.jpg เสมอ
GOLDEN_ONLY_OK = 0.80       # คล้ายต้นแบบอย่างน้อยเท่านี้ → มีเครื่องมือ
GOLDEN_ONLY_MISSING = 0.50  # ต่ำกว่านี้ → ไม่พบเครื่องมือตามต้นแบบ


class SlotResult:
    """ผลตรวจสอบของช่องเดียว"""
    __slots__ = (
        "slot_number", "status", "confidence",
        "slot_bbox_px",  # [x1, y1, x2, y2] ใน aligned image
        "contour_center", "template_center", "center_offset_px",
        "angle_deg", "iou_score",
        "reason",        # ข้อความอธิบายเหตุผล
        "crop",          # numpy array ของ slot crop (สำหรับ debug/UI)
        "golden_score",  # ความคล้ายกับภาพต้นแบบในพื้นที่ polygon (None = ไม่ได้เทียบ)
        "empty_score",   # ความคล้ายกับภาพถาดว่างในพื้นที่ polygon (None = ไม่มีภาพถาดว่าง)
    )

    def __init__(self, slot_number: int):
        self.slot_number = slot_number
        self.status = "recheck"
        self.confidence = 0.0
        self.slot_bbox_px: list[int] = []
        self.contour_center: Optional[tuple[int, int]] = None
        self.template_center: Optional[tuple[int, int]] = None
        self.center_offset_px: float = 0.0
        self.angle_deg: float = 0.0
        self.iou_score: float = 0.0
        self.reason: str = ""
        self.crop: Optional[np.ndarray] = None
        self.golden_score: Optional[float] = None
        self.empty_score: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        rnd = lambda v: None if v is None else round(v, 3)
        return {
            "slot_number": self.slot_number,
            "status": self.status,
            "confidence": round(self.confidence, 3),
            "slot_bbox": self.slot_bbox_px,
            "reason": self.reason,
            "center_offset_px": round(self.center_offset_px, 1),
            "angle_deg": round(self.angle_deg, 1),
            "iou_score": round(self.iou_score, 3),
            "golden_score": rnd(self.golden_score),
            "empty_score": rnd(self.empty_score),
        }


class SlotChecker:
    """
    ตรวจสอบแต่ละช่องของถาดจาก aligned image

    Usage:
        checker = SlotChecker()
        checker.load_empty_refs(ref_image, slots)   # โหลด empty_ref crops
        results = checker.check_all_slots(aligned_image, slots)
    """

    def __init__(self, ref_mode: str = "golden"):
        # ref_mode: "golden" (ภาพถาดที่มีเครื่องมือครบ — default) หรือ "empty" (ถาดว่างเปล่า)
        self.ref_mode = ref_mode
        self._refs: dict[int, np.ndarray] = {}
        # ขนาดภาพที่ใช้วาด polygon ในเทมเพลต (image_width, image_height)
        self._template_size: Optional[tuple[int, int]] = None
        # ภาพต้นแบบ/ถาดว่างที่ย่อแล้ว และข้อมูล polygon ต่อช่อง สำหรับ masked comparison
        self._work_size: Optional[tuple[int, int]] = None
        self._golden_work: Optional[np.ndarray] = None
        self._empty_work: Optional[np.ndarray] = None
        self._geo: dict[int, tuple] = {}
        # CLAHE สำหรับลดแสงสะท้อนจ้า (Specular Glare) บนผิวโลหะชุบโครเมียม
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    # ──────────────────────────────────────────────────────────────────────────
    # Setup
    # ──────────────────────────────────────────────────────────────────────────

    def load_empty_refs(
        self,
        reference_image: np.ndarray,
        slots: list[dict],
        ref_image_size: Optional[tuple[int, int]] = None,
        ref_mode: Optional[str] = None,
        template_size: Optional[tuple[int, int]] = None,
        empty_image: Optional[np.ndarray] = None,
    ) -> int:
        """
        สร้าง reference crops (golden sample หรือ empty ref) โดย ROI crop จาก template reference image

        Args:
            reference_image : ภาพ reference ที่ถ่ายตรง (BGR หรือ Gray)
            slots           : รายการช่องจาก JSON (มี bbox_norm)
            ref_image_size  : (w, h) ถ้าต้องการ override ขนาดจาก image
            ref_mode        : "golden" (เครื่องมือครบ) หรือ "empty" (ถาดว่าง)
            template_size   : (image_width, image_height) ของเทมเพลตที่ใช้วาด polygon
                              ถ้าไม่ระบุจะคำนวณจาก polygon เทียบกับ bbox_norm
            empty_image     : ภาพถาดว่างที่จัดระนาบตรงกับ reference_image แล้ว (ไม่บังคับ)

        Returns:
            จำนวน slot ที่โหลดสำเร็จ
        """
        if reference_image is None:
            return 0

        if ref_mode:
            self.ref_mode = ref_mode

        gray_ref = (
            cv2.cvtColor(reference_image, cv2.COLOR_BGR2GRAY)
            if len(reference_image.shape) == 3
            else reference_image.copy()
        )
        h, w = gray_ref.shape[:2]
        if ref_image_size:
            w, h = ref_image_size

        loaded = 0
        for slot in slots:
            sn = slot.get("slot_number", 0)
            bbox_norm = slot.get("bbox_norm")
            if not bbox_norm or len(bbox_norm) < 4:
                continue

            x1 = max(0, int(bbox_norm[0] * w))
            y1 = max(0, int(bbox_norm[1] * h))
            x2 = min(w, int(bbox_norm[2] * w))
            y2 = min(h, int(bbox_norm[3] * h))

            crop = gray_ref[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            self._refs[sn] = crop
            loaded += 1

        self._template_size = tuple(template_size) if template_size else self._infer_template_size(slots)

        # ── เตรียม masked comparison (golden mode เท่านั้น) ──
        self._geo = {}
        self._golden_work = self._empty_work = None
        if self.ref_mode == "golden":
            k = min(1.0, WORK_MAX_SIDE / float(max(w, h)))
            self._work_size = (max(1, int(round(w * k))), max(1, int(round(h * k))))
            self._golden_work = self._prep_work(gray_ref)
            if empty_image is not None:
                gray_empty = (
                    cv2.cvtColor(empty_image, cv2.COLOR_BGR2GRAY)
                    if len(empty_image.shape) == 3 else empty_image
                )
                self._empty_work = self._prep_work(gray_empty)
            for slot in slots:
                geo = self._slot_geometry(slot)
                if geo is not None:
                    self._geo[slot.get("slot_number", 0)] = geo

        logger.info(
            f"SlotChecker: โหลด reference ({self.ref_mode}) สำเร็จ {loaded}/{len(slots)} ช่อง, "
            f"masked compare {len(self._geo)} ช่อง, empty ref={'มี' if self._empty_work is not None else 'ไม่มี'}"
        )
        return loaded

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers: template geometry & masked comparison
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _infer_template_size(slots: list[dict]) -> Optional[tuple[int, int]]:
        """หา (width, height) ของภาพที่ใช้วาด polygon จาก polygon เทียบกับ bbox_norm ของช่องเดียวกัน"""
        ws, hs = [], []
        for s in slots:
            poly, b = s.get("polygon") or [], s.get("bbox_norm") or []
            if len(poly) < 3 or len(b) < 4:
                continue
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            if b[2] > 0.05:
                ws.append(max(xs) / b[2])
            if b[3] > 0.05:
                hs.append(max(ys) / b[3])
        if not ws or not hs:
            return None
        return int(round(float(np.median(ws)))), int(round(float(np.median(hs))))

    def _polygon_px(self, polygon: list, img_w: int, img_h: int) -> Optional[np.ndarray]:
        """แปลง polygon จากพิกัดเทมเพลตเป็นพิกัดภาพขนาด img_w x img_h"""
        if not polygon or len(polygon) < 3:
            return None
        tw, th = self._template_size or (img_w, img_h)
        pts = np.array(polygon, dtype=np.float32).reshape(-1, 2)
        pts[:, 0] *= img_w / float(tw)
        pts[:, 1] *= img_h / float(th)
        return np.round(pts).astype(np.int32)

    def _prep_work(self, gray: np.ndarray) -> np.ndarray:
        img = cv2.resize(gray, self._work_size, interpolation=cv2.INTER_AREA).astype(np.float32)
        return cv2.GaussianBlur(img, (3, 3), 0)

    def _slot_geometry(self, slot: dict) -> Optional[tuple]:
        """ตำแหน่งและ mask ของช่องในภาพย่อ: (x, y, w, h, mask, golden_patch, empty_patch)"""
        W, H = self._work_size
        poly = self._polygon_px(slot.get("polygon") or [], W, H)
        mask_full = np.zeros((H, W), np.uint8)
        if poly is not None:
            cv2.fillPoly(mask_full, [poly.reshape(-1, 1, 2)], 255)
        else:
            b = slot.get("bbox_norm") or []
            if len(b) < 4:
                return None
            cv2.rectangle(mask_full, (int(b[0] * W), int(b[1] * H)), (int(b[2] * W), int(b[3] * H)), 255, -1)
        if np.count_nonzero(mask_full) < MIN_MASK_AREA:
            mask_full = cv2.dilate(mask_full, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
        x, y, w, h = cv2.boundingRect(mask_full)
        if w < 3 or h < 3:
            return None
        mask = mask_full[y:y + h, x:x + w]
        gold = self._golden_work[y:y + h, x:x + w]
        if float(gold[mask > 0].std()) < 2.0:  # ภาพต้นแบบในช่องเรียบเกินไป เทียบไม่ได้
            return None
        empty = self._empty_work[y:y + h, x:x + w] if self._empty_work is not None else None
        return x, y, w, h, mask.astype(np.float32), gold, empty

    @staticmethod
    def _masked_match(scene: np.ndarray, patch: np.ndarray, mask: np.ndarray,
                      x: int, y: int, r: int) -> tuple[float, tuple[int, int]]:
        """NCC เฉพาะใน mask ระหว่าง patch กับ scene รอบตำแหน่ง (x, y) เลื่อนได้ ±r px → (คะแนนสูงสุด, (dx, dy))"""
        H, W = scene.shape[:2]
        h, w = patch.shape[:2]
        sx1, sy1 = max(0, x - r), max(0, y - r)
        sx2, sy2 = min(W, x + w + r), min(H, y + h + r)
        search = scene[sy1:sy2, sx1:sx2]
        if search.shape[0] < h or search.shape[1] < w:
            return 0.0, (0, 0)
        try:
            res = cv2.matchTemplate(search, patch, cv2.TM_CCOEFF_NORMED, mask=mask)
        except cv2.error:
            return 0.0, (0, 0)
        res = np.nan_to_num(res, nan=-1.0, posinf=-1.0, neginf=-1.0)
        _, best, _, loc = cv2.minMaxLoc(res)
        return float(best), (sx1 + loc[0] - x, sy1 + loc[1] - y)

    def _reference_scores(self, scene_work: np.ndarray, sn: int) -> Optional[dict]:
        """คะแนนความคล้ายของช่องกับภาพต้นแบบ (golden) และภาพถาดว่าง (empty)"""
        geo = self._geo.get(sn)
        if geo is None:
            return None
        x, y, w, h, mask, gold, empty = geo
        r = max(2, int(round(MATCH_SEARCH_FRAC * max(self._work_size))))
        g, shift = self._masked_match(scene_work, gold, mask, x, y, r)
        e = None
        if empty is not None and float(empty[mask > 0].std()) >= 2.0:
            e, _ = self._masked_match(scene_work, empty, mask, x, y, r)
        return {"golden": g, "empty": e, "shift": shift}

    # ──────────────────────────────────────────────────────────────────────────
    # Main check
    # ──────────────────────────────────────────────────────────────────────────

    def check_all_slots(
        self,
        aligned_image: np.ndarray,
        slots: list[dict],
    ) -> list[SlotResult]:
        """
        ตรวจทุกช่องและส่งคืนผลรวม

        Args:
            aligned_image : ภาพที่ผ่าน TrayAligner.align() แล้ว
            slots         : รายการช่องจาก JSON

        Returns:
            list[SlotResult] เรียงตาม slot_number
        """
        h, w = aligned_image.shape[:2]
        gray = cv2.cvtColor(aligned_image, cv2.COLOR_BGR2GRAY) if len(aligned_image.shape) == 3 else aligned_image.copy()
        scene_work = self._prep_work(gray) if self._golden_work is not None else None

        results: list[SlotResult] = []

        for slot in slots:
            result = self._check_single_slot(gray, aligned_image, slot, w, h, scene_work)
            results.append(result)

        return results

    def check_single_slot(
        self,
        aligned_image: np.ndarray,
        slot: dict,
    ) -> SlotResult:
        """ตรวจช่องเดียว (สำหรับทดสอบ)"""
        h, w = aligned_image.shape[:2]
        gray = cv2.cvtColor(aligned_image, cv2.COLOR_BGR2GRAY) if len(aligned_image.shape) == 3 else aligned_image.copy()
        scene_work = self._prep_work(gray) if self._golden_work is not None else None
        return self._check_single_slot(gray, aligned_image, slot, w, h, scene_work)

    # ──────────────────────────────────────────────────────────────────────────
    # Private: slot-level logic
    # ──────────────────────────────────────────────────────────────────────────

    def _check_single_slot(
        self,
        gray_full: np.ndarray,
        color_full: np.ndarray,
        slot: dict,
        img_w: int,
        img_h: int,
        scene_work: Optional[np.ndarray] = None,
    ) -> SlotResult:
        sn = slot.get("slot_number", 0)
        bbox_norm = slot.get("bbox_norm", [])
        polygon = slot.get("polygon", [])
        tolerance = {**DEFAULT_TOLERANCE, **slot.get("tolerance", {})}
        orientation_vec = slot.get("orientation_vec", [0, 1])  # ทิศทาง Y เป็น default

        result = SlotResult(sn)

        # ── Step 2: ตัด slot crop ────────────────────────────────────────────
        if not bbox_norm or len(bbox_norm) < 4:
            result.status = "recheck"
            result.reason = "ไม่มีข้อมูล bbox_norm ในเทมเพลต"
            return result

        x1 = max(0, int(bbox_norm[0] * img_w))
        y1 = max(0, int(bbox_norm[1] * img_h))
        x2 = min(img_w, int(bbox_norm[2] * img_w))
        y2 = min(img_h, int(bbox_norm[3] * img_h))

        result.slot_bbox_px = [x1, y1, x2, y2]

        slot_gray = gray_full[y1:y2, x1:x2]
        slot_color = color_full[y1:y2, x1:x2]

        if slot_gray.size == 0:
            result.status = "recheck"
            result.reason = "พื้นที่ช่องว่างอยู่นอกภาพ"
            return result

        result.crop = slot_color

        # คำนวณ template center ใน slot-local coordinates
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        template_cx = bw // 2
        template_cy = bh // 2
        result.template_center = (template_cx, template_cy)

        # ── Step 3+4 (แบบใหม่): เทียบเฉพาะพื้นที่ polygon กับภาพต้นแบบและภาพถาดว่าง ──
        if scene_work is not None:
            scores = self._reference_scores(scene_work, sn)
            if scores is not None:
                self._decide_from_scores(result, scores, img_w)
                return result

        # ── Step 3: ตรวจว่ามีวัตถุ (แบบเดิม: ใช้เมื่อไม่มีภาพต้นแบบ) ─────────
        ref_crop = self._refs.get(sn)
        is_occupied, presence_conf, presence_reason = self._check_presence(
            slot_gray, ref_crop
        )

        if not is_occupied:
            if presence_conf >= RECHECK_CONFIDENCE_THRESHOLD:
                result.status = "missing"
                result.confidence = presence_conf
                result.reason = f"ช่องว่าง — {presence_reason}"
            else:
                result.status = "recheck"
                result.confidence = presence_conf
                result.reason = f"ไม่แน่ใจ (อาจว่าง) — {presence_reason}"
            return result

        # ── Step 4: ตรวจรูปทรงและตำแหน่ง ────────────────────────────────────
        shape_status, shape_conf, shape_detail = self._check_shape_and_placement(
            slot_gray, polygon, tolerance, orientation_vec,
            offset=(x1, y1), img_size=(img_w, img_h), ref_crop=ref_crop
        )

        result.center_offset_px = shape_detail.get("center_offset", 0.0)
        result.angle_deg = shape_detail.get("angle_deg", 0.0)
        result.iou_score = shape_detail.get("iou", 0.0)

        if result.center_offset_px > 0:
            result.contour_center = shape_detail.get("contour_center")

        # ── ตัดสินสถานะสุดท้าย ──────────────────────────────────────────────
        combined_conf = (presence_conf * 0.4 + shape_conf * 0.6)

        if combined_conf < RECHECK_CONFIDENCE_THRESHOLD:
            result.status = "recheck"
            result.confidence = combined_conf
            result.reason = f"confidence ต่ำ ({combined_conf:.0%}) — {shape_detail.get('reason', '')}"
        elif shape_status == "ok":
            result.status = "correct"
            result.confidence = combined_conf
            result.reason = "มีวัตถุ + รูปทรงและตำแหน่งตรงต้นแบบ"
        else:
            result.status = "misplaced"
            result.confidence = combined_conf
            result.reason = shape_detail.get("reason", "รูปทรงหรือตำแหน่งไม่ตรง")

        return result

    def _decide_from_scores(self, result: SlotResult, scores: dict, img_w: int) -> None:
        """ตัดสินสถานะจากความคล้ายกับภาพต้นแบบ (g) และภาพถาดว่าง (e) ในพื้นที่ polygon"""
        g, e = scores["golden"], scores["empty"]
        result.golden_score, result.empty_score = g, e
        dx, dy = scores["shift"]
        k = img_w / float(self._work_size[0])
        result.center_offset_px = float(np.hypot(dx, dy)) * k
        if result.template_center:
            cx, cy = result.template_center
            result.contour_center = (int(cx + dx * k), int(cy + dy * k))
        txt = f"ต้นแบบ {g:.0%}" + (f", ถาดว่าง {e:.0%}" if e is not None else "")

        if e is not None:
            d = g - e
            if d <= -EMPTY_MARGIN:
                result.status = "missing"
                result.confidence = min(0.98, 0.60 + 0.40 * min(1.0, -d / 0.5))
                result.reason = f"ช่องว่าง — คล้ายถาดว่างมากกว่าต้นแบบ ({txt})"
            elif d >= EMPTY_MARGIN and g >= GOLDEN_MATCH_OK:
                result.status = "correct"
                result.confidence = min(0.98, 0.60 + 0.40 * min(1.0, d / 0.5) * min(1.0, g))
                result.reason = f"มีเครื่องมือตรงตำแหน่งต้นแบบ ({txt})"
            elif d >= EMPTY_MARGIN:
                result.status = "misplaced"
                result.confidence = min(0.90, 0.55 + 0.35 * min(1.0, d / 0.5))
                result.reason = f"มีวัตถุแต่ไม่ตรงต้นแบบ — อาจวางผิดช่อง/กลับด้าน ({txt})"
            else:
                result.status = "recheck"
                result.confidence = 0.50
                result.reason = f"แยกไม่ออกว่ามีของหรือว่าง ({txt})"
            return

        # ไม่มีภาพถาดว่าง: ใช้ความคล้ายต้นแบบอย่างเดียว
        if g >= GOLDEN_ONLY_OK:
            result.status = "correct"
            result.confidence = min(0.95, 0.55 + 0.40 * g)
            result.reason = f"มีเครื่องมือตรงตำแหน่งต้นแบบ ({txt})"
        elif g < GOLDEN_ONLY_MISSING:
            result.status = "missing"
            result.confidence = min(0.90, 0.60 + 0.60 * (GOLDEN_ONLY_MISSING - g))
            result.reason = f"ไม่พบเครื่องมือตามต้นแบบ ({txt})"
        else:
            result.status = "recheck"
            result.confidence = 0.50
            result.reason = f"คล้ายต้นแบบปานกลาง ตัดสินไม่ได้ ({txt})"

    # ──────────────────────────────────────────────────────────────────────────
    # Private: presence detection
    # ──────────────────────────────────────────────────────────────────────────

    def _check_presence(
        self,
        slot_gray: np.ndarray,
        ref_crop: Optional[np.ndarray],
    ) -> tuple[bool, float, str]:
        """
        ตรวจว่าช่องมีวัตถุอยู่หรือไม่ (รองรับทั้ง golden sample และ empty ref)

        Returns:
            (is_occupied, confidence, reason)
        """
        # ปรับ contrast ด้วย CLAHE เพื่อดึงขอบโลหะและลดผลกระทบจากแสงสะท้อนจ้า (specular glare)
        slot_enhanced = self._clahe.apply(slot_gray)
        std_val = float(np.std(slot_gray))
        mean_val = float(np.mean(slot_gray))
        edges = cv2.Canny(slot_enhanced, 40, 120)
        edge_density = float(np.count_nonzero(edges)) / float(max(1, slot_gray.size))

        # ── คำนวณความคล้ายกับ ref_crop (ถ้ามี) ──
        sim_score = 0.0
        if ref_crop is not None and ref_crop.size > 0:
            try:
                ref_resized = cv2.resize(ref_crop, (slot_gray.shape[1], slot_gray.shape[0]))
                res = cv2.matchTemplate(slot_gray, ref_resized, cv2.TM_CCOEFF_NORMED)
                sim_score = float(res.max())
            except cv2.error:
                sim_score = 0.0

        if self.ref_mode == "golden":
            # Golden Reference mode: ref_crop คือเครื่องมือต้นแบบที่ถูกต้อง
            # ช่องว่าง: ผิวโฟมเรียบ ไม่มีขอบ std ต่ำ
            is_empty = (std_val < 15.0 and edge_density < 0.035) or (mean_val < 55.0 and std_val < 13.0)
            if is_empty:
                conf = min(0.95, 0.70 + (15.0 - min(15.0, std_val)) / 20.0)
                return False, conf, f"ช่องว่าง (std={std_val:.1f}, edge={edge_density:.3f})"

            texture_score = min(1.0, std_val / 35.0) * 0.5 + min(1.0, edge_density / 0.06) * 0.5
            conf = min(0.98, max(0.60, 0.45 + texture_score * 0.35 + max(0.0, sim_score) * 0.20))
            return True, conf, f"มีวัตถุ (std={std_val:.1f}, edge={edge_density:.3f})"

        else:
            # Empty Ref mode: ref_crop คือโฟมเปล่า
            if sim_score >= PRESENCE_SSIM_THRESHOLD:
                conf = min(0.95, sim_score)
                return False, conf, f"คล้าย empty_ref ({sim_score:.0%})"

            texture_score = min(1.0, std_val / 40.0) * 0.6 + min(1.0, edge_density / 0.08) * 0.4
            is_occupied = (std_val > PRESENCE_STD_THRESHOLD) or (edge_density > PRESENCE_EDGE_THRESHOLD)
            if is_occupied:
                conf = min(0.95, 0.5 + texture_score * 0.45)
                return True, conf, f"std={std_val:.1f}, edge={edge_density:.3f}"
            else:
                conf = min(0.90, 0.5 + (1.0 - texture_score) * 0.40)
                return False, conf, f"std={std_val:.1f} ต่ำ, edge={edge_density:.3f} ต่ำ"

    # ──────────────────────────────────────────────────────────────────────────
    # Private: shape & placement
    # ──────────────────────────────────────────────────────────────────────────

    def _check_shape_and_placement(
        self,
        slot_gray: np.ndarray,
        polygon: list,
        tolerance: dict,
        orientation_vec: list,
        offset: tuple[int, int],
        img_size: tuple[int, int],
        ref_crop: Optional[np.ndarray] = None,
    ) -> tuple[str, float, dict]:
        """
        ตรวจรูปทรง ตำแหน่ง และทิศทางของวัตถุในช่อง

        Returns:
            (sub_status, confidence, detail_dict)
            sub_status: "ok" | "shifted" | "rotated" | "wrong_shape" | "uncertain"
        """
        sh, sw = slot_gray.shape[:2]
        ox, oy = offset
        img_w, img_h = img_size
        detail: dict[str, Any] = {}

        if sh < 5 or sw < 5 or slot_gray.size == 0:
            detail["reason"] = "ขนาดช่องเล็กเกินไปสำหรับตรวจรูปทรง"
            detail["iou"] = 0.0
            return "uncertain", 0.50, detail

        # ตรวจความคล้ายกับ reference tool
        sim_score = 0.0
        if ref_crop is not None and ref_crop.size > 0:
            try:
                ref_resized = cv2.resize(ref_crop, (sw, sh))
                res = cv2.matchTemplate(slot_gray, ref_resized, cv2.TM_CCOEFF_NORMED)
                sim_score = float(res.max())
            except cv2.error:
                sim_score = 0.0
        detail["sim_score"] = sim_score

        # ── หา contour หลักของวัตถุ ──────────────────────────────────────────
        # ใช้ CLAHE ช่วยปรับ localized contrast บนผิวโลหะก่อน Gaussian Blur และ Adaptive Threshold
        enhanced_slot = self._clahe.apply(slot_gray)
        blur = cv2.GaussianBlur(enhanced_slot, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(
            blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=21, C=4
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            if sim_score >= 0.50:
                detail["reason"] = f"ตรงต้นแบบ (sim={sim_score:.0%})"
                return "ok", 0.85, detail
            detail["reason"] = "ไม่พบ contour วัตถุในช่อง"
            detail["iou"] = 0.0
            return "uncertain", 0.45, detail

        # เลือก contour ใหญ่สุด
        main_cnt = max(contours, key=cv2.contourArea)
        cnt_area = cv2.contourArea(main_cnt)
        slot_area = max(1, sw * sh)

        # ── จุดกึ่งกลาง ─────────────────────────────────────────────────────
        M = cv2.moments(main_cnt)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
        else:
            bx, by, bw, bh = cv2.boundingRect(main_cnt)
            cx, cy = bx + bw // 2, by + bh // 2

        detail["contour_center"] = (cx, cy)
        center_offset = float(np.hypot(cx - sw // 2, cy - sh // 2))
        detail["center_offset"] = center_offset

        # ── ทิศทาง (PCA บน contour points) ─────────────────────────────────
        angle_deg = 0.0
        if len(main_cnt) >= 5:
            try:
                pts = main_cnt.reshape(-1, 2).astype(np.float32)
                _, eigenvectors = cv2.PCACompute(pts, mean=None)
                principal_vec = eigenvectors[0]
                ref_vec = np.array(orientation_vec, dtype=np.float32)
                ref_vec = ref_vec / (np.linalg.norm(ref_vec) + 1e-8)
                cos_angle = float(np.clip(np.dot(principal_vec, ref_vec), -1.0, 1.0))
                angle_deg = float(np.degrees(np.arccos(cos_angle)))
                if angle_deg > 90:
                    angle_deg = 180 - angle_deg
            except Exception:
                angle_deg = 0.0
        detail["angle_deg"] = angle_deg

        # ── Scale polygon จากขนาดภาพของเทมเพลต (image_width x image_height) สู่ current resolution ──
        # (เดิมสมมติว่าเทมเพลตกว้าง 3840 เสมอ ทำให้ถาด 70 ช่องที่ใช้ภาพ 1448 px ได้ polygon ผิดขนาด)
        poly_px = self._polygon_px(polygon, img_w, img_h)
        scaled_polygon = poly_px.tolist() if poly_px is not None else []

        iou_score = 0.0
        if scaled_polygon:
            iou_score = self._compute_polygon_iou(
                main_cnt, scaled_polygon, offset=(ox, oy), img_size=img_size,
                slot_local=True, slot_offset=(ox, oy)
            )
        detail["iou"] = iou_score

        # ── ปรับ tolerance ตาม scale ของภาพ ────────────────────────────────
        res_scale = img_w / 3840.0
        tol_center = max(8.0, float(tolerance.get("center_px", DEFAULT_TOLERANCE["center_px"])) * res_scale * 3.0)
        tol_angle = float(tolerance.get("angle_deg", DEFAULT_TOLERANCE["angle_deg"]))
        tol_iou = float(tolerance.get("iou_min", DEFAULT_TOLERANCE["iou_min"]))

        violations = []
        # ถ้า sim_score สูงมาก (ตรงกับ golden template) ให้ผ่อนปรน violations
        if sim_score >= 0.65:
            confidence = min(0.98, 0.70 + sim_score * 0.28)
            detail["reason"] = f"รูปทรงตรงต้นแบบ (sim={sim_score:.0%})"
            return "ok", confidence, detail

        if center_offset > tol_center:
            violations.append(f"เยื้องออก {center_offset:.0f}px (เกิน {tol_center:.0f}px)")
        if angle_deg > tol_angle:
            violations.append(f"หมุน {angle_deg:.0f}° (เกิน {tol_angle:.0f}°)")
        if iou_score < tol_iou and iou_score > 0 and sim_score < 0.45:
            violations.append(f"รูปทรงไม่ตรง (IoU {iou_score:.0%} < {tol_iou:.0%})")

        if not violations:
            confidence = min(0.95, 0.65 + max(iou_score, sim_score) * 0.30)
            detail["reason"] = "รูปทรงและตำแหน่งตรงต้นแบบ"
            return "ok", confidence, detail
        else:
            confidence = max(0.40, 0.65 - len(violations) * 0.12)
            detail["reason"] = "วางผิด: " + "; ".join(violations)

            if center_offset > tol_center and angle_deg <= tol_angle:
                return "shifted", confidence, detail
            elif angle_deg > tol_angle and center_offset <= tol_center:
                return "rotated", confidence, detail
            else:
                return "wrong_shape", confidence, detail

    def _compute_polygon_iou(
        self,
        contour: np.ndarray,
        polygon_abs: list,
        offset: tuple[int, int],
        img_size: tuple[int, int],
        slot_local: bool = True,
        slot_offset: tuple[int, int] = (0, 0),
    ) -> float:
        """
        คำนวณ IoU ระหว่าง contour วัตถุ กับ polygon ต้นแบบ (absolute pixel)

        polygon_abs: list of [x, y] ใน coordinate ของ reference image เต็ม
        contour: contour ใน slot-local coordinates
        slot_local: ถ้า True ให้แปลง polygon ให้เป็น slot-local ก่อนเทียบ
        """
        try:
            img_w, img_h = img_size
            ox, oy = slot_offset

            # แปลง polygon เป็น numpy
            poly_pts = np.array(polygon_abs, dtype=np.int32)
            if poly_pts.ndim == 3:
                poly_pts = poly_pts.reshape(-1, 2)

            if slot_local:
                # แปลงจาก absolute → slot-local
                poly_pts = poly_pts - np.array([ox, oy], dtype=np.int32)

            # ขนาด mask
            bx, by, bw, bh = cv2.boundingRect(contour)
            mask_h = max(bh + abs(by) + 10, poly_pts[:, 1].max() + 10, 50)
            mask_w = max(bw + abs(bx) + 10, poly_pts[:, 0].max() + 10, 50)
            mask_h = min(mask_h, img_h)
            mask_w = min(mask_w, img_w)

            mask_cnt = np.zeros((mask_h, mask_w), dtype=np.uint8)
            mask_poly = np.zeros((mask_h, mask_w), dtype=np.uint8)

            cv2.drawContours(mask_cnt, [contour], -1, 255, -1)
            cv2.fillPoly(mask_poly, [poly_pts.reshape(-1, 1, 2)], 255)

            # Clip ให้ขนาดเท่ากัน
            h_min = min(mask_cnt.shape[0], mask_poly.shape[0])
            w_min = min(mask_cnt.shape[1], mask_poly.shape[1])
            intersection = np.logical_and(
                mask_cnt[:h_min, :w_min], mask_poly[:h_min, :w_min]
            ).sum()
            union = np.logical_or(
                mask_cnt[:h_min, :w_min], mask_poly[:h_min, :w_min]
            ).sum()

            if union == 0:
                return 0.0
            return float(intersection) / float(union)

        except Exception as e:
            logger.debug(f"IoU compute error: {e}")
            return 0.0
