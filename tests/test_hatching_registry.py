from src.zondeditor.domain.hatching import HATCH_USAGE_EDITOR_INTERACTIVE, HATCH_USAGE_PROTOCOL_EXPORT
from src.zondeditor.domain.hatching.registry import SOIL_TYPE_TO_HATCH_FILE, load_registered_hatch, normalize_soil_type
from src.zondeditor.ui.render.hatch_renderer import render_hatch_pattern


class _CountCanvas:
    def __init__(self) -> None:
        self.lines = 0
        self.ovals = 0

    def create_line(self, *args, **kwargs):
        self.lines += 1

    def create_oval(self, *args, **kwargs):
        self.ovals += 1


def test_normalize_soil_type_handles_spaces_case_and_yo() -> None:
    assert normalize_soil_type('  ЁЛКА  ') == 'елка'


def test_registry_supports_external_hatch_synonyms() -> None:
    assert SOIL_TYPE_TO_HATCH_FILE['гравий'] == 'graviy.json'
    assert SOIL_TYPE_TO_HATCH_FILE['гравийный грунт'] == 'graviy.json'
    assert SOIL_TYPE_TO_HATCH_FILE['песок гравелистый'] == 'PesokGraviy.json'
    assert SOIL_TYPE_TO_HATCH_FILE['песок с гравием'] == 'PesokGraviy.json'


def test_load_registered_hatch_uses_normalization_and_keeps_distinct_patterns() -> None:
    gravel = load_registered_hatch(' ГРАВИЙ ')
    gravelly_sand = load_registered_hatch('Песок гравелистый')
    peat = load_registered_hatch('  ТОРФ  ')

    assert gravel is not None
    assert gravelly_sand is not None
    assert peat is not None
    assert gravel.title == 'graviy'
    assert gravelly_sand.title == 'PesokGraviy'
    assert gravel.source_file != gravelly_sand.source_file
    assert peat.source_file.endswith('Torf.json')


def test_interactive_hatch_mode_is_sparser_for_heavy_registered_hatches() -> None:
    rect = (0.0, 0.0, 120.0, 320.0)
    for soil_name in ('гравий', 'песок гравелистый'):
        pattern = load_registered_hatch(soil_name)
        assert pattern is not None
        interactive = _CountCanvas()
        export = _CountCanvas()
        render_hatch_pattern(interactive, rect, pattern, tags=('interactive',), scale_info={'usage': HATCH_USAGE_EDITOR_INTERACTIVE, 'logical_rect': rect})
        render_hatch_pattern(export, rect, pattern, tags=('export',), scale_info={'usage': HATCH_USAGE_PROTOCOL_EXPORT, 'logical_rect': rect})
        interactive_total = interactive.lines + interactive.ovals
        export_total = export.lines + export.ovals
        assert interactive_total < export_total
