from __future__ import annotations


def viewport_capacity_rows(viewport_height_px: int | float, row_height_px: int | float) -> int:
    vh = max(0.0, float(viewport_height_px))
    rh = max(1.0, float(row_height_px))
    return max(1, int(vh // rh))


def clamp_top_row(total_rows: int, top_row: int, viewport_height_px: int | float, row_height_px: int | float) -> int:
    total = max(0, int(total_rows))
    if total <= 0:
        return 0
    cap = viewport_capacity_rows(viewport_height_px, row_height_px)
    max_top = max(0, total - cap)
    return max(0, min(int(top_row), max_top))


def compute_visible_row_range(
    total_rows: int,
    top_row: int,
    viewport_height_px: int | float,
    row_height_px: int | float,
    *,
    overscan: int = 2,
) -> tuple[int, int]:
    total = max(0, int(total_rows))
    if total <= 0:
        return (0, 0)
    start = clamp_top_row(total, top_row, viewport_height_px, row_height_px)
    cap = viewport_capacity_rows(viewport_height_px, row_height_px)
    end = min(total, start + cap + max(0, int(overscan)))
    return (start, max(start, end))
