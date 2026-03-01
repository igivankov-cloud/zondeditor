#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.zondeditor.io.gxl_reader import parse_gxl_file
from src.zondeditor.export.gxl_export import export_gxl_generated


def main() -> int:
    try:
        fixture = ROOT / "fixtures" / "k2.gxl"
        if not fixture.exists():
            raise FileNotFoundError(f"Missing fixture: {fixture}")

        tests, _meta = parse_gxl_file(fixture)
        if not tests:
            raise RuntimeError("Fixture GXL has no tests")

        with tempfile.TemporaryDirectory(prefix="zondeditor-gxl-roundtrip-") as td:
            out_path = Path(td) / "roundtrip.gxl"
            export_gxl_generated(tests, out_path=out_path, object_code="SELFTEST", include_only_export_on=True)
            if not out_path.exists() or out_path.stat().st_size <= 0:
                raise RuntimeError("Exported GXL file is missing or empty")
            raw = out_path.read_bytes()

        if not raw.startswith(b"<?xml"):
            raise RuntimeError("Exported GXL does not start with XML declaration")
        for tag in (b"<exportfile>", b"<object>", b"<test>", b"<dat>"):
            if tag not in raw:
                raise RuntimeError(f"Exported GXL misses expected tag: {tag!r}")

        print(f"gxl_size={len(raw)} tests_in={len(tests)}")
        print("[RESULT] PASSED")
        return 0
    except Exception as exc:
        print(f"[RESULT] FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
