from src.zondeditor.calculations.ige_policy import build_ige_display_label, get_ige_profile, is_ige_calculable


def test_build_ige_display_label_distinguishes_loams_by_consistency():
    assert build_ige_display_label("ИГЭ-1", label="ИГЭ-1", soil_name="суглинок", params={"consistency": "тугопластичная"}) == "ИГЭ-1"
    assert build_ige_display_label("ИГЭ-2", label="ИГЭ-2", soil_name="суглинок", params={"consistency": "мягкопластичная"}) == "ИГЭ-2"


def test_build_ige_display_label_distinguishes_sands_by_kind():
    assert build_ige_display_label("ИГЭ-4", label="ИГЭ-4", soil_name="песок", params={"sand_kind": "средней крупности"}) == "ИГЭ-4"
    assert build_ige_display_label("ИГЭ-5", label="ИГЭ-5", soil_name="песок", params={"sand_kind": "мелкий"}) == "ИГЭ-5"


def test_gravelly_sand_uses_descriptive_profile_and_is_not_calculable():
    profile = get_ige_profile(soil_name="песок гравелистый")
    assert profile.ui_profile == "descriptive"
    assert profile.available_fields == ()
    assert profile.is_calculable is False
    assert is_ige_calculable(soil_name="песок гравелистый") is False
    assert build_ige_display_label("ИГЭ-7", label="ИГЭ-7", soil_name="песок гравелистый", params={"sand_kind": "гравелистый"}) == "ИГЭ-7"


def test_other_special_soils_use_descriptive_profile():
    for soil in ("торф", "песчаник", "аргиллит", "гравийный грунт"):
        profile = get_ige_profile(soil_name=soil)
        assert profile.ui_profile == "descriptive"
        assert profile.is_calculable is False
