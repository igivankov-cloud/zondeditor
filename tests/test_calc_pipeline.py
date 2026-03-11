from src.zondeditor.calculations.applicability import resolve_applicability
from src.zondeditor.calculations.protocol_builder import build_protocol
from src.zondeditor.calculations.sample_builder import build_ige_samples
from src.zondeditor.domain.layers import Layer, SoilType, calc_mode_for_soil
from src.zondeditor.domain.models import TestData


def _mk_test(tid, layers):
    depth = [str(x / 10) for x in range(0, 61)]
    qc = [str(1 + (x / 20)) for x in range(0, 61)]
    fs = [str(10 + (x / 5)) for x in range(0, 61)]
    t = TestData(tid=tid, dt="", depth=depth, qc=qc, fs=fs, layers=layers)
    t.export_on = True
    return t


def test_sand_with_sufficient_data_calculated():
    layers = [Layer(top_m=1.0, bot_m=2.0, ige_id="ИГЭ-1", soil_type=SoilType.SAND, calc_mode=calc_mode_for_soil(SoilType.SAND))]
    tests = [_mk_test(1, layers)]
    registry = {"ИГЭ-1": {"soil_type": "песок", "soil_code": "sand"}}
    samples = build_ige_samples(tests=tests, ige_registry=registry, profile_id="DEFAULT_CURRENT", allow_fill_by_material=False)
    s = samples[0]
    assert s.status == "CALCULATED"
    assert s.result.status == "ok"
    assert s.stats.n_points > 0
    assert s.result.E_MPa is not None


def test_clay_soil_requires_consistency_or_il():
    layers = [Layer(top_m=1.0, bot_m=2.0, ige_id="ИГЭ-3", soil_type=SoilType.CLAY, calc_mode=calc_mode_for_soil(SoilType.CLAY))]
    tests = [_mk_test(1, layers)]
    registry = {"ИГЭ-3": {"soil_type": "глина", "soil_code": "clay", "consistency": "тугопластичная"}}
    samples = build_ige_samples(tests=tests, ige_registry=registry, profile_id="DEFAULT_CURRENT", allow_fill_by_material=False)
    s = samples[0]
    assert s.status == "CALCULATED"
    assert s.result.status == "ok"
    assert s.result.c_kPa is not None


def test_fill_soil_preliminary_when_allowed_by_material():
    layers = [Layer(top_m=1.0, bot_m=2.0, ige_id="ИГЭ-5", soil_type=SoilType.FILL, calc_mode=calc_mode_for_soil(SoilType.FILL))]
    tests = [_mk_test(1, layers)]
    registry = {"ИГЭ-5": {"soil_type": "насыпной", "soil_code": "fill", "fill_subtype": "песчаный"}}
    samples = build_ige_samples(tests=tests, ige_registry=registry, profile_id="DEFAULT_CURRENT", allow_fill_by_material=True)
    s = samples[0]
    assert s.status == "PRELIMINARY"
    assert s.method == "SP446_CPT_SAND"


def test_insufficient_data_returns_missing_fields():
    layers = [Layer(top_m=1.0, bot_m=2.0, ige_id="ИГЭ-4", soil_type=SoilType.CLAY, calc_mode=calc_mode_for_soil(SoilType.CLAY))]
    tests = [_mk_test(1, layers)]
    # clay without IL/consistency => invalid_input
    registry = {"ИГЭ-4": {"soil_type": "глина", "soil_code": "clay", "consistency": ""}}
    samples = build_ige_samples(tests=tests, ige_registry=registry, profile_id="DEFAULT_CURRENT", allow_fill_by_material=False)
    s = samples[0]
    assert s.result.status == "invalid_input"
    assert "consistency_or_IL" in s.missing_fields
    assert s.errors


def test_method_not_applicable_and_protocol_trace_payload():
    layers = [Layer(top_m=1.0, bot_m=2.0, ige_id="ИГЭ-6", soil_type=SoilType.PEAT, calc_mode=calc_mode_for_soil(SoilType.PEAT))]
    tests = [_mk_test(1, layers)]
    registry = {"ИГЭ-6": {"soil_type": "торф", "soil_code": "peat"}}
    samples = build_ige_samples(tests=tests, ige_registry=registry, profile_id="DEFAULT_CURRENT", allow_fill_by_material=False)
    s = samples[0]
    assert s.status == "NOT_APPLICABLE"

    protocol = build_protocol(project_name="obj", profile_id="DEFAULT_CURRENT", samples=samples)
    trace = protocol["sections"]["calculation_trace"]
    assert len(trace) == 1
    assert trace[0]["status"] == "NOT_APPLICABLE"
    assert "used_soundings" in trace[0]
    assert "excluded_points" in trace[0]
    assert "required_fields" in trace[0]
    assert "contributing_layers" in trace[0]

    export_payload = protocol["sections"]["export_ready_params"]
    assert len(export_payload) == 1
    assert {"E_MPa", "phi_deg", "c_kPa"}.issubset(set(export_payload[0].keys()))


def test_fill_rule_limited_without_manual_confirmation():
    res = resolve_applicability(profile_id="DEFAULT_CURRENT", soil_code="fill", subtype="песчаный", allow_fill_by_material=False)
    assert res.status == "LAB_ONLY"
    assert res.manual_confirmation_required is True


def test_not_implemented_method_returns_status():
    layers = [Layer(top_m=1.0, bot_m=2.0, ige_id="ИГЭ-7", soil_type=SoilType.SAND, calc_mode=calc_mode_for_soil(SoilType.SAND))]
    tests = [_mk_test(1, layers)]
    registry = {"ИГЭ-7": {"soil_type": "песок", "soil_code": "sand"}}
    samples = build_ige_samples(tests=tests, ige_registry=registry, profile_id="LEGACY_SP11_105", allow_fill_by_material=False)
    s = samples[0]
    assert s.status == "NOT_IMPLEMENTED"
    assert s.result.status == "not_implemented"
