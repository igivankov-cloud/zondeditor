from src.zondeditor.domain.hatching.registry import SOIL_TYPE_TO_HATCH_FILE, load_registered_hatch, normalize_soil_type


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
