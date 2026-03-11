from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import IGECalcSample
from .normative_profiles import load_normative_profiles
from .soil_catalog import load_soil_catalog


def build_protocol(*, project_name: str, profile_id: str, samples: list[IGECalcSample]) -> dict[str, Any]:
    profiles = load_normative_profiles()
    prof = profiles.get(profile_id)
    soil_catalog = load_soil_catalog()

    not_applicable = []
    warnings: list[str] = []
    ige_results = []
    calc_trace = []

    for s in samples or []:
        soil_name = ""
        for sc in soil_catalog.values():
            if sc.soil_code and sc.soil_code in str(s.method).lower():
                soil_name = sc.soil_name

        if s.warnings:
            warnings.extend(s.warnings)
        if s.status in {"NOT_APPLICABLE", "LAB_ONLY", "NOT_IMPLEMENTED"}:
            not_applicable.append(
                {
                    "ige_label": s.ige_id,
                    "soil_name": soil_name,
                    "status": s.status,
                    "reason": (s.warnings[0] if s.warnings else ""),
                    "missing_fields": list(s.missing_fields or []),
                    "errors": list(s.errors or []),
                }
            )

        ige_results.append(
            {
                "ige_label": s.ige_id,
                "soil_name": soil_name,
                "subtype": None,
                "method": s.method,
                "status": s.status,
                "n_points": s.stats.n_points,
                "qc_avg_mpa": s.stats.qc_avg_mpa,
                "v_qc": s.stats.v_qc,
                "avg_depth_m": s.stats.avg_depth_m,
                "E_MPa": s.result.E_MPa,
                "phi_deg": s.result.phi_deg,
                "c_kPa": s.result.c_kPa,
                "warning": (s.warnings[0] if s.warnings else None),
            }
        )

        calc_trace.append(
            {
                "ige_id": s.ige_id,
                "profile_id": profile_id,
                "method": s.method,
                "status": s.status,
                "used_soundings": list(s.used_sounding_ids or []),
                "depth_interval": s.depth_interval,
                "n_points": s.stats.n_points,
                "excluded_points": list(s.excluded_points or []),
                "excluded_reasons": list(s.exclusions or []),
                "warnings": list(s.warnings or []),
                "errors": list(s.errors or []),
                "missing_fields": list(s.missing_fields or []),
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
        },
    }
