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
from src.zondeditor.export.selection import select_export_tests


def main() -> int:
    try:
        fixture = ROOT / "fixtures" / "K2_260205A1.GEO"
        if not fixture.exists():
            raise FileNotFoundError(f"Missing fixture: {fixture}")

        tests, _meta, _kind = parse_geo_file(fixture)
        if len(tests) < 3:
            raise RuntimeError("Fixture must contain at least 3 tests")

        deleted_test = tests[0]
        hidden_test = tests[1]
        setattr(deleted_test, "deleted", True)
        setattr(hidden_test, "export_on", False)

        selection = select_export_tests(tests)
        if int(getattr(deleted_test, "tid", 0) or 0) not in selection.skipped_deleted:
            raise RuntimeError("Deleted test was not skipped")
        if int(getattr(hidden_test, "tid", 0) or 0) not in selection.skipped_hidden:
            raise RuntimeError("Hidden test was not skipped")

        with tempfile.TemporaryDirectory(prefix="zondeditor-export-selection-") as td:
            out_path = Path(td) / "export_selection.GEO"
            save_geo_as(
                out_path,
                selection.tests,
                source_bytes=fixture.read_bytes(),
                blocks_info=[t.block for t in tests if getattr(t, "block", None)],
            )
            exported_tests, _meta2, _kind2 = parse_geo_file(out_path)
            exported_ids = [int(getattr(t, "tid", 0) or 0) for t in exported_tests]

        expected_ids = [int(getattr(t, "tid", 0) or 0) for t in selection.tests]
        if exported_ids != expected_ids:
            raise RuntimeError(f"Exported ids mismatch: expected={expected_ids} actual={exported_ids}")

        print(
            "total_tests={total} exported_tests={exported} skipped_hidden={hidden} skipped_deleted={deleted}".format(
                total=selection.total_tests,
                exported=selection.exported_tests,
                hidden=selection.skipped_hidden,
                deleted=selection.skipped_deleted,
            )
        )
        print("[RESULT] PASSED")
        return 0
    except Exception as exc:
        print(f"[RESULT] FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
