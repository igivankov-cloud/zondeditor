# tools/patch_step15_save_geo_v2.py
# Safe patcher: restores monolith from .bak_step15 (if exists) and applies minimal, indentation-safe edits.
#
# Run in project root:
#   py tools\patch_step15_save_geo_v2.py
#
# What it does:
# 1) If <monolith>.bak_step15 exists, restore it first (to undo broken patch).
# 2) Ensure import exists near top-level imports:
#      from src.zondeditor.io.geo_writer import build_k2_geo_from_template
# 3) Replace ONLY the assignment line:
#      geo_bytes = _rebuild_geo_from_template(self.original_bytes, blocks_info, prepared)
#    with:
#      geo_bytes = build_k2_geo_from_template(self.original_bytes, blocks_info, prepared)

from __future__ import annotations
from pathlib import Path

MONOLITH = Path("ZondEditor_SZ_v3_k2k4_dispatch_fix_params_step_depth_v5_nofreeze_k4fix_xlsxfix.py")
BAK = MONOLITH.with_suffix(MONOLITH.suffix + ".bak_step15")

FIND = "geo_bytes = _rebuild_geo_from_template(self.original_bytes, blocks_info, prepared)"
REPL = "geo_bytes = build_k2_geo_from_template(self.original_bytes, blocks_info, prepared)"
IMPORT_LINE = "from src.zondeditor.io.geo_writer import build_k2_geo_from_template"

def main() -> None:
    if not MONOLITH.exists():
        raise SystemExit("[FAIL] monolith not found in project root")

    # restore if backup exists
    if BAK.exists():
        MONOLITH.write_bytes(BAK.read_bytes())
        print("[OK] restored from backup:", BAK.name)

    txt = MONOLITH.read_text(encoding="utf-8", errors="replace")

    if FIND not in txt:
        raise SystemExit("[FAIL] pattern not found. Send save_file() snippet around geo_bytes assignment.")

    # ensure import line (insert after initial imports block)
    if IMPORT_LINE not in txt:
        lines = txt.splitlines()
        insert_at = 0
        # place after shebang/encoding and consecutive import/from lines at top
        for i, ln in enumerate(lines[:400]):  # top part only
            s = ln.strip()
            if s.startswith("import ") or s.startswith("from "):
                insert_at = i + 1
                continue
            # allow comments/blank lines within header
            if s == "" or s.startswith("#"):
                continue
            break
        lines.insert(insert_at, IMPORT_LINE)
        txt = "\n".join(lines) + "\n"

    # replace assignment (first occurrence)
    txt2 = txt.replace(FIND, REPL, 1)
    MONOLITH.write_text(txt2, encoding="utf-8")
    print("[OK] patched v2 successfully (no inline import).")

if __name__ == "__main__":
    main()
