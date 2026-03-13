from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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


def build_preliminary_layers_with_profile(
    samples: list[tuple[float, float, float, float | None]],
    *,
    profile: dict[str, Any] | None = None,
) -> list[AutoLayerCandidate]:
    """Profile-driven wrapper for preliminary layering.

    Supported keys:
      - min_layer_thickness_m
      - max_layers
      - smoothing_window
      - boundary_q_jump
      - boundary_fs_jump
      - boundary_rf_jump
      - rf_sand_max
      - rf_sandy_loam_max
      - merge_same_soil
    """
    cfg = dict(profile or {})
    min_thk = float(cfg.get("min_layer_thickness_m", MIN_AUTO_LAYER_THICKNESS_M) or MIN_AUTO_LAYER_THICKNESS_M)
    max_layers = max(1, int(cfg.get("max_layers", MAX_AUTO_LAYERS_PER_TEST) or MAX_AUTO_LAYERS_PER_TEST))
    smooth_w = max(1, int(cfg.get("smoothing_window", SMOOTH_WINDOW) or SMOOTH_WINDOW))
    q_thr = float(cfg.get("boundary_q_jump", 2.0) or 2.0)
    fs_thr = float(cfg.get("boundary_fs_jump", 40.0) or 40.0)
    rf_thr = float(cfg.get("boundary_rf_jump", 0.8) or 0.8)
    rf_sand = float(cfg.get("rf_sand_max", 1.0) or 1.0)
    rf_sandy_loam = float(cfg.get("rf_sandy_loam_max", 2.5) or 2.5)
    merge_same = bool(cfg.get("merge_same_soil", True))

    if len(samples) < 4:
        return []
    ss = sorted(samples, key=lambda x: x[0])
    depths = [float(x[0]) for x in ss]
    qc = smooth_series([float(x[1]) for x in ss], smooth_w)
    fs = smooth_series([float(x[2]) for x in ss], smooth_w)
    rf = smooth_series([float(x[3]) if x[3] is not None else 0.0 for x in ss], smooth_w)

    top = depths[0]
    bot = depths[-1]
    boundaries = [top]
    for i in range(1, len(ss)):
        d = float(depths[i])
        if (d - boundaries[-1]) < min_thk:
            continue
        if abs(qc[i] - qc[i - 1]) >= q_thr or abs(fs[i] - fs[i - 1]) >= fs_thr or abs(rf[i] - rf[i - 1]) >= rf_thr:
            boundaries.append(d)
        if len(boundaries) >= max_layers:
            break
    if (bot - boundaries[-1]) >= min_thk:
        boundaries.append(bot)
    if len(boundaries) < 2:
        boundaries = [top, bot]

    layers: list[AutoLayerCandidate] = []
    for i in range(len(boundaries) - 1):
        lt = float(boundaries[i])
        lb = float(boundaries[i + 1])
        if (lb - lt) < min_thk:
            continue
        seg_rf = [float(x[3]) for x in ss if lt <= float(x[0]) <= lb and x[3] is not None]
        rf_avg = (sum(seg_rf) / len(seg_rf)) if seg_rf else None
        soil_kind = "супесь"
        if rf_avg is not None:
            if rf_avg < rf_sand:
                soil_kind = "песок"
            elif rf_avg < rf_sandy_loam:
                soil_kind = "супесь"
            else:
                soil_kind = "суглинок"
        layers.append(AutoLayerCandidate(top_m=lt, bot_m=lb, soil_kind=soil_kind))

    if not merge_same:
        return layers[:max_layers]
    merged: list[AutoLayerCandidate] = []
    for lyr in layers:
        if merged and abs(merged[-1].bot_m - lyr.top_m) < 1e-6 and merged[-1].soil_kind == lyr.soil_kind:
            prev = merged[-1]
            merged[-1] = AutoLayerCandidate(top_m=prev.top_m, bot_m=lyr.bot_m, soil_kind=prev.soil_kind)
            continue
        merged.append(lyr)
    return merged[:max_layers]
