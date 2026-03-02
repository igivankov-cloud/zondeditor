#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.zondeditor.io.geo_reader import parse_geo_file
from src.zondeditor.io.geo_writer import build_geo_from_template_with_diff, save_geo_as


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
    return any(a <= i < b for a, b in ranges)


def _safe_mutate_first_point(tests: list[object]) -> tuple[int, int, int]:
    for t in tests:
        qc = list(getattr(t, "qc", []) or [])
        fs = list(getattr(t, "fs", []) or [])
        if not qc or not fs:
            continue
        q0 = int(float(str(qc[0]).replace(",", ".")))
        f0 = int(float(str(fs[0]).replace(",", ".")))
        q1 = (q0 + 1) if q0 < 255 else max(0, q0 - 1)
        f1 = (f0 + 1) if f0 < 255 else max(0, f0 - 1)
        qc[0] = str(q1)
        fs[0] = str(f1)
        setattr(t, "qc", qc)
        setattr(t, "fs", fs)
        return int(getattr(t, "tid", 0) or 0), q1, f1
    raise AssertionError("No test with qc/fs rows to mutate")


def main() -> int:
    fixture = ROOT / "fixtures" / "K2_260205A1.GEO"
    if not fixture.exists():
        raise FileNotFoundError(f"Missing fixture: {fixture}")

    tests, _meta, _kind = parse_geo_file(fixture)
    original = fixture.read_bytes()
    blocks = [t.block for t in tests if getattr(t, "block", None)]
    ranges = _build_allowed_ranges(blocks)

    tid, qv, fv = _safe_mutate_first_point(tests)
    with tempfile.TemporaryDirectory(prefix="geo-export-diff-selfcheck-") as td:
        out = Path(td) / "changed.GEO"
        save_geo_as(out, tests, source_bytes=original, blocks_info=blocks)
        changed = out.read_bytes()

    result = build_geo_from_template_with_diff(original, blocks, tests)
    if result.diff_count <= 0:
        raise AssertionError("diff_count == 0 after explicit qc/fs mutation")
    if changed == original:
        raise AssertionError("Exported GEO is byte-identical to original after mutation")

    bad_positions: list[int] = []
    for i, (a, b) in enumerate(zip(original, changed)):
        if a == b:
            continue
        if not _inside_ranges(i, ranges):
            bad_positions.append(i)
            if len(bad_positions) >= 20:
                break
    if bad_positions:
        raise AssertionError(f"Differences outside data ranges: {bad_positions}")

    print(f"[OK] mutated test tid={tid}, qc0={qv}, fs0={fv}")
    print(f"[OK] diff_count={result.diff_count}")
    print("[RESULT] PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
