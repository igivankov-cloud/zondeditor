from __future__ import annotations

from dataclasses import dataclass

from ._data_loader import load_data_file
from .models import IGECalcResult, IGECalcStats


@dataclass
class MethodCatalogItem:
    method_id: str
    name: str
    family: str
    requires: list[str]
    outputs: list[str]
    supports_c_kPa: bool


def load_method_catalog() -> dict[str, MethodCatalogItem]:
    raw = load_data_file("method_catalog.json")
    out: dict[str, MethodCatalogItem] = {}
    for m in list(raw.get("methods") or []):
        item = MethodCatalogItem(
            method_id=str(m.get("method_id") or ""),
            name=str(m.get("name") or ""),
            family=str(m.get("family") or ""),
            requires=[str(x) for x in (m.get("requires") or [])],
            outputs=[str(x) for x in (m.get("outputs") or [])],
            supports_c_kPa=bool(m.get("supports_c_kPa", False)),
        )
        if item.method_id:
            out[item.method_id] = item
    return out


def run_method(method_id: str, stats: IGECalcStats) -> IGECalcResult:
    qc = float(stats.qc_avg_mpa or 0.0)
    v = float(stats.v_qc or 0.0)
    if method_id == "SP446_CPT_SAND":
        return IGECalcResult(E_MPa=round(max(5.0, qc * 3.0), 2), phi_deg=round(26.0 + min(12.0, qc), 2), c_kPa=None)
    if method_id == "SP446_CPT_CLAY":
        return IGECalcResult(E_MPa=round(max(4.0, qc * 2.4), 2), phi_deg=round(18.0 + min(14.0, qc * 0.8), 2), c_kPa=round(max(0.0, 18.0 - (v * 30.0)), 2))
    return IGECalcResult()
