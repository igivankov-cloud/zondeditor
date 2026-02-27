# tools/patch_editor_gui_colors.py
# Hotfix: add missing GUI_* color constants (GUI_PURPLE etc.) used by UI legend/highlights.
#
# Run:
#   py tools\patch_editor_gui_colors.py
#
# Backup: editor.py.bak_colors

from __future__ import annotations
from pathlib import Path
import re

EDITOR = Path("src") / "zondeditor" / "ui" / "editor.py"

COLORS = """
# ---- UI colors (defaults) ----
GUI_RED = "#ff3b30"
GUI_ORANGE = "#ff9500"
GUI_YELLOW = "#ffd60a"
GUI_BLUE = "#007aff"
GUI_PURPLE = "#af52de"
GUI_GREEN = "#34c759"
GUI_GRAY = "#8e8e93"
# ------------------------------
"""

def main() -> None:
    if not EDITOR.exists():
        raise SystemExit("[FAIL] editor.py not found")
    txt = EDITOR.read_text(encoding="utf-8", errors="replace")

    if re.search(r"^GUI_PURPLE\s*=", txt, flags=re.M):
        print("[OK] GUI_* colors already defined.")
        return

    bak = EDITOR.with_suffix(EDITOR.suffix + ".bak_colors")
    bak.write_text(txt, encoding="utf-8")

    idx = txt.find("class GeoCanvasEditor")
    if idx < 0:
        raise SystemExit("[FAIL] class GeoCanvasEditor not found")

    head = txt[:idx]
    body = txt[idx:]
    EDITOR.write_text(head + "\n" + COLORS + "\n" + body, encoding="utf-8")
    print("[OK] inserted GUI color constants (backup:", bak.name, ")")

if __name__ == "__main__":
    main()
