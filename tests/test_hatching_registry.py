from src.zondeditor.domain.hatching.registry import (
    SOIL_TYPE_TO_HATCH_ASSET,
    SOIL_TYPE_TO_HATCH_FILE,
    SOIL_TYPE_TO_PAT_FILE,
    load_registered_hatch,
    load_registered_pat_pattern,
    normalize_soil_type,
    resolve_hatch_asset,
)


def test_normalize_soil_type_handles_spaces_case_and_yo() -> None:
    assert normalize_soil_type("  ЁЛКА  ") == "елка"


def test_registry_supports_external_hatch_synonyms() -> None:
    assert SOIL_TYPE_TO_HATCH_FILE["гравий"] == "graviy.json"
    assert SOIL_TYPE_TO_HATCH_FILE["гравийный грунт"] == "graviy.json"
    assert SOIL_TYPE_TO_HATCH_FILE["песок гравелистый"] == "PesokGraviy.json"
    assert SOIL_TYPE_TO_HATCH_FILE["песок с гравием"] == "PesokGraviy.json"
    assert SOIL_TYPE_TO_PAT_FILE["гравий"] == "graviy.pat"
    assert SOIL_TYPE_TO_HATCH_ASSET["песок"] == "pesok"


def test_resolve_hatch_asset_returns_both_json_and_pat_paths() -> None:
    asset = resolve_hatch_asset(" ГРАВИЙ ")
    assert asset is not None
    assert asset.json_file == "graviy.json"
    assert asset.pat_file == "graviy.pat"
    assert asset.json_path.name == "graviy.json"
    assert asset.pat_path.name == "graviy.pat"


def test_load_registered_hatch_uses_normalization_and_keeps_distinct_patterns() -> None:
    gravel = load_registered_hatch(" ГРАВИЙ ")
    gravelly_sand = load_registered_hatch("Песок гравелистый")
    peat = load_registered_hatch("  ТОРФ  ")

    assert gravel is not None
    assert gravelly_sand is not None
    assert peat is not None
    assert gravel.title == "graviy"
    assert gravelly_sand.title == "PesokGraviy"
    assert gravel.source_file != gravelly_sand.source_file
    assert peat.source_file.endswith("Torf.json")


def test_load_registered_pat_pattern_uses_pat_assets() -> None:
    gravel = load_registered_pat_pattern(" ГРАВИЙ ")
    peat = load_registered_pat_pattern("  ТОРФ  ")

    assert gravel is not None
    assert peat is not None
    assert gravel.title == "graviy"
    assert gravel.source_file.endswith("graviy.pat")
    assert peat.source_file.endswith("Torf.pat")
    assert len(gravel.definition) == 8
