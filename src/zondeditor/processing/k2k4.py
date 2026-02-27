# src/zondeditor/processing/k2k4.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Any, Iterable, Optional

@dataclass(frozen=True)
class K2K4Result:
    k4_raw: int
    censored: bool
    qc_mpa: float

def convert_k2_raw_to_k4_raw(
    k2_raw: int,
    *,
    mode: str = "K4_50MPA",
) -> K2K4Result:
    """Convert a K2 raw value (0..250) to a K4 raw value (0..1000).

    Modes:
      - K4_30MPA: simple upscale (k4 = k2*4). This matches a K4 device with 30 MPa full scale.
      - K4_50MPA: physics mapping via qc:
          qc_mpa = (k2/250)*30
          k4_raw = round(qc_mpa/50*1000)  (30 MPa -> 600)
    Censorship:
      - if k2_raw >= 250, mark censored=True (K2 hit its limit at 30 MPa)
        do NOT attempt to infer >30 MPa from a saturated K2.
    """
    try:
        k2 = int(k2_raw)
    except Exception:
        k2 = 0
    k2 = max(0, min(250, k2))

    censored = (k2 >= 250)
    qc_mpa = (k2 / 250.0) * 30.0

    m = (mode or "K4_50MPA").upper()
    if m in ("K4_30", "K4_30MPA", "30", "30MPA"):
        k4 = k2 * 4
    else:
        k4 = int(round((qc_mpa / 50.0) * 1000.0))

    k4 = max(0, min(1000, k4))
    return K2K4Result(k4_raw=k4, censored=censored, qc_mpa=qc_mpa)

def convert_test_k2_to_k4(
    test: Any,
    *,
    mode: str = "K4_50MPA",
) -> Tuple[list[int], list[bool]]:
    """Convert an entire test's qc raw series (K2) into K4 raw series.

    Returns:
      (k4_series, censored_mask) aligned with rows.
    Note: only converts qc channel (main), fs is typically measured similarly but device-specific.
    """
    qc = list(getattr(test, "qc", []) or [])
    k4 = []
    mask = []
    for v in qc:
        try:
            k2 = int(float(str(v).replace(",", ".")))
        except Exception:
            k2 = 0
        r = convert_k2_raw_to_k4_raw(k2, mode=mode)
        k4.append(r.k4_raw)
        mask.append(r.censored)
    return k4, mask
