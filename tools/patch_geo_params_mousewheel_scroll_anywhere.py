# tools/patch_geo_params_mousewheel_scroll_anywhere.py
# Enable mousewheel scrolling over the whole "Параметры GEO" dialog area (not only the scrollbar).
#
# This patch inserts a small binding block inside GeoCanvasEditor._prompt_geo_build_params()
# right before the 'row_vars = []' line (after canvas/table creation).
#
# Usage:
#   cd /d C:\ZondEditor_run
#   py tools\patch_geo_params_mousewheel_scroll_anywhere.py
#
# It will create backup: src\zondeditor\ui\editor.py.bak_geo_mw

from __future__ import annotations
from pathlib import Path
import re

TARGET = Path(__file__).resolve().parents[1] / "src" / "zondeditor" / "ui" / "editor.py"

FUNC_DEF_RE = re.compile(r'^\s*def\s+_prompt_geo_build_params\s*\(', re.M)
ROW_VARS_RE = re.compile(r'^\s*row_vars\s*=\s*\[\]', re.M)

def _indent_of(line: str) -> str:
    return line[:len(line) - len(line.lstrip(' '))]

def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"editor.py not found: {TARGET}")

    src = TARGET.read_text(encoding="utf-8", errors="replace")

    mfunc = FUNC_DEF_RE.search(src)
    if not mfunc:
        raise SystemExit("Could not find def _prompt_geo_build_params(...).")

    # Limit search to a reasonable window after function start
    start = mfunc.start()
    window = src[start:start + 60000]

    mrow = ROW_VARS_RE.search(window)
    if not mrow:
        raise SystemExit("Could not find 'row_vars = []' inside _prompt_geo_build_params().")

    # Prevent double-apply
    if "patch_geo_params_mousewheel_scroll_anywhere" in window:
        print("Already patched.")
        return

    # Determine indentation at the 'row_vars' line
    row_line_start = start + mrow.start()
    # get full line containing row_vars
    line_start = src.rfind("\n", 0, row_line_start) + 1
    line_end = src.find("\n", row_line_start)
    if line_end == -1:
        line_end = len(src)
    row_line = src[line_start:line_end]
    ind = _indent_of(row_line)

    block = (
        f"{ind}# patch_geo_params_mousewheel_scroll_anywhere\n"
        f"{ind}# Колесо мыши/тачпад прокручивает список по всему окну диалога, а не только по скроллбару.\n"
        f"{ind}def _geo_mw_scroll_units(delta: int):\n"
        f"{ind}    try:\n"
        f"{ind}        canvas.yview_scroll(delta, 'units')\n"
        f"{ind}    except Exception:\n"
        f"{ind}        pass\n"
        f"{ind}    return 'break'\n"
        f"{ind}def _geo_mw_on_wheel(ev):\n"
        f"{ind}    d = getattr(ev, 'delta', 0)\n"
        f"{ind}    if d == 0:\n"
        f"{ind}        return 'break'\n"
        f"{ind}    return _geo_mw_scroll_units(int(-1 * (d / 120)))\n"
        f"{ind}def _geo_mw_on_up(_ev):\n"
        f"{ind}    return _geo_mw_scroll_units(-1)\n"
        f"{ind}def _geo_mw_on_down(_ev):\n"
        f"{ind}    return _geo_mw_scroll_units(1)\n"
        f"{ind}def _geo_mw_bind_all(w):\n"
        f"{ind}    try:\n"
        f"{ind}        w.bind('<MouseWheel>', _geo_mw_on_wheel, add='+')\n"
        f"{ind}        w.bind('<Button-4>', _geo_mw_on_up, add='+')\n"
        f"{ind}        w.bind('<Button-5>', _geo_mw_on_down, add='+')\n"
        f"{ind}    except Exception:\n"
        f"{ind}        pass\n"
        f"{ind}    try:\n"
        f"{ind}        for ch in w.winfo_children():\n"
        f"{ind}            _geo_mw_bind_all(ch)\n"
        f"{ind}    except Exception:\n"
        f"{ind}        pass\n"
        f"{ind}_geo_mw_bind_all(dlg)\n\n"
    )

    new_src = src[:line_start] + block + src[line_start:]

    backup = TARGET.with_suffix('.py.bak_geo_mw')
    backup.write_text(src, encoding='utf-8')
    TARGET.write_text(new_src, encoding='utf-8')
    print("OK: mousewheel bindings inserted for GEO params dialog.")
    print(f"Backup saved as: {backup}")

if __name__ == "__main__":
    main()
