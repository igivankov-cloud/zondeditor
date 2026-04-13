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
    assert editor._column_x0(0) == editor.pad_x
    assert editor._column_x0(1) == editor.pad_x + expanded_w + editor.col_gap


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
    assert top0[0] == top1[0] == 4
    assert top1[1] > top0[1]
    assert editor._collapsed_header_row_height() >= 40
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
    assert editor._collapsed_dock_width() == 0
    assert editor._column_x0(0) == editor.pad_x


def test_expanded_header_width_does_not_depend_on_graph_toggle():
    tests = [SimpleNamespace(tid="1", dt="01.01.2026 12:00", export_on=True)]
    editor = _make_editor(tests)
    editor._refresh_display_order()

    editor.show_graphs = True
    x0_on, _y0_on, x1_on, _y1_on = editor._header_bbox(0)
    editor.show_graphs = False
    x0_off, _y0_off, x1_off, _y1_off = editor._header_bbox(0)

    assert x0_on == x0_off
    assert (x1_on - x0_on) == (x1_off - x0_off) == editor._table_col_width()


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


def test_header_actions_disabled_for_collapsed_or_locked():
    tests = [
        SimpleNamespace(tid="1", dt="01.01.2026 12:00", export_on=False, locked=False),
        SimpleNamespace(tid="2", dt="02.01.2026 12:00", export_on=True, locked=True),
        SimpleNamespace(tid="3", dt="03.01.2026 12:00", export_on=True, locked=False),
    ]
    editor = _make_editor(tests)
    editor._refresh_display_order()

    assert editor._header_action_buttons_enabled(0) is False
    assert editor._header_action_buttons_enabled(1) is False
    assert editor._header_action_buttons_enabled(2) is True


def test_tsz_header_helpers_format_title_date_and_elevation():
    test = SimpleNamespace(tid="4", dt="2026-01-02 13:45:00", export_on=True, elevation_m=123.4)
    editor = _make_editor([test])

    assert editor._format_tsz_header_title(test) == "ТСЗ-4"
    assert editor._format_tsz_header_date(test.dt) == "02.01.2026"
    assert editor._format_tsz_elevation(test) == "Отм.: 123.40"
