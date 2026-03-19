from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.zondeditor.domain.cpt_ru_sp446 import QcStats, calculate_ige_sp446, qc_stats
from src.zondeditor.calculations.cpt_soil_policy import resolve_cpt_soil_policy

METHOD_SP446 = "SP446_APP_J"
METHOD_SP11 = "SP11_APP_I"


@dataclass
class CptCalcSettings:
    method: str = METHOD_SP446
    alluvial_sands: bool = True
    groundwater_level: float | None = None


@dataclass
class LookupRow:
    qc_from: float
    qc_to: float | None
    phi_norm: float
    e_norm: float


TABLE_SP11: dict[str, list[LookupRow]] = {
    "песок": [
        LookupRow(0.0, 2.0, 27.0, 9.0),
        LookupRow(2.0, 4.0, 29.0, 16.0),
        LookupRow(4.0, 6.0, 31.0, 23.0),
        LookupRow(6.0, 10.0, 33.0, 31.0),
        LookupRow(10.0, None, 35.0, 40.0),
    ],
    "супесь": [LookupRow(0.0, 1.5, 19.0, 7.0), LookupRow(1.5, 3.0, 21.0, 11.0), LookupRow(3.0, 5.0, 23.0, 16.0), LookupRow(5.0, None, 25.0, 21.0)],
    "суглинок": [LookupRow(0.0, 1.0, 15.0, 6.0), LookupRow(1.0, 2.0, 17.0, 9.0), LookupRow(2.0, 4.0, 19.0, 13.0), LookupRow(4.0, None, 21.0, 17.0)],
    "глина": [LookupRow(0.0, 0.8, 13.0, 5.0), LookupRow(0.8, 1.5, 15.0, 8.0), LookupRow(1.5, 3.0, 17.0, 11.0), LookupRow(3.0, None, 19.0, 15.0)],
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
    return ""


def lookup_phi_e(*, qc_mean: float, soil_type: str) -> tuple[float, float, LookupRow, str]:
    group = _soil_group(soil_type)
    rows = TABLE_SP11.get(group)
    if not rows:
        raise ValueError("Для данного типа грунта расчёт по СП 11-105-97 (Приложение И) не выполняется")
    for row in rows:
        if qc_mean >= row.qc_from and (row.qc_to is None or qc_mean < row.qc_to):
            return row.phi_norm, row.e_norm, row, f"[{row.qc_from:g}; {'∞' if row.qc_to is None else f'{row.qc_to:g}'})"
    last = rows[-1]
    return last.phi_norm, last.e_norm, last, f"[{last.qc_from:g}; ∞)"


def calculate_ige_cpt_results(*, tests: list[Any], ige_registry: dict[str, dict[str, Any]], settings: CptCalcSettings) -> dict[str, dict[str, Any]]:
    if str(settings.method or METHOD_SP446) == METHOD_SP446:
        return calculate_ige_sp446(tests=tests, ige_registry=ige_registry, groundwater_level=settings.groundwater_level)

    # fallback СП 11 legacy
    from src.zondeditor.domain.cpt_ru_sp446 import depth_qc_pairs

    samples: dict[str, list[float]] = {}
    bounds: dict[str, list[tuple[float, float]]] = {}
    for test in tests or []:
        if not bool(getattr(test, "export_on", True)):
            continue
        pairs = depth_qc_pairs(test)
        for lyr in (getattr(test, "layers", []) or []):
            ige_id = str(getattr(lyr, "ige_id", "") or "").strip()
            if not ige_id:
                continue
            top = float(getattr(lyr, "top_m", 0.0) or 0.0)
            bot = float(getattr(lyr, "bot_m", 0.0) or 0.0)
            vals = [qc for dep, qc in pairs if top <= dep <= bot]
            if vals:
                samples.setdefault(ige_id, []).extend(vals)
                bounds.setdefault(ige_id, []).append((top, bot))

    out: dict[str, dict[str, Any]] = {}
    for ige_id, values in samples.items():
        stats: QcStats | None = qc_stats(values)
        if stats is None:
            continue
        ent = dict(ige_registry.get(ige_id) or {})
        soil_type = str(ent.get("soil_type") or "")
        policy = resolve_cpt_soil_policy(soil_code=ent.get("soil_code"), soil_name=soil_type)
        if not policy.is_calculable or policy.calc_branch not in {"sand", "clay"}:
            out[ige_id] = {
                "source": "CPT",
                "method": METHOD_SP11,
                "status": "no_norm",
                "status_text": "не рассчитано",
                "soil_type": soil_type,
                "qc_mean": round(stats.qc_mean, 3),
                "n": int(stats.n),
                "qc_min": round(stats.qc_min, 3),
                "qc_max": round(stats.qc_max, 3),
                "std": round(stats.std, 4),
                "variation": round(stats.variation, 4),
                "phi_norm": None,
                "E_norm": None,
                "lookup_table": "СП 11-105-97 Прил. И",
                "lookup_branch": "-",
                "lookup_interval": "-",
                "layer_bounds": bounds.get(ige_id, []),
                "reason": policy.warning or "Для данного типа грунта расчёт по данным зондирования в текущей реализации не выполняется.",
            }
            continue
        phi, e_val, _row, interval = lookup_phi_e(qc_mean=stats.qc_mean, soil_type=soil_type)
        out[ige_id] = {
            "source": "CPT",
            "method": METHOD_SP11,
            "status": "ok",
            "status_text": "OK",
            "soil_type": soil_type,
            "qc_mean": round(stats.qc_mean, 3),
            "n": int(stats.n),
            "qc_min": round(stats.qc_min, 3),
            "qc_max": round(stats.qc_max, 3),
            "std": round(stats.std, 4),
            "variation": round(stats.variation, 4),
            "phi_norm": float(phi),
            "E_norm": float(e_val),
            "lookup_table": "СП 11-105-97 Прил. И",
            "lookup_branch": _soil_group(str(ent.get("soil_type") or "")),
            "lookup_interval": interval,
            "layer_bounds": bounds.get(ige_id, []),
            "reason": "",
        }
    return out
