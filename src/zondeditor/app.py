# src/zondeditor/app.py
# Entrypoint that keeps the project runnable during refactor:
# it executes the current working monolith with runpy.

from __future__ import annotations

import runpy
from pathlib import Path

MONOLITH = "ZondEditor_SZ_v3_k2k4_dispatch_fix_params_step_depth_v5_nofreeze_k4fix_xlsxfix.py"

def main() -> None:
    root = Path(__file__).resolve().parents[2]
    monolith_path = root / MONOLITH
    if not monolith_path.exists():
        raise FileNotFoundError(f"Monolith not found: {monolith_path}")
    runpy.run_path(str(monolith_path), run_name="__main__")

if __name__ == "__main__":
    main()
