from src.zondeditor.ui.import_excel_dialog import _apply_row_bounds, _expand_roles_right, col_to_label


def test_col_to_label_excel_letters():
    assert col_to_label(0) == "A"
    assert col_to_label(25) == "Z"
    assert col_to_label(26) == "AA"


def test_expand_roles_right_prefills_repeated_blocks():
    rows = [
        ["Глубина", "qc", "fs", "qc", "fs", "qc", "fs"],
        [0.0, 1.0, 2.0, 10.0, 20.0, 100.0, 200.0],
    ]
    base_roles = {0: "depth", 1: "qc_mpa", 2: "fs_kpa"}
    expanded = _expand_roles_right(rows, base_roles, repeat_enabled=True)
    assert expanded[0] == "depth"
    assert expanded[1] == "qc_mpa"
    assert expanded[2] == "fs_kpa"
    assert expanded[3] == "qc_mpa"
    assert expanded[4] == "fs_kpa"
    assert expanded[5] == "qc_mpa"
    assert expanded[6] == "fs_kpa"


def test_apply_row_bounds_masks_ignored_and_tail_rows():
    rows = [
        [1, "a"],
        [2, "b"],
        [3, "c"],
        [4, "d"],
    ]
    out = _apply_row_bounds(rows, ignored_rows={2}, data_end_row=3)
    assert out[0] == [1, "a"]
    assert out[1] == [None, None]
    assert out[2] == [3, "c"]
    assert out[3] == [None, None]
