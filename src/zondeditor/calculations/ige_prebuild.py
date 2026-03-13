from __future__ import annotations

from dataclasses import dataclass


MIN_AUTO_LAYER_THICKNESS_M = 0.8
MAX_AUTO_LAYERS_PER_TEST = 6
SMOOTH_WINDOW = 5


@dataclass
class AutoLayerCandidate:
    top_m: float
    bot_m: float
    soil_kind: str


def smooth_series(values: list[float], window: int = SMOOTH_WINDOW) -> list[float]:
    if not values:
        return []
    w = max(1, int(window))
    if w <= 1:
        return [float(v) for v in values]
    out: list[float] = []
    n = len(values)
    r = w // 2
    for i in range(n):
        a = max(0, i - r)
        b = min(n, i + r + 1)
        seg = [float(x) for x in values[a:b]]
        out.append(sum(seg) / len(seg))
    return out


def _soil_from_rf(rf_avg: float | None) -> str:
    if rf_avg is None:
        return "супесь"
    if rf_avg < 1.0:
        return "песок"
    if rf_avg < 2.5:
        return "супесь"
    return "суглинок"


def build_preliminary_layers(samples: list[tuple[float, float, float, float | None]]) -> list[AutoLayerCandidate]:
    """samples: (depth_m, qc_mpa, fs_kpa, rf_pct)."""
    if len(samples) < 4:
        return []
    ss = sorted(samples, key=lambda x: x[0])
    depths = [float(x[0]) for x in ss]
    qc = smooth_series([float(x[1]) for x in ss])
    fs = smooth_series([float(x[2]) for x in ss])
    rf = smooth_series([float(x[3]) if x[3] is not None else 0.0 for x in ss])

    top = depths[0]
    bot = depths[-1]
    boundaries = [top]

    for i in range(1, len(ss)):
        q_jump = abs(qc[i] - qc[i - 1])
        f_jump = abs(fs[i] - fs[i - 1])
        r_jump = abs(rf[i] - rf[i - 1])
        d = float(depths[i])
        if q_jump >= 2.0 or f_jump >= 40.0 or r_jump >= 0.8:
            if (d - boundaries[-1]) >= MIN_AUTO_LAYER_THICKNESS_M:
                boundaries.append(d)
        if len(boundaries) >= MAX_AUTO_LAYERS_PER_TEST:
            break

    if (bot - boundaries[-1]) >= MIN_AUTO_LAYER_THICKNESS_M:
        boundaries.append(bot)
    if len(boundaries) < 2:
        boundaries = [top, bot]

    layers: list[AutoLayerCandidate] = []
    for i in range(len(boundaries) - 1):
        lt = float(boundaries[i])
        lb = float(boundaries[i + 1])
        if lb - lt < MIN_AUTO_LAYER_THICKNESS_M:
            continue
        seg_rf = [float(x[3]) for x in ss if lt <= float(x[0]) <= lb and x[3] is not None]
        rf_avg = (sum(seg_rf) / len(seg_rf)) if seg_rf else None
        layers.append(AutoLayerCandidate(top_m=lt, bot_m=lb, soil_kind=_soil_from_rf(rf_avg)))

    # merge neighbors with same kind or weak contrast
    merged: list[AutoLayerCandidate] = []
    for lyr in layers:
        if not merged:
            merged.append(lyr)
            continue
        prev = merged[-1]
        weak = abs(prev.bot_m - lyr.top_m) < 1e-6
        if weak and prev.soil_kind == lyr.soil_kind:
            merged[-1] = AutoLayerCandidate(top_m=prev.top_m, bot_m=lyr.bot_m, soil_kind=prev.soil_kind)
            continue
        merged.append(lyr)

    return merged[:MAX_AUTO_LAYERS_PER_TEST]
