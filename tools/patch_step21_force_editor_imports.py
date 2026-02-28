# tools/patch_step21_force_editor_imports.py
# Ensure editor.py has required UI helper imports at top-level (not inside try/except).
#
# Fixes NameError like _apply_win11_style not defined by inserting explicit imports
# right before class GeoCanvasEditor and removing any broken/indented import block.
#
# Run:
#   py tools\patch_step21_force_editor_imports.py
#
# Backup:
#   src/zondeditor/ui/editor.py.bak_force_imports

from __future__ import annotations
from pathlib import Path
import re

EDITOR = Path("src") / "zondeditor" / "ui" / "editor.py"

IMPORT_BLOCK = """# --- UPG UI imports (Step21 hotfix) ---
from src.zondeditor.ui.consts import APP_TITLE, APP_VERSION, DEFAULT_GEO_KIND, GUI_RED, GUI_ORANGE, GUI_YELLOW, GUI_BLUE, GUI_PURPLE, GUI_GREEN, GUI_GRAY
from src.zondeditor.ui.helpers import _apply_win11_style, _setup_shared_logger, _validate_nonneg_float_key, _check_license_or_exit
from src.zondeditor.ui.widgets import ToolTip
# --- end ---
"""

def main() -> None:
    if not EDITOR.exists():
        raise SystemExit("[FAIL] editor.py not found")

    txt = EDITOR.read_text(encoding="utf-8", errors="replace")
    idx = txt.find("class GeoCanvasEditor")
    if idx < 0:
        raise SystemExit("[FAIL] class GeoCanvasEditor not found")

    head = txt[:idx]
    body = txt[idx:]

    bak = EDITOR.with_suffix(EDITOR.suffix + ".bak_force_imports")
    bak.write_text(txt, encoding="utf-8")

    # Remove any previous import attempts for these modules (to avoid duplicates / inside try blocks)
    head = re.sub(r"(?m)^\s*from\s+src\.zondeditor\.ui\.consts\s+import\s+\*.*\n", "", head)
    head = re.sub(r"(?m)^\s*from\s+src\.zondeditor\.ui\.helpers\s+import\s+\*.*\n", "", head)
    head = re.sub(r"(?m)^\s*from\s+src\.zondeditor\.ui\.widgets\s+import\s+ToolTip.*\n", "", head)

    # Also remove any commented markers from previous hotfix
    head = re.sub(r"(?ms)^# --- UPG UI imports.*?# --- end ---\n", "", head)

    # Insert import block at top-level near end of head
    head = head.rstrip() + "\n\n" + IMPORT_BLOCK + "\n"

    EDITOR.write_text(head + body, encoding="utf-8")
    print("[OK] inserted explicit UI imports block.")
    print("[OK] backup:", bak.name)

if __name__ == "__main__":
    main()
