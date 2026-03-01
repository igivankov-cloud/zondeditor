# tools/geo_roundtrip_selftest.py
# Roundtrip test: parse K2 -> save GEO -> parse again.
#
# Run:
#   py tools\geo_roundtrip_selftest.py

from __future__ import annotations

import sys
from pathlib import Path

# ensure project root is on sys.path so "src.*" imports work
PROJ_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJ_ROOT))

from src.zondeditor.io.k2_reader import parse_geo_with_blocks
from src.zondeditor.io.geo_writer import save_k2_geo
from src.zondeditor.domain.models import TestData, GeoBlockInfo

FIXTURE = Path("fixtures") / "K2_260205A1.GEO"
OUT = Path("tools") / "_selfcheck_out" / "K2_roundtrip_saved.GEO"

def fail(msg: str) -> None:
    raise SystemExit(f"[FAIL] {msg}")

def ok(msg: str) -> None:
    print(f"[ OK ] {msg}")

def main() -> None:
    if not FIXTURE.exists():
        fail(f"fixture not found: {FIXTURE}")
    data = FIXTURE.read_bytes()
    tests1, meta1 = parse_geo_with_blocks(data, TestData, GeoBlockInfo)
    if not tests1:
        fail("initial parse returned 0 tests")
    ok(f"initial parse: tests={len(tests1)}")

    save_k2_geo(OUT, data, tests1)
    if not OUT.exists() or OUT.stat().st_size < 1000:
        fail("saved GEO not created or too small")
    ok(f"saved: {OUT} ({OUT.stat().st_size} bytes)")

    data2 = OUT.read_bytes()
    tests2, meta2 = parse_geo_with_blocks(data2, TestData, GeoBlockInfo)
    if len(tests2) != len(tests1):
        fail(f"test count mismatch: {len(tests2)} != {len(tests1)}")
    m1 = {t.tid: len(t.qc) for t in tests1}
    m2 = {t.tid: len(t.qc) for t in tests2}
    if m1 != m2:
        fail(f"points mismatch by tid: {m1} != {m2}")
    ok("roundtrip OK (counts match)")

if __name__ == "__main__":
    main()
