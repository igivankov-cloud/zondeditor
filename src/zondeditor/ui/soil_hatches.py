from __future__ import annotations

from typing import Any, Callable

Renderer = Callable[[Any, tuple[float, float, float, float], dict[str, float], Any], None]

# Таблица соответствия: код грунта -> функция отрисовки штриховки.
# Для расширения добавьте новый soil_code в SOIL_CODE_TO_RENDERER.
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

# Карта алиасов/текущих наименований проекта в фиксированные soil_code.
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
    base = 64.0
    factor = h / base
    if scale_info and scale_info.get("layer_height_px"):
        try:
            factor = float(scale_info["layer_height_px"]) / base
        except Exception:
            pass
    factor = max(0.6, min(1.8, factor))
    return {"f": factor, "w": max(1.0, float(x1 - x0)), "h": h}


def _px(v: float, s: dict[str, float], *, min_px: float = 1.0) -> float:
    return max(min_px, round(v * s["f"], 2))


def _diag_segment(x0: float, y0: float, x1: float, y1: float, b: float, slope: int) -> tuple[float, float, float, float] | None:
    pts: list[tuple[float, float]] = []
    if slope > 0:
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
    else:
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


def _draw_diag_family(canvas: Any, bbox: tuple[float, float, float, float], *, step: float, slope: int, tags: Any) -> None:
    x0, y0, x1, y1 = bbox
    if slope > 0:
        offs = range(int(y0 - x1), int(y1 - x0 + step), int(step))
    else:
        offs = range(int(y0 + x0), int(y1 + x1 + step), int(step))
    for b in offs:
        seg = _diag_segment(x0, y0, x1, y1, float(b), slope)
        if seg:
            canvas.create_line(*seg, fill="#000000", width=1, tags=tags)


def _draw_sugl(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    x0, y0, x1, y1 = bbox
    step = _px(9, s)
    cross_len = _px(4, s)
    cross_step = _px(12, s)
    _draw_diag_family(canvas, bbox, step=step, slope=+1, tags=tags)
    for yy in range(int(y0), int(y1 + step), int(step)):
        for xx in range(int(x0), int(x1 + cross_step), int(cross_step)):
            x = float(xx)
            y = float(yy + (x - x0))
            if y0 <= y <= y1 and x0 <= x <= x1:
                canvas.create_line(x - cross_len * 0.5, y + cross_len * 0.5, x + cross_len * 0.5, y - cross_len * 0.5, fill="#000000", width=1, tags=tags)


def _draw_supes(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    x0, y0, x1, y1 = bbox
    step = _px(11, s)
    dash_len = _px(3.5, s)
    dash_step = _px(18, s)
    _draw_diag_family(canvas, bbox, step=step, slope=+1, tags=tags)
    for yy in range(int(y0), int(y1 + step), int(step)):
        for xx in range(int(x0), int(x1 + dash_step), int(dash_step)):
            x = float(xx)
            y = float(yy + (x - x0))
            if y0 <= y <= y1 and x0 <= x <= x1:
                canvas.create_line(x - dash_len * 0.5, y - dash_len * 0.5, x + dash_len * 0.5, y + dash_len * 0.5, fill="#000000", width=1, tags=tags)


def _draw_clay(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    x0, y0, x1, y1 = bbox
    step = _px(7, s)
    for yy in range(int(y0), int(y1 + step), int(step)):
        canvas.create_line(x0, float(yy), x1, float(yy), fill="#000000", width=1, tags=tags)


def _draw_sand(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    x0, y0, x1, y1 = bbox
    step = _px(8, s)
    r = _px(1.2, s)
    row = 0
    for yy in range(int(y0 + step * 0.5), int(y1), int(step)):
        shift = step * 0.5 if (row % 2) else 0
        for xx in range(int(x0 + step * 0.5 + shift), int(x1), int(step)):
            canvas.create_oval(xx - r, yy - r, xx + r, yy + r, fill="#000000", outline="#000000", width=1, tags=tags)
        row += 1


def _draw_peat(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    x0, y0, x1, y1 = bbox
    h_step = _px(12, s)
    bracket = _px(7, s)
    x_step = _px(16, s)
    for yy in range(int(y0 + h_step * 0.5), int(y1), int(h_step)):
        canvas.create_line(x0, float(yy), x1, float(yy), fill="#000000", width=1, tags=tags)
    row = 0
    for yy in range(int(y0 + h_step * 0.5), int(y1), int(h_step)):
        up = (row % 2 == 0)
        shift = x_step * 0.5 if (row % 2) else 0
        for xx in range(int(x0 + shift), int(x1), int(x_step)):
            top = yy - bracket if up else yy
            bot = yy if up else yy + bracket
            canvas.create_line(xx, top, xx, bot, fill="#000000", width=1, tags=tags)
            canvas.create_line(xx, top if up else bot, xx + bracket, top if up else bot, fill="#000000", width=1, tags=tags)
        row += 1


def _draw_fill(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    step = _px(12, s)
    _draw_diag_family(canvas, bbox, step=step, slope=+1, tags=tags)
    _draw_diag_family(canvas, bbox, step=step, slope=-1, tags=tags)


def _draw_gravel(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    x0, y0, x1, y1 = bbox
    step = _px(15, s)
    r = _px(2.5, s)
    row = 0
    for yy in range(int(y0 + step * 0.5), int(y1), int(step)):
        shift = step * 0.5 if (row % 2) else 0
        for xx in range(int(x0 + step * 0.5 + shift), int(x1), int(step)):
            canvas.create_oval(xx - r, yy - r, xx + r, yy + r, outline="#000000", width=1, tags=tags)
        row += 1


def _draw_sand_gravel(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    _draw_sand(canvas, bbox, s, tags)
    x0, y0, x1, y1 = bbox
    step = _px(19, s)
    r = _px(2.5, s)
    row = 0
    for yy in range(int(y0 + step * 0.5), int(y1), int(step)):
        shift = step * 0.5 if (row % 2) else 0
        for xx in range(int(x0 + step * 0.5 + shift), int(x1), int(step)):
            canvas.create_oval(xx - r, yy - r, xx + r, yy + r, outline="#000000", width=1, tags=tags)
        row += 1


def _draw_argillite(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    x0, y0, x1, y1 = bbox
    h_step = _px(12, s)
    d_len = _px(7, s)
    x_step = _px(24, s)
    for yy in range(int(y0), int(y1 + h_step), int(h_step)):
        canvas.create_line(x0, float(yy), x1, float(yy), fill="#000000", width=1, tags=tags)
    for yy in range(int(y0 + h_step * 0.5), int(y1), int(h_step)):
        for xx in range(int(x0 + x_step * 0.5), int(x1), int(x_step)):
            canvas.create_line(xx - d_len * 0.5, yy + d_len * 0.5, xx + d_len * 0.5, yy - d_len * 0.5, fill="#000000", width=1, tags=tags)


def _draw_sandstone(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    x0, y0, x1, y1 = bbox
    h_step = _px(14, s)
    dot_step = _px(10, s)
    cross_step = _px(34, s)
    cross = _px(9, s)
    r = _px(1.0, s)
    for yy in range(int(y0), int(y1 + h_step), int(h_step)):
        canvas.create_line(x0, float(yy), x1, float(yy), fill="#000000", width=1, tags=tags)
    row = 0
    for yy in range(int(y0 + dot_step * 0.5), int(y1), int(dot_step)):
        shift = dot_step * 0.5 if (row % 2) else 0
        for xx in range(int(x0 + dot_step * 0.5 + shift), int(x1), int(dot_step)):
            canvas.create_oval(xx - r, yy - r, xx + r, yy + r, fill="#000000", outline="#000000", width=1, tags=tags)
        row += 1
    for yy in range(int(y0 + cross_step * 0.5), int(y1), int(cross_step)):
        for xx in range(int(x0 + cross_step * 0.5), int(x1), int(cross_step)):
            canvas.create_line(xx - cross * 0.5, yy - cross * 0.5, xx + cross * 0.5, yy + cross * 0.5, fill="#000000", width=1, tags=tags)
            canvas.create_line(xx - cross * 0.5, yy + cross * 0.5, xx + cross * 0.5, yy - cross * 0.5, fill="#000000", width=1, tags=tags)


def _draw_fallback(canvas: Any, bbox: tuple[float, float, float, float], s: dict[str, float], tags: Any) -> None:
    _draw_diag_family(canvas, bbox, step=_px(14, s), slope=+1, tags=tags)


def draw_hatch(canvas: Any, bbox: tuple[float, float, float, float], soil_code: str, scale_info: dict[str, Any] | None, tags: Any) -> None:
    """Единый интерфейс отрисовки штриховки слоя: draw_hatch(canvas, bbox, soil_code, scale_info)."""
    s = _norm_scale(scale_info, bbox)
    key = str(soil_code or "")
    name = SOIL_CODE_TO_RENDERER.get(key)
    renderer = globals().get(name or "", _draw_fallback)
    renderer(canvas, bbox, s, tags)
