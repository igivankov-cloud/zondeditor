from __future__ import annotations

from typing import Any

from src.zondeditor.domain.cpt_ru_sp446 import parse_depth_float

from .applicability import resolve_applicability
from .calc_methods import run_method
from .models import IGECalcPoint, IGECalcResult, IGECalcSample, IGECalcStats, IGEModel
from .soil_catalog import load_soil_catalog, soil_code_by_name
from .statistics import calc_stats


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
    )


def build_ige_samples(*, tests: list[Any], ige_registry: dict[str, dict[str, Any]], profile_id: str, allow_fill_by_material: bool) -> list[IGECalcSample]:
    out: list[IGECalcSample] = []
    for ige_key in sorted((ige_registry or {}).keys()):
        ent = dict(ige_registry.get(ige_key) or {})
        ige = _build_ige_model(ige_key, ent, profile_id)
        app = resolve_applicability(profile_id=profile_id, soil_code=ige.soil_code, subtype=ige.subtype, allow_fill_by_material=allow_fill_by_material)
        points: list[IGECalcPoint] = []
        excluded_count = 0
        exclusions: list[str] = []
        for test in tests or []:
            if not bool(getattr(test, "export_on", True)):
                continue
            tid = str(getattr(test, "tid", ""))
            for lyr in (getattr(test, "layers", []) or []):
                lid = str(getattr(lyr, "ige_id", "") or "").strip()
                if lid != ige_key:
                    continue
                top = float(getattr(lyr, "top_m", 0.0) or 0.0)
                bot = float(getattr(lyr, "bot_m", 0.0) or 0.0)
                seg = f"seg_{tid}_{ige_key}_{top:.2f}_{bot:.2f}"
                for dep, qc_mpa, fs_kpa in _iter_points(test):
                    if top <= dep <= bot:
                        if dep < 1.0:
                            excluded_count += 1
                            if "Глубина менее 1 м" not in exclusions:
                                exclusions.append("Глубина менее 1 м")
                            continue
                        points.append(IGECalcPoint(sounding_id=f"test_{tid}", depth_m=dep, qc_mpa=qc_mpa, fs_kpa=fs_kpa, segment_id=seg))
        stats: IGECalcStats = calc_stats(points)
        result: IGECalcResult = run_method(app.method, stats) if app.status in {"CALCULATED", "PRELIMINARY"} else IGECalcResult()
        warnings = [w for w in [app.warning] if w]
        out.append(IGECalcSample(ige_id=ige.ige_id, profile_id=profile_id, method=app.method, status=app.status, points=points, stats=stats, result=result, warnings=warnings, excluded_count=excluded_count, exclusions=exclusions))

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
                "calc_warning": app.warning or "",
                "override_enabled": bool(app.status == "PRELIMINARY"),
            }
        )
        ige_registry[ige_key] = ent
    return out
