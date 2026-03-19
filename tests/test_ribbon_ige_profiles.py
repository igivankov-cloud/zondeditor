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


def test_set_layers_skips_ige_cards_rebuild_when_rows_unchanged():
    ribbon = RibbonView.__new__(RibbonView)
    ribbon._layer_rows = []
    ribbon._ige_soil_values = []
    ribbon._ige_cards = {}
    ribbon._ige_order = []
    ribbon._add_ige_btn = None
    ribbon.commands = {"add_ige": lambda: None}
    ribbon._ige_columns_frame = object()
    rebuilds: list[tuple[list[dict], list[str], bool]] = []
    sync_calls: list[str] = []

    class _DummyButton:
        def __init__(self):
            self.states = []

        def configure(self, **kwargs):
            self.states.append(kwargs)

        def pack(self, *args, **kwargs):
            return None

    ribbon._render_ige_cards = lambda rows, soils, can_delete: (rebuilds.append((list(rows), list(soils), bool(can_delete))), ribbon._ige_cards.update({"ИГЭ-1": object()}))
    ribbon._sync_ige_canvas = lambda: sync_calls.append("sync")
    ribbon._ige_card_metrics = lambda: (200, 4, 1)

    import src.zondeditor.ui.ribbon as ribbon_module

    original_button = ribbon_module.ttk.Button
    ribbon_module.ttk.Button = lambda *args, **kwargs: _DummyButton()
    try:
        rows = [{"ige_id": "ИГЭ-1", "label": "ИГЭ-1", "soil": "песок", "sand_kind": "", "sand_water_saturation": "", "density_state": "", "sand_is_alluvial": False, "consistency": "", "fill_subtype": "", "notes": ""}]
        soils = ["песок", "глина"]
        ribbon.set_layers(rows, soils, can_add=True, can_delete=True)
        ribbon.set_layers(rows, soils, can_add=True, can_delete=True)
    finally:
        ribbon_module.ttk.Button = original_button

    assert len(rebuilds) == 1
    assert sync_calls == ["sync", "sync"]
