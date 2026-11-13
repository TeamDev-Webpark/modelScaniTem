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

GOOD, GOOD_BG = "#1E9E40", "#E8F7ED"
WARN, WARN_BG, WARN_BORDER = "#B57000", "#FFF9E6", "#D4A000"
BAD_BG = "#FFF2F2"
INFO, INFO_BG, INFO_BORDER = "#2B6CB0", "#EBF8FF", "#3182CE"

# สถานะ: label, icon, ตัวอักษร (fg), พื้น (bg), ขอบ (border)
STATUS = {
    # รายการอุปกรณ์ (core/scan_items.py)
    "present":      {"label": "มี",               "icon": "🟢", "fg": GOOD,       "bg": GOOD_BG, "border": GOOD},
    "absent":       {"label": "ไม่มี",             "icon": "🔴", "fg": PRIMARY,    "bg": BAD_BG,  "border": PRIMARY},
    "misplaced":    {"label": "ผิดที่",             "icon": "🟡", "fg": WARN,       "bg": WARN_BG, "border": WARN_BORDER},
    "recheck":      {"label": "ตรวจซ้ำ",           "icon": "↩️", "fg": TEXT_MUTED, "bg": "#F0F0F0", "border": "#808080"},
    "unchecked":    {"label": "ยังไม่ตรวจ",         "icon": "⚪", "fg": TEXT_MUTED, "bg": SURFACE, "border": BORDER},
    "manual":       {"label": "แก้ด้วยมือ",         "icon": "✋", "fg": INFO,       "bg": INFO_BG, "border": INFO_BORDER},
    # ผลรวมของการสแกนหนึ่งครั้ง (ประวัติ)
    "done":         {"label": "ครบ",              "icon": "✅", "fg": GOOD,       "bg": GOOD_BG, "border": GOOD},
    "needs_review": {"label": "ต้องดำเนินการ",      "icon": "⚠️", "fg": WARN,       "bg": WARN_BG, "border": WARN_BORDER},
    # สถานะที่เก็บไว้ในประวัติจากแอปรุ่นก่อน (ระบบคิวภาพ)
    "pending":      {"label": "รอตรวจ",            "icon": "⏳", "fg": TEXT_MUTED, "bg": SURFACE, "border": BORDER},
    "processing":   {"label": "กำลังตรวจ",          "icon": "🔄", "fg": INFO,       "bg": INFO_BG, "border": INFO_BORDER},
    "failed":       {"label": "ตรวจไม่สำเร็จ",       "icon": "❌", "fg": PRIMARY,    "bg": BAD_BG,  "border": PRIMARY},
}


def status(key: str) -> dict:
    return STATUS.get(key, STATUS["recheck"])


def label(key: str) -> str:
    return status(key)["label"]
