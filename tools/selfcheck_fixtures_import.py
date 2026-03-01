#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.zondeditor.io.geo_reader import parse_geo_file
from src.zondeditor.io.gxl_reader import parse_gxl_file


CASES = [
    ("GEO", Path("fixtures/K2_260205A1.GEO")),
    ("GEO", Path("fixtures/К4_260218O1.GEO")),
    ("GXL", Path("fixtures/k2.gxl")),
    ("GXL", Path("fixtures/k4.gxl")),
]


def _check_not_empty(kind: str, fixture: Path) -> tuple[bool, str]:
    if not fixture.exists():
        return False, f"{kind} {fixture}: file not found"

    if kind == "GEO":
        tests, _meta, geo_kind = parse_geo_file(fixture)
    else:
        tests, _meta = parse_gxl_file(fixture)
        geo_kind = "GXL"

    rows = sum(len(getattr(t, "qc", []) or []) for t in tests)
    if not tests or rows <= 0:
        return False, f"{kind} {fixture}: parsed empty payload (tests={len(tests)}, rows={rows})"

    return True, f"{kind} {fixture}: OK ({geo_kind}, tests={len(tests)}, rows={rows})"


def main() -> int:
    print("[SELF-CHECK] fixtures import")
    failed = False
    for kind, fixture in CASES:
        try:
            ok, msg = _check_not_empty(kind, fixture)
        except Exception as exc:
            ok, msg = False, f"{kind} {fixture}: FAIL ({exc})"

        if ok:
            print(f"[ OK ] {msg}")
        else:
            print(f"[FAIL] {msg}")
            failed = True

    if failed:
        print("[RESULT] FAILED")
        return 1

    print("[RESULT] PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
