# tools/patch_restore_cell_edit_validators.py
# Restores missing cell-edit validators used by _begin_edit/_end_edit:
#   _validate_int_0_300_key, _sanitize_int_0_300
#
# Usage:
#   cd /d C:\ZondEditor_run
#   py tools\patch_restore_cell_edit_validators.py
#
# Backup: src\zondeditor\ui\editor.py.bak_validators

from __future__ import annotations
from pathlib import Path
import re

TARGET = Path(__file__).resolve().parents[1] / "src" / "zondeditor" / "ui" / "editor.py"

VALIDATOR_DEF = r'''
def _validate_int_0_300_key(p: str) -> bool:
    """Tk validatecommand: allow empty while typing; otherwise int in [0, 300]."""
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
    """Normalize entry value to a safe int string in [0, 300]. Empty -> '' (caller decides)."""
    if s is None:
        return ""
    s = str(s).strip()
    if s == "":
        return ""
    # keep only leading signless digits
    if not s.isdigit():
        # try to extract digits
        m = re.search(r"(\d+)", s)
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
'''.lstrip("\n")

def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"editor.py not found: {TARGET}")

    src = TARGET.read_text(encoding="utf-8", errors="replace")

    if "_validate_int_0_300_key" in src and "_sanitize_int_0_300" in src:
        print("Already present. No changes.")
        return

    # Prefer to insert near existing validators (depth validator), else near top (after imports).
    insert_pos = None

    m = re.search(r"^def\s+_validate_depth_0_4_key\s*\(", src, flags=re.M)
    if m:
        insert_pos = m.start()
    else:
        # after last import block
        imports_end = 0
        for m2 in re.finditer(r"^(from\s+\S+\s+import\s+\S+|import\s+\S+).*?$", src, flags=re.M):
            imports_end = m2.end()
        insert_pos = imports_end

    new_src = src[:insert_pos] + "\n" + VALIDATOR_DEF + "\n" + src[insert_pos:]

    backup = TARGET.with_suffix(".py.bak_validators")
    backup.write_text(src, encoding="utf-8")
    TARGET.write_text(new_src, encoding="utf-8")
    print("OK: validators restored.")
    print(f"Backup saved as: {backup}")

if __name__ == "__main__":
    main()
