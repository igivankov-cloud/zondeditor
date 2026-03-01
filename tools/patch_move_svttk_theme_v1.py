# -*- coding: utf-8 -*-
r"""
Patch ZondEditor: move sv_ttk.set_theme("light") AFTER main Tk root creation
to eliminate extra blank "tk" window (implicit default root) and SECOND_ROOT.

Usage (from repo root):
  py tools\patch_move_svttk_theme_v1.py

Creates .bak backups next to modified files.
"""
from __future__ import annotations
import os, re, shutil, sys

APP_PATH = os.path.join("src", "zondeditor", "app.py")
MAINWIN_PATH = os.path.join("src", "zondeditor", "ui", "main_window.py")

def backup(path: str) -> str:
    bak = path + ".bak"
    shutil.copy2(path, bak)
    return bak

def patch_app() -> bool:
    if not os.path.exists(APP_PATH):
        print(f"[ERR] Not found: {APP_PATH}")
        return False
    s = open(APP_PATH, "r", encoding="utf-8").read()
    s0 = s

    # Remove explicit sv_ttk.set_theme('light') calls (keep imports if needed)
    s = re.sub(
        r"(?m)^\s*sv_ttk\.set_theme\(\s*[\"']light[\"']\s*\)\s*$",
        "    # sv_ttk.set_theme('light') moved to ui/main_window.py (after Tk root)\n",
        s,
    )

    # Remove common try/except blocks that only exist to set theme early
    s = re.sub(
        r"(?ms)^\s*try:\s*\n(?:\s+.*\n)*?\s*import\s+sv_ttk\s*\n(?:\s+.*\n)*?\s*sv_ttk\.set_theme\(\s*[\"']light[\"']\s*\)\s*\n(?:\s+.*\n)*?^\s*except\s+Exception\s*:\s*\n\s+pass\s*\n",
        "    # sv_ttk theme is applied after Tk root creation (see ui/main_window.py)\n",
        s
    )

    if s == s0:
        print("[WARN] No early sv_ttk.set_theme found in app.py (maybe already patched).")
        return True

    bak = backup(APP_PATH)
    open(APP_PATH, "w", encoding="utf-8").write(s)
    print("[OK] Patched app.py (removed early sv_ttk theme set)")
    print(f"[OK] Backup: {bak}")
    return True

def patch_main_window() -> bool:
    if not os.path.exists(MAINWIN_PATH):
        print(f"[ERR] Not found: {MAINWIN_PATH}")
        return False
    s = open(MAINWIN_PATH, "r", encoding="utf-8").read()

    pat = re.compile(r"(?m)^(\s*)GeoCanvasEditor\(\)\.mainloop\(\)\s*$")
    m = pat.search(s)
    if not m:
        print("[WARN] No 'GeoCanvasEditor().mainloop()' line found (maybe already patched).")
        return True

    indent = m.group(1)
    replacement = "\n".join([
        f"{indent}app = GeoCanvasEditor()",
        f"{indent}# Apply sv_ttk theme AFTER Tk root exists (prevents extra 'tk' window)",
        f"{indent}try:",
        f"{indent}    import sv_ttk",
        f"{indent}    sv_ttk.set_theme('light')",
        f"{indent}except Exception:",
        f"{indent}    pass",
        f"{indent}app.mainloop()",
    ])
    s2 = pat.sub(replacement, s, count=1)
    if s2 == s:
        print("[WARN] main_window.py unchanged (unexpected).")
        return True

    bak = backup(MAINWIN_PATH)
    open(MAINWIN_PATH, "w", encoding="utf-8").write(s2)
    print("[OK] Patched main_window.py (theme applied after root)")
    print(f"[OK] Backup: {bak}")
    return True

def main() -> None:
    ok = patch_app() and patch_main_window()
    if not ok:
        sys.exit(2)

if __name__ == "__main__":
    main()
