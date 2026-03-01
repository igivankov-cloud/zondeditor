from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.zondeditor.domain.models import GeoBlockInfo, TestData
from src.zondeditor.export.credo_zip import export_credo_zip
from src.zondeditor.io.geo_reader import parse_geo_bytes
from src.zondeditor.io.geo_writer import build_k2_geo_from_template
from src.zondeditor.io.gxl_reader import parse_gxl_file
from src.zondeditor.io.k2_reader import parse_geo_with_blocks
from tools.geo_probe import _is_experiment, _probe_k2, _probe_k4


def fail(msg: str) -> int:
    print(f"[FAIL] {msg}")
    return 1


def ok(msg: str) -> None:
    print(f"[ OK ] {msg}")


def _load_geo_template() -> tuple[bytes, list[GeoBlockInfo]]:
    geo_fixture = ROOT / "fixtures" / "K2_260205A1.GEO"
    if not geo_fixture.exists():
        raise FileNotFoundError(f"GEO fixture not found: {geo_fixture}")
    raw = geo_fixture.read_bytes()
    tests, _ = parse_geo_with_blocks(raw, TestData, GeoBlockInfo)
    blocks = [t.block for t in tests if getattr(t, "block", None)]
    if not blocks:
        raise RuntimeError("K2 GEO fixture has no template blocks")
    return raw, blocks


def _validate_geo_block_data(path: Path) -> None:
    raw = path.read_bytes()
    tests, _meta, kind = parse_geo_bytes(raw)
    blocks = _probe_k4(raw) if kind == "K4" else _probe_k2(raw)
    accepted = [b for b in blocks if _is_experiment(kind, b)]
    if not tests:
        raise RuntimeError(f"{path.name}: no tests parsed")

    if kind == "K2":
        if len(tests) != 6:
            raise RuntimeError(f"{path.name}: expected 6 tests, got {len(tests)}")
    else:
        if any(len(getattr(t, "qc", []) or []) < 10 for t in tests):
            raise RuntimeError(f"{path.name}: tiny blocks were not filtered out (rows < 10 found)")
        if any(int(getattr(t, "tid", 0) or 0) > 300 for t in tests):
            raise RuntimeError(f"{path.name}: service test_id values leaked (>300)")
        if len(tests) != 19:
            raise RuntimeError(f"{path.name}: expected 19 real tests, got {len(tests)}")

    for idx, t in enumerate(tests, start=1):
        block = getattr(t, "block", None)
        if block is None:
            raise RuntimeError(f"{path.name} block#{idx}: missing GeoBlockInfo")

        rows = max(len(getattr(t, "qc", []) or []), len(getattr(t, "fs", []) or []), len(getattr(t, "incl", []) or []))
        bpr = int(getattr(block, "bytes_per_row", 0) or 0)
        data_len = int(getattr(block, "data_len", max(0, int(block.data_end) - int(block.data_start))) or 0)

        if kind == "K2":
            if bpr != 2:
                raise RuntimeError(f"{path.name} block#{idx}: bytes_per_row={bpr}, expected 2")
            if data_len % 2 != 0:
                raise RuntimeError(f"{path.name} block#{idx}: data_len={data_len} is not divisible by 2")
            if rows != data_len // 2:
                raise RuntimeError(f"{path.name} block#{idx}: rows={rows}, expected {data_len // 2}")
        else:
            step_raw = getattr(t, "marker", "").split()
            if len(step_raw) < 2:
                raise RuntimeError(f"{path.name} block#{idx}: invalid marker for step check")
            step = int(step_raw[1], 16) / 1000.0
            if abs(step - 0.05) > 1e-9:
                raise RuntimeError(f"{path.name} block#{idx}: step={step}, expected 0.05")
            if bpr != 9:
                raise RuntimeError(f"{path.name} block#{idx}: bytes_per_row={bpr}, expected 9")
            if data_len % 9 != 0:
                raise RuntimeError(f"{path.name} block#{idx}: data_len={data_len} is not divisible by 9")
            if rows != data_len // 9:
                raise RuntimeError(f"{path.name} block#{idx}: rows={rows}, expected {data_len // 9}")
            if rows < 10:
                raise RuntimeError(f"{path.name} block#{idx}: tiny block rows={rows} leaked")

    ok(f"{path.name}: blocks found={len(blocks)} accepted_as_tests={len(accepted)} parsed_tests={len(tests)} ({kind})")


def main() -> int:
    try:
        gxl_files = [ROOT / "fixtures" / "k2.gxl", ROOT / "fixtures" / "k4.gxl"]
        geo_files = [ROOT / "fixtures" / "K2_260205A1.GEO", ROOT / "fixtures" / "К4_260218O1.GEO"]
        template_raw, template_blocks = _load_geo_template()

        for geo in geo_files:
            if not geo.exists():
                return fail(f"Missing fixture: {geo}")
            _validate_geo_block_data(geo)

        with tempfile.TemporaryDirectory(prefix="zondeditor-fixtures-") as td:
            out_dir = Path(td)
            for gxl in gxl_files:
                if not gxl.exists():
                    return fail(f"Missing fixture: {gxl}")

                tests, _meta = parse_gxl_file(gxl)
                if not tests:
                    return fail(f"{gxl.name}: parser returned 0 tests")

                row_count = sum(len(getattr(t, "depth", []) or []) for t in tests)
                if row_count <= 0:
                    return fail(f"{gxl.name}: parsed tests are empty")
                ok(f"{gxl.name}: parsed tests={len(tests)} rows={row_count}")

                geo_out = out_dir / f"{gxl.stem}.GEO"
                geo_bytes = build_k2_geo_from_template(template_raw, template_blocks, tests)
                geo_out.write_bytes(geo_bytes)
                if (not geo_out.exists()) or geo_out.stat().st_size <= 0:
                    return fail(f"{gxl.name}: GEO export failed")
                ok(f"{gxl.name}: GEO exported ({geo_out.stat().st_size} bytes)")

                zip_out = out_dir / f"{gxl.stem}_credo.zip"
                export_credo_zip(tests, geo_kind="K2", out_zip_path=zip_out)
                if (not zip_out.exists()) or zip_out.stat().st_size <= 0:
                    return fail(f"{gxl.name}: CREDO ZIP export failed")
                ok(f"{gxl.name}: CREDO ZIP exported ({zip_out.stat().st_size} bytes)")

    except Exception as exc:
        return fail(str(exc))

    print("[OK] Fixture selfcheck passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
