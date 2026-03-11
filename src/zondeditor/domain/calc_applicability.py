from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CalcStatus(str, Enum):
    CALCULATED = "CALCULATED"
    PRELIMINARY = "PRELIMINARY"
    LAB_ONLY = "LAB_ONLY"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class ApplicabilityResult:
    method: str
    status: CalcStatus
    warning: str = ""
    requires_manual_confirmation: bool = False
    use_for_auto_calc: bool = False


def evaluate_method_applicability(*, soil_type: str, fill_subtype: str | None, profile_method: str, allow_fill_by_material: bool = False) -> ApplicabilityResult:
    soil = str(soil_type or "").strip().lower()
    fill = str(fill_subtype or "").strip().lower()

    if "торф" in soil:
        return ApplicabilityResult(profile_method, CalcStatus.NOT_APPLICABLE, "Торф не входит в auto-CPT контур")
    if any(x in soil for x in ["гравий", "скаль", "коренн", "аргиллит", "песчаник"]):
        return ApplicabilityResult(profile_method, CalcStatus.NOT_APPLICABLE, "Тип грунта вне применимости первого auto-CPT контура")
    if "насып" in soil:
        if "10%" in fill or "строит" in fill:
            return ApplicabilityResult(profile_method, CalcStatus.NOT_APPLICABLE, "Насыпной с >10% строительного материала исключён из auto-CPT")
        if fill in {"песчаный", "глинистый"}:
            if allow_fill_by_material:
                return ApplicabilityResult(profile_method, CalcStatus.PRELIMINARY, "Результат по насыпному считается как предварительный (по материалу)", use_for_auto_calc=True)
            return ApplicabilityResult(profile_method, CalcStatus.LAB_ONLY, "Требуется ручное подтверждение расчёта по материалу", requires_manual_confirmation=True)
        return ApplicabilityResult(profile_method, CalcStatus.LAB_ONLY, "Для насыпного по умолчанию требуется лабораторное подтверждение")

    if any(x in soil for x in ["песок", "супесь", "суглин", "глин"]):
        return ApplicabilityResult(profile_method, CalcStatus.CALCULATED, use_for_auto_calc=True)

    return ApplicabilityResult(profile_method, CalcStatus.NOT_APPLICABLE, "Неизвестный тип грунта для auto-CPT")
