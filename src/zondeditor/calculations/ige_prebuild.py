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


def correlate_intervals_to_global_iges(
    local_intervals_by_test: dict[str, list[dict[str, Any]]],
    *,
    depth_overlap_min: float = 0.35,
    center_shift_max_m: float = 1.0,
    qc_rel_tol: float = 0.35,
    rf_abs_tol: float = 1.0,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Group local intervals from separate tests into shared global IGE clusters."""

    def _overlap_ratio(a: dict[str, Any], b: dict[str, Any]) -> float:
        at, ab = float(a.get("z_from", 0.0)), float(a.get("z_to", 0.0))
        bt, bb = float(b.get("z_from", 0.0)), float(b.get("z_to", 0.0))
        ov = max(0.0, min(ab, bb) - max(at, bt))
        den = max(1e-6, min(max(0.0, ab - at), max(0.0, bb - bt)))
        return float(ov / den)

    def _center(v: dict[str, Any]) -> float:
        return 0.5 * (float(v.get("z_from", 0.0)) + float(v.get("z_to", 0.0)))

    clusters: list[dict[str, Any]] = []
    assigned: dict[str, list[dict[str, Any]]] = {str(k): [] for k in (local_intervals_by_test or {}).keys()}

    all_items: list[tuple[str, dict[str, Any]]] = []
    for test_id, vals in (local_intervals_by_test or {}).items():
        for iv in (vals or []):
            one = dict(iv or {})
            one.setdefault("test_id", str(test_id))
            all_items.append((str(test_id), one))
    all_items.sort(key=lambda x: (float(x[1].get("z_from", 0.0)), float(x[1].get("z_to", 0.0))))

    for test_id, iv in all_items:
        soil = str(iv.get("preliminary_type") or "")
        qc = iv.get("qc_avg")
        rf = iv.get("rf_avg")
        best_idx = None
        best_score = -1.0
        for idx, cl in enumerate(clusters):
            if str(cl.get("preliminary_type") or "") != soil:
                continue
            rep = dict(cl.get("representative") or {})
            ov = _overlap_ratio(iv, rep)
            cshift = abs(_center(iv) - _center(rep))
            if ov < depth_overlap_min and cshift > center_shift_max_m:
                continue
            score = ov - 0.1 * cshift
            rep_qc = rep.get("qc_avg")
            if qc is not None and rep_qc is not None:
                rel = abs(float(qc) - float(rep_qc)) / max(0.5, abs(float(rep_qc)))
                if rel > qc_rel_tol:
                    continue
                score -= 0.2 * rel
            rep_rf = rep.get("rf_avg")
            if rf is not None and rep_rf is not None:
                drf = abs(float(rf) - float(rep_rf))
                if drf > rf_abs_tol:
                    continue
                score -= 0.1 * (drf / max(0.2, rf_abs_tol))
            if score > best_score:
                best_score = score
                best_idx = idx

        if best_idx is None:
            cluster = {
                "cluster_id": f"cluster_{len(clusters) + 1}",
                "preliminary_type": soil,
                "members": [dict(iv)],
                "representative": dict(iv),
            }
            clusters.append(cluster)
            assigned[str(test_id)].append({**dict(iv), "cluster_id": cluster["cluster_id"]})
            continue

        cl = clusters[best_idx]
        cl["members"].append(dict(iv))
        mem = list(cl["members"])
        cl["representative"] = {
            "z_from": sum(float(x.get("z_from", 0.0)) for x in mem) / len(mem),
            "z_to": sum(float(x.get("z_to", 0.0)) for x in mem) / len(mem),
            "preliminary_type": str(cl.get("preliminary_type") or ""),
            "qc_avg": (sum(float(x.get("qc_avg", 0.0)) for x in mem if x.get("qc_avg") is not None) / max(1, len([x for x in mem if x.get("qc_avg") is not None]))) if any(x.get("qc_avg") is not None for x in mem) else None,
            "rf_avg": (sum(float(x.get("rf_avg", 0.0)) for x in mem if x.get("rf_avg") is not None) / max(1, len([x for x in mem if x.get("rf_avg") is not None]))) if any(x.get("rf_avg") is not None for x in mem) else None,
        }
        assigned[str(test_id)].append({**dict(iv), "cluster_id": str(cl.get("cluster_id"))})

    out_clusters = sorted(clusters, key=lambda x: float((x.get("representative") or {}).get("z_from", 0.0)))
    return assigned, out_clusters
