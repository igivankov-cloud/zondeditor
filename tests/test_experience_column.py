from src.zondeditor.domain.experience_column import (
    ColumnInterval,
    ExperienceColumn,
    append_bottom,
    build_column_from_layers,
    insert_between,
    normalize_column,
    remove_interval,
)
from src.zondeditor.domain.layers import Layer, SoilType, calc_mode_for_soil
from src.zondeditor.domain.models import TestData as _TestData
from src.zondeditor.ui.editor import GeoCanvasEditor


def _make_editor_for_grid(test: _TestData, *, show_geology_column: bool) -> GeoCanvasEditor:
    editor = GeoCanvasEditor.__new__(GeoCanvasEditor)
    editor.tests = [test]
    editor.show_geology_column = show_geology_column
    editor.step_m = 0.1
    editor.depth_start = 0.0
    editor.depth0_by_tid = {}
    editor.compact_1m = False
    editor.expanded_meters = set()
    editor.row_h_default = 22
    editor.row_h_compact_1m = 38
    editor._ensure_test_experience_column = lambda _t: _t.experience_column
    return editor


def test_build_column_from_layers_prepends_absolute_zero_segment():
    layers = [
        Layer(top_m=1.0, bot_m=2.0, ige_id="ИГЭ-2", soil_type=SoilType.SAND, calc_mode=calc_mode_for_soil(SoilType.SAND)),
        Layer(top_m=2.0, bot_m=4.0, ige_id="ИГЭ-3", soil_type=SoilType.CLAY, calc_mode=calc_mode_for_soil(SoilType.CLAY)),
    ]
    column = build_column_from_layers(layers, sounding_top=1.0, sounding_bottom=4.0)
    assert column.column_depth_start == 0.0
    assert column.column_depth_end == 4.0
    assert [(x.from_depth, x.to_depth, x.ige_id) for x in column.intervals] == [
        (0.0, 2.0, "ИГЭ-2"),
        (2.0, 4.0, "ИГЭ-3"),
    ]


def test_normalize_column_keeps_continuous_full_depth():
    column = normalize_column(
        ExperienceColumn(
            column_depth_start=0.0,
            column_depth_end=3.0,
            intervals=[ColumnInterval(0.4, 1.4, "ИГЭ-1"), ColumnInterval(1.4, 3.0, "ИГЭ-2")],
        )
    )
    assert column.intervals[0].from_depth == 0.0
    assert column.intervals[-1].to_depth == 3.0


def test_insert_between_takes_thickness_from_upper_part_of_lower_interval():
    column = ExperienceColumn(
        0.0,
        4.6,
        [
            ColumnInterval(0.0, 1.0, "ИГЭ-A"),
            ColumnInterval(1.0, 4.6, "ИГЭ-B"),
        ],
    )
    column = insert_between(column, 1, thickness=1.0, new_ige_id="ИГЭ-NEW")
    assert [(round(x.from_depth, 2), round(x.to_depth, 2), x.ige_id) for x in column.intervals] == [
        (0.0, 1.0, "ИГЭ-A"),
        (1.0, 2.0, "ИГЭ-NEW"),
        (2.0, 4.6, "ИГЭ-B"),
    ]


def test_append_bottom_takes_thickness_from_bottom_of_last_interval():
    column = ExperienceColumn(
        0.0,
        13.7,
        [
            ColumnInterval(0.0, 9.5, "ИГЭ-1"),
            ColumnInterval(9.5, 13.7, "ИГЭ-LAST"),
        ],
    )
    column = append_bottom(column, thickness=1.0, new_ige_id="ИГЭ-NEW")
    assert [(round(x.from_depth, 2), round(x.to_depth, 2), x.ige_id) for x in column.intervals] == [
        (0.0, 9.5, "ИГЭ-1"),
        (9.5, 12.7, "ИГЭ-LAST"),
        (12.7, 13.7, "ИГЭ-NEW"),
    ]


def test_remove_interval_returns_thickness_to_lower_neighbor_for_middle_insert():
    column = ExperienceColumn(
        0.0,
        4.6,
        [
            ColumnInterval(0.0, 1.0, "ИГЭ-A"),
            ColumnInterval(1.0, 2.0, "ИГЭ-NEW"),
            ColumnInterval(2.0, 4.6, "ИГЭ-B"),
        ],
    )
    column = remove_interval(column, 1)
    assert [(round(x.from_depth, 2), round(x.to_depth, 2), x.ige_id) for x in column.intervals] == [
        (0.0, 1.0, "ИГЭ-A"),
        (1.0, 4.6, "ИГЭ-B"),
    ]


def test_remove_interval_returns_thickness_to_upper_neighbor_for_bottom_insert():
    column = ExperienceColumn(
        0.0,
        13.7,
        [
            ColumnInterval(0.0, 9.5, "ИГЭ-1"),
            ColumnInterval(9.5, 12.7, "ИГЭ-LAST"),
            ColumnInterval(12.7, 13.7, "ИГЭ-NEW"),
        ],
    )
    column = remove_interval(column, 2)
    assert [(round(x.from_depth, 2), round(x.to_depth, 2), x.ige_id) for x in column.intervals] == [
        (0.0, 9.5, "ИГЭ-1"),
        (9.5, 13.7, "ИГЭ-LAST"),
    ]


def test_compute_depth_grid_uses_absolute_column_axis_when_column_visible():
    test = _TestData(
        tid=1,
        dt="",
        depth=["1.0", "1.1", "1.2"],
        qc=["1", "1", "1"],
        fs=["1", "1", "1"],
        experience_column=ExperienceColumn(0.0, 2.0, [ColumnInterval(0.0, 2.0, "ИГЭ-1")]),
    )
    editor = _make_editor_for_grid(test, show_geology_column=True)
    grid, _step, row_maps, _start_rows = editor._compute_depth_grid()
    assert grid[0] == 0.0
    assert grid[-1] == 2.0
    assert row_maps[0][10] == 0


def test_compute_depth_grid_keeps_data_axis_when_column_hidden():
    test = _TestData(
        tid=1,
        dt="",
        depth=["1.0", "1.1", "1.2"],
        qc=["1", "1", "1"],
        fs=["1", "1", "1"],
        experience_column=ExperienceColumn(0.0, 2.0, [ColumnInterval(0.0, 2.0, "ИГЭ-1")]),
    )
    editor = _make_editor_for_grid(test, show_geology_column=False)
    grid, _step, row_maps, _start_rows = editor._compute_depth_grid()
    assert grid[0] == 1.0
    assert row_maps[0][0] == 0


def test_build_grid_collapsed_uses_absolute_meter_rows_for_shifted_start():
    test = _TestData(
        tid=1,
        dt="",
        depth=["1.0", "1.1", "1.2"],
        qc=["1", "1", "1"],
        fs=["1", "1", "1"],
        experience_column=ExperienceColumn(0.0, 2.0, [ColumnInterval(0.0, 2.0, "ИГЭ-1")]),
    )
    editor = _make_editor_for_grid(test, show_geology_column=True)
    editor.compact_1m = True
    editor._build_grid()
    assert editor._grid_units[0] == ("meter", 0)
    assert editor._grid_units[1] == ("meter", 1)


def test_build_grid_expanded_keeps_absolute_zero_rows_for_shifted_start():
    test = _TestData(
        tid=1,
        dt="",
        depth=["1.0", "1.1", "1.2"],
        qc=["1", "1", "1"],
        fs=["1", "1", "1"],
        experience_column=ExperienceColumn(0.0, 2.0, [ColumnInterval(0.0, 2.0, "ИГЭ-1")]),
    )
    editor = _make_editor_for_grid(test, show_geology_column=True)
    editor.compact_1m = True
    editor.expanded_meters = {0, 1}
    editor._build_grid()
    assert editor._grid_base[0] == 0.0
    assert editor._grid_units[0] == ("row", 0)
    assert editor._grid_row_maps[0][10] == 0


def test_ige_display_includes_soil_name():
    editor = GeoCanvasEditor.__new__(GeoCanvasEditor)
    editor._ensure_ige_entry = lambda ige_id: {"soil_type": "суглинок"}
    assert editor._experience_column_ige_display("ИГЭ-1") == "ИГЭ-1 (суглинок)"


def test_ige_choices_use_existing_registry_ids():
    editor = GeoCanvasEditor.__new__(GeoCanvasEditor)
    editor.ige_registry = {"ИГЭ-2": {}, "ИГЭ-1": {}}
    editor._ige_id_to_num = lambda value: int(str(value).split("-")[-1])
    editor._ensure_ige_entry = lambda ige_id: {"soil_type": "песок" if ige_id == "ИГЭ-2" else "суглинок"}
    assert editor._experience_column_ige_choices() == [
        ("ИГЭ-1", "ИГЭ-1 (суглинок)"),
        ("ИГЭ-2", "ИГЭ-2 (песок)"),
    ]


def test_validate_experience_column_iges_accepts_existing_registry_values():
    editor = GeoCanvasEditor.__new__(GeoCanvasEditor)
    editor.ige_registry = {"ИГЭ-1": {}, "ИГЭ-2": {}}
    column = ExperienceColumn(0.0, 2.0, [ColumnInterval(0.0, 1.0, "ИГЭ-1"), ColumnInterval(1.0, 2.0, "ИГЭ-2")])
    assert editor._validate_experience_column_iges(column) is None


def test_validate_experience_column_iges_reports_missing_registry_value_without_picker():
    editor = GeoCanvasEditor.__new__(GeoCanvasEditor)
    editor.ige_registry = {"ИГЭ-1": {}}
    column = ExperienceColumn(0.0, 2.0, [ColumnInterval(0.0, 2.0, "ИГЭ-404")])
    msg = editor._validate_experience_column_iges(column)
    assert msg is not None
    assert "не найден" in msg.lower()
