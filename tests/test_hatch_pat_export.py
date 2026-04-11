import importlib.util
import json
import math
from pathlib import Path

import pytest


_MODULE_PATH = Path("tools/references/hatching/hatch_editor_live_v4_blob.py")
_SPEC = importlib.util.spec_from_file_location("hatch_editor_live_v4_blob", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
row_to_pat_descriptor = _MOD.row_to_pat_descriptor
build_preview_row_geometry = _MOD.build_preview_row_geometry
parse_float = _MOD.parse_float


def _load_rows(json_name: str):
    payload = json.loads(Path(f"src/zondeditor/assets/hatches/{json_name}").read_text(encoding="utf-8"))
    return payload["rows"]


def _pat_world_geometry(row: dict, *, swap_local_axes: bool = False):
    parts = [parse_float(x.strip()) for x in row_to_pat_descriptor(row, swap_local_axes=swap_local_axes).split(",")[:5]]
    angle_pat, x_pat, y_pat, dx_pat, dy_pat = parts
    theta = math.radians(angle_pat)
    ex_pat = (math.cos(theta), math.sin(theta))
    ey_pat = (-math.sin(theta), math.cos(theta))
    base = (x_pat * ex_pat[0] + y_pat * ey_pat[0], x_pat * ex_pat[1] + y_pat * ey_pat[1])
    step = (dx_pat * ex_pat[0] + dy_pat * ey_pat[0], dx_pat * ex_pat[1] + dy_pat * ey_pat[1])
    return base, step


def test_level_a_single_row_preview_world_equals_pat_world():
    row = _load_rows("graviy.json")[0]
    preview = build_preview_row_geometry(row, swap_local_axes=False)
    pat_base, pat_step = _pat_world_geometry(row, swap_local_axes=False)
    assert pat_base == pytest.approx(preview.base_world, abs=1e-6)
    assert pat_step == pytest.approx(preview.step_world, abs=1e-6)


def test_level_b_two_families_preserve_phase_for_graviy():
    rows = _load_rows("graviy.json")[:2]
    for row in rows:
        preview = build_preview_row_geometry(row, swap_local_axes=False)
        pat_base, pat_step = _pat_world_geometry(row, swap_local_axes=False)
        assert pat_base == pytest.approx(preview.base_world, abs=1e-6)
        assert pat_step == pytest.approx(preview.step_world, abs=1e-6)


@pytest.mark.parametrize("json_name", ["graviy.json", "Peschanik.json"])
def test_level_c_full_pattern_rows_match_preview_geometry(json_name: str):
    for row in _load_rows(json_name):
        preview = build_preview_row_geometry(row, swap_local_axes=False)
        pat_base, pat_step = _pat_world_geometry(row, swap_local_axes=False)
        assert pat_base == pytest.approx(preview.base_world, abs=1e-6)
        assert pat_step == pytest.approx(preview.step_world, abs=1e-6)


def test_segments_from_right_panel_are_used_in_pat_descriptor():
    row = _load_rows("graviy.json")[0]
    # dash/gap from row["segments"] must be written into PAT line tail.
    parts = [x.strip() for x in row_to_pat_descriptor(row, swap_local_axes=False).split(",")]
    assert parts[-2:] == ["1.272792", "-5.091169"]
