from src.zondeditor.domain.hatching import (
    BUILTIN_HATCH_PATTERNS,
    SOIL_TYPE_TO_HATCH,
    resolve_hatch_pattern,
)
from src.zondeditor.ui.render.hatch_renderer import render_hatch_pattern


class DummyCanvas:
    def __init__(self):
        self.lines = []

    def create_line(self, *args, **kwargs):
        self.lines.append((args, kwargs))


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
