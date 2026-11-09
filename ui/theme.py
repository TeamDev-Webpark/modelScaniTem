"""Theme values for the scanner app: palette, status colours and breakpoints.

Every page and ui/components.py take colours from here instead of writing hex literals.
"""

# Palette (from the original ui/style.py)
PRIMARY = "#E81D23"         # แดง: ปุ่มหลัก, เน้น
PRIMARY_DARK = "#C7161B"    # แดงเข้ม: hover
TEXT = "#2C2C2C"            # ตัวอักษรหลัก, กล่องตัวเลขเข้ม
TEXT_MUTED = "#525252"      # ตัวอักษรรอง
BORDER = "#C7C7C7"          # เส้นขอบ
SURFACE = "#E5E5E5"         # พื้นรอง (ปุ่มรอง, ป้าย)
BACKGROUND = "#FFFFFF"      # พื้นหลังหน้า

MOBILE_MAX_WIDTH = 768      # px: จอเล็กกว่านี้ใช้รูปแบบมือถือ
TOUCH_TARGET = 44           # px: ขนาดปุ่มกดขั้นต่ำ

# สถานะ: label, icon, ตัวอักษร (fg), พื้น (bg), ขอบ (border)
STATUS = {
    # ผลรายช่องของการตรวจถาด
    "correct":      {"label": "ครบ",              "icon": "🟢", "fg": "#1E9E40", "bg": "#E8F7ED", "border": "#1E9E40"},
    "missing":      {"label": "ขาดหาย",           "icon": "🔴", "fg": PRIMARY,   "bg": "#FFF2F2", "border": PRIMARY},
    "misplaced":    {"label": "ผิดตำแหน่ง",        "icon": "🟡", "fg": "#B57000", "bg": "#FFF9E6", "border": "#D4A000"},
    "recheck":      {"label": "ตรวจซ้ำ",           "icon": "↩️", "fg": TEXT_MUTED, "bg": "#F0F0F0", "border": "#808080"},
    # สถานะของภาพที่ส่งตรวจ
    "pending":      {"label": "รอตรวจสอบ",         "icon": "⏳", "fg": TEXT_MUTED, "bg": SURFACE,   "border": BORDER},
    "processing":   {"label": "กำลังตรวจสอบ",      "icon": "🔄", "fg": "#2B6CB0", "bg": "#EBF8FF", "border": "#3182CE"},
    "done":         {"label": "ตรวจสอบแล้ว",        "icon": "✅", "fg": "#1E9E40", "bg": "#E8F7ED", "border": "#1E9E40"},
    "needs_review": {"label": "ต้องตรวจสอบเพิ่มเติม", "icon": "⚠️", "fg": "#B57000", "bg": "#FFF9E6", "border": "#D4A000"},
    "failed":       {"label": "ตรวจไม่สำเร็จ",       "icon": "❌", "fg": PRIMARY,   "bg": "#FFF2F2", "border": PRIMARY},
    # ผลตรวจรายอุปกรณ์ด้วยตนเอง
    "ok":           {"label": "ปกติ",              "icon": "🟢", "fg": "#1E9E40", "bg": "#E8F7ED", "border": "#1E9E40"},
    "damaged":      {"label": "ชำรุด",             "icon": "🟡", "fg": "#B57000", "bg": "#FFF9E6", "border": "#D4A000"},
    "lost":         {"label": "สูญหาย",            "icon": "🔴", "fg": PRIMARY,   "bg": "#FFF2F2", "border": PRIMARY},
    "unchecked":    {"label": "ยังไม่ตรวจ",         "icon": "⚪", "fg": TEXT_MUTED, "bg": SURFACE,   "border": BORDER},
}


def status(key: str) -> dict:
    return STATUS.get(key, STATUS["recheck"])
