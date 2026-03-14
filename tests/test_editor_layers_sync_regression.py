from types import SimpleNamespace

from src.zondeditor.ui.editor import GeoCanvasEditor


class _RibbonStub:
    def __init__(self):
        self.layers_calls = 0
        self.layer_ige_var = SimpleNamespace(set=lambda _v: None)
        self.layer_soil_var = SimpleNamespace(set=lambda _v: None)
        self.layer_mode_var = SimpleNamespace(set=lambda _v: None)

    def set_layers(self, *_args, **_kwargs):
        self.layers_calls += 1


def test_sync_layers_panel_no_nameerror_when_excluded_tests_not_in_scope():
    editor = GeoCanvasEditor.__new__(GeoCanvasEditor)
    editor.ribbon_view = _RibbonStub()
    editor.ige_registry = {
        "ИГЭ-1": {"soil_type": "супесь", "ordinal": 1, "label": "ИГЭ-1"},
    }
    editor._ensure_default_iges = lambda: None
    editor._ige_sort_key = lambda x: x
    editor._ensure_ige_entry = lambda ige_id: dict(editor.ige_registry.get(ige_id) or {})
    editor._ensure_ige_cpt_fields = lambda ent: ent
    editor._ige_id_to_num = lambda _ige_id: 1
    editor._sync_calc_table = lambda: None

    # Regression check: should not raise NameError (excluded_tests undefined)
    editor._sync_layers_panel()

    assert editor.ribbon_view.layers_calls == 1
