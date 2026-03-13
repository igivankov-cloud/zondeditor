from __future__ import annotations

from typing import Any

from src.zondeditor.domain.cpt_ru_sp446 import parse_depth_float

from .applicability import resolve_applicability
from .calc_methods import load_method_catalog, run_method
from .models import IGECalcPoint, IGECalcResult, IGECalcSample, IGECalcStats, IGEModel
from .rf_utils import calc_rf_pct
from .soil_catalog import load_soil_catalog, soil_code_by_name
from .statistics import calc_stats
from .validation import validate_inputs


def _iter_points(test: Any):
    depth = list(getattr(test, "depth", []) or [])
    qc = list(getattr(test, "qc", []) or [])
    fs = list(getattr(test, "fs", []) or [])
    for i in range(min(len(depth), len(qc), len(fs))):
        d = parse_depth_float(str(depth[i]))
        if d is None:
            continue
        try:
            q = float(str(qc[i]).replace(",", "."))
            f = float(str(fs[i]).replace(",", "."))
        except Exception:
            continue
        if q <= 0:
            continue
        yield float(d), q, f


def _build_ige_model(ige_id: str, ent: dict[str, Any], profile_id: str) -> IGEModel:
    soil_name = str(ent.get("soil_type") or "")
    scode = str(ent.get("soil_code") or "") or soil_code_by_name(soil_name)
    cat = load_soil_catalog()
    soil_family = str(cat.get(scode).soil_family if scode in cat else "")
    return IGEModel(
        ige_id=str(ent.get("stable_ige_id") or ige_id),
        display_label=str(ent.get("display_label") or ent.get("label") or ige_id),
        soil_code=scode,
        soil_family=soil_family,
        subtype=str(ent.get("fill_subtype") or "") or None,
        is_alluvial=bool(ent.get("is_alluvial", ent.get("sand_is_alluvial", False))),
        notes=str(ent.get("manual_notes") or ent.get("notes") or ""),
        calc_profile_id=profile_id,
        input_fields={
            "IL": ent.get("IL"),
            "consistency": ent.get("consistency"),
            "e": ent.get("e"),
            "Sr": ent.get("Sr"),
        },
    )


def _missing_by_required_fields(required_fields: list[str], *, stats: IGECalcStats, ige: IGEModel) -> list[str]:
    missing: list[str] = []
    for rf in required_fields or []:
        if rf == "qc_mpa" and stats.qc_avg_mpa is None:
            missing.append(rf)
        elif rf == "avg_depth_m" and stats.avg_depth_m is None:
            missing.append(rf)
        elif rf == "n_points" and int(stats.n_points or 0) <= 0:
            missing.append(rf)
        elif rf == "consistency_or_IL":
            il = ige.input_fields.get("IL")
            cons = str(ige.input_fields.get("consistency") or "").strip()
            if il in (None, "") and not cons:
                missing.append(rf)
        elif rf in {"e", "Sr"} and ige.input_fields.get(rf) in (None, ""):
            missing.append(rf)
    return missing


def build_ige_samples(*, tests: list[Any], ige_registry: dict[str, dict[str, Any]], profile_id: str, allow_fill_by_material: bool, use_legacy_sandy_loam_sp446: bool = False, allow_normative_lt6: bool = False) -> list[IGECalcSample]:
    out: list[IGECalcSample] = []
    method_catalog = load_method_catalog()

    for ige_key in sorted((ige_registry or {}).keys()):
        ent = dict(ige_registry.get(ige_key) or {})
        ige = _build_ige_model(ige_key, ent, profile_id)
        app = resolve_applicability(profile_id=profile_id, soil_code=ige.soil_code, subtype=ige.subtype, allow_fill_by_material=allow_fill_by_material)

        if ige.soil_code == "sandy_loam":
            if not bool(use_legacy_sandy_loam_sp446):
                app.status = "NOT_APPLICABLE"
                app.warning = "Супесь по действующей редакции СП 446 (Изм. №1) не рассчитывается"
                app.method = "LAB_ONLY"
            else:
                app.status = "CALCULATED"
                app.method = "SP446_CPT_CLAY"
                app.warning = "Рассчитано по старой редакции СП 446"

        points: list[IGECalcPoint] = []
        excluded_points: list[dict[str, Any]] = []
        used_sounding_ids: list[str] = []
        layer_refs: list[dict[str, Any]] = []

        for test in tests or []:
            if not bool(getattr(test, "export_on", True)):
                continue
            tid = str(getattr(test, "tid", ""))
            for idx, lyr in enumerate((getattr(test, "layers", []) or []), start=1):
                lid = str(getattr(lyr, "ige_id", "") or "").strip()
                if lid != ige_key:
                    continue
                top = float(getattr(lyr, "top_m", 0.0) or 0.0)
                bot = float(getattr(lyr, "bot_m", 0.0) or 0.0)
                layer_refs.append({"sounding_id": f"test_{tid}", "layer_index": idx, "top_m": top, "bot_m": bot, "ige_id": lid})
                seg = f"seg_{tid}_{ige_key}_{top:.2f}_{bot:.2f}"
                for dep, qc_mpa, fs_kpa in _iter_points(test):
                    if not (top <= dep <= bot):
                        continue
                    if dep < 1.0:
                        excluded_points.append({"sounding_id": f"test_{tid}", "depth_m": dep, "reason": "Глубина менее 1 м", "segment_id": seg})
                        continue
                    sid = f"test_{tid}"
                    points.append(IGECalcPoint(sounding_id=sid, depth_m=dep, qc_mpa=qc_mpa, fs_kpa=fs_kpa, rf_pct=calc_rf_pct(fs_kpa, qc_mpa), segment_id=seg))
                    if sid not in used_sounding_ids:
                        used_sounding_ids.append(sid)

        stats: IGECalcStats = calc_stats(points)
        warnings = [w for w in [app.warning] if w]
        errors: list[str] = []

        method_item = method_catalog.get(app.method)
        required_fields = list(method_item.required_fields if method_item else [])

        validation = validate_inputs(ige=ige, stats=stats)
        missing_fields = sorted(set(validation.missing_fields + _missing_by_required_fields(required_fields, stats=stats, ige=ige)))

        if app.status in {"NOT_APPLICABLE", "LAB_ONLY"}:
            result = IGECalcResult(status="not_applicable", not_implemented=False)
        elif method_item is not None and not method_item.implemented:
            app.status = "NOT_IMPLEMENTED"
            result = IGECalcResult(status="not_implemented", not_implemented=True)
            warnings.append(f"Метод {app.method} помечен как not implemented")
        elif missing_fields:
            errors = ["Недостаточно исходных данных для расчёта"]
            result = IGECalcResult(status="invalid_input", not_implemented=False)
        else:
            method_run = run_method(
                app.method,
                stats,
                context={
                    "consistency_or_il_present": bool((ige.input_fields.get("IL") not in (None, "")) or str(ige.input_fields.get("consistency") or "").strip()),
                    "soil_code": ige.soil_code,
                    "subtype": ige.subtype,
                },
            )
            result = method_run.result
            warnings.extend(method_run.warnings)
            errors.extend(method_run.errors)
            if method_run.status == "not_implemented" and app.status in {"CALCULATED", "PRELIMINARY"}:
                app.status = "NOT_IMPLEMENTED"
            if method_run.status == "invalid_input":
                app.status = "INVALID_INPUT"

        sounding_count = len(used_sounding_ids)
        n_lt_6_triggered = sounding_count < 6 and app.status in {"CALCULATED", "PRELIMINARY"}
        n_lt_6_blocked = False
        n_lt_6_overridden = False
        if n_lt_6_triggered:
            if not bool(allow_normative_lt6):
                app.status = "N_LT_6_BLOCKED"
                n_lt_6_blocked = True
                errors.append("N < 6 (число опытов): нормативное значение не рассчитывается без разрешающей опции")
                result = IGECalcResult(status="invalid_input", not_implemented=False)
            else:
                n_lt_6_overridden = True
                warnings.append("N < 6 (число опытов): расчёт разрешён с предупреждением")

        depths = [p.depth_m for p in points]
        depth_interval = (min(depths), max(depths)) if depths else None
        exclusions = sorted({str(x.get("reason") or "") for x in excluded_points if str(x.get("reason") or "")})

        sample = IGECalcSample(
            ige_id=ige.ige_id,
            profile_id=profile_id,
            method=app.method,
            status=app.status,
            points=points,
            stats=stats,
            result=result,
            warnings=warnings,
            excluded_count=len(excluded_points),
            exclusions=exclusions,
            missing_fields=missing_fields,
            errors=errors,
            used_sounding_ids=used_sounding_ids,
            sounding_count=sounding_count,
            n_lt_6_triggered=n_lt_6_triggered,
            n_lt_6_blocked=n_lt_6_blocked,
            n_lt_6_overridden=n_lt_6_overridden,
            depth_interval=depth_interval,
            excluded_points=excluded_points,
            contributing_layers=layer_refs,
            required_fields=required_fields,
        )
        out.append(sample)

        ent.update(
            {
                "soil_code": ige.soil_code,
                "soil_family": ige.soil_family,
                "stable_ige_id": ige.ige_id,
                "display_label": ige.display_label,
                "calc_profile_id": profile_id,
                "calc_method": app.method,
                "calc_status": app.status,
                "manual_confirmation_required": bool(app.manual_confirmation_required),
                "calc_warning": "; ".join(warnings),
                "override_enabled": bool(app.status == "PRELIMINARY"),
            }
        )
        ige_registry[ige_key] = ent
    return out
