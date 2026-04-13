from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cpt_soil_policy import resolve_cpt_soil_policy
from .soil_catalog import soil_code_by_name


@dataclass(frozen=True)
class IGEProfile:
    soil_code: str
    soil_name: str
    ui_profile: str
    calc_branch: str
    is_calculable: bool
    available_fields: tuple[str, ...]


def get_ige_profile(*, soil_name: str | None = None, soil_code: str | None = None, params: dict[str, Any] | None = None) -> IGEProfile:
    name = str(soil_name or "").strip().lower()
    code = str(soil_code or "").strip().lower() or soil_code_by_name(name)
    policy = resolve_cpt_soil_policy(soil_code=code, soil_name=name)

    if code == "sand":
        return IGEProfile(soil_code=code, soil_name=name, ui_profile="sand_calculable", calc_branch="sand", is_calculable=True, available_fields=("sand_kind", "sand_water_saturation", "density_state", "sand_is_alluvial"))
    if code == "sandy_loam":
        return IGEProfile(soil_code=code, soil_name=name, ui_profile="clay_supes_calculable", calc_branch="clay", is_calculable=True, available_fields=("consistency",))
    if code in {"loam", "clay"}:
        return IGEProfile(soil_code=code, soil_name=name, ui_profile="clay_calculable", calc_branch="clay", is_calculable=True, available_fields=("consistency",))
    if code == "fill":
        return IGEProfile(soil_code=code, soil_name=name, ui_profile="fill_calculable", calc_branch="fill", is_calculable=True, available_fields=("fill_subtype",))

    return IGEProfile(
        soil_code=code,
        soil_name=name,
        ui_profile="descriptive",
        calc_branch=policy.calc_branch,
        is_calculable=False,
        available_fields=(),
    )


def is_ige_calculable(*, soil_name: str | None = None, soil_code: str | None = None, params: dict[str, Any] | None = None) -> bool:
    return get_ige_profile(soil_name=soil_name, soil_code=soil_code, params=params).is_calculable


def build_ige_display_label(ige_id: str, *, label: str | None = None, soil_name: str | None = None, soil_code: str | None = None, params: dict[str, Any] | None = None) -> str:
    return str(label or "").strip() or str(ige_id or "").strip() or "ИГЭ-1"
