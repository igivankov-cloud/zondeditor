import math

from src.zondeditor.domain.hatching import (
    BUILTIN_HATCH_PATTERNS,
    SOIL_TYPE_TO_HATCH,
    resolve_hatch_pattern,
)
from src.zondeditor.ui.render.hatch_preview import draw_hatch_preview_grid, iter_builtin_preview_patterns
from src.zondeditor.ui.render.hatch_renderer import HATCH_UNIT_PX, render_hatch_pattern


class DummyCanvas:
    def __init__(self):
        self.lines = []
        self.rectangles = []
        self.texts = []

    def create_line(self, *args, **kwargs):
        self.lines.append((args, kwargs))

    def create_rectangle(self, *args, **kwargs):
        self.rectangles.append((args, kwargs))

    def create_text(self, *args, **kwargs):
        self.texts.append((args, kwargs))


def _long_lines(canvas: DummyCanvas):
    out = []
    for args, _kwargs in canvas.lines:
        if len(args) != 4:
            continue
        x0, y0, x1, y1 = [float(v) for v in args]
        ln = math.hypot(x1 - x0, y1 - y0)
        if ln >= 10.0:
            out.append((x0, y0, x1, y1))
    return out


def _projected_spacings(lines, *, angle_deg: float):
    if not lines:
        return []
    a = math.radians(angle_deg)
    vx, vy = math.cos(a), math.sin(a)
    nx, ny = -vy, vx
    vals = sorted({round((x0 * nx) + (y0 * ny), 3) for x0, y0, _x1, _y1 in lines})
    return [round(vals[i + 1] - vals[i], 3) for i in range(len(vals) - 1) if (vals[i + 1] - vals[i]) > 0.5]


def test_builtin_catalog_contains_required_patterns():
    expected = {
        "argill",
        "glina",
        "gravel",
        "graviy",
        "pesch",
        "pesok_g",
        "pesok_k",
        "pesok_m",
        "pesok_p",
        "pesok_s",
        "pochva",
        "sugl",
        "supes",
        "tehno",
        "torf_I",
    }
    assert expected.issubset(set(BUILTIN_HATCH_PATTERNS.keys()))


def test_soil_alias_mapping_contains_project_types():
    assert SOIL_TYPE_TO_HATCH["суглинок"] == "sugl"
    assert SOIL_TYPE_TO_HATCH["супесь"] == "supes"
    assert SOIL_TYPE_TO_HATCH["глина"] == "glina"
    assert SOIL_TYPE_TO_HATCH["песок"] == "pesok_s"
    assert SOIL_TYPE_TO_HATCH["песок гравелистый"] == "pesok_g"
    assert SOIL_TYPE_TO_HATCH["аргиллит"] == "argill"
    assert SOIL_TYPE_TO_HATCH["насыпной"] == "tehno"


def test_resolve_hatch_pattern():
    p = resolve_hatch_pattern("суглинок")
    assert p is not None
    assert p.name == "sugl"
    assert resolve_hatch_pattern("неизвестный тип") is None


def test_renderer_draws_lines_for_pattern():
    canvas = DummyCanvas()
    p = BUILTIN_HATCH_PATTERNS["tehno"]
    render_hatch_pattern(canvas, (0.0, 0.0, 120.0, 80.0), p, tags=("t",), scale_info={"layer_height_px": 80.0})
    assert canvas.lines




def test_pesch_diagonals_use_single_short_segment_per_cycle():
    pesch = BUILTIN_HATCH_PATTERNS["pesch"]
    diagonal_lines = [line for line in pesch.lines if line.angle_deg in (60.0, 120.0)]
    assert len(diagonal_lines) == 2
    for line in diagonal_lines:
        assert line.pattern == [0.11547, -0.57735]

def test_renderer_smoke_for_all_builtin_patterns_and_layer_scales():
    for pattern in BUILTIN_HATCH_PATTERNS.values():
        thin_canvas = DummyCanvas()
        thick_canvas = DummyCanvas()
        render_hatch_pattern(thin_canvas, (0.0, 0.0, 120.0, 18.0), pattern, tags=("thin",), scale_info={"layer_height_px": 18.0})
        render_hatch_pattern(thick_canvas, (0.0, 0.0, 120.0, 180.0), pattern, tags=("thick",), scale_info={"layer_height_px": 180.0})
        assert thin_canvas.lines or thick_canvas.lines


def test_preview_grid_lists_all_builtin_preview_patterns():
    names = [p.name for p in iter_builtin_preview_patterns()]
    assert names == [
        "glina",
        "sugl",
        "supes",
        "pesok_g",
        "pesok_k",
        "pesok_s",
        "pesok_m",
        "pesok_p",
        "graviy",
        "gravel",
        "pesch",
        "argill",
        "torf_I",
        "tehno",
        "pochva",
    ]


def test_preview_grid_draws_labels_and_boxes():
    canvas = DummyCanvas()
    bbox = draw_hatch_preview_grid(canvas, x0=0.0, y0=0.0, cell_w=160.0, cell_h=80.0, columns=3)
    assert bbox[2] > bbox[0]
    assert bbox[3] > bbox[1]
    assert len(canvas.rectangles) >= len(iter_builtin_preview_patterns())
    assert len(canvas.texts) >= len(iter_builtin_preview_patterns())


def test_hatch_scale_is_constant_for_thin_and_thick_glina_layers():
    p = BUILTIN_HATCH_PATTERNS["glina"]
    thin = DummyCanvas()
    thick = DummyCanvas()
    render_hatch_pattern(thin, (0.0, 0.0, 140.0, 24.0), p, tags=("thin",), scale_info={"layer_height_px": 24.0})
    render_hatch_pattern(thick, (0.0, 0.0, 140.0, 160.0), p, tags=("thick",), scale_info={"layer_height_px": 160.0})
    thin_sp = _projected_spacings(_long_lines(thin), angle_deg=0.0)
    thick_sp = _projected_spacings(_long_lines(thick), angle_deg=0.0)
    assert thin_sp
    assert thick_sp
    assert abs(thin_sp[0] - thick_sp[0]) <= 0.01
    assert abs(thin_sp[0] - (0.075 * HATCH_UNIT_PX)) <= 0.05


def test_glina_sugl_supes_share_visual_step_and_sugl_supes_are_mirrored():
    glina = BUILTIN_HATCH_PATTERNS["glina"]
    sugl = BUILTIN_HATCH_PATTERNS["sugl"]
    supes = BUILTIN_HATCH_PATTERNS["supes"]
    assert glina.lines[0].dy == 0.075
    assert sugl.lines[0].dy == supes.lines[0].dy == 0.15
    assert glina.lines[0].angle_deg == 0.0
    assert sugl.lines[0].angle_deg == 120.0
    assert supes.lines[0].angle_deg == 120.0


def test_sugl_supes_keep_same_density_across_layer_heights():
    for name in ("sugl", "supes"):
        p = BUILTIN_HATCH_PATTERNS[name]
        thin = DummyCanvas()
        thick = DummyCanvas()
        render_hatch_pattern(thin, (0.0, 0.0, 140.0, 28.0), p, tags=("thin",), scale_info={"layer_height_px": 28.0})
        render_hatch_pattern(thick, (0.0, 0.0, 140.0, 180.0), p, tags=("thick",), scale_info={"layer_height_px": 180.0})
        thin_sp = _projected_spacings(_long_lines(thin), angle_deg=120.0)
        thick_sp = _projected_spacings(_long_lines(thick), angle_deg=120.0)
        assert thin_sp
        assert thick_sp
        assert abs(thin_sp[0] - thick_sp[0]) <= 0.01
        assert abs(thin_sp[0] - thin_sp[-1]) <= 0.01
