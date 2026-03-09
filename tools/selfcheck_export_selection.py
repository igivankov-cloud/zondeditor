#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.zondeditor.io.geo_reader import parse_geo_file
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

        deleted_id = int(getattr(deleted_test, "tid", 0) or 0)
        hidden_id = int(getattr(hidden_test, "tid", 0) or 0)
        exported_ids = [int(getattr(t, "tid", 0) or 0) for t in selection.tests]

        if deleted_id not in selection.skipped_deleted:
            raise RuntimeError("Deleted test was not skipped")
        if hidden_id not in selection.skipped_hidden:
            raise RuntimeError("Hidden test was not skipped")
        if deleted_id in exported_ids:
            raise RuntimeError("Deleted test is present in exported list")
        if hidden_id in exported_ids:
            raise RuntimeError("Hidden test is present in exported list")

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
