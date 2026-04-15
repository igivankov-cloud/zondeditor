from __future__ import annotations

from dataclasses import dataclass

from ._data_loader import load_data_file
from .cpt_soil_policy import resolve_cpt_soil_policy


@dataclass
class ApplicabilityRule:
    profile_id: str
    soil_code: str
    method: str
    status: str
    manual_confirmation_required: bool
    warning: str | None = None


def _load_rules() -> list[ApplicabilityRule]:
    raw = load_data_file("applicability_rules.json")
    out: list[ApplicabilityRule] = []
    for item in list(raw.get("rules") or []):
        out.append(
            ApplicabilityRule(
                profile_id=str(item.get("profile_id") or "DEFAULT_CURRENT"),
                soil_code=str(item.get("soil_code") or ""),
                method=str(item.get("method") or "LAB_ONLY"),
                status=str(item.get("status") or "NOT_APPLICABLE"),
                manual_confirmation_required=bool(item.get("manual_confirmation_required", False)),
                warning=(None if item.get("warning") in (None, "") else str(item.get("warning"))),
            )
        )
    return out


def resolve_applicability(*, profile_id: str, soil_code: str, subtype: str | None, allow_fill_by_material: bool) -> ApplicabilityRule:
    rules = _load_rules()
    pid = str(profile_id or "DEFAULT_CURRENT")
    scode = str(soil_code or "")
    policy = resolve_cpt_soil_policy(soil_code=scode)

    if not policy.is_calculable:
        return ApplicabilityRule(
            profile_id=pid,
            soil_code=scode,
            method="LAB_ONLY",
            status="NOT_APPLICABLE",
            manual_confirmation_required=False,
            warning=policy.warning,
        )

    base = next((r for r in rules if r.profile_id == pid and r.soil_code == scode), None)
    if base is None:
        base = next((r for r in rules if r.profile_id == "DEFAULT_CURRENT" and r.soil_code == scode), None)
    if base is None:
        return ApplicabilityRule(profile_id=pid, soil_code=scode, method="LAB_ONLY", status="NOT_APPLICABLE", manual_confirmation_required=False, warning="Правило применимости не найдено")

    if scode == "fill":
        sub = str(subtype or "").strip().lower()
        if "10%" in sub or "строит" in sub:
            return ApplicabilityRule(profile_id=pid, soil_code=scode, method="LAB_ONLY", status="NOT_APPLICABLE", manual_confirmation_required=False, warning="Насыпной грунт с содержанием строительного материала более 10% не допускается к расчету по auto-CPT")
        if sub in {"песчаный", "глинистый"} and allow_fill_by_material:
            return ApplicabilityRule(profile_id=pid, soil_code=scode, method=("SP446_CPT_SAND" if sub == "песчаный" else "SP446_CPT_CLAY"), status="PRELIMINARY", manual_confirmation_required=False, warning="Насыпной грунт допущен к предварительному расчету по материалу")
    return base
