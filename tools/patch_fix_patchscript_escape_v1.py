# -*- coding: utf-8 -*-
r"""
Patch: remove SyntaxWarning invalid escape sequence (\p) in patch scripts by fixing backslashes in docstrings.

Usage (from repo root):
  py tools\patch_fix_patchscript_escape_v1.py

Edits:
- tools/patch_ribbon_ttk_font_v1.py
- tools/patch_tk_vars_master_v1.py
Creates .bak next to each edited file.
"""
from __future__ import annotations

import os
import shutil


FILES = [
    os.path.join("tools", "patch_ribbon_ttk_font_v1.py"),
    os.path.join("tools", "patch_tk_vars_master_v1.py"),
]


def _fix_docstring_backslashes(text: str) -> str:
    """
    Minimal safe fix:
    - turn occurrences of: py tools\something.py
      into:             py tools\\something.py
    Only touches literal 'py tools\' patterns.
    """
    return text.replace("py tools\\", "py tools\\\\")


def main() -> None:
    changed_any = False

    for path in FILES:
        if not os.path.exists(path):
            continue

        with open(path, "r", encoding="utf-8") as f:
            s = f.read()

        s2 = _fix_docstring_backslashes(s)
        if s2 == s:
            continue

        bak = path + ".bak"
        shutil.copy2(path, bak)

        with open(path, "w", encoding="utf-8") as f:
            f.write(s2)

        print(f"[OK] Patched: {path}")
        print(f"[OK] Backup : {bak}")
        changed_any = True

    if not changed_any:
        print("[OK] Nothing to patch.")


if __name__ == "__main__":
    main()
