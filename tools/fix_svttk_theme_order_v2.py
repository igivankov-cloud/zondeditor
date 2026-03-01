# -*- coding: utf-8 -*-
r"""
Fix extra blank 'tk' window caused by calling sv_ttk.set_theme() before creating the main Tk root.

Your tk_guard log shows:
  src/zondeditor/app.py:31 -> sv_ttk.set_theme("light")  (creates implicit default Tk)
  then GeoCanvasEditor() creates SECOND_ROOT.

This patch:
1) Comments out ALL sv_ttk.set_theme(...) calls in src/zondeditor/app.py
2) Ensures theme is applied AFTER creating GeoCanvasEditor in src/zondeditor/ui/main_window.py

Usage (from repo root):
  py tools\fix_svttk_theme_order_v2.py

Backups:
- src/zondeditor/app.py.bak
- src/zondeditor/ui/main_window.py.bak
"""
from __future__ import annotations
import os, re, shutil, sys

APP_PATH = os.path.join("src","zondeditor","app.py")
MAIN_PATH = os.path.join("src","zondeditor","ui","main_window.py")

def _bak(path: str) -> str:
    bak = path + ".bak"
    shutil.copy2(path, bak)
    return bak

def patch_app() -> bool:
    if not os.path.exists(APP_PATH):
        print(f"[ERR] Not found: {APP_PATH}")
        return False
    s = open(APP_PATH, "r", encoding="utf-8").read()
    if "sv_ttk.set_theme" not in s:
        print("[OK] app.py: no sv_ttk.set_theme found.")
        return True

    _bak(APP_PATH)
    # Comment out any line that calls sv_ttk.set_theme(...)
    lines = s.splitlines(True)
    out = []
    changed = 0
    for ln in lines:
        if re.search(r"\bsv_ttk\.set_theme\s*\(", ln):
            # keep indentation, comment line
            indent = re.match(r"^(\s*)", ln).group(1)
            out.append(f"{indent}# [moved] {ln.lstrip()}")
            changed += 1
        else:
            out.append(ln)
    open(APP_PATH, "w", encoding="utf-8").write("".join(out))
    print(f"[OK] app.py: commented sv_ttk.set_theme calls: {changed}")
    return True

def patch_main_window() -> bool:
    if not os.path.exists(MAIN_PATH):
        print(f"[ERR] Not found: {MAIN_PATH}")
        return False
    s = open(MAIN_PATH, "r", encoding="utf-8").read()

    # If already has "app = GeoCanvasEditor()" and sv_ttk.set_theme after it, do nothing
    if re.search(r"app\s*=\s*GeoCanvasEditor\(\)", s) and "sv_ttk.set_theme" in s:
        print("[OK] main_window.py: theme already applied after root.")
        return True

    # Replace direct GeoCanvasEditor().mainloop() call with app var + theme + app.mainloop()
    pat = re.compile(r"(?m)^(\s*)GeoCanvasEditor\(\)\.mainloop\(\)\s*$")
    m = pat.search(s)
    if not m:
        print("[WARN] main_window.py: pattern GeoCanvasEditor().mainloop() not found; no change.")
        return True

    indent = m.group(1)
    repl = "\n".join([
        f"{indent}app = GeoCanvasEditor()",
        f"{indent}# Apply sv_ttk theme AFTER Tk root exists (prevents extra 'tk' window)",
        f"{indent}try:",
        f"{indent}    import sv_ttk",
        f"{indent}    sv_ttk.set_theme('light')",
        f"{indent}except Exception:",
        f"{indent}    pass",
        f"{indent}app.mainloop()",
    ])
    _bak(MAIN_PATH)
    s2 = pat.sub(repl, s, count=1)
    open(MAIN_PATH, "w", encoding="utf-8").write(s2)
    print("[OK] main_window.py: updated to apply theme after root.")
    return True

def main() -> None:
    ok = patch_app() and patch_main_window()
    if not ok:
        sys.exit(2)
    print("[DONE] Now run with guard to verify:\n  set ZONDEDITOR_TK_GUARD=1\n  py run_zondeditor.py")

if __name__ == "__main__":
    main()
