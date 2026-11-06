import cv2
import os
import sys
import numpy as np
import time
import json
import datetime

# แก้ปัญหา Windows console encoding (cp1252 ไม่รองรับภาษาไทย)
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

class ShapeScanner:
    """
    ระบบสแกนรูปแบบเครื่องมือโดยใช้ SIFT Feature Matching
    
    Methods แบ่งเป็นหมวดหมู่:
    - Initialization: __init__
    - Template Management: load_and_train
    - Image Processing: _preprocess_image, _apply_clahe, _create_mask
    - Feature Matching: _extract_features, _match_features, _calculate_homography
    - Results Processing: _calculate_match_area, _filter_results
    - Public Scanning: scan_with_tiling, scan_multiple_items
    - Visualization: visualize_keypoints
    """
    
    # ===== SECTION 1: INITIALIZATION =====
    def __init__(self, db_folder=None):
        if db_folder is None:
            from config import MASTER_DATA_DIR
            db_folder = str(MASTER_DATA_DIR)
        self.db_folder = db_folder
        
        # ใช้ SIFT (SIFT_create) ที่ปรับแต่งมาเพื่อจับพื้นผิวโลหะ
        # contrastThreshold=0.03: ช่วยให้จับลายบนผิวเหล็กได้ดีขึ้น
        # edgeThreshold=10: ลดการจับขอบเงาที่หลอกตา
        self.sift = cv2.SIFT_create(contrastThreshold=0.03, edgeThreshold=10)
        
        # ตั้งค่า FLANN Matcher สำหรับการจับคู่เร็ว
        self.index_params = dict(algorithm=1, trees=5)
        self.search_params = dict(checks=50)
        
        self.templates = [] 
        self.load_and_train()

    # ===== SECTION 2: TEMPLATE MANAGEMENT =====
    def load_and_train(self):
        """โหลดรูปแบบเครื่องมือจากโฟลเดอร์และดึงลักษณะเฉพาะ"""
        print(f"--- กำลังตรวจสอบโฟลเดอร์: {os.path.abspath(self.db_folder)} ---")
        
        if not os.path.exists(self.db_folder):
            print(f"❌ ERROR: ไม่พบโฟลเดอร์ '{self.db_folder}'")
            return

        files = [f for f in os.listdir(self.db_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        total_files = len(files)
        
        for i, file in enumerate(files):
            path = os.path.join(self.db_folder, file)
            self._load_template(path, file, i, total_files)

        print(f"--- สรุป: จำได้ {len(self.templates)} รูปแบบ ---")

    def _load_template(self, path, filename, index, total):
        """โหลดเทมเพลตเดียว และดึงลักษณะเฉพาะ"""
        try:
            img_color = cv2.imread(path)
            if img_color is None:
                return

            # ประมวลผลภาพ
            img_gray = self._preprocess_image(img_color)
            mask = self._create_mask(img_gray)

            # ดึงลักษณะเฉพาะ (Features)
            kp, des = self.sift.detectAndCompute(img_gray, mask)
            
            if des is not None and len(kp) > 0:
                self.templates.append({
                    "name": filename,
                    "kp": kp,
                    "des": des,
                    "shape": img_gray.shape
                })
                print(f"[{index+1}/{total}] ✅ จดจำเนื้อเครื่องมือ: {filename} ({len(kp)} จุด)")
        
        except Exception as e:
            print(f"⚠️ ข้ามไฟล์ {filename}: {e}")
    
    # ===== SECTION 3: IMAGE PROCESSING =====
    def _preprocess_image(self, img_color):
        """แปลงภาพสีเป็นภาพขาวดำและปรับแสง"""
        img_gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
        img_gray = self._apply_clahe(img_gray)
        return img_gray
    
    def _apply_clahe(self, img_gray):
        """ปรับแสงของภาพขาวดำ (Contrast Limited Adaptive Histogram Equalization)"""
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        return clahe.apply(img_gray)
    
    def _create_mask(self, img_gray):
        """สร้าง Mask เพื่อลบพื้นหลังสีขาว"""
        # ถ้าพิกเซลไหนสว่างมากๆ (>235) ให้ถือว่าเป็นพื้นหลัง (สีดำใน mask)
        _, mask = cv2.threshold(img_gray, 235, 255, cv2.THRESH_BINARY_INV)
        return mask
    
    # ===== SECTION 4: FEATURE MATCHING =====
    def _extract_features(self, img_gray, mask=None):
        """ดึงลักษณะเฉพาะจากภาพ"""
        kp, des = self.sift.detectAndCompute(img_gray, mask)
        return kp, des
    
    def _match_features(self, template_des, scene_des):
        """จับคู่ลักษณะระหว่างเทมเพลตและฉากภาพ"""
        flann = cv2.FlannBasedMatcher(self.index_params, self.search_params)
        
        if template_des is None or scene_des is None or len(template_des) < 2:
            return []
        
        matches = flann.knnMatch(template_des, scene_des, k=2)
        good_matches = self._filter_good_matches(matches)
        return good_matches
    
    def _filter_good_matches(self, matches):
        """กรองการจับคู่ที่ดี (Lowe's ratio test)"""
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < 0.7 * n.distance:
                    good_matches.append(m)
        return good_matches
    
    def _calculate_homography(self, template_kp, scene_kp, good_matches):
        """คำนวณ Homography Matrix จากการจับคู่ที่ดี"""
        if len(good_matches) < 8:
            return None, None, 0
        
        try:
            src_pts = np.float32([template_kp[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([scene_kp[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            
            if M is not None:
                matchesMask = mask.ravel().tolist()
                real_score = sum(matchesMask)
                return M, mask, real_score
        
        except Exception:
            pass
        
        return None, None, 0
    
    # ===== SECTION 5: RESULTS PROCESSING =====
    def _calculate_match_area(self, template_shape, homography_matrix):
        """คำนวณพื้นที่การจับคู่"""
        h, w = template_shape
        pts = np.float32([[0, 0], [0, h-1], [w-1, h-1], [w-1, 0]]).reshape(-1, 1, 2)
        
        try:
            dst = cv2.perspectiveTransform(pts, homography_matrix)
            area = cv2.contourArea(np.int32(dst))
            return area
        except:
            return 0
    
    def _filter_results(self, found_in_chunk, threshold, min_area=100):
        """กรองผลลัพธ์ตามเกณฑ์"""
        filtered = []
        for item in found_in_chunk:
            if item["score"] >= threshold and item.get("area", 0) > min_area:
                filtered.append(item)
        return filtered
    
    def _merge_results(self, all_results):
        """รวมผลลัพธ์จากหลายส่วน และเก็บคะแนนสูงสุด"""
        final_results = {}
        for res in all_results:
            name = res['filename']
            score = res['score']
            if name not in final_results or score > final_results[name]['score']:
                final_results[name] = res
        return sorted(list(final_results.values()), key=lambda x: x['score'], reverse=True)

    # ===== SECTION 6: SCANNING LOGIC (PRIVATE) =====
    def _scan_single_image(self, img_gray, threshold, min_area=100):
        """scanning ภาพ 1 ภาพ (ใช้ภายใน Class)"""
        found_in_chunk = []
        
        # ปรับแสง
        img_gray = self._apply_clahe(img_gray)

        # ดึงลักษณะเฉพาะจากฉากภาพ
        kp_scene, des_scene = self._extract_features(img_gray, mask=None)
        if des_scene is None:
            return []

        # จับคู่กับแต่ละเทมเพลต
        for item in self.templates:
            found_item = self._match_template(item, kp_scene, des_scene, threshold, min_area)
            if found_item:
                found_in_chunk.append(found_item)
        
        return found_in_chunk
    
    def _match_template(self, template, kp_scene, des_scene, threshold, min_area):
        """จับคู่เทมเพลตเดียวกับฉากภาพ"""
        try:
            # จับคู่ลักษณะ
            good_matches = self._match_features(template['des'], des_scene)
            if len(good_matches) < 8:
                return None
            
            # คำนวณ Homography
            M, mask, real_score = self._calculate_homography(
                template['kp'], kp_scene, good_matches
            )
            
            if M is None or real_score < threshold:
                return None
            
            # ตรวจสอบพื้นที่
            area = self._calculate_match_area(template['shape'], M)
            if area <= min_area:
                return None
            
            return {
                "filename": template['name'],
                "score": int(real_score),
                "area": int(area)
            }
        
        except Exception:
            return None

    # ===== SECTION 7: PUBLIC SCANNING METHODS =====
    def scan_with_tiling(self, scene_image, threshold=8, min_area=100):
        """ 
        [Main Method] แบ่งภาพเป็น 4 ส่วนแล้วสแกน (Image Tiling)
        
        Args:
            scene_image: ภาพฉากที่จะสแกน (BGR)
            threshold: เกณฑ์ขั้นต่ำของคะแนนการจับคู่
            min_area: พื้นที่ขั้นต่ำของการจับคู่
        
        Returns:
            List of matched items sorted by score (descending)
        """
        gray_scene = cv2.cvtColor(scene_image, cv2.COLOR_BGR2GRAY)
        h, w = gray_scene.shape
        
        # กำหนดจุดกึ่งกลาง และระยะ Overlap (10%)
        mid_h, mid_w = h // 2, w // 2
        overlap_h = int(h * 0.1)
        overlap_w = int(w * 0.1)

        # นิยาม 4 พื้นที่ (ROI: Region of Interest)
        rois = [
            gray_scene[0:mid_h+overlap_h, 0:mid_w+overlap_w],       # ซ้ายบน
            gray_scene[0:mid_h+overlap_h, mid_w-overlap_w:w],       # ขวาบน
            gray_scene[mid_h-overlap_h:h, 0:mid_w+overlap_w],       # ซ้ายล่าง
            gray_scene[mid_h-overlap_h:h, mid_w-overlap_w:w]        # ขวาล่าง
        ]
        
        print(f"--- เริ่มสแกนแบบ Tiling (4 ส่วน) ---")
        
        all_results = []
        for i, roi in enumerate(rois):
            results = self._scan_single_image(roi, threshold, min_area)
            print(f"   ส่วนที่ {i+1}: เจอ {len(results)} รายการ")
            all_results.extend(results)
        
        # รวมและกรองผลลัพธ์
        return self._merge_results(all_results)

    def scan_multiple_items(self, scene_image, threshold=8, min_area=100):
        """ 
        (Legacy) ค้นหาแบบเต็มภาพ ไม่แบ่งส่วน
        
        Args:
            scene_image: ภาพฉากที่จะสแกน (BGR)
            threshold: เกณฑ์ขั้นต่ำของคะแนนการจับคู่
            min_area: พื้นที่ขั้นต่ำของการจับคู่
        
        Returns:
            List of matched items sorted by score (descending)
        """
        gray_scene = cv2.cvtColor(scene_image, cv2.COLOR_BGR2GRAY)
        results = self._scan_single_image(gray_scene, threshold, min_area)
        return sorted(results, key=lambda x: x['score'], reverse=True)
    
    # ===== SECTION 8: VISUALIZATION =====
    def visualize_keypoints(self, image):
        """
        วาดจุดลักษณะเฉพาะบนภาพ
        
        Returns:
            Tuple: (ภาพวาด, จำนวนจุด)
        """
        output_img = image.copy()
        gray = cv2.cvtColor(output_img, cv2.COLOR_BGR2GRAY)
        
        gray = self._apply_clahe(gray)
        kp, _ = self._extract_features(gray, mask=None)
        
        # วาดกากบาทเล็กๆ สีแดง
        for k in kp:
            x, y = int(k.pt[0]), int(k.pt[1])
            cv2.drawMarker(output_img, (x, y), (0, 0, 255), 
                          markerType=cv2.MARKER_CROSS, markerSize=5, thickness=1)
        
        return output_img, len(kp)

    # ===== SECTION 9: TRAY TEMPLATE METHODS =====

    def _get_tool_info_from_db(self, filename):
        """โหลดข้อมูลชื่อ/หมวดหมู่จาก data.json"""
        data_path = os.path.join(self.db_folder, 'data.json')
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                base = os.path.basename(filename)
                base_no_ext = os.path.splitext(base)[0]
                for item in data:
                    if (item.get('filename') == base or 
                        item.get('code') == base or 
                        item.get('code') == base_no_ext or
                        item.get('name_en') == base_no_ext or
                        item.get('class_key') == base_no_ext):
                        return item
        except Exception:
            pass
        return None

    def _get_match_bbox(self, template_shape, homography_matrix, scene_shape):
        """คำนวณ Bounding Box ในภาพฉากจาก Homography Matrix"""
        h_tmpl, w_tmpl = template_shape
        h_scene, w_scene = scene_shape
        pts = np.float32([
            [0, 0], [0, h_tmpl - 1], [w_tmpl - 1, h_tmpl - 1], [w_tmpl - 1, 0]
        ]).reshape(-1, 1, 2)
        try:
            dst = cv2.perspectiveTransform(pts, homography_matrix)
            x_coords = dst[:, 0, 0]
            y_coords = dst[:, 0, 1]
            x1 = float(max(0.0, np.min(x_coords)))
            y1 = float(max(0.0, np.min(y_coords)))
            x2 = float(min(float(w_scene), np.max(x_coords)))
            y2 = float(min(float(h_scene), np.max(y_coords)))
            # กรองผลที่ไม่สมเหตุสมผล
            if x2 - x1 < 5 or y2 - y1 < 5:
                return None
            return x1, y1, x2, y2
        except Exception:
            return None

    def _match_template_with_position(self, template, kp_scene, des_scene, scene_shape, threshold=8, min_area=100):
        """จับคู่เทมเพลตและคืนตำแหน่ง Bounding Box ในภาพ"""
        try:
            good_matches = self._match_features(template['des'], des_scene)
            if len(good_matches) < 8:
                return None

            M, mask, real_score = self._calculate_homography(
                template['kp'], kp_scene, good_matches
            )
            if M is None or real_score < threshold:
                return None

            area = self._calculate_match_area(template['shape'], M)
            if area <= min_area:
                return None

            bbox = self._get_match_bbox(template['shape'], M, scene_shape)
            if bbox is None:
                return None

            return {
                "filename": template['name'],
                "score": int(real_score),
                "area": int(area),
                "bbox": bbox  # (x1, y1, x2, y2) relative to tile
            }
        except Exception:
            return None

    def register_tray_template(self, scene_img, tray_id, tray_name, threshold=8):
        """
        ลงทะเบียน Template ถาด: สแกนหาเครื่องมือ + บันทึกตำแหน่งและ Brightness Baseline

        Args:
            scene_img : ภาพถาด BGR ที่มีเครื่องมือครบทุกชิ้น
            tray_id   : รหัสถาด (ใช้เป็นชื่อไฟล์ JSON)
            tray_name : ชื่อถาดสำหรับแสดงผล
            threshold : เกณฑ์คะแนน SIFT ขั้นต่ำ

        Returns:
            dict: ข้อมูล Template ที่บันทึก (tray_name, slots, ...)
        """
        gray_full = cv2.cvtColor(scene_img, cv2.COLOR_BGR2GRAY)
        h_full, w_full = gray_full.shape

        # Tiling เหมือน scan_with_tiling (4 ส่วน + overlap 10%)
        mid_h, mid_w = h_full // 2, w_full // 2
        overlap_h = int(h_full * 0.1)
        overlap_w = int(w_full * 0.1)

        # (row_start, col_start, row_end, col_end)
        tiles_info = [
            (0,                 0,                 mid_h + overlap_h, mid_w + overlap_w),  # ซ้ายบน
            (0,                 mid_w - overlap_w, mid_h + overlap_h, w_full),              # ขวาบน
            (mid_h - overlap_h, 0,                 h_full,            mid_w + overlap_w),  # ซ้ายล่าง
            (mid_h - overlap_h, mid_w - overlap_w, h_full,            w_full),              # ขวาล่าง
        ]

        all_results = {}  # fname -> best result

        for (r1, c1, r2, c2) in tiles_info:
            tile_gray  = gray_full[r1:r2, c1:c2]
            tile_clahe = self._apply_clahe(tile_gray)
            tile_h, tile_w = tile_clahe.shape

            kp_scene, des_scene = self._extract_features(tile_clahe, mask=None)
            if des_scene is None:
                continue

            for tmpl in self.templates:
                result = self._match_template_with_position(
                    tmpl, kp_scene, des_scene, (tile_h, tile_w), threshold
                )
                if result is None:
                    continue

                fname = result['filename']

                # แปลงตำแหน่งจาก Tile → Full Image
                tx1, ty1, tx2, ty2 = result['bbox']
                fx1 = max(0.0, min(tx1 + c1, float(w_full)))
                fy1 = max(0.0, min(ty1 + r1, float(h_full)))
                fx2 = max(0.0, min(tx2 + c1, float(w_full)))
                fy2 = max(0.0, min(ty2 + r1, float(h_full)))

                if fname not in all_results or result['score'] > all_results[fname]['score']:
                    # วัดค่าความสว่าง Baseline ในพื้นที่ ROI
                    crop = gray_full[int(fy1):int(fy2), int(fx1):int(fx2)]
                    mean_bright = float(np.mean(crop)) if crop.size > 0 else 128.0

                    # โหลดชื่อ / หมวดหมู่จาก data.json
                    info = self._get_tool_info_from_db(fname)

                    all_results[fname] = {
                        "filename": fname,
                        "name": info['name'] if info else fname,
                        "category": info['category'] if info else "Unknown",
                        "description": info.get('description', '-') if info else '-',
                        "score": result['score'],
                        "bbox_norm": [
                            round(fx1 / w_full, 5),
                            round(fy1 / h_full, 5),
                            round(fx2 / w_full, 5),
                            round(fy2 / h_full, 5)
                        ],
                        "mean_brightness": round(mean_bright, 2)
                    }

        # สร้างโฟลเดอร์ tray_templates/ ถ้ายังไม่มี
        template_dir = os.path.join(self.db_folder, 'tray_templates')
        os.makedirs(template_dir, exist_ok=True)

        tray_data = {
            "tray_name": tray_name,
            "tray_id": tray_id,
            "registered_at": datetime.datetime.now().isoformat(timespec='seconds'),
            "image_size": [w_full, h_full],
            "slots": list(all_results.values())
        }

        out_path = os.path.join(template_dir, f"{tray_id}.json")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(tray_data, f, ensure_ascii=False, indent=2)

        print(f"\u2705 บันทึก Template ถาด '{tray_name}': {len(all_results)} รายการ -> {out_path}")
        return tray_data

    def check_tray_slots(self, scene_img, tray_id, brightness_threshold_pct=18):
        """
        ตรวจสอบว่าถาดมีเครื่องมือครบตาม Template โดยใช้ Region Comparison (Brightness / Visual)

        Args:
            scene_img                : ภาพถาดปัจจุบัน BGR
            tray_id                  : รหัสถาดที่ต้องการตรวจ
            brightness_threshold_pct : % ความต่างของ brightness ที่ถือว่า "ขาด" (default 18%)

        Returns:
            Tuple: (List[dict] results, dict tray_data) หรือ (None, error_msg)
        """
        template_dir = os.path.join(self.db_folder, 'tray_templates')
        template_path = os.path.join(template_dir, f"{tray_id}.json")
        tray_data = None

        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                tray_data = json.load(f)
        else:
            # ค้นหาจากไฟล์ทั้งหมดในโฟลเดอร์ template_dir กรณีชื่อไฟล์ไม่ตรงกับ tray_id
            if os.path.exists(template_dir):
                for fname in os.listdir(template_dir):
                    if fname.endswith('.json'):
                        p = os.path.join(template_dir, fname)
                        try:
                            with open(p, 'r', encoding='utf-8') as f:
                                d = json.load(f)
                            if d.get('tray_id') == tray_id:
                                tray_data = d
                                break
                        except Exception:
                            continue

        if tray_data is None:
            return None, f"ไม่พบ Template: {tray_id}"

        gray_scene = cv2.cvtColor(scene_img, cv2.COLOR_BGR2GRAY)
        h_scene, w_scene = gray_scene.shape

        results = []
        for slot in tray_data.get('slots', []):
            bbox_norm = slot.get('bbox_norm')
            if not bbox_norm:
                continue

            x1_n, y1_n, x2_n, y2_n = bbox_norm

            # Denormalize + padding 1% เพื่อความยืดหยุ่น
            pad_x = w_scene * 0.01
            pad_y = h_scene * 0.01
            x1 = int(max(0, x1_n * w_scene - pad_x))
            y1 = int(max(0, y1_n * h_scene - pad_y))
            x2 = int(min(w_scene, x2_n * w_scene + pad_x))
            y2 = int(min(h_scene, y2_n * h_scene + pad_y))

            crop = gray_scene[y1:y2, x1:x2]

            if crop.size == 0:
                status       = "unknown"
                current_b    = slot.get('mean_brightness', 128.0)
                diff_pct     = 0.0
            else:
                current_b = float(np.mean(crop))
                # ถ้ามี mean_brightness baseline ให้เทียบ diff
                if 'mean_brightness' in slot and slot['mean_brightness'] is not None:
                    baseline  = slot['mean_brightness']
                    diff_pct  = abs(current_b - baseline) / max(baseline, 1.0) * 100
                    status    = "missing" if diff_pct > brightness_threshold_pct else "present"
                else:
                    # ถ้าไม่มี baseline ใช้ contrast & edge density เช็คการมีอยู่
                    std_val = float(np.std(crop))
                    edges = cv2.Canny(crop, 50, 150)
                    edge_density = float(np.count_nonzero(edges)) / float(max(1, crop.size))
                    is_present = (std_val > 18.0) or (edge_density > 0.04) or (current_b > 85.0 and std_val > 14.0)
                    status = "present" if is_present else "missing"
                    diff_pct = 0.0 if is_present else 100.0

            results.append({
                **slot,
                "status":               status,
                "current_brightness":   round(current_b, 2),
                "brightness_diff_pct": round(diff_pct, 1),
                "bbox_px":             [x1, y1, x2, y2]
            })

        return results, tray_data

    def list_tray_templates(self):
        """คืนรายชื่อ Template ถาดทั้งหมดที่ลงทะเบียนแล้ว"""
        template_dir = os.path.join(self.db_folder, 'tray_templates')
        if not os.path.exists(template_dir):
            return []

        templates = []
        for fname in os.listdir(template_dir):
            if not fname.endswith('.json'):
                continue
            path = os.path.join(template_dir, fname)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                templates.append({
                    "tray_id":       data['tray_id'],
                    "tray_name":     data['tray_name'],
                    "slot_count":    len(data.get('slots', [])),
                    "registered_at": data.get('registered_at', '-')
                })
            except Exception:
                pass

        return sorted(templates, key=lambda x: x['tray_name'])

    def delete_tray_template(self, tray_id):
        """ลบ Template ถาด"""
        path = os.path.join(self.db_folder, 'tray_templates', f"{tray_id}.json")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False