from types import SimpleNamespace

from src.zondeditor.ui.editor import GeoCanvasEditor


def _make_editor(tests, mode="date"):
    editor = GeoCanvasEditor.__new__(GeoCanvasEditor)
    editor.tests = tests
    editor.display_sort_mode = mode
    editor.display_cols = []
    return editor


def test_refresh_display_order_excludes_disabled_experiences_and_compacts_layout():
    tests = [
        SimpleNamespace(tid="3", dt="03.01.2026 12:00", export_on=True),
        SimpleNamespace(tid="1", dt="01.01.2026 12:00", export_on=False),
        SimpleNamespace(tid="2", dt="02.01.2026 12:00", export_on=True),
    ]
    editor = _make_editor(tests, mode="date")

    editor._refresh_display_order()

    assert editor.display_cols == [2, 0]


def test_refresh_display_order_keeps_disabled_data_in_model():
    tests = [
        SimpleNamespace(tid="1", dt="01.01.2026 12:00", export_on=False),
        SimpleNamespace(tid="2", dt="02.01.2026 12:00", export_on=False),
    ]
    editor = _make_editor(tests, mode="date")

    editor._refresh_display_order()

    assert editor.display_cols == []
    assert len(editor.tests) == 2
