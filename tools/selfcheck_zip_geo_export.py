#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.zondeditor.export.geo_export import bundle_geo_filename, export_bundle_geo
from src.zondeditor.io.geo_reader import parse_geo_file


FIXTURE = ROOT / "fixtures" / "K2_260205A1.GEO"


def _allowed_ranges(blocks: list[object]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for b in blocks:
        ds = int(getattr(b, "data_start", 0) or 0)
        dl = int(getattr(b, "data_len", 0) or 0)
        bpr = int(getattr(b, "bytes_per_row", 0) or 0)
        de = int(getattr(b, "data_end", ds) or ds)
        if bpr <= 0 or dl % bpr != 0:
            raise AssertionError("invalid block geometry")
        pe = ds + dl
        if not (0 <= ds <= pe <= de):
            raise AssertionError("invalid data range")
        ranges.append((ds, pe))
    return ranges


def _inside(i: int, ranges: list[tuple[int, int]]) -> bool:
    return any(a <= i < b for a, b in ranges)


def _mutate_first_qc(tests: list[object]) -> None:
    for t in tests:
        qc = list(getattr(t, "qc", []) or [])
        if qc:
            old = int(float(str(qc[0]).replace(",", ".")))
            qc[0] = str(old + 7)
            setattr(t, "qc", qc)
            return
    raise AssertionError("no qc row to mutate")


def _zip_with_geo(tests: list[object], source_bytes: bytes, blocks: list[object], out_zip: Path, source_geo: Path) -> str:
    geo_name = bundle_geo_filename(source_geo_path=source_geo, fallback_name="geo_export")
    with tempfile.TemporaryDirectory(prefix="zip-geo-selfcheck-") as td:
        td_path = Path(td)
        geo_path = td_path / geo_name
        export_bundle_geo(geo_path, tests=tests, source_bytes=source_bytes, blocks_info=blocks)
        with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(geo_path, geo_name)
    return geo_name


def _extract(zip_path: Path, member: str) -> bytes:
    with zipfile.ZipFile(zip_path, "r") as zf:
        if member not in zf.namelist():
            raise AssertionError(f"{member} missing in zip")
        data = zf.read(member)
    if len(data) <= 0:
        raise AssertionError("geo in zip is empty")
    return data


def _check_changed(original: bytes, changed: bytes, ranges: list[tuple[int, int]]) -> None:
    if changed == original:
        raise AssertionError("changed export is byte-identical to original")
    if len(changed) != len(original):
        raise AssertionError("changed export has different size")

    bad: list[int] = []
    good = 0
    for i, (a, b) in enumerate(zip(original, changed)):
        if a == b:
            continue
        if _inside(i, ranges):
            good += 1
        else:
            bad.append(i)
            if len(bad) >= 20:
                break
    if bad:
        raise AssertionError(f"diffs outside data ranges: {bad}")
    if good == 0:
        raise AssertionError("no diffs in allowed data ranges")


def main() -> int:
    if not FIXTURE.exists():
        raise FileNotFoundError(FIXTURE)

    tests, _meta, _kind = parse_geo_file(FIXTURE)
    original = FIXTURE.read_bytes()
    tests = [t for t in tests if list(getattr(t, "qc", []) or []) and list(getattr(t, "fs", []) or [])]
    blocks = [t.block for t in tests if getattr(t, "block", None)]
    ranges = _allowed_ranges(blocks)

    with tempfile.TemporaryDirectory(prefix="selfcheck-zip-geo-") as td:
        td_path = Path(td)

        changed_tests = list(tests)
        _mutate_first_qc(changed_tests)
        zip_changed = td_path / "changed_bundle.zip"
        geo_member = _zip_with_geo(changed_tests, original, blocks, zip_changed, FIXTURE)
        changed_geo = _extract(zip_changed, geo_member)
        _check_changed(original, changed_geo, ranges)
        print(f"[OK] changed ZIP GEO patched in data ranges only: {geo_member}")

        fresh_tests, _meta2, _kind2 = parse_geo_file(FIXTURE)
        fresh_tests = [t for t in fresh_tests if list(getattr(t, "qc", []) or []) and list(getattr(t, "fs", []) or [])]
        zip_clean = td_path / "clean_bundle.zip"
        geo_member_clean = _zip_with_geo(fresh_tests, original, blocks, zip_clean, FIXTURE)
        clean_geo = _extract(zip_clean, geo_member_clean)
        if clean_geo != original:
            raise AssertionError("no-change ZIP GEO is not byte-identical")
        print(f"[OK] no-change ZIP GEO is byte-identical: {geo_member_clean}")

    print("[RESULT] PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
