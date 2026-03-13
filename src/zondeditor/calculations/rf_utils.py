from __future__ import annotations


def calc_rf_pct(fs_kpa: float | None, qc_mpa: float | None) -> float | None:
    """Rf = (fs / qc) * 100%, where fs in kPa and qc in MPa.

    qc is converted to kPa before ratio. Returns None for invalid/zero denominators.
    """
    try:
        if fs_kpa is None or qc_mpa is None:
            return None
        qc_kpa = float(qc_mpa) * 1000.0
        fs = float(fs_kpa)
        if qc_kpa <= 1e-9 or fs < 0:
            return None
        return (fs / qc_kpa) * 100.0
    except Exception:
        return None


def robust_rf_scale_max(rf_values: list[float], *, default_max: float = 10.0, percentile: float = 0.95, cap_max: float = 15.0) -> float:
    vals = [float(v) for v in (rf_values or []) if v is not None and float(v) >= 0.0]
    if not vals:
        return float(default_max)
    vals.sort()
    p = min(1.0, max(0.5, float(percentile)))
    idx = int(round((len(vals) - 1) * p))
    pval = vals[max(0, min(len(vals) - 1, idx))]
    scaled = max(float(default_max), pval * 1.2)
    return min(float(cap_max), scaled)
