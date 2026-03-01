#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.zondeditor.io.geo_reader import parse_geo_file
from src.zondeditor.io.geo_writer import save_geo_as


def _range_positions(start: int, end: int) -> set[int]:
    return set(range(int(start), int(end))) if end > start else set()


def _changed_positions(a: bytes, b: bytes) -> set[int]:
    n = min(len(a), len(b))
    out = {i for i in range(n) if a[i] != b[i]}
    if len(a) != len(b):
        out |= set(range(n, max(len(a), len(b))))
    return out


def main() -> int:
    fixture = ROOT / "fixtures" / "K2_260205A1.GEO"
    tests, _meta, kind = parse_geo_file(fixture)
    if kind != "K2":
        raise RuntimeError(f"Expected K2 fixture, got {kind}")

    original = fixture.read_bytes()
    blocks = [t.block for t in tests if getattr(t, "block", None) is not None]
    if len(blocks) < 2:
        raise RuntimeError(f"Expected multiple blocks, got {len(blocks)}")

    with tempfile.TemporaryDirectory(prefix="zondeditor-geo-header-") as td:
        td_path = Path(td)

        # 1) no-op roundtrip must preserve headers
        out_same = td_path / "same.GEO"
        save_geo_as(out_same, tests, source_bytes=original, blocks_info=blocks)
        same = out_same.read_bytes()

        for bi in blocks:
            hs = int(bi.header_start)
            ds = int(bi.data_start)
            if original[hs:ds] != same[hs:ds]:
                raise RuntimeError(f"Header changed for block at {hs}:{ds} in no-op export")
            if original[ds:int(bi.data_end)] != same[ds:int(bi.data_end)]:
                raise RuntimeError(f"Data changed for block at {ds}:{int(bi.data_end)} in no-op export")

        # 2) modify one cell, verify only data ranges change
        modified = list(tests)
        first = modified[0]
        qc = list(getattr(first, "qc", []) or [])
        fs = list(getattr(first, "fs", []) or [])
        if not qc or not fs:
            raise RuntimeError("Fixture first test has no qc/fs rows")
        qc[0] = str((int(float(qc[0].replace(",", "."))) + 1) % 255)
        first.qc = qc
        first.fs = fs

        out_mod = td_path / "mod.GEO"
        save_geo_as(out_mod, modified, source_bytes=original, blocks_info=blocks)
        mod = out_mod.read_bytes()

        changed = _changed_positions(original, mod)
        allowed = set()
        for bi in blocks:
            allowed |= _range_positions(int(bi.data_start), int(bi.data_end))

        forbidden = sorted(changed - allowed)
        if forbidden:
            raise RuntimeError(f"Found header/suffix changes outside data ranges, first positions: {forbidden[:20]}")

    print("[RESULT] PASSED: GEO header roundtrip selfcheck")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
