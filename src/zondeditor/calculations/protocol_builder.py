from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import IGECalcSample
from .normative_profiles import load_normative_profiles


def _soil_name_from_sample(sample: IGECalcSample) -> str:
    method = str(sample.method or "").upper()
    if "SAND" in method:
        return "песок"
    if "CLAY" in method:
        return "глинистый"
    return ""


def build_protocol(*, project_name: str, profile_id: str, samples: list[IGECalcSample]) -> dict[str, Any]:
    profiles = load_normative_profiles()
    prof = profiles.get(profile_id)

    not_applicable: list[dict[str, Any]] = []
    warnings: list[str] = []
    ige_results: list[dict[str, Any]] = []
    calc_trace: list[dict[str, Any]] = []
    export_ready_params: list[dict[str, Any]] = []

    for s in samples or []:
        soil_name = _soil_name_from_sample(s)
        if s.warnings:
            warnings.extend(s.warnings)

        if s.status in {"NOT_APPLICABLE", "LAB_ONLY", "NOT_IMPLEMENTED", "INVALID_INPUT"}:
            not_applicable.append(
                {
                    "ige_label": s.ige_id,
                    "soil_name": soil_name,
                    "status": s.status,
                    "reason": (s.warnings[0] if s.warnings else ""),
                    "missing_fields": list(s.missing_fields or []),
                    "errors": list(s.errors or []),
                    "required_fields": list(s.required_fields or []),
                }
            )

        row = {
            "ige_label": s.ige_id,
            "soil_name": soil_name,
            "normative_profile": profile_id,
            "method": s.method,
            "status": s.status,
            "used_soundings": list(s.used_sounding_ids or []),
            "depth_interval": s.depth_interval,
            "n_points": s.stats.n_points,
            "excluded_points": list(s.excluded_points or []),
            "excluded_reasons": list(s.exclusions or []),
            "sample_stats": {
                "qc_avg_mpa": s.stats.qc_avg_mpa,
                "qc_min_mpa": s.stats.qc_min_mpa,
                "qc_max_mpa": s.stats.qc_max_mpa,
                "fs_avg_kpa": s.stats.fs_avg_kpa,
                "v_qc": s.stats.v_qc,
                "avg_depth_m": s.stats.avg_depth_m,
            },
            "result_params": {
                "E_MPa": s.result.E_MPa,
                "phi_deg": s.result.phi_deg,
                "c_kPa": s.result.c_kPa,
            },
            "warnings": list(s.warnings or []),
            "errors": list(s.errors or []),
            "missing_fields": list(s.missing_fields or []),
            "required_fields": list(s.required_fields or []),
            "contributing_layers": list(s.contributing_layers or []),
            "preliminary_or_not_applicable": bool(s.status in {"PRELIMINARY", "NOT_APPLICABLE", "LAB_ONLY", "NOT_IMPLEMENTED", "INVALID_INPUT"}),
        }
        ige_results.append(row)
        calc_trace.append(row)

        export_ready_params.append(
            {
                "ige_id": s.ige_id,
                "status": s.status,
                "method": s.method,
                "E_MPa": s.result.E_MPa,
                "phi_deg": s.result.phi_deg,
                "c_kPa": s.result.c_kPa,
                "warnings": list(s.warnings or []),
                "errors": list(s.errors or []),
            }
        )

    return {
        "project_name": project_name,
        "profile_id": profile_id,
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat(),
        "sections": {
            "header": {
                "object_name": project_name,
                "profile_name": (prof.profile_name if prof else profile_id),
                "documents_used": [f"{d.get('title', '')} {d.get('amendments', '')}".strip() for d in (prof.documents if prof else [])],
            },
            "ige_results": ige_results,
            "not_applicable": not_applicable,
            "warnings": warnings,
            "calculation_trace": calc_trace,
            "export_ready_params": export_ready_params,
        },
    }
