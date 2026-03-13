from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._data_loader import load_data_file
from .models import IGECalcResult, IGECalcStats


@dataclass
class MethodCatalogItem:
    method_id: str
    name: str
    family: str
    applicable_soils: list[str]
    required_fields: list[str]
    optional_fields: list[str]
    blocking_conditions: list[str]
    warning_conditions: list[str]
    output_params: list[str]
    supports_c_kPa: bool
    implemented: bool
    implementation_note: str = ""


@dataclass
class MethodRunResult:
    result: IGECalcResult
    status: str  # ok|not_implemented|invalid_input
    warnings: list[str]
    errors: list[str]


def load_method_catalog() -> dict[str, MethodCatalogItem]:
    raw = load_data_file("method_catalog.json")
    out: dict[str, MethodCatalogItem] = {}
    for m in list(raw.get("methods") or []):
        item = MethodCatalogItem(
            method_id=str(m.get("method_id") or ""),
            name=str(m.get("name") or ""),
            family=str(m.get("family") or ""),
            applicable_soils=[str(x) for x in (m.get("applicable_soils") or [])],
            required_fields=[str(x) for x in (m.get("required_fields") or [])],
            optional_fields=[str(x) for x in (m.get("optional_fields") or [])],
            blocking_conditions=[str(x) for x in (m.get("blocking_conditions") or [])],
            warning_conditions=[str(x) for x in (m.get("warning_conditions") or [])],
            output_params=[str(x) for x in (m.get("output_params") or [])],
            supports_c_kPa=bool(m.get("supports_c_kPa", False)),
            implemented=bool(m.get("implemented", False)),
            implementation_note=str(m.get("implementation_note") or ""),
        )
        if item.method_id:
            out[item.method_id] = item
    return out


def _not_implemented(method_id: str, note: str = "") -> MethodRunResult:
    ws = [f"Метод {method_id} пока не реализован"]
    if note:
        ws.append(note)
    return MethodRunResult(result=IGECalcResult(status="not_implemented", not_implemented=True), status="not_implemented", warnings=ws, errors=[])


def run_method(method_id: str, stats: IGECalcStats, *, context: dict[str, Any] | None = None) -> MethodRunResult:
    context = dict(context or {})
    catalog = load_method_catalog()
    item = catalog.get(method_id)
    if item is None:
        return _not_implemented(method_id, "Метод отсутствует в каталоге")
    if not item.implemented:
        return _not_implemented(method_id, item.implementation_note)

    qc = float(stats.qc_avg_mpa or 0.0)
    v = float(stats.v_qc or 0.0)
    n = int(stats.n_points or 0)
    warnings: list[str] = []
    errors: list[str] = []

    if n <= 0 or qc <= 0:
        return MethodRunResult(result=IGECalcResult(status="invalid_input", not_implemented=False), status="invalid_input", warnings=warnings, errors=["Недостаточно статистических данных (n/qc)"])

    if method_id == "SP446_CPT_SAND":
        # Conservative engineering policy: simplified branch pending full normative audit
        warnings.append("Используется инженерная упрощенная ветка SP446_CPT_SAND; требуется сверка с нормативной таблицей")
        if qc < 1.0:
            warnings.append("qc ниже рекомендуемого диапазона СП446 для песчаной ветки; использован консервативный минимум")
        if qc > 12.0:
            warnings.append("qc выше рекомендуемого диапазона СП446 для песчаной ветки; использован консервативный потолок")
        if v > 0.35:
            warnings.append("Повышенная вариативность V_qc для песков")
        qc_eff = min(12.0, max(1.0, qc))
        e_val = round(max(5.0, qc_eff * 3.0), 2)
        phi = round(26.0 + min(12.0, qc_eff), 2)
        return MethodRunResult(result=IGECalcResult(E_MPa=e_val, phi_deg=phi, c_kPa=None, status="ok", not_implemented=False), status="ok", warnings=warnings, errors=errors)

    if method_id == "SP446_CPT_CLAY":
        warnings.append("Используется инженерная упрощенная ветка SP446_CPT_CLAY; требуется сверка с нормативной таблицей")
        if context.get("consistency_or_il_present") is False:
            return MethodRunResult(result=IGECalcResult(status="invalid_input", not_implemented=False), status="invalid_input", warnings=warnings, errors=["Для глинистых требуется IL или консистенция"])
        if qc < 0.8:
            warnings.append("qc ниже рекомендуемого диапазона СП446 для глинистой ветки; использован консервативный минимум")
        if qc > 10.0:
            warnings.append("qc выше рекомендуемого диапазона СП446 для глинистой ветки; использован консервативный потолок")
        if v > 0.40:
            warnings.append("Повышенная вариативность V_qc для глинистых")
        qc_eff = min(10.0, max(0.8, qc))
        e_val = round(max(4.0, qc_eff * 2.4), 2)
        phi = round(18.0 + min(14.0, qc_eff * 0.8), 2)
        c_val = round(max(0.0, 18.0 - (v * 30.0)), 2)
        return MethodRunResult(result=IGECalcResult(E_MPa=e_val, phi_deg=phi, c_kPa=c_val, status="ok", not_implemented=False), status="ok", warnings=warnings, errors=errors)

    return _not_implemented(method_id, "Нет формализованной инженерной формулы")
