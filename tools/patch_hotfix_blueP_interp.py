# tools/patch_hotfix_blueP_interp.py
from __future__ import annotations
from pathlib import Path
import re

CONSTS = Path("src") / "zondeditor" / "ui" / "consts.py"
HELPERS = Path("src") / "zondeditor" / "ui" / "helpers.py"
EDITOR  = Path("src") / "zondeditor" / "ui" / "editor.py"

def backup(path: Path, suffix: str) -> None:
    bak = path.with_suffix(path.suffix + suffix)
    bak.write_bytes(path.read_bytes())

def ensure_const(name: str, base: str) -> int:
    txt = CONSTS.read_text(encoding="utf-8", errors="replace")
    if re.search(rf"^%s\s*=" % re.escape(name), txt, flags=re.M):
        return 0
    backup(CONSTS, f".bak_{name}")
    add = f"\n{name} = {base}  # preview mode color\n"
    CONSTS.write_text(txt.rstrip() + add + "\n", encoding="utf-8")
    return 1

def patch_consts() -> int:
    if not CONSTS.exists():
        raise SystemExit("[FAIL] consts.py not found")
    changed = 0
    # define GUI_BLUE_P aliasing GUI_BLUE
    # (same pattern as GUI_ORANGE_P we already added)
    changed += ensure_const("GUI_BLUE_P", "GUI_BLUE")
    return changed

def patch_helpers_interp() -> int:
    txt = HELPERS.read_text(encoding="utf-8", errors="replace")
    if re.search(r"^def\s+_interp_with_noise\s*\(", txt, flags=re.M):
        return 0
    backup(HELPERS, ".bak_interp")
    add = (
        "\n\n"
        "def _interp_with_noise(a, b, t=0.5, rel=0.02, abs_min=1):\n"
        "    \"\"\"Linear interpolation between a and b at fraction t, with tiny noise.\n"
        "    Used by fix_by_algorithm to avoid identical flats.\n"
        "    \"\"\"\n"
        "    try:\n"
        "        aa = float(a)\n"
        "        bb = float(b)\n"
        "        tt = float(t)\n"
        "        x = aa + (bb - aa) * tt\n"
        "    except Exception:\n"
        "        x = a\n"
        "    try:\n"
        "        return _noise_around(x, rel=rel, abs_min=abs_min)\n"
        "    except Exception:\n"
        "        return x\n"
    )
    HELPERS.write_text(txt.rstrip() + add + "\n", encoding="utf-8")
    return 1

def patch_editor_imports() -> int:
    txt = EDITOR.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^from\s+src\.zondeditor\.ui\.helpers\s+import\s+(.+)$", txt, flags=re.M)
    if not m:
        raise SystemExit("[FAIL] helpers import line not found in editor.py")
    line = m.group(0)
    need = []
    if "_interp_with_noise" not in line:
        need.append("_interp_with_noise")
    # also ensure GUI_BLUE_P imported from consts? editor imports consts with '*', so ok.
    if not need:
        return 0
    backup(EDITOR, ".bak_interp")
    txt2 = txt.replace(line, line + ", " + ", ".join(need), 1)
    EDITOR.write_text(txt2, encoding="utf-8")
    return 1

def main() -> None:
    if not (CONSTS.exists() and HELPERS.exists() and EDITOR.exists()):
        raise SystemExit("[FAIL] missing expected files")
    a = patch_consts()
    b = patch_helpers_interp()
    c = patch_editor_imports()
    print(f"[OK] patched: consts={a}, helpers_interp={b}, editor_imports={c}")

if __name__ == "__main__":
    main()
