from src.zondeditor.ui.ribbon import RibbonView


def test_ige_ui_profile_routes_supported_soils_to_full_cards():
    ribbon = RibbonView.__new__(RibbonView)
    assert ribbon._ige_ui_profile("песок") == "sand"
    assert ribbon._ige_ui_profile("песок гравелистый") == "simplified"
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
    ribbon._ige_rows_cache = {}
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

    ribbon._render_ige_cards = lambda rows, soils, can_delete: (rebuilds.append((list(rows), list(soils), bool(can_delete))), ribbon._ige_cards.update({"ИГЭ-1": object()}), ribbon._ige_rows_cache.update({"ИГЭ-1": dict(rows[0])}))
    ribbon._replace_ige_card = lambda row, soils, can_delete: None
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


def test_set_layers_updates_only_changed_card_without_full_rebuild():
    ribbon = RibbonView.__new__(RibbonView)
    rows_initial = [
        {"ige_id": "ИГЭ-1", "label": "ИГЭ-1", "soil": "глина", "consistency": "тугопластичная", "notes": ""},
        {"ige_id": "ИГЭ-2", "label": "ИГЭ-2", "soil": "песок", "sand_kind": "", "sand_water_saturation": "", "density_state": "", "sand_is_alluvial": False, "consistency": "", "fill_subtype": "", "notes": ""},
    ]
    rows_changed = [
        {"ige_id": "ИГЭ-1", "label": "ИГЭ-1", "soil": "глина", "consistency": "мягкопластичная", "notes": ""},
        {"ige_id": "ИГЭ-2", "label": "ИГЭ-2", "soil": "песок", "sand_kind": "", "sand_water_saturation": "", "density_state": "", "sand_is_alluvial": False, "consistency": "", "fill_subtype": "", "notes": ""},
    ]
    soils = ["песок", "глина"]

    ribbon._layer_rows = list(rows_initial)
    ribbon._ige_soil_values = list(soils)
    ribbon._ige_cards = {"ИГЭ-1": object(), "ИГЭ-2": object()}
    ribbon._ige_order = ["ИГЭ-1", "ИГЭ-2"]
    class _DummyButton:
        def __init__(self):
            self.states = []

        def configure(self, **kwargs):
            self.states.append(kwargs)

        def pack(self, *args, **kwargs):
            return None

    ribbon._add_ige_btn = _DummyButton()
    ribbon.commands = {"add_ige": lambda: None}
    ribbon._ige_columns_frame = object()
    rebuilds: list[tuple[list[dict], list[str], bool]] = []
    replacements: list[tuple[str, str]] = []
    sync_calls: list[str] = []

    ribbon._render_ige_cards = lambda rows, soils, can_delete: rebuilds.append((list(rows), list(soils), bool(can_delete)))
    ribbon._replace_ige_card = lambda row, soils, can_delete: replacements.append((str(row.get("ige_id")), str(row.get("consistency", ""))))
    ribbon._sync_ige_canvas = lambda: sync_calls.append("sync")
    ribbon._ige_card_metrics = lambda: (200, 4, 1)
    ribbon._ige_rows_cache = {
        "ИГЭ-1": {"ige_id": "ИГЭ-1", "label": "ИГЭ-1", "soil": "глина", "consistency": "тугопластичная", "notes": ""},
        "ИГЭ-2": {"ige_id": "ИГЭ-2", "label": "ИГЭ-2", "soil": "песок", "sand_kind": "", "sand_water_saturation": "", "density_state": "", "sand_is_alluvial": False, "consistency": "", "fill_subtype": "", "notes": ""},
    }

    ribbon.set_layers(rows_changed, soils, can_add=True, can_delete=True)

    assert rebuilds == []
    assert replacements == [("ИГЭ-1", "мягкопластичная")]
    assert sync_calls == ["sync"]


def test_ige_ui_profile_hides_secondary_fields_for_gravelly_sand():
    ribbon = RibbonView.__new__(RibbonView)
    row = {"soil": "песок гравелистый", "sand_kind": "гравелистый"}
    assert ribbon._ige_ui_profile("песок гравелистый", row) == "simplified"
