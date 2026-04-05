from types import SimpleNamespace

from src.zondeditor.processing.diagnostics import evaluate_diagnostics


def _test(tid, qc, fs, export_on=True):
    return SimpleNamespace(tid=tid, qc=qc, fs=fs, export_on=export_on)


def _flags(*, invalid=False, user_cells=None, interp_cells=None, force_cells=None, algo_cells=None):
    return SimpleNamespace(
        invalid=invalid,
        user_cells=set(user_cells or []),
        interp_cells=set(interp_cells or []),
        force_cells=set(force_cells or []),
        algo_cells=set(algo_cells or []),
    )


def test_diagnostics_uses_single_invalid_rule_and_aggregates_protocol_entry():
    tests = [_test(1, ["1", "0", "0", "0", "0", "0", "0"], ["1", "1", "1", "1", "1", "1", "1"]) ]
    report = evaluate_diagnostics(tests, {1: _flags()})
    assert report.tests_invalid == 1
    assert report.cells_missing == 0
    assert len(report.protocol_entries) == 1
    assert report.protocol_entries[0].type == "invalid_zero_run"


def test_diagnostics_counts_missing_only_for_valid_exported_tests():
    tests = [
        _test(1, ["1", ""], ["1", ""], export_on=True),
        _test(2, ["0", "0", "0", "0", "0", "0"], ["1", "1", "1", "1", "1", "1"], export_on=True),
        _test(3, ["0"], ["0"], export_on=False),
    ]
    report = evaluate_diagnostics(
        tests,
        {
            1: _flags(user_cells={(1, "fs")}),
            2: _flags(),
            3: _flags(),
        },
    )
    # test #1: missing qc at row 1 (fs is manual -> excluded)
    # test #2: invalid due to zero run -> missing not counted in footer aggregate
    assert report.tests_total == 2
    assert report.tests_invalid == 1
    assert report.cells_missing == 1


def test_diagnostics_protocol_contains_missing_and_invalid_other():
    tests = [_test(1, ["1", ""], ["1", ""]), _test(2, ["1"], ["1"]) ]
    report = evaluate_diagnostics(
        tests,
        {
            1: _flags(),
            2: _flags(invalid=True),
        },
    )
    kinds = [e.type for e in report.protocol_entries]
    assert "missing_qc" in kinds
    assert "missing_fs" in kinds
    assert "invalid_other" in kinds
