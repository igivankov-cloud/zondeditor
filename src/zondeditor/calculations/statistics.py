from __future__ import annotations

from statistics import mean, pstdev

from .models import IGECalcPoint, IGECalcStats


def calc_stats(points: list[IGECalcPoint]) -> IGECalcStats:
    qc = [float(p.qc_mpa) for p in points if float(p.qc_mpa) > 0]
    fs = [float(p.fs_kpa) for p in points if p.fs_kpa is not None]
    depths = [float(p.depth_m) for p in points]
    if not qc:
        return IGECalcStats()
    avg = float(mean(qc))
    sd = float(pstdev(qc)) if len(qc) > 1 else 0.0
    return IGECalcStats(
        n_points=len(qc),
        qc_avg_mpa=avg,
        qc_min_mpa=min(qc),
        qc_max_mpa=max(qc),
        fs_avg_kpa=(float(mean(fs)) if fs else None),
        v_qc=(sd / avg if avg > 0 else 0.0),
        avg_depth_m=(float(mean(depths)) if depths else None),
    )
