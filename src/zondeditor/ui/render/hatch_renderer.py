from __future__ import annotations

import math
from typing import Any

from src.zondeditor.domain.hatching import HatchLine, HatchPattern, clip_segment_to_rect, clock_basis, local_to_world


HATCH_UNIT_PX = 80.0


def _draw_point(canvas: Any, x: float, y: float, color: str, thickness_mm: float, scale: float, tags: Any) -> int:
    dot_r_px = max(1, int(round(max(0.15, thickness_mm if thickness_mm > 0 else 0.15) * scale * 0.35)))
    canvas.create_oval(x - dot_r_px, y - dot_r_px, x + dot_r_px, y + dot_r_px, fill=color, outline=color, tags=tags)
    return 1


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


def render_hatch_line(canvas: Any, rect: tuple[float, float, float, float], line: HatchLine, *, unit_px: float, tags: Any) -> None:
    if not line.enabled:
        return
    x0, y0, x1, y1 = rect
    scale = float(unit_px)

    angle = float(line.angle_deg)
    ex, ey = clock_basis(angle)
    ux, uy = ex
    base_x, base_y = local_to_world(angle, float(line.x), float(line.y))
    step_x, step_y = local_to_world(angle, float(line.dx), float(line.dy))
    perp_step = step_x * ey[0] + step_y * ey[1]

    xmin = x0 / scale
    xmax = x1 / scale
    ymin = -y1 / scale
    ymax = -y0 / scale
    diag = math.hypot(xmax - xmin, ymax - ymin)

    if abs(perp_step) < 1e-9:
        k_values = (0,)
    else:
        kmax = int(diag / abs(perp_step)) + 6
        k_values = range(-kmax, kmax + 1)

    half_len = diag * 2.5
    for k in k_values:
        px = base_x + k * step_x
        py = base_y + k * step_y
        x_start = px - ux * half_len
        y_start = py - uy * half_len
        x_end = px + ux * half_len
        y_end = py + uy * half_len
        clipped = clip_segment_to_rect(x_start, y_start, x_end, y_end, xmin, ymin, xmax, ymax)
        if not clipped:
            continue
        cx1, cy1, cx2, cy2 = clipped
        t1 = (cx1 - px) * ux + (cy1 - py) * uy
        t2 = (cx2 - px) * ux + (cy2 - py) * uy
        if t2 < t1:
            t1, t2 = t2, t1
        _draw_pattern_sequence(canvas, 0.0 + px * scale, 0.0 - py * scale, ux, uy, t1, t2, line, scale, tags)


def render_hatch_pattern(canvas: Any, rect: tuple[float, float, float, float], pattern: HatchPattern, *, tags: Any, scale_info: dict[str, float] | None = None) -> None:
    x0, y0, x1, y1 = [float(v) for v in rect]
    if x1 <= x0 or y1 <= y0:
        return
    unit_px = HATCH_UNIT_PX / max(1e-9, float(pattern.scale or 1.0))
    for line in pattern.lines:
        render_hatch_line(canvas, (x0, y0, x1, y1), line, unit_px=unit_px, tags=tags)
