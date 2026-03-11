from src.zondeditor.domain.calc_applicability import CalcStatus, evaluate_method_applicability
from src.zondeditor.domain.calc_pipeline import build_calc_rows
from src.zondeditor.domain.layers import Layer, SoilType, calc_mode_for_soil
from src.zondeditor.domain.models import TestData


def _mk_test(tid, layers):
    depth = [str(x / 10) for x in range(0, 61)]
    qc = [str(1 + (x / 20)) for x in range(0, 61)]
    fs = [str(10 + (x / 5)) for x in range(0, 61)]
    t = TestData(tid=tid, dt="", depth=depth, qc=qc, fs=fs, layers=layers)
    t.export_on = True
    return t


def test_applicability_fill_requires_manual_confirmation():
    res = evaluate_method_applicability(soil_type="насыпной", fill_subtype="песчаный", profile_method="SP446_APP_J", allow_fill_by_material=False)
    assert res.status == CalcStatus.LAB_ONLY
    assert res.requires_manual_confirmation is True


def test_pipeline_collects_rows_and_not_applicable():
    layers = [
        Layer(top_m=0.0, bot_m=1.0, ige_id="ИГЭ-1", soil_type=SoilType.SAND, calc_mode=calc_mode_for_soil(SoilType.SAND)),
        Layer(top_m=1.0, bot_m=2.0, ige_id="ИГЭ-6", soil_type=SoilType.PEAT, calc_mode=calc_mode_for_soil(SoilType.PEAT)),
    ]
    tests = [_mk_test(1, layers)]
    registry = {
        "ИГЭ-1": {"soil_type": "песок"},
        "ИГЭ-6": {"soil_type": "торф"},
    }
    rows, _samples = build_calc_rows(tests=tests, ige_registry=registry, method="SP446_APP_J")
    by = {r["ige_id"]: r for r in rows}
    assert by["ИГЭ-1"]["status"] == "CALCULATED"
    assert by["ИГЭ-1"]["n_points"] > 0
    assert by["ИГЭ-6"]["status"] == "NOT_APPLICABLE"
