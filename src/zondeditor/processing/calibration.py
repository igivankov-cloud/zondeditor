# src/zondeditor/processing/calibration.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple

# Геометрия датчиков (как в монолите/GeoExplorer-подходе)
CONE_AREA_CM2 = 10.0
SLEEVE_AREA_CM2 = 350.0

@dataclass(frozen=True)
class Calibration:
    # делитель шкалы (K2=250, K4=1000)
    scale_div: int
    # пределы измерения (кН) для пересчёта (настройка прибора)
    fcone_kn: float
    fsleeve_kn: float
    # площади датчиков (см²)
    cone_area_cm2: float = CONE_AREA_CM2
    sleeve_area_cm2: float = SLEEVE_AREA_CM2

# ДЕФОЛТЫ:
# K2: 30 МПа (через 30 кН на конус) и 10 кН на муфту, шкала 250
K2_DEFAULT = Calibration(scale_div=250, fcone_kn=30.0, fsleeve_kn=10.0)
# K4 (частый вариант): 50 МПа на конус и 10 кН на муфту, шкала 1000
# Если у твоего K4 предел другой — просто передавай свою Calibration.
K4_DEFAULT = Calibration(scale_div=1000, fcone_kn=50.0, fsleeve_kn=10.0)


def _to_float(value: Any, default: float) -> float:
    try:
        text = str(value or "").strip().replace(",", ".")
        return float(text) if text else default
    except Exception:
        return default


def calibration_from_common_params(
    common_params: Mapping[str, Any] | None,
    *,
    geo_kind: str = "K2",
) -> Calibration:
    """Build calibration snapshot from common params with safe defaults."""
    g = (geo_kind or "K2").upper()
    default = K4_DEFAULT if g == "K4" else K2_DEFAULT
    cp = dict(common_params or {})

    scale_div = int(round(_to_float(cp.get("controller_scale_div"), float(default.scale_div))))
    if scale_div <= 0:
        scale_div = default.scale_div

    fcone_kn = _to_float(cp.get("cone_kn"), default.fcone_kn)
    fsleeve_kn = _to_float(cp.get("sleeve_kn"), default.fsleeve_kn)
    cone_area_cm2 = _to_float(cp.get("cone_area_cm2"), default.cone_area_cm2)
    sleeve_area_cm2 = _to_float(cp.get("sleeve_area_cm2"), default.sleeve_area_cm2)

    if fcone_kn <= 0:
        fcone_kn = default.fcone_kn
    if fsleeve_kn <= 0:
        fsleeve_kn = default.fsleeve_kn
    if cone_area_cm2 <= 0:
        cone_area_cm2 = default.cone_area_cm2
    if sleeve_area_cm2 <= 0:
        sleeve_area_cm2 = default.sleeve_area_cm2

    return Calibration(
        scale_div=scale_div,
        fcone_kn=fcone_kn,
        fsleeve_kn=fsleeve_kn,
        cone_area_cm2=cone_area_cm2,
        sleeve_area_cm2=sleeve_area_cm2,
    )

def calc_qc_fs_from_del(
    qc_del: int,
    fs_del: int,
    *,
    scale_div: int = 250,
    fcone_kn: float = 30.0,
    fsleeve_kn: float = 10.0,
    cone_area_cm2: float = CONE_AREA_CM2,
    sleeve_area_cm2: float = SLEEVE_AREA_CM2,
) -> Tuple[float, float]:
    """Пересчёт делений в qc (МПа) и fs (кПа) (GeoExplorer-like).

    qc_mpa = (qc_del/scale_div) * fcone_kn * (10 / cone_area_cm2)
    fs_kpa = (fs_del/scale_div) * fsleeve_kn * (10000 / sleeve_area_cm2)
    """
    if scale_div <= 0:
        scale_div = 250
    if cone_area_cm2 <= 0:
        cone_area_cm2 = CONE_AREA_CM2
    if sleeve_area_cm2 <= 0:
        sleeve_area_cm2 = SLEEVE_AREA_CM2
    qc_mpa = (qc_del / scale_div) * fcone_kn * (10.0 / cone_area_cm2)
    fs_kpa = (fs_del / scale_div) * fsleeve_kn * (10000.0 / sleeve_area_cm2)
    return qc_mpa, fs_kpa

def calc_qc_fs(
    qc_raw: int,
    fs_raw: int,
    *,
    geo_kind: str = "K2",
    cal: Calibration | None = None,
) -> Tuple[float, float]:
    """Единый пересчёт qc/fs для K2 и K4.

    geo_kind:
      - "K2": ожидаются qc_raw/fs_raw в диапазоне 0..250
      - "K4": ожидаются qc_raw/fs_raw в диапазоне 0..1000

    cal:
      - если None, берём дефолт K2_DEFAULT или K4_DEFAULT.
    """
    g = (geo_kind or "K2").upper()
    if cal is None:
        cal = K4_DEFAULT if g == "K4" else K2_DEFAULT
    return calc_qc_fs_from_del(
        qc_raw,
        fs_raw,
        scale_div=cal.scale_div,
        fcone_kn=cal.fcone_kn,
        fsleeve_kn=cal.fsleeve_kn,
        cone_area_cm2=cal.cone_area_cm2,
        sleeve_area_cm2=cal.sleeve_area_cm2,
    )
