from dataclasses import dataclass

from src.zondeditor.export.geo_export import prepare_geo_tests
from src.zondeditor.export.selection import select_export_tests
from src.zondeditor.processing.calibration import calibration_from_common_params, calc_qc_fs


@dataclass
class T:
    tid: int
    dt: str
    depth: list[str]
    qc: list[str]
    fs: list[str]
    export_on: bool = True


def test_select_export_tests_respects_export_on_and_deleted_flags():
    tests = [
        T(1, "", ["0"], ["1"], ["1"], export_on=True),
        T(2, "", ["0"], ["1"], ["1"], export_on=False),
    ]
    tests[1].deleted = True
    sel = select_export_tests(tests)
    assert [t.tid for t in sel.tests] == [1]
    assert sel.exported_tests == [1]


def test_prepare_geo_tests_drops_only_fully_empty_rows():
    t = T(
        tid=1,
        dt="",
        depth=["0", "", "1"],
        qc=["10", "", ""],
        fs=["20", "", "30"],
    )
    out = prepare_geo_tests([t])[0]
    assert out.depth == ["0", "1"]
    assert out.qc == ["10", ""]
    assert out.fs == ["20", "30"]


def test_k2_k4_calibration_invariants():
    k2 = calibration_from_common_params({"controller_scale_div": "250", "cone_kn": "30", "sleeve_kn": "10"}, geo_kind="K2")
    k4 = calibration_from_common_params({"controller_scale_div": "1000", "cone_kn": "50", "sleeve_kn": "10"}, geo_kind="K4")
    q2, _ = calc_qc_fs(250, 0, geo_kind="K2", cal=k2)
    q4, _ = calc_qc_fs(1000, 0, geo_kind="K4", cal=k4)
    assert round(q2, 3) == 30.0
    assert round(q4, 3) == 50.0
