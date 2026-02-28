from __future__ import annotations

import re

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
    """Tk validatecommand: allow empty or non-negative float (with dot/comma)."""
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

# Backward-compatible alias used by editor.py
from src.zondeditor.licensing.check import check_license_or_exit as _check_license_or_exit

# ---- parsing helpers (extracted from monolith) ----
def _parse_depth_float(s: str) -> float:
    """Parse depth string safely.
    Accepts comma or dot. Returns 0.0 for empty/invalid.
    """
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
    """Try parse date/time string used for ordering tests.
    Returns datetime or None. Supports common formats used in GEO.
    """
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
# -----------------------------------------------

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

def _validate_tid_key(P: str) -> bool:
    """Validate 'test id' / experience number input in header editor.
    Allows empty, digits, and short tokens like '1', '01', '1a', '1A', '12-1'.
    """
    if P is None:
        return True
    s = str(P).strip()
    if s == "":
        return True
    # allow digits, latin letters, dash/underscore
    return re.fullmatch(r"[0-9A-Za-z_-]{1,12}", s) is not None

def _validate_depth_0_4_key(P: str) -> bool:
    """Lenient depth validator while typing.
    Allows empty, digits, dot/comma and partial floats.
    Final step=0.4 enforcement should be applied on OK/apply, not per keystroke.
    """
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

def _parse_cell_int(v):
    """Parse cell value to int; supports None/''/str/float. Returns None if not parseable."""
    if v is None:
        return None
    try:
        s = str(v).strip()
    except Exception:
        return None
    if s == "":
        return None
    s = s.replace(",", ".")
    try:
        return int(float(s))
    except Exception:
        return None

def _max_zero_run(seq) -> int:
    """Return maximum length of consecutive zeros in a numeric sequence."""
    best = 0
    cur = 0
    for v in seq or []:
        try:
            vv = int(v)
        except Exception:
            try:
                vv = int(float(str(v).replace(',', '.')))
            except Exception:
                vv = 0
        if vv == 0:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best

def _noise_around(v, rel=0.05, abs_min=1):
    """Return small random-ish perturbation around value v.
    Used by fix_by_algorithm interpolation to avoid perfectly flat repeats.
    rel: relative amplitude, abs_min: minimum amplitude in raw units.
    """
    try:
        import random
        x = float(v)
    except Exception:
        return v
    amp = max(abs(x) * float(rel), float(abs_min))
    return x + (random.random() * 2.0 - 1.0) * amp

def _interp_with_noise(a, b, t=0.5, rel=0.02, abs_min=1):
    """Linear interpolation between a and b at fraction t, with tiny noise.
    Used by fix_by_algorithm to avoid identical flats.
    """
    try:
        aa = float(a)
        bb = float(b)
        tt = float(t)
        x = aa + (bb - aa) * tt
    except Exception:
        x = a
    try:
        return _noise_around(x, rel=rel, abs_min=abs_min)
    except Exception:
        return x

