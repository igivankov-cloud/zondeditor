# tools/repair_ui_helpers_full.py
# One-shot repair for src/zondeditor/ui/helpers.py after many incremental patches.
#
# Fixes:
# - removes BOM chars (U+FEFF) anywhere
# - replaces literal "\n" sequences with real newlines
# - ensures `from __future__ import annotations` is at the top
# - ensures required helper functions exist (adds missing ones via generated block)
#
# Run:
#   py tools\repair_ui_helpers_full.py
#
# Then:
#   py tools\selfcheck.py
#   py run_zondeditor.py
#
# Backup:
#   helpers.py.bak_repair_full

from __future__ import annotations
from pathlib import Path
import re

HELPERS = Path("src") / "zondeditor" / "ui" / "helpers.py"
BOM = "\ufeff"
FUT = "from __future__ import annotations"

REQUIRED_BLOCK = r'''
# ===================== UI HELPERS (generated) =====================

def _apply_win11_style(root):
    """Best-effort Win11-ish style. Uses sv_ttk if available, otherwise no-op."""
    try:
        import sv_ttk  # type: ignore
        try:
            sv_ttk.set_theme("light")
        except Exception:
            sv_ttk.set_theme("dark")
    except Exception:
        pass

def _setup_shared_logger():
    """Minimal logger stub (dev)."""
    import logging
    logger = logging.getLogger("ZondEditor")
    if not logger.handlers:
        h = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        h.setFormatter(fmt)
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
    return logger

def _validate_nonneg_float_key(P: str) -> bool:
    """Tk validatecommand: allow empty or non-negative float (dot/comma)."""
    if P is None:
        return True
    s = str(P).strip()
    if s == "":
        return True
    s2 = s.replace(",", ".")
    if s2 == ".":
        return True
    try:
        v = float(s2)
        return v >= 0.0
    except Exception:
        return False

def _parse_depth_float(s: str) -> float:
    """Parse depth string safely. Accepts comma/dot."""
    if s is None:
        return 0.0
    t = str(s).strip()
    if t == "":
        return 0.0
    t = t.replace(",", ".")
    try:
        return float(t)
    except Exception:
        return 0.0

def _try_parse_dt(s: str):
    """Try parse date/time string used for ordering tests. Returns datetime or None."""
    import datetime as _dt
    if s is None:
        return None
    t = str(s).strip()
    if not t:
        return None
    t = t.replace("T", " ").replace("/", ".").replace("-", ".")
    fmts = [
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d.%m.%y %H:%M:%S",
        "%d.%m.%y %H:%M",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%d.%m.%Y",
        "%d.%m.%y",
    ]
    for f in fmts:
        try:
            return _dt.datetime.strptime(t, f)
        except Exception:
            pass
    return None

def _pick_icon_font(size: int = 12):
    """Pick an icon-capable font for UI glyphs (best-effort)."""
    try:
        import tkinter.font as tkfont
        for fam in ("Segoe MDL2 Assets", "Segoe UI Symbol", "Segoe UI Emoji", "Segoe UI"):
            try:
                if fam in tkfont.families():
                    return (fam, size)
            except Exception:
                continue
        return ("Segoe UI", size)
    except Exception:
        return ("Segoe UI", size)

def _format_date_ru(d):
    """Format date as DD.MM.YYYY. Accepts date/datetime/None."""
    if d is None:
        return ""
    try:
        import datetime as _dt
        if isinstance(d, _dt.datetime):
            d = d.date()
        return f"{d.day:02d}.{d.month:02d}.{d.year:04d}"
    except Exception:
        return str(d)

def _format_time_ru(t):
    """Format time as HH:MM. Accepts time/datetime/None."""
    if t is None:
        return ""
    try:
        import datetime as _dt
        if isinstance(t, _dt.datetime):
            t = t.time()
        return f"{t.hour:02d}:{t.minute:02d}"
    except Exception:
        return str(t)

def _canvas_view_bbox(cnv):
    """Return visible bbox of a tkinter Canvas in canvas coordinates."""
    try:
        vx0 = cnv.canvasx(0)
        vy0 = cnv.canvasy(0)
        vx1 = cnv.canvasx(cnv.winfo_width())
        vy1 = cnv.canvasy(cnv.winfo_height())
        return vx0, vy0, vx1, vy1
    except Exception:
        return 0, 0, 0, 0

def _validate_hh_key(P: str) -> bool:
    """Validate hour 0-23 while typing."""
    if P is None:
        return True
    s = str(P).strip()
    if s == "":
        return True
    if not s.isdigit() or len(s) > 2:
        return False
    try:
        v = int(s)
    except Exception:
        return False
    return 0 <= v <= 23

def _validate_mm_key(P: str) -> bool:
    """Validate minute 0-59 while typing."""
    if P is None:
        return True
    s = str(P).strip()
    if s == "":
        return True
    if not s.isdigit() or len(s) > 2:
        return False
    try:
        v = int(s)
    except Exception:
        return False
    return 0 <= v <= 59

def _validate_tid_key(P: str) -> bool:
    """Validate experience id token."""
    if P is None:
        return True
    s = str(P).strip()
    if s == "":
        return True
    return re.fullmatch(r"[0-9A-Za-z_-]{1,12}", s) is not None

def _validate_depth_0_4_key(P: str) -> bool:
    """Lenient depth validator while typing (do not enforce 0.4 step here)."""
    if P is None:
        return True
    s = str(P).strip()
    if s == "":
        return True
    s2 = s.replace(",", ".")
    if s2 in (".", "-", "-.", "+", "+."):
        return True
    if s2.endswith("."):
        s2 = s2[:-1]
        if s2 in ("", "-", "+"):
            return True
    try:
        float(s2)
        return True
    except Exception:
        return False

# Backward-compatible alias used by editor.py
from src.zondeditor.licensing.check import check_license_or_exit as _check_license_or_exit

# ================================================================
'''.strip() + "\n"

def ensure_future_top(txt: str) -> str:
    lines = [ln.replace(BOM, "") for ln in txt.splitlines()]
    lines = [ln for ln in lines if ln.strip() != FUT]
    ins = 0
    if lines and lines[0].startswith("#!"):
        ins = 1
    if len(lines) > ins and re.match(r"^#.*coding[:=]\s*[-\w.]+", lines[ins]):
        ins += 1
    lines.insert(ins, FUT)
    if len(lines) > ins+1 and lines[ins+1].strip() != "":
        lines.insert(ins+1, "")
    return "\n".join(lines) + "\n"

def main() -> None:
    if not HELPERS.exists():
        raise SystemExit("[FAIL] helpers.py not found")

    raw = HELPERS.read_text(encoding="utf-8", errors="replace")
    bak = HELPERS.with_suffix(HELPERS.suffix + ".bak_repair_full")
    bak.write_text(raw, encoding="utf-8")

    txt = raw.replace(BOM, "")
    txt = txt.replace("\\r\\n", "\n").replace("\\n", "\n")
    txt = ensure_future_top(txt)

    if not re.search(r"(?m)^import\s+re\s*$", txt):
        lines = txt.splitlines()
        for i, ln in enumerate(lines[:15]):
            if ln.strip() == FUT:
                insert = i + 1
                if insert < len(lines) and lines[insert].strip() != "":
                    lines.insert(insert, "")
                    insert += 1
                lines.insert(insert, "import re")
                txt = "\n".join(lines) + "\n"
                break

    if "UI HELPERS (generated)" in txt:
        txt = re.sub(r"(?ms)^# ===================== UI HELPERS \(generated\).*?# ================================================================\s*$",
                     REQUIRED_BLOCK.rstrip(),
                     txt.rstrip())
        txt = txt.rstrip() + "\n"
    else:
        txt = txt.rstrip() + "\n\n" + REQUIRED_BLOCK

    HELPERS.write_text(txt, encoding="utf-8")
    print("[OK] helpers.py repaired. backup:", bak.name)

if __name__ == "__main__":
    main()
