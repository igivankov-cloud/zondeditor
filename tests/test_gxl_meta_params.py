from src.zondeditor.ui.editor import GeoCanvasEditor
from src.zondeditor.io.gxl_reader import parse_gxl_file


def test_apply_calibration_from_meta_uses_most_common_values():
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

    GeoCanvasEditor._apply_calibration_from_meta(editor, meta_rows)

    assert applied["controller_scale_div"] == "1000"
    assert applied["cone_kn"] == "50"
    assert applied["sleeve_kn"] == "20"


def test_apply_calibration_from_meta_supports_zond_max_aliases():
    editor = object.__new__(GeoCanvasEditor)
    applied: dict[str, str] = {}

    def _set_common_params(upd, _geo_kind=None):
        applied.update(dict(upd or {}))

    editor._set_common_params = _set_common_params
    editor.geo_kind = "K4"

    meta_rows = [
        {"key": "scalemax", "value": "1000"},
        {"key": "conemax", "value": "50"},
        {"key": "sleevemax", "value": "20"},
    ]

    GeoCanvasEditor._apply_calibration_from_meta(editor, meta_rows)

    assert applied["controller_scale_div"] == "1000"
    assert applied["cone_kn"] == "50"
    assert applied["sleeve_kn"] == "20"


def test_parse_gxl_file_collects_zond_max_meta(tmp_path):
    p = tmp_path / "sample.gxl"
    p.write_text(
        """<?xml version="1.0" encoding="windows-1251"?>
<exportfile>
  <object>
    <test>
      <numtest>1</numtest>
      <date>01.01.2026</date>
      <deepbegin>1,0</deepbegin>
      <stepzond>0,05</stepzond>
      <controllertype>2</controllertype>
      <zond>
        <scalemax>1000</scalemax>
        <conemax>50</conemax>
        <sleevemax>20</sleevemax>
      </zond>
      <dat>10;2;0;0;0</dat>
    </test>
  </object>
</exportfile>
""",
        encoding="cp1251",
    )
    _tests, meta_rows = parse_gxl_file(p)
    kv = {(row.get("key"), row.get("value")) for row in meta_rows}
    assert ("scalemax", "1000") in kv
    assert ("conemax", "50") in kv
    assert ("sleevemax", "20") in kv
