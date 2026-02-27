# src/zondeditor/ui/main_window.py
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

MONOLITH_FILE = "ZondEditor_SZ_v3_k2k4_dispatch_fix_params_step_depth_v5_nofreeze_k4fix_xlsxfix.py"
MONOLITH_MODNAME = "zondeditor_monolith"

def _project_root() -> Path:
    # .../src/zondeditor/ui/main_window.py -> parents:
    # 0 ui, 1 zondeditor, 2 src, 3 <project root>
    return Path(__file__).resolve().parents[3]

def _load_monolith(root: Path) -> ModuleType:
    path = root / MONOLITH_FILE
    if not path.exists():
        raise FileNotFoundError(f"Monolith not found: {path}")

    if MONOLITH_MODNAME in sys.modules:
        return sys.modules[MONOLITH_MODNAME]

    spec = importlib.util.spec_from_file_location(MONOLITH_MODNAME, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for {path}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules[MONOLITH_MODNAME] = mod
    spec.loader.exec_module(mod)
    return mod

def main() -> None:
    """Start UI (modular entrypoint)."""
    root = _project_root()
    mod = _load_monolith(root)

    AppCls = getattr(mod, "GeoCanvasEditor", None)
    if AppCls is None:
        raise AttributeError("GeoCanvasEditor not found in monolith")

    AppCls().mainloop()

if __name__ == "__main__":
    main()
