from pathlib import Path

import pytest

from src.zondeditor.calculations.lookup_loader import LookupFileError, resolve_lookup_path
from src.zondeditor.calculations.preview_model import NOTE_LEGACY_SUPES, NOTE_PRELIM_FILL, NOTE_REFERENCE_ONLY, StaticCalcRow
from src.zondeditor.calculations.static_calc_engine import (
    StaticCalcOptions,
    convert_cohesion_mpa_to_kpa,
    run_static_sounding_calculation,
)
from src.zondeditor.domain.layers import Layer, SoilType, calc_mode_for_soil
from src.zondeditor.domain.models import TestData


def _make_test(ige_id: str, soil_type: SoilType, depths: list[float], qcs: list[float]) -> TestData:
    layer = Layer(
        top_m=min(depths) - 0.01,
        bot_m=max(depths) + 0.01,
        ige_id=ige_id,
        soil_type=soil_type,
        calc_mode=calc_mode_for_soil(soil_type),
    )
    test = TestData(
        tid=1,
        dt="01.02.2026 10:00",
        depth=[f"{value:.2f}" for value in depths],
        qc=[f"{value:.2f}" for value in qcs],
        fs=["0" for _ in qcs],
        layers=[layer],
    )
    test.export_on = True
    return test


def _run(registry: dict, test: TestData | list[TestData], *, legacy_supes: bool = False, fill_preliminary: bool = False, alluvial: bool = False, allow_reference: bool = False):
    tests = test if isinstance(test, list) else [test]
    return run_static_sounding_calculation(
        tests=tests,
        ige_registry=registry,
        project_name="Объект",
        options=StaticCalcOptions(
            use_legacy_sandy_loam_sp446=legacy_supes,
            allow_fill_preliminary=fill_preliminary,
            allow_reference_on_insufficient_stats=allow_reference,
            alluvial_sands=alluvial,
        ),
    )


def test_lookup_file_resolves_from_project_root():
    path = resolve_lookup_path()
    assert path.exists()
    assert path.name == "sp446_static_calc_lookup_final.csv"


def test_lookup_file_error_when_missing():
    with pytest.raises(LookupFileError):
        resolve_lookup_path("raschet/missing_lookup.csv")


def test_sand_e_is_taken_from_j2():
    test = _make_test("ИГЭ-1", SoilType.SAND, [1.1, 1.2, 1.3, 1.4, 1.5, 1.6], [10, 10, 10, 10, 10, 10])
    registry = {"ИГЭ-1": {"soil_type": SoilType.SAND.value, "sand_kind": "мелкий", "sand_water_saturation": "влажный"}}
    row = _run(registry, test, alluvial=False, allow_reference=True).rows[0]
    assert row.e_n_mpa == pytest.approx(30.0)


def test_sand_phi_uses_j3_column_for_depth_le_2m():
    test = _make_test("ИГЭ-1", SoilType.SAND, [1.1, 1.2, 1.3, 1.4, 1.5, 1.6], [3, 3, 3, 3, 3, 3])
    registry = {"ИГЭ-1": {"soil_type": SoilType.SAND.value, "sand_kind": "мелкий", "sand_water_saturation": "влажный"}}
    row = _run(registry, test, alluvial=False, allow_reference=True).rows[0]
    assert row.phi_n_deg == pytest.approx(30.0)


def test_sand_phi_uses_j3_column_for_depth_ge_5m():
    test = _make_test("ИГЭ-1", SoilType.SAND, [5.1, 5.2, 5.3, 5.4, 5.5, 5.6], [3, 3, 3, 3, 3, 3])
    registry = {"ИГЭ-1": {"soil_type": SoilType.SAND.value, "sand_kind": "мелкий", "sand_water_saturation": "влажный"}}
    row = _run(registry, test, alluvial=False, allow_reference=True).rows[0]
    assert row.phi_n_deg == pytest.approx(28.0)


def test_sand_phi_interpolates_for_depth_between_2_and_5m():
    test = _make_test("ИГЭ-1", SoilType.SAND, [3.25, 3.35, 3.45, 3.55, 3.65, 3.75], [3, 3, 3, 3, 3, 3])
    registry = {"ИГЭ-1": {"soil_type": SoilType.SAND.value, "sand_kind": "мелкий", "sand_water_saturation": "влажный"}}
    row = _run(registry, test, alluvial=False, allow_reference=True).rows[0]
    assert row.phi_n_deg == pytest.approx(29.0)


def test_loam_is_calculated_from_j4():
    test = _make_test("ИГЭ-2", SoilType.LOAM, [3.1, 3.2, 3.3, 3.4, 3.5, 3.6], [4, 4, 4, 4, 4, 4])
    registry = {"ИГЭ-2": {"soil_type": SoilType.LOAM.value, "consistency": "тугопластичная"}}
    row = _run(registry, test, allow_reference=True).rows[0]
    assert row.e_n_mpa == pytest.approx(10.0)
    assert row.phi_n_deg == pytest.approx(18.0)
    assert row.c_n_kpa == pytest.approx(16.0)


def test_clay_is_calculated_from_j4():
    test = _make_test("ИГЭ-3", SoilType.CLAY, [3.1, 3.2, 3.3, 3.4, 3.5, 3.6], [4, 4, 4, 4, 4, 4])
    registry = {"ИГЭ-3": {"soil_type": SoilType.CLAY.value, "consistency": "твердая"}}
    row = _run(registry, test, allow_reference=True).rows[0]
    assert row.e_n_mpa == pytest.approx(20.0)
    assert row.phi_n_deg == pytest.approx(26.0)
    assert row.c_n_kpa == pytest.approx(41.0)


def test_cohesion_conversion_helper_converts_mpa_to_kpa():
    assert convert_cohesion_mpa_to_kpa(0.015) == pytest.approx(15.0)


def test_sandy_loam_is_blocked_without_legacy_flag():
    test = _make_test("ИГЭ-4", SoilType.SANDY_LOAM, [2.1, 2.2, 2.3, 2.4, 2.5, 2.6], [3, 3, 3, 3, 3, 3])
    registry = {"ИГЭ-4": {"soil_type": SoilType.SANDY_LOAM.value, "consistency": "пластичная"}}
    row = _run(registry, test, legacy_supes=False).rows[0]
    assert row.blocked is True
    assert row.phi_n_deg is None


def test_sandy_loam_is_calculated_with_legacy_flag():
    test = _make_test("ИГЭ-4", SoilType.SANDY_LOAM, [2.1, 2.2, 2.3, 2.4, 2.5, 2.6], [3, 3, 3, 3, 3, 3])
    registry = {"ИГЭ-4": {"soil_type": SoilType.SANDY_LOAM.value, "consistency": "пластичная"}}
    row = _run(registry, test, legacy_supes=True, allow_reference=True).rows[0]
    assert row.blocked is False
    assert NOTE_LEGACY_SUPES in row.note_marks
    assert row.e_n_mpa == pytest.approx(16.0)


def test_fill_is_blocked_without_preliminary_flag():
    test = _make_test("ИГЭ-5", SoilType.FILL, [2.1, 2.2, 2.3, 2.4, 2.5, 2.6], [5, 5, 5, 5, 5, 5])
    registry = {"ИГЭ-5": {"soil_type": SoilType.FILL.value, "fill_subtype": "песчаный"}}
    row = _run(registry, test, fill_preliminary=False, alluvial=False).rows[0]
    assert row.blocked is True


def test_fill_is_calculated_preliminarily_by_material():
    test = _make_test("ИГЭ-5", SoilType.FILL, [3.2, 3.3, 3.4, 3.5, 3.6, 3.7], [5, 5, 5, 5, 5, 5])
    registry = {"ИГЭ-5": {"soil_type": SoilType.FILL.value, "fill_subtype": "песчаный"}}
    row = _run(registry, test, fill_preliminary=True, alluvial=False, allow_reference=True).rows[0]
    assert row.blocked is False
    assert NOTE_PRELIM_FILL in row.note_marks
    assert row.e_n_mpa == pytest.approx(15.0)


def test_clayey_fill_is_calculated_preliminarily_by_material():
    test = _make_test("ИГЭ-5", SoilType.FILL, [3.2, 3.3, 3.4, 3.5, 3.6, 3.7], [5, 5, 5, 5, 5, 5])
    registry = {"ИГЭ-5": {"soil_type": SoilType.FILL.value, "fill_subtype": "глинистый"}}
    row = _run(registry, test, fill_preliminary=True, allow_reference=True).rows[0]
    assert row.blocked is False
    assert NOTE_PRELIM_FILL in row.note_marks
    assert row.e_n_mpa == pytest.approx(14.0)
    assert row.phi_n_deg == pytest.approx(20.0)
    assert row.c_n_kpa == pytest.approx(30.0)
    assert row.phi_i_deg is not None and row.c_i_kpa is not None


def test_fill_with_more_than_10_percent_construction_material_is_blocked_normatively():
    test = _make_test("ИГЭ-5", SoilType.FILL, [3.2, 3.3, 3.4, 3.5, 3.6, 3.7], [5, 5, 5, 5, 5, 5])
    registry = {"ИГЭ-5": {"soil_type": SoilType.FILL.value, "fill_subtype": "более 10% строительного материала"}}
    row = _run(registry, test, fill_preliminary=True, allow_reference=True).rows[0]
    assert row.blocked is True
    assert row.phi_n_deg is None and row.c_n_kpa is None
    assert "для насыпного грунта с содержанием строительного мусора более 10%" in row.detail_reason.lower()


def test_reference_mark_is_added_when_n_lt_6():
    test = _make_test("ИГЭ-1", SoilType.SAND, [1.1, 1.2, 1.3, 1.4, 1.5], [3, 3, 3, 3, 3])
    registry = {"ИГЭ-1": {"soil_type": SoilType.SAND.value, "sand_kind": "мелкий", "sand_water_saturation": "влажный"}}
    row = _run(registry, test, alluvial=False, allow_reference=True).rows[0]
    assert NOTE_REFERENCE_ONLY in row.note_marks
    assert row.reference_only is True


def test_reference_mark_is_added_when_variation_gt_030():
    test = _make_test("ИГЭ-1", SoilType.SAND, [1.1, 1.2, 1.3, 1.4, 1.5, 1.6], [1, 1, 1, 1, 10, 10])
    registry = {"ИГЭ-1": {"soil_type": SoilType.SAND.value, "sand_kind": "мелкий", "sand_water_saturation": "влажный"}}
    row = _run(registry, test, alluvial=False, allow_reference=True).rows[0]
    assert NOTE_REFERENCE_ONLY in row.note_marks
    assert row.reference_only is True


def test_note_marks_can_be_combined():
    test = _make_test("ИГЭ-4", SoilType.SANDY_LOAM, [2.1, 2.2, 2.3, 2.4, 2.5], [3, 3, 3, 3, 3])
    registry = {"ИГЭ-4": {"soil_type": SoilType.SANDY_LOAM.value, "consistency": "пластичная"}}
    row = _run(registry, test, legacy_supes=True, allow_reference=True).rows[0]
    assert row.note_marks == (NOTE_LEGACY_SUPES, NOTE_REFERENCE_ONLY)


def test_n_is_counted_by_active_soundings_not_depth_points():
    tests = []
    for tid in range(1, 7):
        test = _make_test("ИГЭ-1", SoilType.SAND, [1.1, 1.2, 1.3], [3, 3, 3])
        test.tid = tid
        tests.append(test)
    registry = {"ИГЭ-1": {"soil_type": SoilType.SAND.value, "sand_kind": "мелкий", "sand_water_saturation": "влажный"}}
    row = _run(registry, tests, alluvial=False).rows[0]
    assert row.n_points == 6
    assert row.phi_i_deg is not None and row.phi_ii_deg is not None
    assert NOTE_REFERENCE_ONLY not in row.note_marks


def test_disabled_sounding_reduces_n_and_blocks_design_values_without_reference_flag():
    tests = []
    for tid in range(1, 7):
        test = _make_test("ИГЭ-1", SoilType.SAND, [1.1, 1.2, 1.3], [3, 3, 3])
        test.tid = tid
        tests.append(test)
    tests[-1].export_on = False
    registry = {"ИГЭ-1": {"soil_type": SoilType.SAND.value, "sand_kind": "мелкий", "sand_water_saturation": "влажный"}}
    row = _run(registry, tests, alluvial=False, allow_reference=False).rows[0]
    assert row.n_points == 5
    assert row.blocked is False
    assert row.phi_i_deg is None and row.c_i_kpa is None and row.phi_ii_deg is None and row.c_ii_kpa is None
    assert "число опытов n = 5" in row.detail_reason


def test_disabled_sounding_reduces_n_and_keeps_reference_values_with_flag():
    tests = []
    for tid in range(1, 7):
        test = _make_test("ИГЭ-1", SoilType.SAND, [1.1, 1.2, 1.3], [3, 3, 3])
        test.tid = tid
        tests.append(test)
    tests[-1].export_on = False
    registry = {"ИГЭ-1": {"soil_type": SoilType.SAND.value, "sand_kind": "мелкий", "sand_water_saturation": "влажный"}}
    row = _run(registry, tests, alluvial=False, allow_reference=True).rows[0]
    assert row.n_points == 5
    assert row.blocked is False
    assert NOTE_REFERENCE_ONLY in row.note_marks
    assert row.phi_i_deg is not None and row.phi_ii_deg is not None


def test_variation_gt_threshold_blocks_design_values_without_reference_flag():
    tests = []
    values = [1, 1, 1, 1, 10, 10]
    for tid, qc in enumerate(values, start=1):
        test = _make_test("ИГЭ-1", SoilType.SAND, [1.1, 1.2, 1.3], [qc, qc, qc])
        test.tid = tid
        tests.append(test)
    registry = {"ИГЭ-1": {"soil_type": SoilType.SAND.value, "sand_kind": "мелкий", "sand_water_saturation": "влажный"}}
    row = _run(registry, tests, alluvial=False, allow_reference=False).rows[0]
    assert row.n_points == 6
    assert row.blocked is False
    assert row.phi_i_deg is None and row.c_i_kpa is None and row.phi_ii_deg is None and row.c_ii_kpa is None
    assert "коэффициент вариации" in row.detail_reason


def test_variation_gt_threshold_keeps_reference_values_with_flag():
    tests = []
    values = [1, 1, 1, 1, 10, 10]
    for tid, qc in enumerate(values, start=1):
        test = _make_test("ИГЭ-1", SoilType.SAND, [1.1, 1.2, 1.3], [qc, qc, qc])
        test.tid = tid
        tests.append(test)
    registry = {"ИГЭ-1": {"soil_type": SoilType.SAND.value, "sand_kind": "мелкий", "sand_water_saturation": "влажный"}}
    row = _run(registry, tests, alluvial=False, allow_reference=True).rows[0]
    assert row.n_points == 6
    assert NOTE_REFERENCE_ONLY in row.note_marks
    assert row.phi_i_deg is not None and row.phi_ii_deg is not None


def test_display_rounding_is_applied_only_on_summary_values():
    row = StaticCalcRow(
        ige_id="ИГЭ-9",
        soil_name="Песок мелкий, влажный",
        qc_avg_mpa=3.456,
        e_n_mpa=8.26,
        phi_n_deg=31.6,
        c_n_kpa=15.6,
        phi_i_deg=30.6,
        c_i_kpa=14.6,
        phi_ii_deg=31.4,
        c_ii_kpa=15.4,
        note_marks=(NOTE_REFERENCE_ONLY,),
    )
    assert row.summary_values() == (
        "9",
        "Песок мелкий, влажный",
        "3.46",
        "8.3",
        "32",
        "16",
        "31***",
        "15***",
        "31***",
        "15***",
    )


def test_legacy_and_reference_marks_are_attached_only_to_relevant_values():
    row = StaticCalcRow(
        ige_id="ИГЭ-10",
        soil_name="Супесь пластичная",
        qc_avg_mpa=2.0,
        e_n_mpa=12.0,
        phi_n_deg=24.0,
        c_n_kpa=13.0,
        phi_i_deg=23.0,
        c_i_kpa=12.0,
        phi_ii_deg=24.0,
        c_ii_kpa=12.0,
        note_marks=(NOTE_LEGACY_SUPES, NOTE_REFERENCE_ONLY),
    )
    assert row.summary_values() == (
        "10",
        "Супесь пластичная",
        "2.00",
        "12.0*",
        "24*",
        "13*",
        "23* ***",
        "12* ***",
        "24* ***",
        "12* ***",
    )


def test_export_summary_values_use_engineering_column_order_and_decimal_comma():
    row = StaticCalcRow(
        ige_id="ИГЭ-11",
        soil_name="Суглинок тугопластичный",
        qc_avg_mpa=9.3,
        e_n_mpa=27.1,
        phi_n_deg=22.0,
        c_n_kpa=33.0,
        phi_i_deg=21.0,
        c_i_kpa=31.0,
        phi_ii_deg=22.0,
        c_ii_kpa=32.0,
        note_marks=(NOTE_REFERENCE_ONLY,),
    )
    assert row.export_summary_values() == (
        "11",
        "Суглинок тугопластичный",
        "9,30",
        "22",
        "33",
        "21***",
        "31***",
        "22***",
        "32***",
        "27,1",
    )
