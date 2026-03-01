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
    if not tests:
        raise RuntimeError(f"{path.name}: no tests parsed")

    for idx, t in enumerate(tests, start=1):
        block = getattr(t, "block", None)
        if block is None:
            continue

        rows = max(len(getattr(t, "qc", []) or []), len(getattr(t, "fs", []) or []), len(getattr(t, "incl", []) or []))
        bpr = int(getattr(block, "bytes_per_row", 2) or 2)
        data_len = int(getattr(block, "data_len", max(0, int(block.data_end) - int(block.data_start))) or 0)
        min_bpr = 2 if kind == "K2" else 6

        if data_len < rows * min_bpr:
            raise RuntimeError(
                f"{path.name} block#{idx}: data_len={data_len} too small for rows={rows} min_bytes_per_row={min_bpr}"
            )

        expected = rows * bpr
        if data_len != expected:
            raise RuntimeError(
                f"{path.name} block#{idx}: data_len={data_len} not aligned with decoded rows={rows} and bytes_per_row={bpr}"
            )

    ok(f"{path.name}: GEO block layout validated ({kind})")


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
