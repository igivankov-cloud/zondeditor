# tools/patch_step16_ui_exports.py
# Patch monolith to route Excel/CREDO/GXL exports through src/zondeditor/export modules.
#
# Run in project root:
#   py tools\patch_step16_ui_exports.py
#
# Creates backup: <monolith>.bak_step16
#
# Patches (best-effort, safe):
# - Adds imports near top-level imports if missing:
#     from src.zondeditor.export.excel_export import export_excel
#     from src.zondeditor.export.credo_zip import export_credo_zip
#     from src.zondeditor.export.gxl_export import export_gxl_generated
# - Tries to replace calls to the old local functions (if present) with module calls.
#
# If a pattern is not found, the script prints a warning and leaves that part unchanged.

from __future__ import annotations
from pathlib import Path

MONOLITH = Path("ZondEditor_SZ_v3_k2k4_dispatch_fix_params_step_depth_v5_nofreeze_k4fix_xlsxfix.py")
BAK = MONOLITH.with_suffix(MONOLITH.suffix + ".bak_step16")

IMPORTS = [
    "from src.zondeditor.export.excel_export import export_excel",
    "from src.zondeditor.export.credo_zip import export_credo_zip",
    "from src.zondeditor.export.gxl_export import export_gxl_generated",
]

REPLS = [
    # Excel: old maybe _export_excel_xlsx(...) or save_excel_generated(...)
    ("save_excel_generated(", "export_excel("),
    ("_export_excel_xlsx(", "export_excel("),

    # CREDO ZIP: old maybe save_credo_zip(...) or _export_credo_zip(...)
    ("save_credo_zip(", "export_credo_zip("),
    ("_export_credo_zip(", "export_credo_zip("),

    # GXL generator: old maybe save_gxl_generated(...)
    ("save_gxl_generated(", "export_gxl_generated("),
]

def _ensure_imports(txt: str) -> str:
    if all(imp in txt for imp in IMPORTS):
        return txt
    lines = txt.splitlines()
    insert_at = 0
    for i, ln in enumerate(lines[:600]):
        s = ln.strip()
        if s.startswith("import ") or s.startswith("from "):
            insert_at = i + 1
            continue
        if s == "" or s.startswith("#"):
            continue
        break
    # insert missing imports
    for imp in IMPORTS:
        if imp not in txt:
            lines.insert(insert_at, imp)
            insert_at += 1
    return "\n".join(lines) + "\n"

def main() -> None:
    if not MONOLITH.exists():
        raise SystemExit("[FAIL] monolith not found in project root")

    txt = MONOLITH.read_text(encoding="utf-8", errors="replace")
    BAK.write_text(txt, encoding="utf-8")

    txt2 = _ensure_imports(txt)

    changed = 0
    for a, b in REPLS:
        if a in txt2:
            txt2 = txt2.replace(a, b)
            changed += 1

    MONOLITH.write_text(txt2, encoding="utf-8")

    print("[OK] step16 patch applied. Backup:", BAK.name)
    print("[INFO] replacements made:", changed)
    if changed == 0:
        print("[WARN] No known call-patterns found. Your monolith may use different function names.")
        print("[WARN] If exports still work, you can ignore this; otherwise send me the export button handlers.")

if __name__ == "__main__":
    main()
