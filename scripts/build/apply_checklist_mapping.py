"""Match tray template slots to the Merchandise Visit Checklist (Excel) and verify the result.

Inputs
  data/merchandise_checklist.json   - the Excel sheets exported to JSON
  data/checklist_slot_mapping.json  - slot -> checklist number (read from the numbered tray photos)

Usage
  python scripts/apply_checklist_mapping.py           # verify only, write report + check images
  python scripts/apply_checklist_mapping.py --apply   # verify, then write names/part numbers into the templates

Re-run this after any build_template_* / build_tray_* script, because those scripts
assign names by position heuristics and will overwrite the matched names.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.config import (CATALOG_PATH, CHECKLIST_MAPPING_PATH, CHECKLIST_MATCH_DIR, CHECKLIST_PATH,  # noqa: E402
                    CLASSES_70_PATH, MASTER_DATA_DIR, TRAY_TEMPLATES_DIR)

DB = MASTER_DATA_DIR
TEMPLATES = TRAY_TEMPLATES_DIR
OUT_DIR = CHECKLIST_MATCH_DIR


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def norm(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


class Report:
    def __init__(self):
        self.errors, self.warnings, self.passed = [], [], []

    def check(self, ok, msg, level="error"):
        if ok:
            self.passed.append(msg)
        elif level == "error":
            self.errors.append(msg)
        else:
            self.warnings.append(msg)
        return ok


# --------------------------------------------------------------------------- checks

def expected_classes(name):
    """Which detector class_key a slot should carry, judged from the checklist name."""
    if "คีม" in name:
        return {"pliers"}
    if "ฆ้อน" in name:
        return {"hammer"}
    if "ประแจ L" in name:
        return {"hex key"}
    if name.startswith(("ลูกบ๊อกซ์", "ลูกบล็อค", "ลูกบล๊อค", "ข้อต่อ", "ด้ามต่อ")):
        return {"socket"}
    if "ไขควง" in name and "ด้ามขันฟรี" not in name:
        return {"screwdriver"}
    if name.startswith(("ประแจ", "ด้ามขัน", "ชุดด้ามขันฟรี")):
        return {"wrench", "socket"}
    return None  # e.g. feeler gauge: no rule


def slot_size(slot, W, H):
    b = slot["bbox_norm"]
    w, h = (b[2] - b[0]) * W, (b[3] - b[1]) * H
    return max(w, h), w * h


def check_size_order(rep, tray_id, by_no, W, H):
    """Tools of one family must get bigger as the size in their name grows."""
    families = [
        ("ลูกบ๊อกซ์ 6 เหลี่ยม No.8-22", [1, 2, 3, 4, 5, 6, 7, 8, 9], "area"),
        ("ลูกบล็อคลม #8-22", [50, 51, 52, 53, 54, 55, 56, 57], "area"),
        ("ลูกบล็อคลม #22 < 1/2\" No.24", [57, 68], "area"),
        ("ประแจแหวน 8x10 - 22x24", [36, 37, 38, 39, 40, 41], "length"),
        ("ประแจรวม 5.5 - 17", [63, 64, 42, 43, 44, 45, 46], "length"),
        ("ไขควงแบน 75/100/150", [27, 28, 29], "length"),
        ("ไขควงแฉก 75/100/150", [31, 32, 33], "length"),
        ("ด้ามต่อบ๊อกซ์ 50/75/150", [18, 19, 20], "length"),
    ]
    for label, seq, metric in families:
        if not all(n in by_no for n in seq):
            continue
        vals = [slot_size(by_no[n][0], W, H)[0 if metric == "length" else 1] for n in seq]
        bad = [(seq[i], seq[i + 1]) for i in range(len(vals) - 1) if vals[i + 1] < vals[i] * 0.97]
        detail = ", ".join(f"#{n}={v:.0f}" for n, v in zip(seq, vals))
        rep.check(not bad, f"[{tray_id}] ขนาดเรียงถูกต้อง: {label} ({metric}: {detail})"
                  if not bad else
                  f"[{tray_id}] ขนาดไม่เรียงตามเบอร์: {label} คู่ที่ผิด {bad} ({metric}: {detail})",
                  level="warning")


def check_excel(rep, sheets):
    s86, s31 = sheets["standard_new_86"]["items"], sheets["special_new_31"]["items"]
    s55, s20 = sheets["standard_old_55"]["items"], sheets["special_old_20"]["items"]
    for key, items in sheets.items():
        items = items["items"]
        nos = [i["no"] for i in items]
        rep.check(nos == list(range(1, len(items) + 1)), f"[Excel:{key}] ลำดับเรียง 1..{len(items)} ไม่ข้าม")
        codes = [i["part_number"] for i in items]
        dup = sorted({c for c in codes if codes.count(c) > 1})
        rep.check(not dup, f"[Excel:{key}] หมายเลขอะไหล่ไม่ซ้ำ" if not dup else
                  f"[Excel:{key}] หมายเลขอะไหล่ซ้ำ: {dup}", level="warning")
        names = [norm(i["name"]) for i in items]
        dupn = sorted({n for n in names if names.count(n) > 1})
        rep.check(not dupn, f"[Excel:{key}] ชื่อรายการไม่ซ้ำ" if not dupn else
                  f"[Excel:{key}] ชื่อรายการซ้ำ (ต่างรหัส): " + "; ".join(
                      f"{n} = {[i['part_number'] for i in items if norm(i['name']) == n]}" for n in dupn),
                  level="warning")
    by86 = {i["part_number"]: norm(i["name"]) for i in s86}
    miss = [i for i in s55 if by86.get(i["part_number"]) != norm(i["name"])]
    rep.check(not miss, "[Excel] ชีต 55 รายการ (เดิม) อยู่ในชีต 86 รายการครบ ชื่อและรหัสตรงกัน" if not miss else
              f"[Excel] ชีต 55 ไม่ตรงกับชีต 86: {[(i['no'], i['part_number']) for i in miss]}")
    by31 = {i["part_number"]: norm(i["name"]) for i in s31}
    for i in s20:
        if i["part_number"] not in by31:
            rep.check(False, f"[Excel:special_old_20] #{i['no']} {i['part_number']} ไม่มีในชีต 31 รายการ", "warning")
        elif by31[i["part_number"]] != norm(i["name"]):
            rep.check(False, f"[Excel:special_old_20] #{i['no']} {i['part_number']} ชื่อ '{i['name']}' "
                             f"แต่ชีต 31 ใช้รหัสนี้กับ '{by31[i['part_number']]}'", "warning")


def special_catalog():
    """data.json holds two lists that reuse ids 1..N: the 31 special tools (snake_case codes)
    and the standard tools (part-number codes). Keep only the special-tool entries."""
    out = {}
    for d in load(CATALOG_PATH):
        if isinstance(d.get("id"), int) and not str(d.get("code", "")).startswith("90"):
            out.setdefault(d["id"], d)
    return out


def check_catalogs(rep, sheets):
    s86 = sheets["standard_new_86"]["items"]
    s31 = sheets["special_new_31"]["items"]
    classes = load(CLASSES_70_PATH)
    by_code = {c["code"]: c for c in classes}
    for it in s86[:70]:
        c = by_code.get(it["part_number"])
        if c is None:
            rep.check(False, f"[classes_ya1_2_70_tools.json] ไม่มี #{it['no']} {it['part_number']} {it['name']}", "warning")
        elif norm(c["name"]) != norm(it["name"]):
            rep.check(False, f"[classes_ya1_2_70_tools.json] {it['part_number']} ชื่อ '{c['name']}' ไม่ตรง Excel '{it['name']}'", "warning")
    data = special_catalog()
    for it in s31:
        d = data.get(it["no"])
        same = d is not None and norm(d["name"]).replace(" ", "") == norm(it["name"]).replace(" ", "")
        if d is None:
            rep.check(False, f"[data.json] ไม่มีเครื่องมือพิเศษ id {it['no']} {it['name']}", "warning")
        elif same:
            rep.check(True, f"[data.json] id {it['no']} ชื่อตรงกับ Excel")
        else:
            rep.check(False, f"[data.json] id {it['no']} ชื่อ '{d['name']}' ต่างจาก Excel '{it['name']}' (ใช้ code '{d['code']}')", "warning")


# --------------------------------------------------------------------------- matching

def build_tray(rep, tray_cfg, sheets, data_codes):
    tray_id = tray_cfg["tray_id"]
    tpl_path = TEMPLATES / f"{tray_id}.json"
    tpl = load(tpl_path)
    items = {i["no"]: i for i in sheets[tray_cfg["sheet"]]["items"]}
    offset, key = tray_cfg["number_offset"], tray_cfg["slot_key"]
    mapping = tray_cfg["slots"]
    W, H = tpl["image_width"], tpl["image_height"]

    slot_keys = [s.get(key) for s in tpl["slots"]]
    dup = sorted({k for k in slot_keys if slot_keys.count(k) > 1})
    rep.check(not dup, f"[{tray_id}] รหัสช่อง ({key}) ไม่ซ้ำกัน" if not dup else f"[{tray_id}] รหัสช่องซ้ำ {dup}")
    unmapped = [k for k in slot_keys if k not in mapping]
    rep.check(not unmapped, f"[{tray_id}] ทุกช่อง ({len(slot_keys)}) มีรายการ Excel จับคู่" if not unmapped else
              f"[{tray_id}] ช่องที่ยังไม่ได้จับคู่: {unmapped}")
    unknown = [k for k in mapping if k not in slot_keys]
    rep.check(not unknown, f"[{tray_id}] mapping ไม่มีรหัสช่องที่ไม่มีอยู่จริง" if not unknown else
              f"[{tray_id}] mapping อ้างถึงช่องที่ไม่มีใน template: {unknown}")

    rows, by_no = [], {}
    for slot in tpl["slots"]:
        m = mapping.get(slot.get(key))
        if not m:
            continue
        local_no, conf = m[0], m[1]
        note = m[2] if len(m) > 2 else ""
        extra = [n + offset for n in (m[3] if len(m) > 3 else [])]
        no = local_no + offset
        it = items.get(no)
        if not rep.check(it is not None, f"[{tray_id}] ช่อง {slot.get(key)} -> ลำดับ {no} มีใน Excel"):
            continue
        by_no.setdefault(no, []).append(slot)
        rows.append({"slot": slot, "no": no, "item": it, "confidence": conf, "note": note,
                     "extra": [items[n] for n in extra]})
        exp = expected_classes(it["name"]) if "class_key" in slot else None
        if exp:
            rep.check(slot["class_key"] in exp,
                      f"[{tray_id}] ช่อง {slot.get(key)} ประเภท '{slot['class_key']}' ตรงกับ #{no} {it['name']}",
                      level="warning")

    # every checklist item of this tray has a place
    lo = offset + 1
    hi = offset + max(v[0] for v in mapping.values())
    placed = set(by_no) | {e["no"] for r in rows for e in r["extra"]}
    skip = {int(k) for k in tray_cfg.get("not_in_tray", {})}
    missing = [n for n in range(lo, hi + 1) if n not in placed and n not in skip]
    rep.check(not missing, f"[{tray_id}] รายการ Excel ลำดับ {lo}-{hi} มีช่องวางครบ"
              + (f" (ยกเว้น {sorted(skip)} ซึ่งไม่อยู่ในถาด)" if skip else "") if not missing else
              f"[{tray_id}] รายการ Excel ที่ไม่มีช่องวาง: {missing}")
    for n, why in tray_cfg.get("not_in_tray", {}).items():
        rep.check(False, f"[{tray_id}] #{n} {items[int(n)]['name']}: {why}", level="warning")
    for r in rows:
        if r["confidence"] == "inferred":
            rep.check(False, f"[{tray_id}] ช่อง {r['slot'].get(key)} -> #{r['no']} {r['item']['name']} "
                             f"เป็นการอนุมาน: {r['note']}", level="warning")
        if r["extra"]:
            rep.check(False, f"[{tray_id}] ช่อง {r['slot'].get(key)} วางมากกว่า 1 รายการ: "
                             + ", ".join(f"#{e['no']} {e['name']}" for e in [r['item']] + r['extra'])
                             + " (ถ้าหายชิ้นเดียว ระบบจะยังเห็นช่องไม่ว่าง)", level="warning")
    if tray_id == "box1-template01_70-item":
        check_size_order(rep, tray_id, by_no, W, H)
        for r in rows:
            length, area = slot_size(r["slot"], W, H)
            if area < 600:
                rep.check(False, f"[{tray_id}] ช่อง {r['slot'].get(key)} (#{r['no']}) polygon เล็กผิดปกติ "
                                 f"{area:.0f} px² อาจตรวจจับไม่ได้ ควร annotate ใหม่", level="warning")

    # new slot values
    changed = 0
    for r in rows:
        s, it = r["slot"], r["item"]
        if tray_cfg["sheet"] == "special_new_31":
            code = data_codes.get(r["no"], it["part_number"])
        else:
            code = it["part_number"]
        new = {"name": it["name"], "part_number": it["part_number"], "code": code,
               "filename": f"{code}.png", "checklist_no": r["no"],
               "checklist_sheet": sheets[tray_cfg["sheet"]]["sheet_name"],
               "match_confidence": r["confidence"]}
        if r["note"]:
            new["match_note"] = r["note"]
        if r["extra"]:
            new["extra_items"] = [{"checklist_no": e["no"], "part_number": e["part_number"], "name": e["name"]}
                                  for e in r["extra"]]
        r["old_name"] = s.get("name")
        if norm(s.get("name")) != norm(it["name"]):
            changed += 1
        r["new"] = new
    return tpl, tpl_path, rows, changed


def apply_rows(tpl, rows, key):
    by_key = {r["slot"].get(key): r["new"] for r in rows}
    for lst in ("slots", "tools"):
        for s in tpl.get(lst, []):
            new = by_key.get(s.get(key))
            if new:
                for k in ("match_note", "extra_items"):
                    s.pop(k, None)
                s.update(new)


def draw_check_image(tpl, rows, key, out_path, photo_dir=None):
    ref = ROOT / tpl["reference_image"]
    if photo_dir:
        # e.g. dataYamaha/Merchecklist/Tools/tian/<tray_id>_number.png - easier to compare by eye
        photo = Path(photo_dir) / f"{tpl['tray_id']}_number.png"
        ref = photo if photo.exists() else ref
    W, H = tpl["image_width"], tpl["image_height"]
    im = Image.open(ref).convert("RGB").resize((W, H))
    dr = ImageDraw.Draw(im)
    fs = max(14, W // 75)
    try:
        font = ImageFont.truetype("arialbd.ttf", fs)
    except OSError:
        font = ImageFont.load_default()
    colors = {"labeled": (60, 220, 90), "set_part": (0, 200, 255), "inferred": (255, 150, 0)}
    for r in rows:
        s = r["slot"]
        col = colors.get(r["confidence"], (255, 0, 0))
        poly = [tuple(p) for p in s.get("polygon", [])]
        if len(poly) > 2:
            dr.polygon(poly, outline=col, width=max(2, W // 600))
        b = s["bbox_norm"]
        cx, cy = (b[0] + b[2]) / 2 * W, (b[1] + b[3]) / 2 * H
        tag = str(r["no"]) + ("".join(f"+{e['no']}" for e in r["extra"]))
        dr.text((cx, cy), tag, fill=col, font=font, anchor="mm", stroke_width=max(2, fs // 6), stroke_fill=(0, 0, 0))
    im.save(out_path, quality=90)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the matched names into the templates")
    ap.add_argument("--photos", help="folder with <tray_id>_number.png photos to draw the check images on")
    args = ap.parse_args()

    checklist = load(CHECKLIST_PATH)
    sheets = {s["key"]: s for s in checklist["sheets"]}
    mapping = load(CHECKLIST_MAPPING_PATH)
    data_codes = {i: d["code"] for i, d in special_catalog().items()}

    rep = Report()
    check_excel(rep, sheets)
    check_catalogs(rep, sheets)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    table, results = [], []
    for cfg in mapping["trays"]:
        tpl, path, rows, changed = build_tray(rep, cfg, sheets, data_codes)
        key = cfg["slot_key"]
        results.append((cfg, tpl, path, rows))
        draw_check_image(tpl, rows, key, OUT_DIR / f"{cfg['tray_id']}_matched.jpg", args.photos)
        print(f"{cfg['tray_id']}: {len(rows)} ช่อง, ชื่อเปลี่ยน {changed} ช่อง")
        for r in sorted(rows, key=lambda r: (r["no"], str(r["slot"].get(key)))):
            table.append({"tray": cfg["tray_id"], "slot": r["slot"].get(key), "slot_number": r["slot"]["slot_number"],
                          "checklist_no": r["no"], "part_number": r["item"]["part_number"], "name": r["item"]["name"],
                          "extra": [e["no"] for e in r["extra"]], "confidence": r["confidence"],
                          "note": r["note"], "old_name": r["old_name"],
                          "name_changed": norm(r["old_name"]) != norm(r["item"]["name"])})

    report = {"errors": rep.errors, "warnings": rep.warnings, "passed": rep.passed, "matches": table}
    (OUT_DIR / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nผ่าน {len(rep.passed)} | คำเตือน {len(rep.warnings)} | ผิดพลาด {len(rep.errors)}")
    for e in rep.errors:
        print("  ERROR:", e)
    for w in rep.warnings:
        print("  WARN :", w)

    if args.apply:
        if rep.errors:
            print("\nมีข้อผิดพลาด ไม่บันทึกลง template")
            sys.exit(1)
        for cfg, tpl, path, rows in results:
            apply_rows(tpl, rows, cfg["slot_key"])
            path.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
            print("บันทึก", path.relative_to(ROOT))
    sys.exit(1 if rep.errors else 0)


if __name__ == "__main__":
    main()
