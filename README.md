# 🔧 modelScaniTem: ระบบตรวจเช็คเครื่องมือในถาด

ระบบตรวจว่าเครื่องมือในถาด/แผงอยู่ครบและวางถูกช่องหรือไม่ จากภาพถ่ายมือถือหรือ iPad
ใช้กับรายการเครื่องมือตาม **Merchandise Visit Checklist** (ชุดมาตรฐาน 86 รายการ และเครื่องมือพิเศษ 31 รายการ)

มี 2 แอป (Streamlit):

| แอป | ไฟล์ | ใช้ทำอะไร |
|---|---|---|
| แอปสแกน | `app.py` | สแกนเครื่องมือ, เช็คลิสต์, ลงทะเบียนและตรวจถาด |
| แอป admin | `admin.py` | จัดการคลาสเครื่องมือ, เก็บภาพเทรน, export dataset, จัดการโมเดล YOLO, ทดสอบสแกน (ต้องมี PostgreSQL) |

---

## 📦 โครงสร้างโปรเจกต์

```
modelScaniTem/
├── app.py                  # แอปสแกน: ประกอบหน้า + เมนู
├── admin.py                # แอป admin (YOLO + PostgreSQL)
├── ui/                     # หน้าของแอปสแกน
│   ├── style.py            #   CSS ธีม + header
│   ├── common.py           #   session state, โหลดภาพ (EXIF), ข้อมูลเครื่องมือ
│   ├── scanner_page.py     #   หน้า "สแกน"
│   ├── checklist_page.py   #   หน้า "เช็คลิสต์"
│   └── tray_page.py        #   หน้า "ถาด" (ลงทะเบียน / ตรวจสอบถาด)
├── scan_workflow/          # pipeline ตรวจถาด (ดูหัวข้อด้านล่าง)
├── scanners/               # ShapeScanner (SIFT, หน้า "สแกน") และ YOLOToolScanner (แอป admin)
├── admin_modules/          # หน้าของแอป admin
├── core/                   # config.py (path ทั้งหมด), db.py, models_db.py
├── data/                   # ข้อมูลหลัก (อยู่ใน git)
│   ├── tray_templates/     #   เทมเพลตถาด: ช่อง, polygon, ชื่อ/รหัสอะไหล่ตาม checklist
│   ├── tray_refs/          #   ภาพต้นแบบ <tray_id>.jpg, ภาพถาดว่าง <tray_id>_empty.jpg
│   ├── data.json           #   รายการเครื่องมือ
│   ├── merchandise_checklist.json   # Excel checklist ที่แปลงเป็น JSON
│   ├── checklist_slot_mapping.json  # ช่องในถาด → ลำดับใน checklist
│   └── sample_images/
├── admin_data/             # ไฟล์ที่แอป admin สร้าง: images/, models/, exports/
├── reports/                # ผลเทส (เก็บ json/csv ใน git, ไม่เก็บภาพผล)
├── scripts/
│   ├── build/              # สร้าง/อัปเดตข้อมูลถาด
│   ├── eval/               # เทสและวัดความแม่นยำ
│   └── legacy/             # สคริปต์เก่า (ดู scripts/legacy/README.md)
└── notebooks/              # Colab สำหรับเทรน YOLOv8
```

path ทั้งหมดอยู่ใน `core/config.py` ที่เดียว แอปและสคริปต์จึงรันจากโฟลเดอร์ไหนก็ได้

---

## 🚀 เริ่มต้นใช้งาน

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

ตั้งค่า `.env` (ดูตัวอย่างใน `.env.example`):

| ตัวแปร | ใช้ทำอะไร |
|---|---|
| `DATABASE_URL` | PostgreSQL ของแอป admin |
| `SECRET_KEY`, `ADMIN_DEFAULT_USER`, `ADMIN_DEFAULT_PASS` | การล็อกอินแอป admin |
| `DATA_DIR` | โฟลเดอร์ไฟล์ของแอป admin (ค่าเริ่มต้น `admin_data`) |
| `YAMAHA_DATA_DIR` | (ไม่บังคับ) โฟลเดอร์ภาพดิบนอก repo เช่น `C:/MyProject/Webpark/dataYamaha` สคริปต์จะใช้เป็นค่าเริ่มต้นของ `--photos` |

> ช่วงพัฒนา `.env`, โมเดล `.pt` และภาพเทรนใน `admin_data/` ถูกเก็บใน git โดยตั้งใจ
> ก่อนใช้งานจริงให้เพิ่มกลับเข้า `.gitignore` (ดูหมายเหตุบรรทัดแรกของไฟล์) และเปลี่ยนรหัสผ่านทั้งหมด

รันแอป:

```bash
streamlit run app.py
```

```bash
streamlit run admin.py
```

---

## 🔍 การตรวจถาด (`scan_workflow/`)

```
ภาพถ่าย → Quality Gate → จัดระนาบ (SIFT + Homography กับ data/tray_refs/<tray_id>.jpg)
        → ตรวจทีละช่อง (SlotChecker) → สรุปผล + วาดกรอบสี (ScanAggregator)
```

| ขั้น | ไฟล์ | หมายเหตุ |
|---|---|---|
| Quality Gate | `quality_gate.py` | เบลอ/มืด/สว่างเกิน |
| ตัดขอบถาด | `tray_cropper.py` | ใช้เมื่อจัดระนาบตรงๆ ไม่ได้ (ถ่ายไกล, อยู่ในตู้) |
| จัดระนาบ | `aligner.py` | ลองหมุน 0/90/180/270°; ภาพแนวตั้งถูกหมุนเป็นแนวนอนก่อน |
| ตรวจช่อง | `slot_checker.py` | เทียบพื้นที่ polygon ของช่องกับภาพถาดครบและภาพถาดว่าง |
| สรุปผล | `aggregator.py` | ถ้าจัดระนาบไม่สำเร็จ ทุกช่องเป็น "ตรวจซ้ำ" และขอให้ถ่ายใหม่ |

สถานะของแต่ละช่อง: 🟢 ครบ, 🔴 ขาดหาย, 🟡 ผิดตำแหน่ง, ↩️ ตรวจซ้ำ

**ข้อจำกัดตอนนี้:** ภาพต้นแบบเป็นภาพสตูดิโอของถาดอีกใบ ภาพหน้างาน (ถาดโฟมเทาในตู้, แผงหลังกระจก)
จึงยังจัดระนาบไม่ค่อยได้ ควรถ่ายภาพต้นแบบใหม่จากถาดหน้างาน (ดูหัวข้อถัดไป)

---

## 🧰 เพิ่มหรืออัปเดตถาด

1. **เทมเพลต** `data/tray_templates/<tray_id>.json` ต้องมี `image_width`, `image_height` และแต่ละช่องมี `slot_number`, `bbox_norm`, `polygon`
2. **จับคู่กับ checklist:** เพิ่มช่องใน `data/checklist_slot_mapping.json` แล้วรัน
   ```bash
   python scripts/build/apply_checklist_mapping.py --apply --photos <โฟลเดอร์ภาพ <tray_id>_number.png>
   ```
   ผลตรวจอยู่ที่ `reports/checklist_match/`
3. **ภาพต้นแบบ:** เตรียม `<tray_id>_full.png` (ถาดครบ) และ `<tray_id>_empty.png` (ถาดว่าง) ในมุมเดียวกับเทมเพลต แล้วรัน
   ```bash
   python scripts/build/build_tray_refs.py --photos <โฟลเดอร์ภาพ>
   ```
   สคริปต์จะเขียน `data/tray_refs/<tray_id>.jpg`, `<tray_id>_empty.jpg` และภาพตรวจใน `reports/tray_refs_check/`
4. **วัดผล** (หัวข้อถัดไป)

---

## 🧪 เทสและวัดความแม่นยำ (`scripts/eval/`)

| สคริปต์ | ทำอะไร | ผลลัพธ์ |
|---|---|---|
| `test_box2_scan.py`, `test_orientation_and_accuracy.py` | เทสเร็ว: แนวนอน/แนวตั้ง/กลับหัว, จับของหาย | ผ่าน/ไม่ผ่าน |
| `test_all_three_trays.py` | สแกนภาพต้นแบบทั้ง 3 ถาด | `reports/benchmark_3_trays_results.json` |
| `simulate_scan_accuracy.py` | จำลองเอาเครื่องมือออก + สภาพกล้อง 3 ระดับ | `reports/scan_simulation/` |
| `test_real_photos.py` | รันกับภาพหน้างานจริง | `reports/real_photo_test/<ชุด>/report.csv` |

```bash
python scripts/eval/test_orientation_and_accuracy.py
```

```bash
python scripts/eval/simulate_scan_accuracy.py --photos C:/MyProject/Webpark/dataYamaha/Merchecklist/Tools/tian
```

```bash
python scripts/eval/test_real_photos.py --images <โฟลเดอร์ภาพ> --trays box1-template01_70-item,box1-template02_16-item --out reports/real_photo_test/86
```

---

## 🗂️ ถาดที่มีตอนนี้

| tray_id | ถาด | ช่อง | ชีต checklist |
|---|---|---|---|
| `box1-template01_70-item` | YA 1/2 | 69 | มาตรฐาน 86 รายการ ลำดับ 1–70 (ลำดับ 49 ไม่มีช่องในถาด) |
| `box1-template02_16-item` | YA 2/2 | 17 | มาตรฐาน 86 รายการ ลำดับ 71–86 |
| `box2-template01_31-item` | แผงเครื่องมือพิเศษ | 41 | เครื่องมือพิเศษ 31 รายการ |

---

## 📝 ShapeScanner (หน้า "สแกน")

`scanners/scanner_module.py` จดจำเครื่องมือด้วย SIFT จากภาพต้นแบบในโฟลเดอร์ `data/` (ไฟล์ `.png/.jpg/.jpeg/.bmp`)
และสแกนแบบแบ่งภาพเป็น 4 ส่วน (`scan_with_tiling`) คืนรายการ `{"filename", "score", "area"}` เรียงจากคะแนนสูงไปต่ำ
ตอนนี้ยังไม่มีภาพต้นแบบใน `data/` หน้า "สแกน" จึงยังจำเครื่องมือไม่ได้
