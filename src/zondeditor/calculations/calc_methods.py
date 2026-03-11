from __future__ import annotations

from dataclasses import dataclass

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
    status: str  # ok|not_implemented
    warnings: list[str]


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


def run_method(method_id: str, stats: IGECalcStats) -> MethodRunResult:
    catalog = load_method_catalog()
    item = catalog.get(method_id)
    if item is None:
        return MethodRunResult(result=IGECalcResult(status="not_implemented", not_implemented=True), status="not_implemented", warnings=[f"Метод {method_id} не найден в каталоге"])
    if not item.implemented:
        return MethodRunResult(
            result=IGECalcResult(status="not_implemented", not_implemented=True),
            status="not_implemented",
            warnings=[f"Метод {method_id} пока не реализован", item.implementation_note] if item.implementation_note else [f"Метод {method_id} пока не реализован"],
        )

    qc = float(stats.qc_avg_mpa or 0.0)
    v = float(stats.v_qc or 0.0)
    warnings: list[str] = []

    if method_id == "SP446_CPT_SAND":
        if v > 0.35:
            warnings.append("Повышенная вариативность V_qc для песков")
        return MethodRunResult(
            result=IGECalcResult(E_MPa=round(max(5.0, qc * 3.0), 2), phi_deg=round(26.0 + min(12.0, qc), 2), c_kPa=None, status="ok", not_implemented=False),
            status="ok",
            warnings=warnings,
        )

    if method_id == "SP446_CPT_CLAY":
        if v > 0.40:
            warnings.append("Повышенная вариативность V_qc для глинистых")
        return MethodRunResult(
            result=IGECalcResult(E_MPa=round(max(4.0, qc * 2.4), 2), phi_deg=round(18.0 + min(14.0, qc * 0.8), 2), c_kPa=round(max(0.0, 18.0 - (v * 30.0)), 2), status="ok", not_implemented=False),
            status="ok",
            warnings=warnings,
        )

    return MethodRunResult(result=IGECalcResult(status="not_implemented", not_implemented=True), status="not_implemented", warnings=[f"Метод {method_id} пока не реализован в вычислителе"]) 
