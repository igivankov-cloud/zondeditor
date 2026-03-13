import json
from pathlib import Path

from src.zondeditor.calculations.calc_methods import run_method
from src.zondeditor.calculations.models import IGECalcStats


def _load_cases():
    p = Path("fixtures/reference_calc_cases.json")
    return json.loads(p.read_text(encoding="utf-8")).get("cases", [])


def _assert_contains_all(haystack: list[str], needles: list[str]):
    joined = " | ".join(haystack).lower()
    for n in needles:
        assert n.lower() in joined


def test_reference_cases_program_vs_expected():
    cases = _load_cases()
    assert len(cases) >= 5

    for case in cases:
        stats_in = case["stats"]
        stats = IGECalcStats(
            n_points=int(stats_in.get("n_points", 0)),
            qc_avg_mpa=stats_in.get("qc_avg_mpa"),
            v_qc=stats_in.get("v_qc"),
            avg_depth_m=stats_in.get("avg_depth_m"),
        )
        got = run_method(case["method"], stats, context=dict(case.get("context") or {}))
        exp = case["expected"]

        assert got.status == exp["status"], case["case_id"]
        assert got.result.status == exp["result_status"], case["case_id"]
        _assert_contains_all(got.warnings, list(exp.get("warnings_contains") or []))
        _assert_contains_all(got.errors, list(exp.get("errors_contains") or []))

        out = exp.get("outputs") or {}
        tol = exp.get("tolerance") or {}

        for key in ["E_MPa", "phi_deg", "c_kPa"]:
            expected_val = out.get(key)
            got_val = getattr(got.result, key)
            if expected_val is None:
                assert got_val is None, f"{case['case_id']} {key}"
            else:
                delta = abs(float(got_val) - float(expected_val))
                assert delta <= float(tol.get(key, 1e-9)), f"{case['case_id']} {key}: {got_val} vs {expected_val}"
