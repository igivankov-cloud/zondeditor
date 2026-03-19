from __future__ import annotations

import math
from typing import Any

from src.zondeditor.domain.hatching import HatchLine, HatchPattern


HATCH_UNIT_PX = 80.0


def _line_rect_intersections(px: float, py: float, vx: float, vy: float, rect: tuple[float, float, float, float]) -> tuple[float, float] | None:
    x0, y0, x1, y1 = rect
    pts: list[float] = []
    eps = 1e-9
    if abs(vx) > eps:
        for xx in (x0, x1):
            t = (xx - px) / vx
            yy = py + t * vy
            if y0 - 1e-6 <= yy <= y1 + 1e-6:
                pts.append(t)
    if abs(vy) > eps:
        for yy in (y0, y1):
            t = (yy - py) / vy
            xx = px + t * vx
            if x0 - 1e-6 <= xx <= x1 + 1e-6:
                pts.append(t)
    if len(pts) < 2:
        return None
    pts.sort()
    return (pts[0], pts[-1])


def _draw_patterned_segment(canvas: Any, px: float, py: float, vx: float, vy: float, t0: float, t1: float, pattern_px: list[float], tags: Any) -> None:
    if not pattern_px:
        canvas.create_line(px + t0 * vx, py + t0 * vy, px + t1 * vx, py + t1 * vy, fill="#000000", width=1, tags=tags)
        return

    total = sum(abs(x) for x in pattern_px)
    if total <= 1e-6:
        canvas.create_line(px + t0 * vx, py + t0 * vy, px + t1 * vx, py + t1 * vy, fill="#000000", width=1, tags=tags)
        return

    pos = t0
    idx = 0
    guard = 0
    while pos < t1 and guard < 400:
        seg = max(0.5, abs(pattern_px[idx % len(pattern_px)]))
        nxt = min(t1, pos + seg)
        if pattern_px[idx % len(pattern_px)] > 0:
            canvas.create_line(px + pos * vx, py + pos * vy, px + nxt * vx, py + nxt * vy, fill="#000000", width=1, tags=tags)
        pos = nxt
        idx += 1
        guard += 1


def render_hatch_line(canvas: Any, rect: tuple[float, float, float, float], line: HatchLine, *, unit_px: float, tags: Any) -> None:
    x0, y0, x1, y1 = rect
    a = math.radians(float(line.angle_deg))
    vx = math.cos(a)
    vy = math.sin(a)

    # нормаль к направлению штриховки
    nx = -vy
    ny = vx

    # базовая точка паттерна привязана к глобальным координатам canvas,
    # чтобы слой только клиппировал штриховку, а не масштабировал/сдвигал её заново.
    p0x = float(line.x0) * unit_px
    p0y = float(line.y0) * unit_px
    ox = float(line.dx) * unit_px
    oy = float(line.dy) * unit_px

    off_proj = ox * nx + oy * ny
    if abs(off_proj) < 1e-6:
        off_proj = max(4.0, 0.12 * unit_px)
        ox, oy = nx * off_proj, ny * off_proj

    corners = [(x0, y0), (x0, y1), (x1, y0), (x1, y1)]
    cs = [cx * nx + cy * ny for cx, cy in corners]
    cmin, cmax = min(cs), max(cs)

    c0 = p0x * nx + p0y * ny
    k0 = int(math.floor((cmin - c0) / off_proj)) - 2
    k1 = int(math.ceil((cmax - c0) / off_proj)) + 2

    pattern_px = [float(v) * unit_px for v in (line.pattern or [])]

    if abs(k1 - k0) > 500:
        mid = (k0 + k1) // 2
        k0, k1 = mid - 250, mid + 250

    for k in range(min(k0, k1), max(k0, k1) + 1):
        px = p0x + k * ox
        py = p0y + k * oy
        ts = _line_rect_intersections(px, py, vx, vy, rect)
        if not ts:
            continue
        t_start, t_end = ts
        _draw_patterned_segment(canvas, px, py, vx, vy, t_start, t_end, pattern_px, tags)


def render_hatch_pattern(canvas: Any, rect: tuple[float, float, float, float], pattern: HatchPattern, *, tags: Any, scale_info: dict[str, float] | None = None) -> None:
    x0, y0, x1, y1 = [float(v) for v in rect]
    if x1 <= x0 or y1 <= y0:
        return
    # Масштаб паттерна постоянный для всех слоёв.
    # rect используется только как область клиппинга.
    unit_px = HATCH_UNIT_PX

    for line in (pattern.lines or []):
        render_hatch_line(canvas, (x0, y0, x1, y1), line, unit_px=unit_px, tags=tags)
