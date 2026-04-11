import importlib.util
import json
import math
from pathlib import Path


_MODULE_PATH = Path("tools/references/hatching/hatch_editor_live_v4_blob.py")
_SPEC = importlib.util.spec_from_file_location("hatch_editor_live_v4_blob", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
row_to_pat_descriptor = _MOD.row_to_pat_descriptor
build_preview_row_geometry = _MOD.build_preview_row_geometry
build_pat_row_geometry = _MOD.build_pat_row_geometry
parse_angle_deg = _MOD.parse_angle_deg
parse_float = _MOD.parse_float


def _load_rows(json_name: str):
    payload = json.loads(Path(f"src/zondeditor/assets/hatches/{json_name}").read_text(encoding="utf-8"))
    return payload["rows"]


def _dot2(a: tuple[float, float], b: tuple[float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _assert_close(actual: float, expected: float, *, abs_tol: float = 1e-6) -> None:
    assert math.isclose(actual, expected, abs_tol=abs_tol), f"expected {expected:.6f}, got {actual:.6f}"


def _assert_pair_close(actual: tuple[float, float], expected: tuple[float, float], *, abs_tol: float = 1e-6) -> None:
    _assert_close(actual[0], expected[0], abs_tol=abs_tol)
    _assert_close(actual[1], expected[1], abs_tol=abs_tol)


def _parse_pat_descriptor(row: dict, *, swap_local_axes: bool = False):
    parts = [parse_float(x.strip()) for x in row_to_pat_descriptor(row, swap_local_axes=swap_local_axes).split(",")[:5]]
    angle_pat, x_pat, y_pat, dx_pat, dy_pat = parts
    theta = math.radians(angle_pat)
    ex_pat = (math.cos(theta), math.sin(theta))
    ey_pat = (-math.sin(theta), math.cos(theta))
    return {
        "angle_pat": angle_pat,
        "origin_world": (x_pat, y_pat),
        "offset_local": (dx_pat, dy_pat),
        "direction_world": ex_pat,
        "step_world": (
            dx_pat * ex_pat[0] + dy_pat * ey_pat[0],
            dx_pat * ex_pat[1] + dy_pat * ey_pat[1],
        ),
    }


def _legacy_projected_fields(row: dict):
    """Reproduce the broken projection path that collapsed back to x, -y, dx, -dy."""
    preview = build_preview_row_geometry(row, swap_local_axes=False)
    angle_pat = (90.0 - parse_angle_deg(row.get("angle"), 0.0)) % 360.0
    theta = math.radians(angle_pat)
    ex_pat = (math.cos(theta), math.sin(theta))
    ey_pat = (-math.sin(theta), math.cos(theta))
    return {
        "angle_pat": angle_pat,
        "x_pat": _dot2(preview.base_world, ex_pat),
        "y_pat": _dot2(preview.base_world, ey_pat),
        "dx_pat": _dot2(preview.step_world, ex_pat),
        "dy_pat": _dot2(preview.step_world, ey_pat),
    }


def _legacy_local_hack(row: dict):
    return {
        "angle_pat": (90.0 - parse_angle_deg(row.get("angle"), 0.0)) % 360.0,
        "x_pat": parse_float(row.get("x"), 0.0),
        "y_pat": -parse_float(row.get("y"), 0.0),
        "dx_pat": parse_float(row.get("dx"), 0.0),
        "dy_pat": -parse_float(row.get("dy"), 0.0),
    }


def _line_intersection(
    point_a: tuple[float, float],
    dir_a: tuple[float, float],
    point_b: tuple[float, float],
    dir_b: tuple[float, float],
) -> tuple[float, float]:
    det = dir_a[0] * dir_b[1] - dir_a[1] * dir_b[0]
    assert abs(det) > 1e-9
    delta_x = point_b[0] - point_a[0]
    delta_y = point_b[1] - point_a[1]
    t = (delta_x * dir_b[1] - delta_y * dir_b[0]) / det
    return (point_a[0] + t * dir_a[0], point_a[1] + t * dir_a[1])


def _phase_at(point: tuple[float, float], origin: tuple[float, float], direction: tuple[float, float]) -> float:
    return _dot2((point[0] - origin[0], point[1] - origin[1]), direction)


def test_legacy_projection_path_is_algebraically_equivalent_to_old_hack():
    sample_rows = [
        _load_rows("Peschanik.json")[2],
        _load_rows("Peschanik.json")[3],
        *_load_rows("graviy.json")[:4],
    ]
    for row in sample_rows:
        projected = _legacy_projected_fields(row)
        hacked = _legacy_local_hack(row)
        for key in ("angle_pat", "x_pat", "y_pat", "dx_pat", "dy_pat"):
            _assert_close(projected[key], hacked[key])


def test_build_pat_row_geometry_uses_preview_world_origin():
    row = _load_rows("Peschanik.json")[2]
    preview = build_preview_row_geometry(row, swap_local_axes=False)
    pat = build_pat_row_geometry(row, swap_local_axes=False)
    _assert_pair_close(pat.origin_world, preview.base_world)
    _assert_close(pat.offset_local[0], parse_float(row.get("dx"), 0.0))
    _assert_close(pat.offset_local[1], -parse_float(row.get("dy"), 0.0))


def test_peschanik_minimal_pair_matches_preview_origin_step_and_intersection():
    rows = _load_rows("Peschanik.json")
    diagnostics = []
    for idx in (2, 3):
        row = rows[idx]
        preview = build_preview_row_geometry(row, swap_local_axes=False)
        pat = _parse_pat_descriptor(row, swap_local_axes=False)
        diagnostics.append((preview, pat))
        _assert_pair_close(pat["origin_world"], preview.base_world)
        _assert_pair_close(pat["step_world"], preview.step_world)

    preview_hit = _line_intersection(
        diagnostics[0][0].base_world,
        diagnostics[0][1]["direction_world"],
        diagnostics[1][0].base_world,
        diagnostics[1][1]["direction_world"],
    )
    pat_hit = _line_intersection(
        diagnostics[0][1]["origin_world"],
        diagnostics[0][1]["direction_world"],
        diagnostics[1][1]["origin_world"],
        diagnostics[1][1]["direction_world"],
    )
    _assert_pair_close(pat_hit, preview_hit)


def test_graviy_first_four_rows_preserve_origin_step_and_phase():
    rows = _load_rows("graviy.json")[:4]
    parsed = []
    for row in rows:
        preview = build_preview_row_geometry(row, swap_local_axes=False)
        pat = _parse_pat_descriptor(row, swap_local_axes=False)
        parsed.append((preview, pat))
        _assert_pair_close(pat["origin_world"], preview.base_world)
        _assert_pair_close(pat["step_world"], preview.step_world)

    for left, right in ((0, 2), (1, 3)):
        preview_left, pat_left = parsed[left]
        preview_right, pat_right = parsed[right]
        preview_hit = _line_intersection(
            preview_left.base_world,
            pat_left["direction_world"],
            preview_right.base_world,
            pat_right["direction_world"],
        )
        pat_hit = _line_intersection(
            pat_left["origin_world"],
            pat_left["direction_world"],
            pat_right["origin_world"],
            pat_right["direction_world"],
        )
        _assert_pair_close(pat_hit, preview_hit)
        _assert_close(
            _phase_at(pat_hit, pat_left["origin_world"], pat_left["direction_world"]),
            _phase_at(preview_hit, preview_left.base_world, pat_left["direction_world"]),
        )
        _assert_close(
            _phase_at(pat_hit, pat_right["origin_world"], pat_right["direction_world"]),
            _phase_at(preview_hit, preview_right.base_world, pat_right["direction_world"]),
        )


def test_full_patterns_preserve_preview_geometry_under_autocad_semantics():
    for json_name in ("graviy.json", "Peschanik.json"):
        for row in _load_rows(json_name):
            preview = build_preview_row_geometry(row, swap_local_axes=False)
            pat = _parse_pat_descriptor(row, swap_local_axes=False)
            _assert_pair_close(pat["origin_world"], preview.base_world)
            _assert_pair_close(pat["step_world"], preview.step_world)


def test_segments_from_right_panel_are_used_in_pat_descriptor():
    row = _load_rows("graviy.json")[0]
    parts = [x.strip() for x in row_to_pat_descriptor(row, swap_local_axes=False).split(",")]
    assert parts[-2:] == ["1.272792", "-5.091169"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
