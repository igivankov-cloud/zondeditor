from __future__ import annotations

import math
from typing import Iterable

from .models import HatchSegment


def parse_float(value: str | float | int | None, default: float = 0.0) -> float:
    try:
        s = str(value or "").strip().replace(",", ".")
        if not s:
            return default
        return float(s)
    except Exception:
        return default


def parse_angle_deg(value: str | float | int | None, default: float = 0.0) -> float:
    s = str(value or "").strip()
    if not s:
        return default
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        pass
    try:
        s2 = s.replace("°", " ").replace("'", " ").replace('"', " ")
        parts = [p for p in s2.split() if p]
        if not parts:
            return default
        deg = float(parts[0])
        minute = float(parts[1]) if len(parts) > 1 else 0.0
        second = float(parts[2]) if len(parts) > 2 else 0.0
        sign = -1.0 if deg < 0 else 1.0
        deg = abs(deg)
        return sign * (deg + minute / 60.0 + second / 3600.0)
    except Exception:
        return default


def clip_segment_to_rect(x1: float, y1: float, x2: float, y2: float, xmin: float, ymin: float, xmax: float, ymax: float) -> tuple[float, float, float, float] | None:
    dx = x2 - x1
    dy = y2 - y1
    p = [-dx, dx, -dy, dy]
    q = [x1 - xmin, xmax - x1, y1 - ymin, ymax - y1]
    u1, u2 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if abs(pi) < 1e-12:
            if qi < 0:
                return None
        else:
            t = qi / pi
            if pi < 0:
                if t > u2:
                    return None
                if t > u1:
                    u1 = t
            else:
                if t < u1:
                    return None
                if t < u2:
                    u2 = t
    return x1 + u1 * dx, y1 + u1 * dy, x1 + u2 * dx, y1 + u2 * dy


def clock_basis(angle_deg: float) -> tuple[tuple[float, float], tuple[float, float]]:
    a = math.radians(angle_deg % 360.0)
    ex = (math.sin(a), math.cos(a))
    ey = (ex[1], -ex[0])
    return ex, ey


def local_to_world(angle_deg: float, lx: float, ly: float) -> tuple[float, float]:
    ex, ey = clock_basis(angle_deg)
    return lx * ex[0] + ly * ey[0], lx * ex[1] + ly * ey[1]


def infer_line_type(segments: Iterable[HatchSegment]) -> str:
    segments = tuple(segments)
    if not segments:
        return "Сплошная"
    if len(segments) == 1 and segments[0].kind == "Точка":
        return "Точка"
    return "Штрих"


def normalize_segments(segments: Iterable[dict] | None) -> tuple[HatchSegment, ...]:
    normalized: list[HatchSegment] = []
    for seg in segments or ():
        if not isinstance(seg, dict):
            continue
        kind = str(seg.get("kind") or "Штрих").strip()
        if kind not in {"Штрих", "Точка"}:
            kind = "Штрих"
        if kind == "Точка":
            normalized.append(HatchSegment(kind="Точка", dash=0.0, gap=max(1e-9, parse_float(seg.get("gap"), 1.0))))
        else:
            normalized.append(
                HatchSegment(
                    kind="Штрих",
                    dash=max(0.0, parse_float(seg.get("dash"), 0.3)),
                    gap=max(0.0, parse_float(seg.get("gap"), 3.85692)),
                )
            )
    return tuple(normalized)
