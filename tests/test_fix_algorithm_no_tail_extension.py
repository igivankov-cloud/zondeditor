from dataclasses import dataclass

from src.zondeditor.processing.fixes import fix_tests_by_algorithm


@dataclass
class T:
    tid: int
    qc: list[str]
    fs: list[str]
    depth: list[str]


def test_fix_algorithm_does_not_extend_when_qc_longer_than_fs():
    t = T(
        tid=1,
        qc=["10", "0", "30", "0"],
        fs=["20", "0", "40"],
        depth=["0", "0.1", "0.2"],
    )

    before_qc = len(t.qc)
    before_fs = len(t.fs)
    before_depth = len(t.depth)

    fix_tests_by_algorithm([t])

    assert len(t.qc) == before_qc
    assert len(t.fs) == before_fs
    assert len(t.depth) == before_depth


def test_fix_algorithm_does_not_extend_when_fs_longer_than_qc():
    t = T(
        tid=1,
        qc=["10", "0", "30"],
        fs=["20", "0", "40", "0"],
        depth=["0", "0.1", "0.2"],
    )

    before_qc = len(t.qc)
    before_fs = len(t.fs)
    before_depth = len(t.depth)

    fix_tests_by_algorithm([t])

    assert len(t.qc) == before_qc
    assert len(t.fs) == before_fs
    assert len(t.depth) == before_depth
