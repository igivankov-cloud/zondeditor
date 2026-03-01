from __future__ import annotations
from pathlib import Path

LICENSE_PATH = Path(r"C:\ProgramData\ZondEditor\license.dat")

def check_license_or_exit(messagebox=None) -> bool:
    """Basic license check."""
    try:
        if LICENSE_PATH.exists():
            return True
    except Exception:
        pass

    msg = f"Лицензия не найдена: {LICENSE_PATH}"
    try:
        if messagebox is not None:
            messagebox.showerror("ZondEditor", msg)
    except Exception:
        pass
    raise SystemExit(msg)
