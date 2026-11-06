# Legacy scripts

Kept for reference only. They were written for the first tray layout (`TRAY_YA_1_2`) or
one-off checks, use paths relative to the project root, and are not maintained.

| Script | What it did | Why it is here |
|---|---|---|
| `generate_standard_template.py` | Built the `TRAY_YA_1_2` template, sketch and reference | Tray replaced by `box1-template01_70-item`; overwrites `data/classes_ya1_2_70_tools.json` (disabled) |
| `import_new_tray_template.py` | Same as above from a polygon dump | Same (disabled) |
| `build_tray_70_json.py` | Built `TRAY_YA_1_2.json` and the 70-tool class list | Same (disabled) |
| `build_template02_16_item.py` | Built the 16-item template from an upload in `.gemini/...` | Source folder is gone; it would overwrite `data/tray_refs/box1-template02_16-item.jpg` with an annotated image (disabled) |
| `check_coords.py` | Printed hard-coded polygons for checking | One-off |
| `debug.py` | Listed the files in the master data folder | One-off |

The four disabled scripts exit unless you pass `--i-know-this-overwrites-data`.
Current tray data is built with `scripts/build/` (see the main README).
