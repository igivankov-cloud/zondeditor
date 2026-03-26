from __future__ import annotations

import math
from typing import Any

from src.zondeditor.domain.hatching import (
    DEFAULT_HATCH_USAGE,
    HatchLine,
    HatchPattern,
    clip_segment_to_rect,
    clock_basis,
    local_to_world,
    resolve_hatch_render_scale,
)


HATCH_UNIT_PX = 80.0


def _emit_hatch_debug(scale_info: dict[str, Any] | None, event: str, **payload: Any) -> None:
    if not isinstance(scale_info, dict):
        return
    hook = scale_info.get("debug_hook")
    if not callable(hook):
        return
    try:
        hook(event, **payload)
    except Exception:
        pass


def _draw_point(canvas: Any, x: float, y: float, color: str, thickness_mm: float, scale: float, tags: Any) -> int:
    dot_r_px = max(1, int(round(max(0.15, thickness_mm if thickness_mm > 0 else 0.15) * scale * 0.35)))
    canvas.create_oval(x - dot_r_px, y - dot_r_px, x + dot_r_px, y + dot_r_px, fill=color, outline=color, tags=tags)
    return 1


def _rect_to_world(rect: tuple[float, float, float, float], scale: float) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = [float(v) for v in rect]
    return (x0 / scale, -y1 / scale, x1 / scale, -y0 / scale)


def _expand_world_rect(rect: tuple[float, float, float, float], margin: float) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = rect
    pad = max(0.0, float(margin))
    return (x0 - pad, y0 - pad, x1 + pad, y1 + pad)


def _project_rect_to_axis(rect: tuple[float, float, float, float], ax: float, ay: float) -> tuple[float, float]:
    x0, y0, x1, y1 = rect
    vals = [
        x0 * ax + y0 * ay,
        x0 * ax + y1 * ay,
        x1 * ax + y0 * ay,
        x1 * ax + y1 * ay,
    ]
    return (min(vals), max(vals))


def _stable_k_range(base_x: float, base_y: float, step_x: float, step_y: float, nx: float, ny: float, generation_rect_world: tuple[float, float, float, float]) -> range:
    off_proj = step_x * nx + step_y * ny
    if abs(off_proj) < 1e-9:
        return range(0, 1)
    rect_min, rect_max = _project_rect_to_axis(generation_rect_world, nx, ny)
    base_proj = base_x * nx + base_y * ny
    k0 = int(math.floor((rect_min - base_proj) / off_proj)) - 2
    k1 = int(math.ceil((rect_max - base_proj) / off_proj)) + 2
    if k1 < k0:
        k0, k1 = k1, k0
    if (k1 - k0) > 5000:
        mid = (k0 + k1) // 2
        k0, k1 = mid - 2500, mid + 2500
    return range(k0, k1 + 1)


def _draw_pattern_sequence(canvas: Any, px: float, py: float, ux: float, uy: float, t1: float, t2: float, line: HatchLine, scale: float, tags: Any) -> int:
    parts = []
    total = 0.0
    for seg in line.segments or ():
        if seg.kind == 'Точка':
            gap = max(1e-9, float(seg.gap))
            parts.append(('Точка', 0.0, gap))
            total += gap
        else:
            dash = max(0.0, float(seg.dash))
            gap = max(0.0, float(seg.gap))
            parts.append(('Штрих', dash, gap))
            total += max(1e-9, dash + gap)

    line_px = max(1, int(round(max(0.0, line.thickness_mm) * scale)))
    if not parts or total <= 1e-9:
        canvas.create_line(px + t1 * ux * scale, py - t1 * uy * scale, px + t2 * ux * scale, py - t2 * uy * scale, fill=line.color, width=line_px, tags=tags)
        return 1

    # Важный инвариант: phase sequence считается по абсолютному параметру t
    # вдоль бесконечной линии от стабильного anchor (px, py), а не от начала clipped-сегмента.
    drawn = 0
    n_start = math.floor(t1 / total) - 1
    n_end = math.ceil(t2 / total) + 1
    for n in range(n_start, n_end + 1):
        cursor = n * total
        for kind, dash, gap in parts:
            if kind == 'Точка':
                t = cursor
                if t1 <= t <= t2:
                    drawn += _draw_point(canvas, px + t * ux * scale, py - t * uy * scale, line.color, line.thickness_mm, scale, tags)
                cursor += gap
            else:
                a = cursor
                b = cursor + dash
                if b >= t1 and a <= t2 and b > a:
                    sa = max(t1, a)
                    sb = min(t2, b)
                    if sb > sa:
                        canvas.create_line(px + sa * ux * scale, py - sa * uy * scale, px + sb * ux * scale, py - sb * uy * scale, fill=line.color, width=line_px, tags=tags)
                        drawn += 1
                cursor += dash + gap
    return drawn


def render_hatch_line(
    canvas: Any,
    rect: tuple[float, float, float, float],
    line: HatchLine,
    *,
    unit_px: float,
    tags: Any,
    logical_rect: tuple[float, float, float, float] | None = None,
    scale_info: dict[str, Any] | None = None,
) -> None:
    if not line.enabled:
        _emit_hatch_debug(scale_info, "hatch_line_skip", reason="line_disabled")
        return
    x0, y0, x1, y1 = rect
    scale = float(unit_px)
    if x1 <= x0 or y1 <= y0:
        _emit_hatch_debug(scale_info, "hatch_line_skip", reason="empty_rect")
        return

    angle = float(line.angle_deg)
    ex, ey = clock_basis(angle)
    ux, uy = ex
    nx, ny = ey

    # Стабильный anchor/origin паттерна задаётся только JSON-параметрами строки.
    base_x, base_y = local_to_world(angle, float(line.x), float(line.y))
    step_x, step_y = local_to_world(angle, float(line.dx), float(line.dy))

    draw_rect_world = _rect_to_world(rect, scale)
    source_rect = logical_rect if logical_rect is not None else rect
    logical_rect_world = _rect_to_world(source_rect, scale)
    logical_diag = math.hypot(logical_rect_world[2] - logical_rect_world[0], logical_rect_world[3] - logical_rect_world[1])
    generation_rect_world = _expand_world_rect(logical_rect_world, max(2.0, logical_diag * 0.5))

    k_values = _stable_k_range(base_x, base_y, step_x, step_y, nx, ny, generation_rect_world)
    rect_corners = (
        (generation_rect_world[0], generation_rect_world[1]),
        (generation_rect_world[0], generation_rect_world[3]),
        (generation_rect_world[2], generation_rect_world[1]),
        (generation_rect_world[2], generation_rect_world[3]),
        (draw_rect_world[0], draw_rect_world[1]),
        (draw_rect_world[0], draw_rect_world[3]),
        (draw_rect_world[2], draw_rect_world[1]),
        (draw_rect_world[2], draw_rect_world[3]),
    )
    candidate_count = 0
    culled_count = 0
    primitive_count = 0
    max_half_len = 0.0

    for k in k_values:
        candidate_count += 1
        px = base_x + k * step_x
        py = base_y + k * step_y

        # Важно: anchor линии задаётся стабильным JSON-origin и может находиться далеко
        # от текущей карточки по касательной линии. Полудлина должна покрывать расстояние
        # от anchor до rect, а не только размер rect, иначе дальние карточки «исчезают».
        half_len = max(math.hypot(cx - px, cy - py) for cx, cy in rect_corners) + 1.0
        if half_len > max_half_len:
            max_half_len = half_len

        # Бесконечная линия строится от стабильного anchor семейства, потом только клиппируется draw rect'ом.
        x_start = px - ux * half_len
        y_start = py - uy * half_len
        x_end = px + ux * half_len
        y_end = py + uy * half_len
        clipped = clip_segment_to_rect(x_start, y_start, x_end, y_end, *draw_rect_world)
        if not clipped:
            culled_count += 1
            continue
        cx1, cy1, cx2, cy2 = clipped
        t1 = (cx1 - px) * ux + (cy1 - py) * uy
        t2 = (cx2 - px) * ux + (cy2 - py) * uy
        if t2 < t1:
            t1, t2 = t2, t1
        primitive_count += _draw_pattern_sequence(canvas, px * scale, -py * scale, ux, uy, t1, t2, line, scale, tags)

    _emit_hatch_debug(
        scale_info,
        "hatch_line_drawn",
        angle_deg=float(line.angle_deg),
        candidate_lines=int(candidate_count),
        culled_lines=int(culled_count),
        primitives_count=int(primitive_count),
        max_half_len=float(max_half_len),
        draw_rect_world=tuple(float(v) for v in draw_rect_world),
        generation_rect_world=tuple(float(v) for v in generation_rect_world),
    )


def render_hatch_pattern(canvas: Any, rect: tuple[float, float, float, float], pattern: HatchPattern, *, tags: Any, scale_info: dict[str, float | str | tuple[float, float, float, float]] | None = None) -> None:
    x0, y0, x1, y1 = [float(v) for v in rect]
    if x1 <= x0 or y1 <= y0:
        return
    info = dict(scale_info or {})
    usage = str(info.get('usage') or DEFAULT_HATCH_USAGE)
    logical_rect_raw = info.get('logical_rect')
    logical_rect = tuple(float(v) for v in logical_rect_raw) if isinstance(logical_rect_raw, (tuple, list)) and len(logical_rect_raw) == 4 else None
    render_scale = resolve_hatch_render_scale(pattern, usage=usage, base_unit_px=HATCH_UNIT_PX)
    _emit_hatch_debug(
        info,
        "hatch_pattern_begin",
        rect=(x0, y0, x1, y1),
        logical_rect=logical_rect,
        usage=usage,
        pattern_name=str(getattr(pattern, "name", "") or ""),
        lines_count=len(pattern.lines),
        effective_unit_px=float(render_scale.effective_unit_px),
    )
    for line in pattern.lines:
        render_hatch_line(
            canvas,
            (x0, y0, x1, y1),
            line,
            unit_px=render_scale.effective_unit_px,
            tags=tags,
            logical_rect=logical_rect,
            scale_info=info,
        )
