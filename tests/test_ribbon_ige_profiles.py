from src.zondeditor.ui.ribbon import RibbonView


def test_ige_ui_profile_routes_supported_soils_to_full_cards():
    ribbon = RibbonView.__new__(RibbonView)
    assert ribbon._ige_ui_profile("песок") == "sand"
    assert ribbon._ige_ui_profile("песок гравелистый") == "sand"
    assert ribbon._ige_ui_profile("супесь") == "clay_supes"
    assert ribbon._ige_ui_profile("суглинок") == "clay_general"
    assert ribbon._ige_ui_profile("глина") == "clay_general"
    assert ribbon._ige_ui_profile("насыпной") == "fill"


def test_ige_ui_profile_routes_special_soils_to_simplified_card():
    ribbon = RibbonView.__new__(RibbonView)
    for soil in ("аргиллит", "песчаник", "гравийный грунт", "торф"):
        assert ribbon._ige_ui_profile(soil) == "simplified"
