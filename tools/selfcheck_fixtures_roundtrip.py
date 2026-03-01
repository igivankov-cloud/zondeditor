#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.zondeditor.io.geo_reader import parse_geo_file, load_geo
from src.zondeditor.io.geo_writer import save_geo_as


def main() -> int:
    try:
        fixture = ROOT / "fixtures" / "K2_260205A1.GEO"
        if not fixture.exists():
            raise FileNotFoundError(f"Missing fixture: {fixture}")

        series = load_geo(fixture)
        tests, _meta, _kind = parse_geo_file(fixture)
        source_bytes = fixture.read_bytes()
        blocks_info = [t.block for t in tests if getattr(t, "block", None)]
        if not blocks_info:
            raise RuntimeError("No template blocks for GEO roundtrip")

        with tempfile.TemporaryDirectory(prefix="zondeditor-roundtrip-") as td:
            out_path = Path(td) / "roundtrip.GEO"
            save_geo_as(out_path, series, source_bytes=source_bytes, blocks_info=blocks_info)
            if (not out_path.exists()) or out_path.stat().st_size <= 0:
                raise RuntimeError("Roundtrip GEO was not created or has empty size")
            raw = out_path.read_bytes()

            marker_hits = 0
            for s in series[: min(5, len(series))]:
                tid = int(getattr(s, "test_id", 0) or 0)
                if tid <= 0:
                    continue
                p0a = bytes((0xFF, 0xFF, tid, 0x1E, 0x0A))
                p14 = bytes((0xFF, 0xFF, tid, 0x1E, 0x14))
                if p0a in raw or p14 in raw:
                    marker_hits += 1

            print(f"roundtrip_file={out_path} size={out_path.stat().st_size} marker_hits={marker_hits}")
            if marker_hits < 2:
                raise RuntimeError("Expected marker hits for multiple tests in roundtrip GEO")

        print("[RESULT] PASSED")
        return 0
    except Exception as exc:
        print(f"[RESULT] FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
