from __future__ import annotations

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

# Backward-compatible alias used in editor.py
from src.zondeditor.licensing.check import check_license_or_exit as _check_license_or_exit

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
