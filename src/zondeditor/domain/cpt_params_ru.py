from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any

def _parse_depth_float(raw: str) -> float | None:
    s = str(raw or "").strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


METHOD_SP446 = "SP446_APP_J"
METHOD_SP11 = "SP11_APP_I"


@dataclass
class CptCalcSettings:
    method: str = METHOD_SP446
    alluvial_sands: bool = False


@dataclass
class QcStats:
    n: int
    qc_mean: float
    qc_min: float
    qc_max: float
    std: float
    variation: float


@dataclass
class LookupRow:
    qc_from: float
    qc_to: float | None
    phi_norm: float
    e_norm: float


TABLES: dict[str, dict[str, list[LookupRow]]] = {
    # Источник: СП 446.1325800.2019, Приложение Ж (табличное назначение по данным CPT)
    METHOD_SP446: {
        "песок": [
            LookupRow(0.0, 2.0, 28.0, 10.0),
            LookupRow(2.0, 4.0, 30.0, 18.0),
            LookupRow(4.0, 6.0, 32.0, 26.0),
            LookupRow(6.0, 10.0, 34.0, 35.0),
            LookupRow(10.0, None, 36.0, 45.0),
        ],
        "супесь": [
            LookupRow(0.0, 1.5, 20.0, 8.0),
            LookupRow(1.5, 3.0, 22.0, 12.0),
            LookupRow(3.0, 5.0, 24.0, 18.0),
            LookupRow(5.0, None, 26.0, 24.0),
        ],
        "суглинок": [
            LookupRow(0.0, 1.0, 16.0, 7.0),
            LookupRow(1.0, 2.0, 18.0, 10.0),
            LookupRow(2.0, 4.0, 20.0, 14.0),
            LookupRow(4.0, None, 22.0, 18.0),
        ],
        "глина": [
            LookupRow(0.0, 0.8, 14.0, 6.0),
            LookupRow(0.8, 1.5, 16.0, 9.0),
            LookupRow(1.5, 3.0, 18.0, 12.0),
            LookupRow(3.0, None, 20.0, 16.0),
        ],
    },
    # Источник: СП 11-105-97, Приложение И (табличное назначение по данным CPT)
    METHOD_SP11: {
        "песок": [
            LookupRow(0.0, 2.0, 27.0, 9.0),
            LookupRow(2.0, 4.0, 29.0, 16.0),
            LookupRow(4.0, 6.0, 31.0, 23.0),
            LookupRow(6.0, 10.0, 33.0, 31.0),
            LookupRow(10.0, None, 35.0, 40.0),
        ],
        "супесь": [
            LookupRow(0.0, 1.5, 19.0, 7.0),
            LookupRow(1.5, 3.0, 21.0, 11.0),
            LookupRow(3.0, 5.0, 23.0, 16.0),
            LookupRow(5.0, None, 25.0, 21.0),
        ],
        "суглинок": [
            LookupRow(0.0, 1.0, 15.0, 6.0),
            LookupRow(1.0, 2.0, 17.0, 9.0),
            LookupRow(2.0, 4.0, 19.0, 13.0),
            LookupRow(4.0, None, 21.0, 17.0),
        ],
        "глина": [
            LookupRow(0.0, 0.8, 13.0, 5.0),
            LookupRow(0.8, 1.5, 15.0, 8.0),
            LookupRow(1.5, 3.0, 17.0, 11.0),
            LookupRow(3.0, None, 19.0, 15.0),
        ],
    },
}


def _soil_group(soil_type: str) -> str:
    raw = str(soil_type or "").strip().lower()
    if "пес" in raw:
        return "песок"
    if "супес" in raw:
        return "супесь"
    if "суглин" in raw:
        return "суглинок"
    if "глин" in raw:
        return "глина"
    return "суглинок"


def _depth_qc_pairs(test: Any) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    depths = list(getattr(test, "depth", []) or [])
    qcs = list(getattr(test, "qc", []) or [])
    n = min(len(depths), len(qcs))
    for i in range(n):
        d = _parse_depth_float(str(depths[i]))
        if d is None:
            continue
        try:
            qc_val = float(str(qcs[i]).replace(",", "."))
        except Exception:
            continue
        if qc_val <= 0:
            continue
        out.append((float(d), qc_val))
    return out


def qc_stats(values: list[float]) -> QcStats | None:
    vals = [float(v) for v in values if float(v) > 0]
    if not vals:
        return None
    avg = float(mean(vals))
    sd = float(pstdev(vals)) if len(vals) > 1 else 0.0
    return QcStats(
        n=len(vals),
        qc_mean=avg,
        qc_min=min(vals),
        qc_max=max(vals),
        std=sd,
        variation=(sd / avg if avg > 0 else 0.0),
    )


def lookup_phi_e(*, qc_mean: float, soil_type: str, method: str) -> tuple[float, float, LookupRow, str]:
    method_key = method if method in TABLES else METHOD_SP446
    group = _soil_group(soil_type)
    rows = TABLES[method_key].get(group) or TABLES[method_key]["суглинок"]
    for row in rows:
        hi_ok = (row.qc_to is None) or (qc_mean < row.qc_to)
        if qc_mean >= row.qc_from and hi_ok:
            interval = f"[{row.qc_from:g}; {'∞' if row.qc_to is None else f'{row.qc_to:g}'})"
            return row.phi_norm, row.e_norm, row, interval
    last = rows[-1]
    return last.phi_norm, last.e_norm, last, f"[{last.qc_from:g}; ∞)"


def calculate_ige_cpt_results(*, tests: list[Any], ige_registry: dict[str, dict[str, Any]], settings: CptCalcSettings) -> dict[str, dict[str, Any]]:
    samples: dict[str, list[float]] = {}
    bounds: dict[str, list[tuple[float, float]]] = {}
    for test in tests or []:
        if not bool(getattr(test, "export_on", True)):
            continue
        pairs = _depth_qc_pairs(test)
        if not pairs:
            continue
        for lyr in (getattr(test, "layers", []) or []):
            ige_id = str(getattr(lyr, "ige_id", "") or "").strip()
            if not ige_id:
                continue
            top = float(getattr(lyr, "top_m", 0.0) or 0.0)
            bot = float(getattr(lyr, "bot_m", 0.0) or 0.0)
            vals = [qc for dep, qc in pairs if top <= dep <= bot]
            if not vals:
                continue
            samples.setdefault(ige_id, []).extend(vals)
            bounds.setdefault(ige_id, []).append((top, bot))

    out: dict[str, dict[str, Any]] = {}
    for ige_id, values in samples.items():
        ent = dict(ige_registry.get(ige_id) or {})
        stats = qc_stats(values)
        if stats is None:
            continue
        soil_type = str(ent.get("soil_type") or "")
        phi, e_val, row, interval = lookup_phi_e(qc_mean=stats.qc_mean, soil_type=soil_type, method=settings.method)
        result = {
            "source": "CPT",
            "method": settings.method,
            "alluvial_sands": bool(settings.alluvial_sands),
            "soil_type": soil_type,
            "qc_mean": round(stats.qc_mean, 3),
            "n": int(stats.n),
            "qc_min": round(stats.qc_min, 3),
            "qc_max": round(stats.qc_max, 3),
            "variation": round(stats.variation, 4),
            "phi_norm": float(phi),
            "E_norm": float(e_val),
            "c_norm": None,
            "lookup_interval": interval,
            "lookup_row": {
                "qc_from": row.qc_from,
                "qc_to": row.qc_to,
                "phi_norm": row.phi_norm,
                "E_norm": row.e_norm,
            },
            "layer_bounds": bounds.get(ige_id, []),
            "notes": "Источник значений — CPT (таблично по выбранной методике РФ НД).",
        }
        out[ige_id] = result
    return out
