from __future__ import annotations

from dataclasses import dataclass

from ._data_loader import load_data_file


@dataclass
class SoilCatalogItem:
    soil_code: str
    soil_name: str
    soil_family: str
    ui_group: str
    supports_alluvial_flag: bool
    subtypes: list[str]


def load_soil_catalog() -> dict[str, SoilCatalogItem]:
    raw = load_data_file("soil_catalog.json")
    out: dict[str, SoilCatalogItem] = {}
    for item in list(raw.get("soil_types") or []):
        s = SoilCatalogItem(
            soil_code=str(item.get("soil_code") or ""),
            soil_name=str(item.get("soil_name") or ""),
            soil_family=str(item.get("soil_family") or ""),
            ui_group=str(item.get("ui_group") or "other"),
            supports_alluvial_flag=bool(item.get("supports_alluvial_flag", False)),
            subtypes=[str(x) for x in (item.get("subtypes") or [])],
        )
        if s.soil_code:
            out[s.soil_code] = s
    return out


def soil_code_by_name(soil_name: str) -> str:
    name = str(soil_name or "").strip().lower()
    by_name = {v.soil_name.lower(): v.soil_code for v in load_soil_catalog().values()}
    return by_name.get(name, "")
