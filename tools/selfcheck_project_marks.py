from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJ_ROOT))

from src.zondeditor.project import Project, ProjectSettings, SourceInfo, load_project, save_project
from src.zondeditor.project.ops import op_algo_fix_applied, op_cell_set


def fail(msg: str) -> None:
    raise SystemExit(f"[FAIL] {msg}")


def ok(msg: str) -> None:
    print(f"[ OK ] {msg}")


def _row_by_depth(depths: list[str], depth_m: float | None) -> int | None:
    if depth_m is None:
        return None
    tgt = round(float(depth_m), 3)
    for i, d in enumerate(depths):
        try:
            dv = round(float(str(d).replace(",", ".")), 3)
        except Exception:
            continue
        if dv == tgt:
            return i
    return None


def build_marks_index_from_ops(ops: list[dict], tests: list[dict]) -> dict[tuple[int, int, str], dict]:
    by_tid = {int(t["tid"]): t for t in tests}
    out: dict[tuple[int, int, str], dict] = {}
    for op in ops:
        op_type = str((op or {}).get("opType") or "")
        payload = dict((op or {}).get("payload") or {})
        op_mark = dict((op or {}).get("mark") or {})
        if op_type == "cell_set":
            tid = int(payload.get("testId"))
            t = by_tid[tid]
            row = payload.get("row")
            try:
                row_i = int(row)
            except Exception:
                row_i = -1
            if row_i < 0:
                row_i = _row_by_depth(t["depth"], payload.get("depthM")) or -1
            fld = str(payload.get("field") or "")
            if row_i >= 0 and fld:
                out[(tid, row_i, fld)] = dict(op_mark)
        elif op_type == "algo_fix_applied":
            for ch in list(payload.get("changes") or []):
                one = dict(ch or {})
                tid = int(one.get("testId"))
                t = by_tid[tid]
                row = one.get("row")
                try:
                    row_i = int(row)
                except Exception:
                    row_i = -1
                if row_i < 0:
                    row_i = _row_by_depth(t["depth"], one.get("depthM")) or -1
                fld = str(one.get("field") or "")
                if row_i >= 0 and fld:
                    out[(tid, row_i, fld)] = dict(one.get("mark") or op_mark)
    return out


def main() -> None:
    tests = [{"tid": 101, "depth": ["0.00", "0.10", "0.20"], "qc": ["10", "20", "30"], "fs": ["5", "6", "7"]}]

    ops: list[dict] = []
    ops.append(op_cell_set(test_id=101, row=1, field="qc", before="20", after="25", depth_m=0.10))
    ops.append(op_cell_set(test_id=101, row=2, field="fs", before="7", after="9", depth_m=0.20))
    ops.append(
        op_algo_fix_applied(
            changes=[
                {"testId": 101, "row": 0, "field": "qc", "depthM": 0.00, "mark": {"reason": "algo_fix", "color": "green"}},
                {"testId": 101, "row": 1, "field": "fs", "depthM": 0.10, "mark": {"reason": "algo_fix", "color": "green"}},
            ]
        )
    )

    for op in ops[:2]:
        if op.get("mark", {}).get("color") != "purple" or op.get("mark", {}).get("reason") != "manual_edit":
            fail("manual cell_set op missing purple/manual_edit mark")
    algo_changes = list((ops[2].get("payload") or {}).get("changes") or [])
    if not algo_changes:
        fail("algo_fix_applied changes are empty")
    for ch in algo_changes:
        m = dict(ch.get("mark") or {})
        if m.get("color") != "green" or m.get("reason") != "algo_fix":
            fail("algo_fix_applied change missing green/algo_fix mark")

    state = {
        "tests": [
            {
                "tid": 101,
                "dt": "01.01.2026 00:00:00",
                "depth": tests[0]["depth"],
                "qc": tests[0]["qc"],
                "fs": tests[0]["fs"],
                "incl": None,
                "marker": "",
                "header_pos": "",
                "orig_id": 101,
                "export_on": True,
                "block": None,
            }
        ],
        "flags": {"101": {"invalid": False, "interp": [], "force": [], "user": [], "algo": [], "tail": []}},
        "step_m": 0.1,
        "depth0_by_tid": {"101": 0.0},
    }

    project = Project(
        object_name="selfcheck_marks",
        source=SourceInfo(kind="GEO", filename="selfcheck.geo", ext="geo", mime="application/octet-stream"),
        settings=ProjectSettings(step_m=0.1),
        ops=ops,
        state=state,
    )

    with tempfile.TemporaryDirectory(prefix="zond_marks_") as td:
        zproj = Path(td) / "project.zproj"
        save_project(zproj, project=project, source_bytes=b"FAKE_GEO")
        if not zproj.exists():
            fail("project .zproj not created")
        loaded, src = load_project(zproj)
        if src != b"FAKE_GEO":
            fail("source bytes were not restored")

    marks_index = build_marks_index_from_ops(loaded.ops, tests)
    expected = {
        (101, 1, "qc"): "purple",
        (101, 2, "fs"): "purple",
        (101, 0, "qc"): "green",
        (101, 1, "fs"): "green",
    }
    if len(marks_index) != len(expected):
        fail(f"marks_index size mismatch: {len(marks_index)} != {len(expected)}")

    for key, color in expected.items():
        mark = marks_index.get(key) or {}
        if mark.get("color") != color:
            fail(f"mark color mismatch for {key}: {mark}")

    ok(f"ops loaded: {len(loaded.ops)}")
    ok(f"mark records built: {len(marks_index)}")
    ok(f"cells highlighted (by index): {len(expected)}")
    ok("selfcheck_project_marks passed")


if __name__ == "__main__":
    main()
