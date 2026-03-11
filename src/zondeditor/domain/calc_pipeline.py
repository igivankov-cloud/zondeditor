from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any

from src.zondeditor.domain.calc_applicability import ApplicabilityResult, CalcStatus, evaluate_method_applicability
from src.zondeditor.domain.cpt_ru_sp446 import parse_depth_float


@dataclass
class IgeCalcSample:
    qc_values: list[float]
    fs_values: list[float]
    depths: list[float]
    sounding_ids: list[int]
    intervals: list[tuple[int, float, float]]
    excluded_points_info: list[dict[str, Any]]

    @property
    def n_points(self) -> int:
        return len(self.qc_values)


def _depth_pairs(test: Any) -> list[tuple[float, float, float]]:
    out: list[tuple[float, float, float]] = []
    depths = list(getattr(test, "depth", []) or [])
    qcs = list(getattr(test, "qc", []) or [])
    fss = list(getattr(test, "fs", []) or [])
    for i in range(min(len(depths), len(qcs), len(fss))):
        d = parse_depth_float(str(depths[i]))
        if d is None:
            continue
        try:
            qc = float(str(qcs[i]).replace(",", "."))
            fs = float(str(fss[i]).replace(",", "."))
        except Exception:
            continue
        if qc <= 0:
            continue
        out.append((float(d), qc, fs))
    return out


def collect_ige_samples(tests: list[Any]) -> dict[str, IgeCalcSample]:
    samples: dict[str, IgeCalcSample] = {}
    for test in tests or []:
        if not bool(getattr(test, "export_on", True)):
            continue
        tid = int(getattr(test, "tid", 0) or 0)
        pairs = _depth_pairs(test)
        for lyr in (getattr(test, "layers", []) or []):
            ige_id = str(getattr(lyr, "ige_id", "") or "").strip()
            if not ige_id:
                continue
            top = float(getattr(lyr, "top_m", 0.0) or 0.0)
            bot = float(getattr(lyr, "bot_m", 0.0) or 0.0)
            smp = samples.setdefault(ige_id, IgeCalcSample([], [], [], [], [], []))
            smp.intervals.append((tid, top, bot))
            if tid not in smp.sounding_ids:
                smp.sounding_ids.append(tid)
            for dep, qc, fs in pairs:
                if top <= dep <= bot:
                    smp.depths.append(dep)
                    smp.qc_values.append(qc)
                    smp.fs_values.append(fs)
                else:
                    smp.excluded_points_info.append({"sounding_id": tid, "depth": dep, "reason": "outside_interval", "ige_id": ige_id})
    return samples


def sample_stats(sample: IgeCalcSample) -> dict[str, Any]:
    vals = [float(v) for v in sample.qc_values if float(v) > 0]
    if not vals:
        return {"n_points": 0, "qc_avg": None, "qc_min": None, "qc_max": None, "V_qc": None, "avg_depth": None, "fs_avg": None}
    qc_avg = float(mean(vals))
    std = float(pstdev(vals)) if len(vals) > 1 else 0.0
    fs_avg = float(mean(sample.fs_values)) if sample.fs_values else None
    avg_depth = float(mean(sample.depths)) if sample.depths else None
    return {
        "n_points": len(vals),
        "qc_avg": qc_avg,
        "qc_min": min(vals),
        "qc_max": max(vals),
        "V_qc": (std / qc_avg if qc_avg > 0 else 0.0),
        "avg_depth": avg_depth,
        "fs_avg": fs_avg,
    }


def build_calc_rows(*, tests: list[Any], ige_registry: dict[str, dict[str, Any]], method: str, allow_fill_by_material: bool = False) -> tuple[list[dict[str, Any]], dict[str, IgeCalcSample]]:
    samples = collect_ige_samples(tests)
    rows: list[dict[str, Any]] = []
    for ige_id in sorted((ige_registry or {}).keys()):
        ent = dict(ige_registry.get(ige_id) or {})
        soil_type = str(ent.get("soil_type") or "")
        fill_subtype = str(ent.get("fill_subtype") or "")
        smp = samples.get(ige_id, IgeCalcSample([], [], [], [], [], []))
        stats = sample_stats(smp)
        app: ApplicabilityResult = evaluate_method_applicability(
            soil_type=soil_type,
            fill_subtype=fill_subtype,
            profile_method=method,
            allow_fill_by_material=allow_fill_by_material,
        )
        ent["calc_method"] = app.method
        ent["calc_status"] = str(app.status.value)
        ent["calc_warning"] = app.warning
        ent["use_for_auto_calc"] = bool(app.use_for_auto_calc)
        ent["requires_manual_confirmation"] = bool(app.requires_manual_confirmation)
        result_stub = {"E": None, "phi": None, "c": None}
        if app.status in {CalcStatus.CALCULATED, CalcStatus.PRELIMINARY} and stats["n_points"] > 0:
            result_stub = {"E": round(max(5.0, (stats["qc_avg"] or 0.0) * 2.8), 2), "phi": round(18.0 + min(20.0, (stats["qc_avg"] or 0.0) * 1.2), 2), "c": round(max(0.0, 5.0 - (stats["V_qc"] or 0.0) * 10), 2)}
        rows.append(
            {
                "ige_id": ige_id,
                "soil_type": soil_type,
                "fill_subtype": fill_subtype,
                "method": app.method,
                "status": str(app.status.value),
                "warning": app.warning,
                "intervals": list(smp.intervals),
                **stats,
                **result_stub,
            }
        )
        ige_registry[ige_id] = ent
    return rows, samples
