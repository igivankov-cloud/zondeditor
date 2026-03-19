from src.zondeditor.domain.experience_column import (
    ColumnInterval,
    ExperienceColumn,
    build_column_from_layers,
    normalize_column,
    remove_column_interval,
    split_column_interval,
)
from src.zondeditor.domain.layers import Layer, SoilType, calc_mode_for_soil


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


def test_split_and_remove_column_interval_roundtrip():
    column = ExperienceColumn(0.0, 3.0, [ColumnInterval(0.0, 3.0, "ИГЭ-1")])
    column = split_column_interval(column, 0, new_ige_id="ИГЭ-2")
    assert len(column.intervals) == 2
    column = remove_column_interval(column, 0)
    assert len(column.intervals) == 1
    assert column.intervals[0].from_depth == 0.0
    assert column.intervals[0].to_depth == 3.0
