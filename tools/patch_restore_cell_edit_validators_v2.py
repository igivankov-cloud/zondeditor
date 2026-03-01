# tools/patch_restore_cell_edit_validators_v2.py
# Force-restore missing TOP-LEVEL validators used by _begin_edit/_end_edit.
# Fixes case where previous patch inserted strings but not real module-level defs.
#
# Usage:
#   cd /d C:\ZondEditor_run
#   py tools\patch_restore_cell_edit_validators_v2.py
#
# Backup: src\zondeditor\ui\editor.py.bak_validators2

from __future__ import annotations
from pathlib import Path
import re

TARGET = Path(__file__).resolve().parents[1] / "src" / "zondeditor" / "ui" / "editor.py"

BLOCK = """
# --- Cell edit validators (auto-restored) ---
import re as _re__cell

def _validate_int_0_300_key(p: str) -> bool:
    \"\"\"Tk validatecommand: allow empty while typing; otherwise int in [0, 300].\"\"\"
    if p is None:
        return True
    p = str(p)
    if p == "":
        return True
    if not p.isdigit():
        return False
    try:
        v = int(p)
    except Exception:
        return False
    return 0 <= v <= 300


def _sanitize_int_0_300(s: str) -> str:
    \"\"\"Normalize entry value to a safe int string in [0, 300]. Empty -> ''.\"\"\"
    if s is None:
        return ""
    s = str(s).strip()
    if s == "":
        return ""
    if not s.isdigit():
        m = _re__cell.search(r"(\\d+)", s)
        if not m:
            return ""
        s = m.group(1)
    try:
        v = int(s)
    except Exception:
        return ""
    if v < 0:
        v = 0
    if v > 300:
        v = 300
    return str(v)
"""


TOP_DEF_RE = re.compile(r"^def\s+_validate_int_0_300_key\s*\(", re.M)
CLASS_RE = re.compile(r"^class\s+GeoCanvasEditor\b", re.M)

def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"editor.py not found: {TARGET}")

    src = TARGET.read_text(encoding="utf-8", errors="replace")

    if TOP_DEF_RE.search(src):
        print("Top-level validator already exists. No changes.")
        return

    mclass = CLASS_RE.search(src)
    if not mclass:
        raise SystemExit("Could not find class GeoCanvasEditor in editor.py")

    insert_pos = mclass.start()

    new_src = src[:insert_pos] + BLOCK + src[insert_pos:]

    backup = TARGET.with_suffix(".py.bak_validators2")
    backup.write_text(src, encoding="utf-8")
    TARGET.write_text(new_src, encoding="utf-8")

    print("OK: inserted TOP-LEVEL validators before GeoCanvasEditor.")
    print(f"Backup saved as: {backup}")

if __name__ == "__main__":
    main()
