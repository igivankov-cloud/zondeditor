from __future__ import annotations

from typing import Any, Callable

Renderer = Callable[[Any, tuple[float, float, float, float], dict[str, float], Any], None]

# Таблица соответствия: код грунта -> функция отрисовки штриховки.
# Для расширения добавьте новый soil_code и renderer-функцию.
SOIL_CODE_TO_RENDERER: dict[str, str] = {
    "SiL": "_draw_sugl",
    "Si": "_draw_supes",
    "Cl": "_draw_clay",
    "Sand": "_draw_sand",
    "Peat": "_draw_peat",
    "Fill": "_draw_fill",
    "Gravel": "_draw_gravel",
    "SandGravel": "_draw_sand_gravel",
    "Argillite": "_draw_argillite",
    "Sandstone": "_draw_sandstone",
}

SOIL_TYPE_TO_CODE: dict[str, str] = {
    "суглинок": "SiL",
    "супесь": "Si",
    "глина": "Cl",
    "песок": "Sand",
    "торф": "Peat",
    "насыпной": "Fill",
    "гравийный грунт": "Gravel",
    "песок гравелистый": "SandGravel",
    "аргиллит": "Argillite",
    "песчаник": "Sandstone",
}


def soil_code_from_value(value: str) -> str:
    raw = str(value or "").strip()
    if raw in SOIL_CODE_TO_RENDERER:
        return raw
    return SOIL_TYPE_TO_CODE.get(raw.lower(), "")


def _norm_scale(scale_info: dict[str, Any] | None, bbox: tuple[float, float, float, float]) -> dict[str, float]:
    x0, y0, x1, y1 = bbox
    h = max(1.0, float(y1 - y0))
    factor = h / 64.0
    if scale_info and scale_info.get("layer_height_px"):
        try:
            factor = float(scale_info["layer_height_px"]) / 64.0
        except Exception:
            pass
    factor = max(0.6, min(1.8, factor))
    return {"f": factor, "w": max(1.0, float(x1 - x0)), "h": h}


def _px(v: float, s: dict[str, float], *, min_px: float = 1.0) -> float:
    return max(min_px, round(v * s["f"], 2))


def _diag_segment(x0: float, y0: float, x1: float, y1: float, b: float, slope: int) -> tuple[float, float, float, float] | None:
    pts: list[tuple[float, float]] = []
    if slope > 0:  # y = x + b
        yy = x0 + b
        if y0 <= yy <= y1:
            pts.append((x0, yy))
        yy = x1 + b
        if y0 <= yy <= y1:
            pts.append((x1, yy))
        xx = y0 - b
        if x0 <= xx <= x1:
            pts.append((xx, y0))
        xx = y1 - b
        if x0 <= xx <= x1:
            pts.append((xx, y1))
    else:  # y = -x + b
        yy = -x0 + b
        if y0 <= yy <= y1:
            pts.append((x0, yy))
        yy = -x1 + b
        if y0 <= yy <= y1:
            pts.append((x1, yy))
        xx = b - y0
        if x0 <= xx <= x1:
            pts.append((xx, y0))
        xx = b - y1
        if x0 <= xx <= x1:
            pts.append((xx, y1))
    uniq: list[tuple[float, float]] = []
    for p in pts:
        if not any(abs(p[0] - q[0]) < 1e-6 and abs(p[1] - q[1]) < 1e-6 for q in uniq):
            uniq.append(p)
    if len(uniq) >= 2:
        return (uniq[0][0], uniq[0][1], uniq[1][0], uniq[1][1])
    return None


# --- helpers ---
def draw_diagonal_lines(canvas: Any, bbox: tuple[float, float, float, float], *, step: float, slope: int, tags: Any) -> list[tuple[float, float, float, float]]:
    x0, y0, x1, y1 = bbox
    segs: list[tuple[float, float, float, float]] = []
    offs = range(int(y0 - x1), int(y1 - x0 + step), int(step)) if slope > 0 else range(int(y0 + x0), int(y1 + x1 + step), int(step))
    for b in offs:
        seg = _diag_segment(x0, y0, x1, y1, float(b), slope)
        if seg:
            canvas.create_line(*seg, fill="#000000", width=1, tags=tags)
            segs.append(seg)
    return segs


def draw_broken_diagonal_lines(
    canvas: Any,
    bbox: tuple[float, float, float, float],
    *,
    step: float,
    slope: int,
    seg_len: float,
    gap_len: float,
    tags: Any,
) -> None:
    segs = draw_diagonal_lines(canvas, bbox, step=step, slope=slope, tags=("_tmp",))
    try:
        canvas.delete("_tmp")
    except Exception:
        pass
    for li, (x0, y0, x1, y1) in enumerate(segs):
        dx = x1 - x0
        dy = y1 - y0
        ln = (dx * dx + dy * dy) ** 0.5
        if ln < 1.0:
            continue
        ux, uy = dx / ln, dy / ln
        # шахматный сдвиг разрывов между соседними диагоналями
        offset = 0.5 * (seg_len + gap_len) if (li % 2) else 0.0
        pos = offset
        while pos < ln:
            a = pos
            b = min(ln, pos + seg_len)
            canvas.create_line(x0 + ux * a, y0 + uy * a, x0 + ux * b, y0 + uy * b, fill="#000000", width=1, tags=tags)
            pos += seg_len + gap_len


def draw_small_dots(canvas: Any, bbox: tuple[float, float, float, float], *, step: float, dot_size: float, tags: Any) -> None:
    x0, y0, x1, y1 = bbox
    half = max(0.35, dot_size * 0.5)
    row = 0
    for yy in range(int(y0 + step * 0.5), int(y1), int(step)):
        shift = step * 0.5 if (row % 2) else 0.0
        for xx in range(int(x0 + step * 0.5 + shift), int(x1), int(step)):
            canvas.create_rectangle(xx - half, yy - half, xx + half, yy + half, fill="#000000", outline="#000000", width=1, tags=tags)
        row += 1


def draw_open_circles(canvas: Any, bbox: tuple[float, float, float, float], *, step: float, diameter: float, tags: Any) -> None:
    x0, y0, x1, y1 = bbox
    r = max(1.0, diameter * 0.5)
    row = 0
    for yy in range(int(y0 + step * 0.5), int(y1), int(step)):
        shift = step * 0.5 if (row % 2) else 0.0
        for xx in range(int(x0 + step * 0.5 + shift), int(x1), int(step)):
            canvas.create_oval(xx - r, yy - r, xx + r, yy + r, outline="#000000", width=1, tags=tags)
        row += 1


def draw_horizontal_lines(canvas: Any, bbox: tuple[float, float, float, float], *, step: float, tags: Any) -> list[float]:
    x0, y0, x1, y1 = bbox
    ys: list[float] = []
    for yy in range(int(y0), int(y1 + step), int(step)):
        y = float(yy)
        ys.append(y)
        canvas.create_line(x0, y, x1, y, fill="#000000", width=1, tags=tags)
    return ys


def draw_marks_on_lines(
    canvas: Any,
    bbox: tuple[float, float, float, float],
    lines_y: list[float],
    *,
    x_step: float,
    mark_len: float,
    slope: int,
    stagger: bool,
    tags: Any,
) -> None:
    x0, _, x1, _ = bbox
    for i, y in enumerate(lines_y):
        shift = x_step * 0.5 if (stagger and (i % 2)) else 0.0
        for xx in range(int(x0 + x_step * 0.5 + shift), int(x1), int(x_step)):
            if slope > 0:
                canvas.create_line(xx - mark_len * 0.5, y - mark_len * 0.5, xx + mark_len * 0.5, y + mark_len * 0.5, fill="#000000", width=1, tags=tags)
            else:
                canvas.create_line(xx - mark_len * 0.5, y + mark_len * 0.5, xx + mark_len * 0.5, y - mark_len * 0.5, fill="#000000", width=1, tags=tags)


def draw_bracket_pattern(canvas: Any, bbox: tuple[float, float, float, float], *, line_step: float, bracket_h: float, x_step: float, tags: Any) -> None:
    x0, y0, x1, y1 = bbox
    row = 0
    for yy in range(int(y0 + line_step * 0.5), int(y1), int(line_step)):
        y = float(yy)
        canvas.create_line(x0, y, x1, y, fill="#000000", width=1, tags=tags)
        up = row % 2 == 0
        shift = x_step * 0.5 if (row % 2) else 0.0
        for xx in range(int(x0 + shift), int(x1), int(x_step)):
            x = float(xx)
            if up:
                top, bot, cap_y = y - bracket_h, y, y - bracket_h
            else:
                top, bot, cap_y = y, y + bracket_h, y + bracket_h
            canvas.create_line(x, top, x, bot, fill="#000000", width=1, tags=tags)
            canvas.create_line(x, cap_y, x + bracket_h, cap_y, fill="#000000", width=1, tags=tags)
        row += 1


def draw_crosses_between_lines(
    canvas: Any,
    bbox: tuple[float, float, float, float],
    lines_y: list[float],
    *,
    x_step: float,
    cross_size: float,
    tags: Any,
) -> None:
    x0, _, x1, _ = bbox
    half = cross_size * 0.5
    for i in range(len(lines_y) - 1):
        cy = (lines_y[i] + lines_y[i + 1]) * 0.5  # строго между горизонталями
        shift = x_step * 0.5 if (i % 2) else 0.0
        for xx in range(int(x0 + x_step * 0.5 + shift), int(x1), int(x_step)):
            canvas.create_line(xx - half, cy - half, xx + half, cy + half, fill="#000000", width=1, tags=tags)
            canvas.create_line(xx - half, cy + half, xx + half, cy - half, fill="#000000", width=1, tags=tags)


# --- renderers ---
def _draw_sugl(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    # SiL: только чистые параллельные диагонали.
    draw_diagonal_lines(canvas, bbox, step=_px(9, s), slope=-1, tags=tags)


def _draw_supes(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    # Si: диагонали с короткими разрывами в шахматном порядке между соседними линиями.
    draw_broken_diagonal_lines(
        canvas,
        bbox,
        step=_px(11, s),
        slope=-1,
        seg_len=_px(12, s),
        gap_len=_px(5, s),
        tags=tags,
    )


def _draw_clay(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    draw_horizontal_lines(canvas, bbox, step=_px(7, s), tags=tags)


def _draw_sand(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    draw_small_dots(canvas, bbox, step=_px(8, s), dot_size=_px(0.8, s, min_px=0.6), tags=tags)


def _draw_peat(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    draw_bracket_pattern(canvas, bbox, line_step=_px(12, s), bracket_h=_px(7, s), x_step=_px(16, s), tags=tags)


def _draw_fill(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    draw_diagonal_lines(canvas, bbox, step=_px(12, s), slope=+1, tags=tags)
    draw_diagonal_lines(canvas, bbox, step=_px(12, s), slope=-1, tags=tags)


def _draw_gravel(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    draw_open_circles(canvas, bbox, step=_px(15, s), diameter=_px(5, s), tags=tags)


def _draw_sand_gravel(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    draw_small_dots(canvas, bbox, step=_px(8, s), dot_size=_px(0.8, s, min_px=0.6), tags=tags)
    draw_open_circles(canvas, bbox, step=_px(19, s), diameter=_px(5, s), tags=tags)


def _draw_argillite(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    lines = draw_horizontal_lines(canvas, bbox, step=_px(12, s), tags=tags)
    draw_marks_on_lines(
        canvas,
        bbox,
        lines,
        x_step=_px(24, s),
        mark_len=_px(7, s),
        slope=+1,
        stagger=True,
        tags=tags,
    )


def _draw_sandstone(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    lines = draw_horizontal_lines(canvas, bbox, step=_px(14, s), tags=tags)
    draw_small_dots(canvas, bbox, step=_px(10, s), dot_size=_px(0.75, s, min_px=0.55), tags=tags)
    draw_crosses_between_lines(canvas, bbox, lines, x_step=_px(34, s), cross_size=_px(9, s), tags=tags)


def _draw_fallback(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    draw_diagonal_lines(canvas, bbox, step=_px(14, s), slope=+1, tags=tags)


def draw_hatch(canvas: Any, bbox: tuple[float, float, float, float], soil_code: str, scale_info: dict[str, Any] | None, tags: Any) -> None:
    """Единый интерфейс отрисовки штриховки: draw_hatch(canvas, bbox, soil_code, scale_info)."""
    s = _norm_scale(scale_info, bbox)
    name = SOIL_CODE_TO_RENDERER.get(str(soil_code or ""))
    renderer = globals().get(name or "", _draw_fallback)
    renderer(canvas, bbox, s, tags)
