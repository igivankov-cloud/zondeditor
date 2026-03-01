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


def _build_allowed_ranges(blocks: list[object]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for b in blocks:
        ds = int(getattr(b, "data_start", 0) or 0)
        dl = int(getattr(b, "data_len", 0) or 0)
        bpr = int(getattr(b, "bytes_per_row", 0) or 0)
        de = int(getattr(b, "data_end", ds) or ds)

        if bpr <= 0:
            raise AssertionError(f"bytes_per_row invalid: {bpr}")
        if dl % bpr != 0:
            raise AssertionError(f"data_len % bytes_per_row != 0 for block {b}")
        pe = ds + dl
        if not (0 <= ds <= pe <= de):
            raise AssertionError(f"data bounds invalid: ds={ds} pe={pe} de={de}")
        ranges.append((ds, pe))
    return ranges


def _inside_ranges(i: int, ranges: list[tuple[int, int]]) -> bool:
    for a, b in ranges:
        if a <= i < b:
            return True
    return False


def _mutate_one_point(tests: list[object]) -> None:
    for t in tests:
        qc = list(getattr(t, "qc", []) or [])
        fs = list(getattr(t, "fs", []) or [])
        if qc and fs:
            qc[0] = str(int(float(str(qc[0]).replace(",", "."))) + 1)
            fs[0] = str(int(float(str(fs[0]).replace(",", "."))) + 1)
            setattr(t, "qc", qc)
            setattr(t, "fs", fs)
            return
    raise AssertionError("No test with qc/fs rows to mutate")


def _check_no_change_roundtrip(fixture: Path) -> None:
    tests, _meta, _kind = parse_geo_file(fixture)
    original = fixture.read_bytes()
    blocks = [t.block for t in tests if getattr(t, "block", None)]
    with tempfile.TemporaryDirectory(prefix="geo-template-selfcheck-") as td:
        out = Path(td) / fixture.name
        save_geo_as(out, tests, source_bytes=original, blocks_info=blocks)
        got = out.read_bytes()
    if got != original:
        raise AssertionError(f"Byte-identical export failed for {fixture.name}")


def _check_masked_diff(fixture: Path) -> None:
    tests, _meta, _kind = parse_geo_file(fixture)
    original = fixture.read_bytes()
    blocks = [t.block for t in tests if getattr(t, "block", None)]
    ranges = _build_allowed_ranges(blocks)

    _mutate_one_point(tests)
    with tempfile.TemporaryDirectory(prefix="geo-template-selfcheck-") as td:
        out = Path(td) / f"changed_{fixture.name}"
        save_geo_as(out, tests, source_bytes=original, blocks_info=blocks)
        changed = out.read_bytes()

    if len(changed) != len(original):
        raise AssertionError("Output size differs from original; template integrity broken")

    bad_pos: list[int] = []
    good_changes = 0
    for i, (a, b) in enumerate(zip(original, changed)):
        if a == b:
            continue
        if _inside_ranges(i, ranges):
            good_changes += 1
        else:
            bad_pos.append(i)
            if len(bad_pos) >= 20:
                break

    if bad_pos:
        raise AssertionError(f"Found differences outside data ranges: {bad_pos}")
    if good_changes == 0:
        raise AssertionError("No differences inside allowed data ranges; export did not apply changes")


def main() -> int:
    fixtures = [
        ROOT / "fixtures" / "K2_260205A1.GEO",
        ROOT / "fixtures" / "К4_260218O1.GEO",
    ]
    for f in fixtures:
        if not f.exists():
            raise FileNotFoundError(f"Missing fixture: {f}")

    for f in fixtures:
        _check_no_change_roundtrip(f)
        print(f"[OK] byte-identical no-change: {f.name}")

    for f in fixtures:
        _check_masked_diff(f)
        print(f"[OK] masked-diff only in data ranges: {f.name}")

    print("[RESULT] PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
