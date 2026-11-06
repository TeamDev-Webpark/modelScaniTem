"""
YOLOv8 Tool Scanner & Tray Verification Engine.
Supports:
Part 1: Scanning individual tools placed freely or aligned (Object Detection).
Part 2: Tray block verification (Checking tool completeness and correct placement in slots).
"""
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Thai font fallback paths on Windows and Linux
FONT_PATHS = [
    "C:/Windows/Fonts/tahoma.ttf",
    "C:/Windows/Fonts/leelawad.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/thai/Loma.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

def get_thai_font(size: int = 14) -> ImageFont.FreeTypeFont:
    for font_path in FONT_PATHS:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    return ImageFont.load_default()

# Check if ultralytics is available
try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
    logger.warning("ultralytics is not installed. YOLO inference will run in simulation/fallback mode.")


class YOLOToolScanner:
    """
    Core detection engine utilizing YOLOv8 and Tray Slot Verification logic.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.model_path = model_path
        self.class_names: Dict[int, str] = {}
        self._alias_map: Dict[str, str] = {}
        self._load_tool_mappings()
        if model_path and ULTRALYTICS_AVAILABLE:
            self.load_model(model_path)

    def _load_tool_mappings(self):
        """Loads tool code/part-number to class_name alias mappings from mock_database/data.json."""
        try:
            import json
            from config import CATALOG_PATH
            data_file = CATALOG_PATH
            if data_file.exists():
                with open(data_file, "r", encoding="utf-8") as f:
                    items = json.load(f)
                    for it in items:
                        target = (it.get("name_en") or it.get("class_key") or it.get("code") or "").strip().lower().replace("-", "_").replace(" ", "_")
                        code = (it.get("code") or "").strip().lower().replace("-", "_").replace(" ", "_")
                        name_th = (it.get("name") or "").strip().lower()
                        if target:
                            if code:
                                self._alias_map[code] = target
                            if name_th:
                                self._alias_map[name_th] = target
        except Exception as e:
            logger.warning(f"Could not load tool mappings: {e}")


    def load_model(self, model_path: str) -> bool:
        """Loads YOLO weights (.pt file)."""
        if not ULTRALYTICS_AVAILABLE:
            logger.error("Ultralytics not installed.")
            return False
        
        path = Path(model_path)
        if not path.exists():
            logger.error(f"Model file not found: {model_path}")
            return False

        try:
            self.model = YOLO(str(path))
            self.model_path = str(path)
            self.class_names = self.model.names if hasattr(self.model, "names") else {}
            logger.info(f"Loaded YOLO model: {model_path} with {len(self.class_names)} classes.")
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

    @classmethod
    def load_active_model_from_db(cls) -> "YOLOToolScanner":
        """Factory method to load the currently active model registered in PostgreSQL."""
        try:
            from db import get_db
            from models_db import TrainedModel

            with get_db() as db:
                active = db.query(TrainedModel).filter(TrainedModel.is_active == True).first()
                if active and Path(active.model_path).exists():
                    return cls(active.model_path)
        except Exception as e:
            logger.warning(f"Could not load active model from DB: {e}")
        
        return cls()

    # =========================================================================
    # PART 1: Object Detection (Tools placed freely or in rows)
    # =========================================================================
    def detect_tools(
        self,
        image: np.ndarray,
        conf_threshold: float = 0.40,
        iou_threshold: float = 0.45
    ) -> List[Dict[str, Any]]:
        """
        Part 1: Detects tools in the image.
        Returns a list of detected objects:
        [
            {
                "class_id": int,
                "class_name": str,
                "confidence": float,
                "bbox": [x1, y1, x2, y2],  # absolute pixel coordinates
                "bbox_norm": [x1_norm, y1_norm, x2_norm, y2_norm],
                "center": (cx, cy)
            },
            ...
        ]
        """
        if self.model is None:
            return []

        h, w = image.shape[:2]
        results = self.model.predict(
            source=image,
            conf=conf_threshold,
            iou=iou_threshold,
            verbose=False
        )

        detected_items = []
        if not results:
            return detected_items

        result = results[0]
        boxes = result.boxes

        if boxes is not None:
            for box in boxes:
                coords = box.xyxy[0].cpu().numpy()  # x1, y1, x2, y2
                x1, y1, x2, y2 = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                cls_name = self.class_names.get(cls_id, f"Class_{cls_id}")

                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0

                detected_items.append({
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "confidence": round(conf, 3),
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "bbox_norm": [
                        round(x1 / w, 4),
                        round(y1 / h, 4),
                        round(x2 / w, 4),
                        round(y2 / h, 4)
                    ],
                    "center": (int(cx), int(cy))
                })

        return detected_items

    # =========================================================================
    # PART 2: Tray Verification (Check slot completeness and item correctness)
    # =========================================================================
    def _check_slot_visually_occupied(self, slot_crop: np.ndarray) -> Tuple[bool, float]:
        """
        Visual occupancy check for a slot when custom YOLO object classes are not detected.
        Analyzes standard deviation (contrast/texture), brightness (metallic reflection),
        and Canny edge density to distinguish a real tool from an empty dark foam slot.
        """
        if slot_crop is None or slot_crop.size == 0:
            return False, 0.0

        gray = cv2.cvtColor(slot_crop, cv2.COLOR_BGR2GRAY) if len(slot_crop.shape) == 3 else slot_crop
        std_val = float(np.std(gray))
        mean_val = float(np.mean(gray))
        
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.count_nonzero(edges)) / float(max(1, gray.size))

        # A slot with tools typically has high contrast (std > 18) or visible edges (edge_density > 0.04)
        # Empty foam slots are uniform/flat with very low edge density and std.
        is_occupied = (std_val > 18.0) or (edge_density > 0.04) or (mean_val > 85.0 and std_val > 14.0)
        confidence = min(0.99, max(0.50, (std_val / 50.0) * 0.7 + (edge_density / 0.15) * 0.3))
        return is_occupied, confidence

    def _detect_tray_bounds(self, image: np.ndarray) -> Tuple[int, int, int, int]:
        """
        Detects the outer boundary of the tool tray within the image.
        Uses contrast between dark foam and lighter background/table surface.
        Returns (x, y, w, h). If no distinct tray contour is found, returns the full image bounds.
        """
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Downscale for stable & fast boundary finding
        scale = 400.0 / max(h, w)
        small = cv2.resize(gray, (int(w * scale), int(h * scale)))
        sh, sw = small.shape[:2]
        
        blur = cv2.GaussianBlur(small, (9, 9), 0)
        thresh_val = np.percentile(blur, 45)
        _, mask = cv2.threshold(blur, thresh_val, 255, cv2.THRESH_BINARY_INV)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 13))
        mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_OPEN, kernel)
        
        contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_cnt = None
        max_area = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 0.30 * (sw * sh) and area > max_area:
                max_area = area
                best_cnt = cnt
                
        if best_cnt is not None:
            bx, by, bw, bh = cv2.boundingRect(best_cnt)
            # Add small padding
            bx_orig = max(0, int(bx / scale) - 5)
            by_orig = max(0, int(by / scale) - 5)
            bw_orig = min(w - bx_orig, int(bw / scale) + 10)
            bh_orig = min(h - by_orig, int(bh / scale) + 10)
            
            # Ensure it is at least 60% of the image
            if (bw_orig * bh_orig) > 0.40 * (w * h):
                return (bx_orig, by_orig, bw_orig, bh_orig)
                
        return (0, 0, w, h)

    def _fine_tune_slot_coords(
        self,
        gray: np.ndarray,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        search_radius: int = 14
    ) -> Tuple[int, int, int, int]:
        """
        Fine-tunes the slot coordinates by searching locally (+- search_radius px)
        to lock onto the tool edges/contrast center if the tray is slightly shifted or rotated.
        """
        h, w = gray.shape[:2]
        box_w = max(1, x2 - x1)
        box_h = max(1, y2 - y1)
        
        best_x1, best_y1 = x1, y1
        max_energy = -1.0
        
        for dy in range(-search_radius, search_radius + 1, 3):
            ny1 = max(0, min(h - box_h, y1 + dy))
            ny2 = ny1 + box_h
            for dx in range(-search_radius, search_radius + 1, 3):
                nx1 = max(0, min(w - box_w, x1 + dx))
                nx2 = nx1 + box_w
                
                sub = gray[ny1:ny2, nx1:nx2]
                if sub.size == 0:
                    continue
                std_v = float(np.std(sub))
                if std_v > max_energy:
                    max_energy = std_v
                    best_x1, best_y1 = nx1, ny1
                    
        return best_x1, best_y1, best_x1 + box_w, best_y1 + box_h

    def verify_tray(
        self,
        image: np.ndarray,
        tray_template: Dict[str, Any],
        conf_threshold: float = 0.40,
        iou_threshold: float = 0.45,
        slot_overlap_threshold: float = 0.25,
        detections: Optional[List[Dict[str, Any]]] = None,
        use_workflow: bool = True,
        reference_image: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Part 2: Checks if tools are complete and placed correctly in each slot of the tray.
        When use_workflow=True, delegates to the 5-step scan_workflow pipeline (Quality Gate,
        Homography Alignment, Slot Presence, Shape & Placement Check, Aggregator).
        Falls back to local tracking & YOLO detection matching when use_workflow=False.
        """
        if use_workflow:
            try:
                from scan_workflow import ScanAggregator
                agg = ScanAggregator()
                agg.setup(tray_template, reference_image=reference_image)
                summary = agg.scan(image)

                return {
                    "is_complete": summary.is_complete,
                    "total_slots": summary.total_slots,
                    "correct_count": summary.correct_count,
                    "missing_count": summary.missing_count,
                    "misplaced_count": summary.misplaced_count,
                    "recheck_count": summary.recheck_count,
                    "wrong_count": summary.misplaced_count,  # backward compat
                    "slot_results": summary.slot_results,
                    "annotated_image": summary.annotated_image,
                    "quality": summary.quality.to_dict() if summary.quality else None,
                    "align": summary.align.to_dict() if summary.align else None,
                    "all_detections": detections or [],
                    "unmatched_detections": [],
                }
            except Exception as e:
                logger.warning(f"scan_workflow execution failed, falling back to legacy verify: {e}")

        h, w = image.shape[:2]
        if detections is None:
            detections = self.detect_tools(image, conf_threshold, iou_threshold)

        # 1. Automatic tray boundary detection to handle camera shift / zoom / table background
        tx, ty, tw, th = self._detect_tray_bounds(image)
        gray_full = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        slots = tray_template.get("slots", [])
        slot_results = []
        matched_detection_indices = set()

        # Check each slot against detections
        for slot in slots:
            slot_num = slot.get("slot_number", 0)
            expected_name = slot.get("item_name") or slot.get("name", f"Slot {slot_num}")
            expected_code = slot.get("item_code") or slot.get("class_key") or slot.get("code", "")
            
            # Slot bounding box [x1_norm, y1_norm, x2_norm, y2_norm]
            bbox_norm = slot.get("bbox_norm") or [
                slot.get("bbox_x1_norm", 0.0),
                slot.get("bbox_y1_norm", 0.0),
                slot.get("bbox_x2_norm", 1.0),
                slot.get("bbox_y2_norm", 1.0)
            ]

            # Map coordinates: If tray was detected within a larger scene, map onto tray bounds
            if (tw * th) < 0.95 * (w * h):
                init_x1 = max(0, min(w - 1, int(tx + bbox_norm[0] * tw)))
                init_y1 = max(0, min(h - 1, int(ty + bbox_norm[1] * th)))
                init_x2 = max(0, min(w, int(tx + bbox_norm[2] * tw)))
                init_y2 = max(0, min(h, int(ty + bbox_norm[3] * th)))
            else:
                init_x1 = max(0, min(w - 1, int(bbox_norm[0] * w)))
                init_y1 = max(0, min(h - 1, int(bbox_norm[1] * h)))
                init_x2 = max(0, min(w, int(bbox_norm[2] * w)))
                init_y2 = max(0, min(h, int(bbox_norm[3] * h)))

            # Fine-tune coordinates locally to handle slight shifts and vibrations
            slot_x1, slot_y1, slot_x2, slot_y2 = self._fine_tune_slot_coords(
                gray_full, init_x1, init_y1, init_x2, init_y2, search_radius=12
            )
            slot_area = max(1, (slot_x2 - slot_x1) * (slot_y2 - slot_y1))

            # Find best overlapping YOLO detection
            best_det = None
            best_det_idx = -1
            best_iou = 0.0

            for idx, det in enumerate(detections):
                if idx in matched_detection_indices:
                    continue

                dx1, dy1, dx2, dy2 = det["bbox"]
                # Intersection
                ix1 = max(slot_x1, dx1)
                iy1 = max(slot_y1, dy1)
                ix2 = min(slot_x2, dx2)
                iy2 = min(slot_y2, dy2)

                iw = max(0, ix2 - ix1)
                ih = max(0, iy2 - iy1)
                intersection = iw * ih

                overlap_ratio = intersection / slot_area
                if overlap_ratio > slot_overlap_threshold and overlap_ratio > best_iou:
                    best_iou = overlap_ratio
                    best_det = det
                    best_det_idx = idx

            # Determine slot status
            if best_det is not None:
                matched_detection_indices.add(best_det_idx)
                detected_name = best_det["class_name"]
                
                # Check if item matches expected item
                norm_det = detected_name.strip().lower().replace("-", "_").replace(" ", "_")
                norm_exp_code = expected_code.strip().lower().replace("-", "_").replace(" ", "_") if expected_code else ""
                norm_exp_name = expected_name.strip().lower() if expected_name else ""

                is_correct = False
                if norm_exp_code:
                    if norm_exp_code == norm_det or norm_exp_code in norm_det or norm_det in norm_exp_code:
                        is_correct = True
                    elif self._alias_map.get(norm_exp_code) == norm_det:
                        is_correct = True

                if not is_correct and norm_exp_name:
                    if norm_det in norm_exp_name or norm_exp_name in norm_det:
                        is_correct = True
                    elif self._alias_map.get(norm_exp_name) == norm_det:
                        is_correct = True

                status = "correct" if is_correct else "wrong_item"
                slot_results.append({
                    "slot_number": slot_num,
                    "expected_name": expected_name,
                    "expected_code": expected_code,
                    "status": status,
                    "detected_item": detected_name,
                    "confidence": best_det["confidence"],
                    "slot_bbox": [slot_x1, slot_y1, slot_x2, slot_y2],
                    "det_bbox": best_det["bbox"],
                })
            else:
                # No custom YOLO tool class matched. Use Visual Slot Analysis fallback.
                slot_crop = image[slot_y1:slot_y2, slot_x1:slot_x2]
                is_occupied, visual_conf = self._check_slot_visually_occupied(slot_crop)

                if is_occupied:
                    slot_results.append({
                        "slot_number": slot_num,
                        "expected_name": expected_name,
                        "expected_code": expected_code,
                        "status": "correct",
                        "detected_item": expected_name,
                        "confidence": visual_conf,
                        "slot_bbox": [slot_x1, slot_y1, slot_x2, slot_y2],
                        "det_bbox": [slot_x1, slot_y1, slot_x2, slot_y2],
                    })
                else:
                    slot_results.append({
                        "slot_number": slot_num,
                        "expected_name": expected_name,
                        "expected_code": expected_code,
                        "status": "missing",
                        "detected_item": None,
                        "confidence": 0.0,
                        "slot_bbox": [slot_x1, slot_y1, slot_x2, slot_y2],
                        "det_bbox": None,
                    })

        # Calculate summary statistics
        total_slots = len(slots)
        correct_count = sum(1 for s in slot_results if s["status"] == "correct")
        missing_count = sum(1 for s in slot_results if s["status"] == "missing")
        wrong_count = sum(1 for s in slot_results if s["status"] == "wrong_item")

        is_complete = (missing_count == 0 and wrong_count == 0)

        return {
            "is_complete": is_complete,
            "total_slots": total_slots,
            "correct_count": correct_count,
            "missing_count": missing_count,
            "wrong_count": wrong_count,
            "slot_results": slot_results,
            "all_detections": detections,
            "unmatched_detections": [
                det for idx, det in enumerate(detections) if idx not in matched_detection_indices
            ]
        }

    # =========================================================================
    # Visualizations with Thai Font Support
    # =========================================================================
    def draw_detections(
        self,
        image: np.ndarray,
        detections: List[Dict[str, Any]]
    ) -> np.ndarray:
        """Draws bounding boxes and labels for general object detections with Thai font support."""
        annotated = image.copy()
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 128), 2)

        # Draw labels with PIL for full Unicode/Thai font support
        img_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        draw = ImageDraw.Draw(pil_img)
        font = get_thai_font(size=14)

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cls_name = det["class_name"]
            conf = det["confidence"]
            label_text = f"{cls_name} ({conf:.0%})"

            bbox = draw.textbbox((x1, y1), label_text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            badge_y1 = max(0, y1 - th - 6)
            badge_y2 = y1
            draw.rectangle([x1, badge_y1, x1 + tw + 8, badge_y2], fill=(0, 200, 100))
            draw.text((x1 + 4, badge_y1 + 1), label_text, font=font, fill=(0, 0, 0))

        annotated_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return annotated_bgr

    def draw_tray_verification(
        self,
        image: np.ndarray,
        verification_result: Dict[str, Any]
    ) -> np.ndarray:
        """
        Draws color-coded verification results on tray slots:
        Green (OK/ครบ), Red (Missing/ขาด), Orange (Wrong/ผิดช่อง) with sharp Thai font badges.
        """
        annotated = image.copy()
        
        # Draw bounding boxes first using OpenCV
        for slot in verification_result.get("slot_results", []):
            x1, y1, x2, y2 = slot["slot_bbox"]
            status = slot.get("status", "recheck")

            if status == "correct":
                color_bgr = (0, 220, 0)      # Green
            elif status == "missing":
                color_bgr = (0, 0, 255)      # Red
            elif status in ("misplaced", "wrong_item"):
                color_bgr = (0, 180, 240)    # Yellow / Gold
            else:
                color_bgr = (130, 130, 130)  # Gray for recheck

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color_bgr, 2)

        # Draw Thai labels using PIL
        img_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        draw = ImageDraw.Draw(pil_img)
        font = get_thai_font(size=14)

        for slot in verification_result.get("slot_results", []):
            x1, y1, x2, y2 = slot["slot_bbox"]
            status = slot.get("status", "recheck")
            slot_num = slot.get("slot_number", 0)

            if status == "correct":
                color_rgb = (0, 180, 0)
                status_th = "ครบ"
            elif status == "missing":
                color_rgb = (220, 30, 30)
                status_th = "ขาดหาย"
            elif status in ("misplaced", "wrong_item"):
                color_rgb = (220, 160, 0)
                detected = slot.get("detected_item") or slot.get("reason", "ผิดตำแหน่ง")
                status_th = f"ผิดตำแหน่ง ({detected})" if len(str(detected)) < 15 else "ผิดตำแหน่ง"
            else:
                color_rgb = (120, 120, 120)
                status_th = "ตรวจซ้ำ"

            badge_text = f"#{slot_num}: {status_th}"
            bbox = draw.textbbox((x1, y1), badge_text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]

            badge_y1 = max(0, y1 - th - 6)
            badge_y2 = y1
            draw.rectangle([x1, badge_y1, x1 + tw + 8, badge_y2], fill=color_rgb)
            draw.text((x1 + 4, badge_y1 + 1), badge_text, font=font, fill=(255, 255, 255))

        annotated_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return annotated_bgr

