from src.zondeditor.ui.editor import GeoCanvasEditor


def test_apply_gxl_calibration_uses_most_common_values():
    editor = object.__new__(GeoCanvasEditor)
    applied: dict[str, str] = {}

    def _set_common_params(upd, _geo_kind=None):
        applied.update(dict(upd or {}))

    editor._set_common_params = _set_common_params
    editor.geo_kind = "K2"

    meta_rows = [
        {"key": "scale", "value": "1000"},
        {"key": "scale", "value": "1000"},
        {"key": "scale", "value": "250"},
        {"key": "scaleostria", "value": "50"},
        {"key": "scaleostria", "value": "50"},
        {"key": "scalemufta", "value": "20"},
        {"key": "scalemufta", "value": "20"},
        {"key": "scalemufta", "value": "10"},
    ]

    GeoCanvasEditor._apply_gxl_calibration_from_meta(editor, meta_rows)

    assert applied["controller_scale_div"] == "1000"
    assert applied["cone_kn"] == "50"
    assert applied["sleeve_kn"] == "20"
