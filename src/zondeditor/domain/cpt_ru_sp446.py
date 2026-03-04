from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any


@dataclass
class QcStats:
    n: int
    qc_mean: float
    qc_min: float
    qc_max: float
    std: float
    variation: float


@dataclass
class IntervalValue:
    qc_from: float
    qc_to: float | None
    value: float


# СП 446.1325800.2019, Приложение Ж, табл. Ж.2 — E для песков
TABLE_J2_E_SAND: dict[str, dict[str, float]] = {
    "крупный": {"обычные": 42.0, "аллювиальные/флювиогляциальные": 38.0},
    "средней крупности": {"обычные": 36.0, "аллювиальные/флювиогляциальные": 32.0},
    "мелкий": {"обычные": 30.0, "аллювиальные/флювиогляциальные": 26.0},
    "пылеватый": {"обычные": 24.0, "аллювиальные/флювиогляциальные": 20.0},
}

# СП 446.1325800.2019, Приложение Ж, табл. Ж.3 — φ для песков (по qc, глубина 2 м и 5+ м)
TABLE_J3_PHI_SAND: dict[str, dict[str, list[IntervalValue]]] = {
    "крупный": {
        "2м": [IntervalValue(0.0, 4.0, 32.0), IntervalValue(4.0, 8.0, 34.0), IntervalValue(8.0, None, 36.0)],
        "5м+": [IntervalValue(0.0, 4.0, 33.0), IntervalValue(4.0, 8.0, 35.0), IntervalValue(8.0, None, 37.0)],
    },
    "средней крупности": {
        "2м": [IntervalValue(0.0, 3.0, 30.0), IntervalValue(3.0, 7.0, 32.0), IntervalValue(7.0, None, 34.0)],
        "5м+": [IntervalValue(0.0, 3.0, 31.0), IntervalValue(3.0, 7.0, 33.0), IntervalValue(7.0, None, 35.0)],
    },
    "мелкий": {
        "2м": [IntervalValue(0.0, 2.0, 28.0), IntervalValue(2.0, 6.0, 30.0), IntervalValue(6.0, None, 32.0)],
        "5м+": [IntervalValue(0.0, 2.0, 29.0), IntervalValue(2.0, 6.0, 31.0), IntervalValue(6.0, None, 33.0)],
    },
    "пылеватый": {
        "2м": [IntervalValue(0.0, 1.5, 26.0), IntervalValue(1.5, 5.0, 28.0), IntervalValue(5.0, None, 30.0)],
        "5м+": [IntervalValue(0.0, 1.5, 27.0), IntervalValue(1.5, 5.0, 29.0), IntervalValue(5.0, None, 31.0)],
    },
    "пылеватый_водонасыщенный": {
        "2м": [IntervalValue(0.0, 1.5, 24.0), IntervalValue(1.5, 5.0, 26.0), IntervalValue(5.0, None, 28.0)],
        "5м+": [IntervalValue(0.0, 1.5, 25.0), IntervalValue(1.5, 5.0, 27.0), IntervalValue(5.0, None, 29.0)],
    },
}

# СП 446.1325800.2019, Приложение Ж — глинистые (ветки по IL/консистенции)
TABLE_J_CLAY: dict[str, dict[str, list[IntervalValue]]] = {
    "глина": {
        "твердая": [IntervalValue(0.0, 1.0, 18.0), IntervalValue(1.0, 2.0, 20.0), IntervalValue(2.0, None, 22.0)],
        "полутвердая": [IntervalValue(0.0, 1.0, 16.0), IntervalValue(1.0, 2.0, 18.0), IntervalValue(2.0, None, 20.0)],
        "тугопластичная": [IntervalValue(0.0, 1.0, 14.0), IntervalValue(1.0, 2.0, 16.0), IntervalValue(2.0, None, 18.0)],
    },
    "суглинок": {
        "твердый": [IntervalValue(0.0, 1.2, 20.0), IntervalValue(1.2, 2.5, 22.0), IntervalValue(2.5, None, 24.0)],
        "полутвердый": [IntervalValue(0.0, 1.2, 18.0), IntervalValue(1.2, 2.5, 20.0), IntervalValue(2.5, None, 22.0)],
        "тугопластичный": [IntervalValue(0.0, 1.2, 16.0), IntervalValue(1.2, 2.5, 18.0), IntervalValue(2.5, None, 20.0)],
    },
}
TABLE_J_CLAY_E: dict[str, dict[str, float]] = {
    "глина": {"твердая": 22.0, "полутвердая": 18.0, "тугопластичная": 14.0},
    "суглинок": {"твердый": 24.0, "полутвердый": 20.0, "тугопластичный": 16.0},
    "супесь": {"твердая": 24.0, "пластичная": 18.0, "текучая": 12.0},
}

TABLE_J_CLAY["супесь"] = {
    "твердая": [IntervalValue(0.0, 1.5, 22.0), IntervalValue(1.5, 3.0, 24.0), IntervalValue(3.0, None, 26.0)],
    "пластичная": [IntervalValue(0.0, 1.5, 18.0), IntervalValue(1.5, 3.0, 20.0), IntervalValue(3.0, None, 22.0)],
    "текучая": [IntervalValue(0.0, 1.5, 14.0), IntervalValue(1.5, 3.0, 16.0), IntervalValue(3.0, None, 18.0)],
}


def parse_depth_float(raw: str) -> float | None:
    s = str(raw or "").strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def qc_stats(values: list[float]) -> QcStats | None:
    vals = [float(v) for v in values if float(v) > 0]
    if not vals:
        return None
    avg = float(mean(vals))
    sd = float(pstdev(vals)) if len(vals) > 1 else 0.0
    return QcStats(n=len(vals), qc_mean=avg, qc_min=min(vals), qc_max=max(vals), std=sd, variation=(sd / avg if avg > 0 else 0.0))


def depth_qc_pairs(test: Any) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    depths = list(getattr(test, "depth", []) or [])
    qcs = list(getattr(test, "qc", []) or [])
    for i in range(min(len(depths), len(qcs))):
        d = parse_depth_float(str(depths[i]))
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


def _interval_lookup(rows: list[IntervalValue], qc_mean: float) -> tuple[float, str]:
    for row in rows:
        if qc_mean >= row.qc_from and (row.qc_to is None or qc_mean < row.qc_to):
            return row.value, f"[{row.qc_from:g}; {'∞' if row.qc_to is None else f'{row.qc_to:g}'})"
    last = rows[-1]
    return last.value, f"[{last.qc_from:g}; ∞)"


def _normalize_sand_class(raw: str) -> str:
    v = str(raw or "").strip().lower()
    aliases = {
        "крупный": "крупный",
        "крупные": "крупный",
        "средней крупности": "средней крупности",
        "средний": "средней крупности",
        "мелкий": "мелкий",
        "пылеватый": "пылеватый",
    }
    return aliases.get(v, "")


def _soil_group(raw: str) -> str:
    s = str(raw or "").strip().lower()
    if "супес" in s:
        return "супесь"
    if "суглин" in s:
        return "суглинок"
    if "глин" in s:
        return "глина"
    if "пес" in s:
        return "песок"
    return ""


def _consistency_by_il(il: float | None, soil_group: str) -> str:
    if il is None:
        return ""
    if soil_group == "супесь":
        if il < 0:
            return "твердая"
        if il <= 1.0:
            return "пластичная"
        return "текучая"
    if il < 0:
        return "твердая" if soil_group == "глина" else "твердый"
    if il <= 0.25:
        return "полутвердая" if soil_group == "глина" else "полутвердый"
    return "тугопластичная" if soil_group == "глина" else "тугопластичный"


def infer_saturated(*, mid_depth: float | None, groundwater_level: float | None) -> bool | None:
    if groundwater_level is None or mid_depth is None:
        return None
    return bool(mid_depth >= groundwater_level)


def calculate_ige_sp446(*, tests: list[Any], ige_registry: dict[str, dict[str, Any]], groundwater_level: float | None) -> dict[str, dict[str, Any]]:
    samples: dict[str, list[float]] = {}
    bounds: dict[str, list[tuple[float, float]]] = {}
    for test in tests or []:
        if not bool(getattr(test, "export_on", True)):
            continue
        pairs = depth_qc_pairs(test)
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
        layer_bounds = bounds.get(ige_id, [])
        mid_depth = None
        if layer_bounds:
            mids = [0.5 * (a + b) for a, b in layer_bounds]
            mid_depth = float(mean(mids))

        soil_type = str(ent.get("soil_type") or "")
        soil_group = _soil_group(soil_type)
        saturated_auto = infer_saturated(mid_depth=mid_depth, groundwater_level=groundwater_level)
        saturated = bool(ent.get("saturated", False))

        result: dict[str, Any] = {
            "source": "CPT",
            "method": "SP446_APP_J",
            "soil_type": soil_type,
            "status": "ok",
            "status_text": "OK",
            "qc_mean": round(stats.qc_mean, 3),
            "n": int(stats.n),
            "qc_min": round(stats.qc_min, 3),
            "qc_max": round(stats.qc_max, 3),
            "std": round(stats.std, 4),
            "variation": round(stats.variation, 4),
            "layer_bounds": layer_bounds,
            "mid_depth": (None if mid_depth is None else round(mid_depth, 3)),
            "groundwater_level": groundwater_level,
            "saturated_auto": saturated_auto,
            "saturated": saturated,
            "sand_class": ent.get("sand_class"),
            "alluvial": bool(ent.get("alluvial", True)),
            "il": ent.get("IL"),
            "consistency": ent.get("consistency"),
            "consistency_source": "manual",
            "source_flags": dict(ent.get("source_flags") or {"CPT": True, "LAB": False, "Stamp": False}),
            "note": str(ent.get("note") or ""),
            "phi_norm": None,
            "E_norm": None,
            "lookup_table": "-",
            "lookup_branch": "-",
            "lookup_interval": "-",
            "reason": "",
        }

        if soil_group == "песок":
            sand_class = _normalize_sand_class(str(ent.get("sand_class") or ""))
            if sand_class not in TABLE_J2_E_SAND:
                result["status"] = "no_norm"
                result["status_text"] = "не рассчитано"
                result["reason"] = "Не задан класс песка (sand_class) для расчёта по табл. Ж.2/Ж.3"
                out[ige_id] = result
                continue
            depth_col = "5м+" if (mid_depth is not None and mid_depth >= 5.0) else "2м"
            sand_phi_key = sand_class
            branch_parts = [f"песок {sand_class}", f"глубина: {depth_col}"]
            if sand_class == "пылеватый" and saturated is True:
                sand_phi_key = "пылеватый_водонасыщенный"
                branch_parts.append("ветка Ж.1: водонасыщенный")
            phi, phi_interval = _interval_lookup(TABLE_J3_PHI_SAND[sand_phi_key][depth_col], stats.qc_mean)
            e_branch = "аллювиальные/флювиогляциальные"
            e_val = TABLE_J2_E_SAND[sand_class][e_branch]
            result.update(
                {
                    "phi_norm": float(phi),
                    "E_norm": float(e_val),
                    "lookup_table": "Ж.3 (φ), Ж.2 (E), Ж.1 (ветка водонасыщения)",
                    "lookup_branch": ", ".join(branch_parts + [f"E: {e_branch}"]),
                    "lookup_interval": phi_interval,
                }
            )
            out[ige_id] = result
            continue

        if soil_group in {"глина", "суглинок", "супесь"}:
            il_raw = ent.get("IL")
            il_val = None
            try:
                if il_raw not in (None, ""):
                    il_val = float(str(il_raw).replace(",", "."))
            except Exception:
                il_val = None
            consistency = str(ent.get("consistency") or "").strip().lower()
            consistency_source = "manual"
            if il_val is not None:
                consistency = _consistency_by_il(il_val, soil_group)
                consistency_source = "auto_by_il"
            if consistency not in TABLE_J_CLAY.get(soil_group, {}):
                result["status"] = "no_norm"
                result["status_text"] = "не рассчитано"
                result["reason"] = "Не заданы IL/консистенция для выбора ветки таблицы Прил. Ж"
                out[ige_id] = result
                continue
            phi, phi_interval = _interval_lookup(TABLE_J_CLAY[soil_group][consistency], stats.qc_mean)
            e_val = TABLE_J_CLAY_E[soil_group][consistency]
            result.update(
                {
                    "phi_norm": float(phi),
                    "E_norm": float(e_val),
                    "lookup_table": "Прил. Ж (глинистые грунты)",
                    "lookup_branch": f"{soil_group}, консистенция: {consistency}",
                    "lookup_interval": phi_interval,
                    "consistency": consistency,
                    "consistency_source": consistency_source,
                }
            )
            out[ige_id] = result
            continue

        result["status"] = "no_norm"
        result["status_text"] = "не рассчитано"
        result["reason"] = "Автоназначение по СП 446 Прил. Ж для данного типа не выполняется, требуется другой источник"
        out[ige_id] = result

    return out
