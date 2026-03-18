from src.zondeditor.domain.hatching import (
    BUILTIN_HATCH_PATTERNS,
    SOIL_TYPE_TO_HATCH,
    resolve_hatch_pattern,
)
from src.zondeditor.ui.render.hatch_preview import draw_hatch_preview_grid, iter_builtin_preview_patterns
from src.zondeditor.ui.render.hatch_renderer import render_hatch_pattern


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
