from dataclasses import dataclass

from src.zondeditor.ui.editor import GeoCanvasEditor, TestFlags as EditorTestFlags


@dataclass
class _DummyTest:
    tid: int
    depth: list[str]
    qc: list[str]
    fs: list[str]


def _mk_editor() -> GeoCanvasEditor:
    ed = GeoCanvasEditor.__new__(GeoCanvasEditor)
    ed.tests = []
    ed.step_m = 0.1
    ed.step_by_tid = {}
    ed.depth0_by_tid = {}
    ed.flags = {}
    ed.project_ops = []
    ed._rebuild_marks_index = lambda: None
    ed._push_undo = lambda: None
    ed._show_validation_error_once = lambda _msg: None
    return ed


def _empty_flags() -> EditorTestFlags:
    return EditorTestFlags(False, set(), set(), set(), set())


def test_allowed_steps_only_005_010_020():
    ed = _mk_editor()
    assert ed._allowed_step_values() == (0.05, 0.1, 0.2)
    assert ed._normalize_allowed_step("0.10") == 0.1
    assert ed._normalize_allowed_step("0.30") is None


def test_non_neighbor_transition_is_rejected():
    ed = _mk_editor()
    assert ed._is_neighbor_step_transition(0.2, 0.05) is False
    assert ed._is_neighbor_step_transition(0.2, 0.1) is True


def test_overwrite_mode_changes_only_step_value():
    ed = _mk_editor()
    t = _DummyTest(tid=1, depth=["0.00", "0.10", "0.20"], qc=["1", "2", "3"], fs=["10", "20", "30"])
    ed.tests = [t]
    ed.flags = {1: _empty_flags()}
    ed._ask_step_change_mode = lambda **_kwargs: "overwrite"

    ok = ed._apply_step_change_request(old_step=0.1, new_step=0.2)
    assert ok is True
    assert t.depth == ["0.00", "0.10", "0.20"]
    assert t.qc == ["1", "2", "3"]
    assert t.fs == ["10", "20", "30"]
    assert ed.step_by_tid[1] == 0.2


def test_resample_reduce_and_increase_adjust_rows():
    ed = _mk_editor()
    t = _DummyTest(tid=1, depth=["0.00", "0.10", "0.20"], qc=["10", "20", "30"], fs=["100", "200", "300"])
    ed.tests = [t]
    ed.flags = {1: _empty_flags()}

    ed._ask_step_change_mode = lambda **_kwargs: "resample"
    assert ed._apply_step_change_request(old_step=0.1, new_step=0.05) is True
    assert len(t.depth) == 5
    assert t.depth[1] == "0.05"
    assert t.depth[3] == "0.15"
    assert (1, "qc") in ed.flags[1].algo_cells
    assert (3, "fs") in ed.flags[1].algo_cells

    ed._ask_step_change_mode = lambda **_kwargs: "resample"
    assert ed._apply_step_change_request(old_step=0.05, new_step=0.1) is True
    assert t.depth == ["0.00", "0.10", "0.20"]
