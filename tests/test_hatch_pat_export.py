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
local_to_world = _MOD.local_to_world
parse_float = _MOD.parse_float
parse_angle_deg = _MOD.parse_angle_deg


def _load_graviy_rows():
    payload = json.loads(Path("src/zondeditor/assets/hatches/graviy.json").read_text(encoding="utf-8"))
    return payload["rows"]


def test_graviy_pat_row_keeps_local_origin_without_swap():
    row = _load_graviy_rows()[0]
    line = row_to_pat_descriptor(row, swap_local_axes=False)
    # angle, x, y, dx, dy, dash, gap
    parts = [x.strip() for x in line.split(",")]
    assert parts[:5] == ["45.000000", "4.136575", "-0.318198", "0.000000", "6.363961"]


def test_graviy_pat_row_changes_origin_if_forced_legacy_swap():
    row = _load_graviy_rows()[0]
    line = row_to_pat_descriptor(row, swap_local_axes=True)
    parts = [x.strip() for x in line.split(",")]
    assert parts[:5] == ["45.000000", "0.318198", "-4.136575", "0.000000", "6.363961"]


def test_pat_coordinates_match_preview_world_geometry():
    row = _load_graviy_rows()[0]
    angle_editor = parse_angle_deg(row["angle"])
    # preview world base/step from editor-local row
    preview_base = local_to_world(angle_editor, parse_float(row["x"]), parse_float(row["y"]))
    preview_step = local_to_world(angle_editor, parse_float(row["dx"]), parse_float(row["dy"]))

    # parse generated PAT row and map back to world with PAT basis
    parts = [parse_float(x.strip()) for x in row_to_pat_descriptor(row, swap_local_axes=False).split(",")[:5]]
    angle_pat, x_pat, y_pat, dx_pat, dy_pat = parts
    theta = math.radians(angle_pat)
    ex_pat = (math.cos(theta), math.sin(theta))
    ey_pat = (-math.sin(theta), math.cos(theta))
    pat_base_world = (x_pat * ex_pat[0] + y_pat * ey_pat[0], x_pat * ex_pat[1] + y_pat * ey_pat[1])
    pat_step_world = (dx_pat * ex_pat[0] + dy_pat * ey_pat[0], dx_pat * ex_pat[1] + dy_pat * ey_pat[1])

    assert pat_base_world == pytest.approx(preview_base, abs=1e-6)
    assert pat_step_world == pytest.approx(preview_step, abs=1e-6)
