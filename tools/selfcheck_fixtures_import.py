#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.zondeditor.io.geo_reader import load_geo
from src.zondeditor.io.gxl_reader import load_gxl


def _rows_count(tests) -> int:
    return sum(len(getattr(t, "rows", []) or []) for t in tests)


def main() -> int:
    try:
        geo_k2 = ROOT / "fixtures" / "K2_260205A1.GEO"
        geo_k4 = ROOT / "fixtures" / "К4_260218O1.GEO"
        gxl_k2 = ROOT / "fixtures" / "k2.gxl"
        gxl_k4 = ROOT / "fixtures" / "k4.gxl"

        for p in (geo_k2, geo_k4, gxl_k2, gxl_k4):
            if not p.exists():
                raise FileNotFoundError(f"Missing fixture: {p}")

        tests = load_geo(geo_k2)
        print(f"GEO K2: tests={len(tests)} rows={_rows_count(tests)}")
        assert len(tests) > 1, "K2 GEO should contain more than one test"

        tests = load_geo(geo_k4)
        print(f"GEO K4: tests={len(tests)} rows={_rows_count(tests)}")
        assert len(tests) > 1, "K4 GEO should contain more than one test"

        tests = load_gxl(gxl_k2)
        print(f"GXL k2: tests={len(tests)} rows={_rows_count(tests)}")
        assert len(tests) > 0, "k2.gxl should contain tests"

        tests = load_gxl(gxl_k4)
        print(f"GXL k4: tests={len(tests)} rows={_rows_count(tests)}")
        assert len(tests) > 0, "k4.gxl should contain tests"

        print("[RESULT] PASSED")
        return 0
    except Exception as exc:
        print(f"[RESULT] FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
