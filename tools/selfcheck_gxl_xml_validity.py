#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.zondeditor.io.geo_reader import parse_geo_file
from src.zondeditor.export.gxl_export import export_gxl_generated


def main() -> int:
    fixture = ROOT / "fixtures" / "K2_260205A1.GEO"
    tests, _meta, _kind = parse_geo_file(fixture)

    with tempfile.TemporaryDirectory(prefix="zondeditor-gxl-valid-") as td:
        out = Path(td) / "roundtrip.gxl"
        export_gxl_generated(tests, out_path=out, object_code="SELFTEST", include_only_export_on=False)
        raw = out.read_bytes()
        if not raw.startswith(b"<?xml"):
            raise RuntimeError("GXL must start with <?xml")
        ET.fromstring(raw.decode("cp1251", errors="strict"))

    print("[RESULT] PASSED: GXL XML validity selfcheck")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
