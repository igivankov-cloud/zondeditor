from __future__ import annotations

from dataclasses import dataclass

from .soil_catalog import soil_code_by_name


NON_CALCULABLE_CPT_MESSAGE = "Для данного типа грунта расчёт по данным зондирования в текущей реализации не выполняется."

_SAND_CODES = {"sand"}
_CLAY_CODES = {"sandy_loam", "loam", "clay"}
_FILL_CODES = {"fill"}
_CALCULABLE_CODES = _SAND_CODES | _CLAY_CODES | _FILL_CODES


@dataclass(frozen=True)
class CptSoilPolicy:
    soil_code: str
    soil_name: str
    calc_branch: str
    is_calculable: bool
    warning: str | None


def resolve_cpt_soil_policy(*, soil_code: str | None = None, soil_name: str | None = None) -> CptSoilPolicy:
    code = str(soil_code or "").strip().lower()
    name = str(soil_name or "").strip()
    if not code and name:
        code = soil_code_by_name(name)

    if code in _SAND_CODES:
        return CptSoilPolicy(soil_code=code, soil_name=name, calc_branch="sand", is_calculable=True, warning=None)
    if code in _CLAY_CODES:
        return CptSoilPolicy(soil_code=code, soil_name=name, calc_branch="clay", is_calculable=True, warning=None)
    if code in _FILL_CODES:
        return CptSoilPolicy(soil_code=code, soil_name=name, calc_branch="fill", is_calculable=True, warning=None)

    label = name or code or "Неизвестный тип грунта"
    return CptSoilPolicy(
        soil_code=code,
        soil_name=name,
        calc_branch="unsupported",
        is_calculable=False,
        warning=f"{label}: {NON_CALCULABLE_CPT_MESSAGE}",
    )


def soil_participates_in_cpt(*, soil_code: str | None = None, soil_name: str | None = None) -> bool:
    return resolve_cpt_soil_policy(soil_code=soil_code, soil_name=soil_name).is_calculable


def is_calculable_soil_code(soil_code: str | None) -> bool:
    return str(soil_code or "").strip().lower() in _CALCULABLE_CODES
