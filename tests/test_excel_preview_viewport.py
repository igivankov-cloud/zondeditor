from src.zondeditor.ui.preview_viewport import clamp_top_row, compute_visible_row_range


def test_resize_keeps_top_row_visible_and_expands_bottom():
    total_rows = 80
    top_row = 10
    before = compute_visible_row_range(total_rows, top_row, viewport_height_px=24 * 8, row_height_px=24)
    after = compute_visible_row_range(total_rows, top_row, viewport_height_px=24 * 12, row_height_px=24)
    assert before[0] == 10
    assert after[0] == 10
    assert after[1] > before[1]


def test_top_row_is_clamped_when_viewport_becomes_taller():
    total_rows = 80
    top_row = 75
    clamped = clamp_top_row(total_rows, top_row, viewport_height_px=24 * 12, row_height_px=24)
    assert clamped == 68
