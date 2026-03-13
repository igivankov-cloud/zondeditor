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
