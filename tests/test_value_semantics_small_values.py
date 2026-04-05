from types import SimpleNamespace

from src.zondeditor.processing.diagnostics import evaluate_diagnostics
from src.zondeditor.processing.fixes import fix_tests_by_algorithm
from src.zondeditor.processing.value_semantics import is_effective_zero, is_missing_value, max_zero_run


def _flags(*, invalid=False, user_cells=None, interp_cells=None, force_cells=None, algo_cells=None):
    return SimpleNamespace(
        invalid=invalid,
        user_cells=set(user_cells or []),
        interp_cells=set(interp_cells or []),
        force_cells=set(force_cells or []),
        algo_cells=set(algo_cells or []),
    )


def test_small_positive_values_are_not_missing_and_not_zero():
    vals = [0.72, 0.48, 0.36, 0.24, 0.12]
    assert all(not is_missing_value(v) for v in vals)
    assert all(not is_effective_zero(v) for v in vals)
    assert max_zero_run(vals) == 0


def test_true_zeros_form_zero_run():
    vals = [0, 0.0, 0.0, 0, 0]
    assert max_zero_run(vals) == 5


def test_none_nan_empty_are_missing():
    assert is_missing_value(None)
    assert is_missing_value("")
    assert is_missing_value("   ")
    assert is_missing_value(float("nan"))


def test_diagnostics_do_not_mark_subunit_values_invalid_or_missing():
    test = SimpleNamespace(tid=1, qc=["0.72", "0.48", "0.36", "0.24", "0.12"], fs=["0.72", "0.48", "0.36", "0.24", "0.12"], export_on=True)
    report = evaluate_diagnostics([test], {1: _flags()})
    assert report.tests_invalid == 0
    assert report.cells_missing == 0


def test_fix_algorithm_keeps_small_positive_measurements():
    test = SimpleNamespace(
        tid=1,
        qc=["0.72", "0.48", "0.36", "0.24", "0.12"],
        fs=["0.72", "0.48", "0.36", "0.24", "0.12"],
        depth=["0", "0.1", "0.2", "0.3", "0.4"],
    )
    flags = fix_tests_by_algorithm([test])
    assert flags[0].invalid is False
    assert test.qc[0] == "0.72"
    assert test.fs[-1] == "0.12"
