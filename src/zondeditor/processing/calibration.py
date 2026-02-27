# src/zondeditor/processing/calibration.py
from __future__ import annotations

from typing import Tuple

CONE_AREA_CM2 = 10.0
SLEEVE_AREA_CM2 = 350.0

def calc_qc_fs_from_del(
    qc_del: int,
    fs_del: int,
    *,
    scale_div: int = 250,
    fcone_kn: float = 30.0,
    fsleeve_kn: float = 10.0,
) -> Tuple[float, float]:
    """Пересчёт делений в qc (МПа) и fs (кПа) как в GeoExplorer.

    Формулы (как в текущем монолите):
      qc_mpa = (qc_del/scale_div) * fcone_kn * (10 / CONE_AREA_CM2)
      fs_kpa = (fs_del/scale_div) * fsleeve_kn * (10000 / SLEEVE_AREA_CM2)
    """
    if scale_div <= 0:
        scale_div = 250
    qc_mpa = (qc_del / scale_div) * fcone_kn * (10.0 / CONE_AREA_CM2)
    fs_kpa = (fs_del / scale_div) * fsleeve_kn * (10000.0 / SLEEVE_AREA_CM2)
    return qc_mpa, fs_kpa
