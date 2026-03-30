from types import SimpleNamespace

from src.zondeditor.ui.editor import GeoCanvasEditor


def _make_editor(tests, mode="date"):
    editor = GeoCanvasEditor.__new__(GeoCanvasEditor)
    editor.tests = tests
    editor.display_sort_mode = mode
    editor.display_cols = []
    editor.pad_x = 10
    editor.pad_y = 8
    editor.hdr_h = 120
    editor.col_gap = 12
    editor.w_depth = 60
    editor.w_val = 70
    editor.graph_w = 150
    editor.show_graphs = True
    editor.show_geology_column = True
    editor.geo_kind = "K2"
    editor.show_inclinometer = False
    editor._total_body_height = lambda: 500
    return editor


def test_unchecked_experience_stays_in_display_order():
    tests = [
        SimpleNamespace(tid="3", dt="03.01.2026 12:00", export_on=True),
        SimpleNamespace(tid="1", dt="01.01.2026 12:00", export_on=False),
        SimpleNamespace(tid="2", dt="02.01.2026 12:00", export_on=True),
    ]
    editor = _make_editor(tests)

    editor._refresh_display_order()

    assert editor.display_cols == [1, 2, 0]
    assert editor.collapsed_cols == [1]
    assert editor.expanded_cols == [2, 0]


def test_unchecked_experience_moves_to_left_dock_and_expanded_lane_has_no_gap():
    tests = [
        SimpleNamespace(tid="1", dt="01.01.2026 12:00", export_on=True),
        SimpleNamespace(tid="2", dt="02.01.2026 12:00", export_on=False),
        SimpleNamespace(tid="3", dt="03.01.2026 12:00", export_on=True),
    ]
    editor = _make_editor(tests)

    editor._refresh_display_order()

    expanded_w = editor._column_block_width()
    dock_w = editor._collapsed_dock_width()

    assert dock_w > 0
    assert editor.expanded_cols == [0, 2]
    assert editor._column_x0(0) == editor.pad_x + dock_w
    assert editor._column_x0(1) == editor.pad_x + dock_w + expanded_w + editor.col_gap


def test_multiple_collapsed_experiences_stack_vertically_in_left_dock():
    tests = [
        SimpleNamespace(tid="1", dt="01.01.2026 12:00", export_on=False),
        SimpleNamespace(tid="2", dt="02.01.2026 12:00", export_on=False),
        SimpleNamespace(tid="3", dt="03.01.2026 12:00", export_on=True),
    ]
    editor = _make_editor(tests)

    editor._refresh_display_order()

    top0 = editor._collapsed_header_bbox(0)
    top1 = editor._collapsed_header_bbox(1)
    assert top0[0] == top1[0] == editor.pad_x
    assert top1[1] > top0[1]
    assert editor.expanded_cols == [2]


def test_recheck_restores_expanded_width_and_graph_area():
    tests = [
        SimpleNamespace(tid="1", dt="01.01.2026 12:00", export_on=False),
        SimpleNamespace(tid="2", dt="02.01.2026 12:00", export_on=True),
    ]
    editor = _make_editor(tests)

    editor._refresh_display_order()
    collapsed_graph_rect = editor._graph_rect_for_test(0)

    assert collapsed_graph_rect is None
    assert editor.collapsed_cols == [0]
    assert editor.expanded_cols == [1]

    tests[0].export_on = True
    editor._refresh_display_order()

    expanded_graph_rect = editor._graph_rect_for_test(0)
    assert expanded_graph_rect is not None
    assert editor.collapsed_cols == []
    assert editor.expanded_cols == [0, 1]


def test_collapsed_mode_keeps_data_in_model_and_stable_order():
    tests = [
        SimpleNamespace(tid="10", dt="10.01.2026 12:00", export_on=False),
        SimpleNamespace(tid="11", dt="11.01.2026 12:00", export_on=True),
    ]
    editor = _make_editor(tests)

    editor._refresh_display_order()

    assert len(editor.tests) == 2
    assert [t.tid for t in editor.tests] == ["10", "11"]
    assert editor.display_cols == [0, 1]
