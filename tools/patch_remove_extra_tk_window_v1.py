# -*- coding: utf-8 -*-
r"""
Patch ZondEditor: remove extra blank "tk" window on startup.

Symptom:
- A second empty window titled "tk" appears when the app starts.

Most common cause:
- Some helper creates a second root window via tk.Tk() (often inside _pick_icon_font).

Fix strategy (safe for Win7/10/11):
- Rework _pick_icon_font in src/zondeditor/ui/ribbon.py to NEVER create tk.Tk().
- Make it accept a parent (existing root) and create font objects with master=parent.
- Update the caller in editor.py to pass self.

Usage (from repo root):
  py tools\patch_remove_extra_tk_window_v1.py

Edits (in place) and writes .bak backups:
- src/zondeditor/ui/ribbon.py
- src/zondeditor/ui/editor.py
"""
from __future__ import annotations

import os
import re
import shutil
import sys

RIBBON_PATH = os.path.join("src", "zondeditor", "ui", "ribbon.py")
EDITOR_PATH = os.path.join("src", "zondeditor", "ui", "editor.py")

NEW_PICK_ICON_FONT = r"""
def _pick_icon_font(parent, size: int = 11):
    \"\"\"
    Pick an icon font without creating any extra Tk() root.
    Works on Windows 7/10/11.

    Returns:
      tkinter.font.Font instance (preferred), or a (family, size) tuple fallback.
    \"\"\"
    try:
        import tkinter.font as tkfont
    except Exception:
        return ("Segoe UI Symbol", size)

    candidates = [
        "Segoe Fluent Icons",      # Win11+
        "Segoe MDL2 Assets",       # Win10
        "Segoe UI Symbol",         # Win7/10/11
        "Arial",
    ]

    master = parent
    for fam in candidates:
        try:
            f = tkfont.Font(master=master, family=fam, size=size)
            if f.actual().get("family"):
                return f
        except Exception:
            continue

    return ("Segoe UI Symbol", size)
""".lstrip()


def _backup(path: str) -> str:
    bak = path + ".bak"
    shutil.copy2(path, bak)
    return bak


def patch_ribbon() -> bool:
    if not os.path.exists(RIBBON_PATH):
        print(f"[ERR] Not found: {RIBBON_PATH}")
        return False

    with open(RIBBON_PATH, "r", encoding="utf-8") as f:
        s = f.read()

    m = re.search(r"^def\\s+_pick_icon_font\\s*\\(.*?\\):\\s*\\n", s, flags=re.M)
    if not m:
        print("[ERR] _pick_icon_font not found in ribbon.py")
        return False

    start = m.start()
    # end at next top-level def/class or EOF
    m2 = re.search(r"^(def|class)\\s+\\w+", s[m.end():], flags=re.M)
    end = len(s) if not m2 else (m.end() + m2.start())

    bak = _backup(RIBBON_PATH)
    s2 = s[:start] + NEW_PICK_ICON_FONT + "\n\n" + s[end:].lstrip()

    with open(RIBBON_PATH, "w", encoding="utf-8") as f:
        f.write(s2)

    print("[OK] Patched ribbon.py: _pick_icon_font(parent, size) without tk.Tk()")
    print(f"[OK] Backup: {bak}")
    return True


def patch_editor() -> bool:
    if not os.path.exists(EDITOR_PATH):
        print(f"[ERR] Not found: {EDITOR_PATH}")
        return False

    with open(EDITOR_PATH, "r", encoding="utf-8") as f:
        s = f.read()

    pat = re.compile(r"_pick_icon_font\\(\\s*(\\d+)\\s*\\)")
    if not pat.search(s):
        print("[WARN] No _pick_icon_font(<n>) call found in editor.py (maybe already patched).")
        return True

    bak = _backup(EDITOR_PATH)
    s2 = pat.sub(r"_pick_icon_font(self, \\1)", s)

    with open(EDITOR_PATH, "w", encoding="utf-8") as f:
        f.write(s2)

    print("[OK] Patched editor.py: pass self into _pick_icon_font(self, n)")
    print(f"[OK] Backup: {bak}")
    return True


def main() -> None:
    ok1 = patch_ribbon()
    ok2 = patch_editor()
    if not (ok1 and ok2):
        sys.exit(2)


if __name__ == "__main__":
    main()
