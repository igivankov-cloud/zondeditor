from __future__ import annotations

from dataclasses import dataclass

from .models import IGECalcStats, IGEModel


@dataclass
class ValidationResult:
    ok: bool
    missing_fields: list[str]
    errors: list[str]


def validate_inputs(*, ige: IGEModel, stats: IGECalcStats) -> ValidationResult:
    missing: list[str] = []
    errors: list[str] = []

    if stats.n_points <= 0:
        missing.append("n_points")
    if stats.qc_avg_mpa is None:
        missing.append("qc_avg_mpa")
    if stats.avg_depth_m is None:
        missing.append("avg_depth_m")

    if ige.soil_family == "sand_like":
        # enough with statistical CPT core
        pass
    elif ige.soil_family == "clay_like":
        il = ige.input_fields.get("IL")
        cons = str(ige.input_fields.get("consistency") or "").strip()
        if il in (None, "") and not cons:
            missing.append("consistency_or_IL")
    elif ige.soil_code == "fill":
        if not str(ige.subtype or "").strip():
            missing.append("fill_subtype")
    return ValidationResult(ok=(len(missing) == 0 and len(errors) == 0), missing_fields=sorted(set(missing)), errors=errors)
