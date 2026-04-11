from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .loader import load_hatch_pattern
from .models import HatchPattern, PatPattern
from .pat_loader import load_pat_pattern

ASSET_DIR = Path(__file__).resolve().parents[2] / "assets" / "hatches"


@dataclass(frozen=True)
class HatchAssetSpec:
    stem: str

    @property
    def json_file(self) -> str:
        return f"{self.stem}.json"

    @property
    def pat_file(self) -> str:
        return f"{self.stem}.pat"

    @property
    def json_path(self) -> Path:
        return ASSET_DIR / self.json_file

    @property
    def pat_path(self) -> Path:
        return ASSET_DIR / self.pat_file


HATCH_ASSETS: dict[str, HatchAssetSpec] = {
    "peschanik": HatchAssetSpec("Peschanik"),
    "argillit": HatchAssetSpec("Argillit"),
    "glina": HatchAssetSpec("Glina"),
    "graviy": HatchAssetSpec("graviy"),
    "nasipnoy": HatchAssetSpec("Nasipnoy"),
    "pesok": HatchAssetSpec("Pesok"),
    "pesok_graviy": HatchAssetSpec("PesokGraviy"),
    "suglinok": HatchAssetSpec("Suglinok"),
    "supes": HatchAssetSpec("Supes"),
    "torf": HatchAssetSpec("Torf"),
}

SOIL_TYPE_TO_HATCH_ASSET: dict[str, str] = {
    "песчаник": "peschanik",
    "аргиллит": "argillit",
    "аргилит": "argillit",
    "глина": "glina",
    "гравий": "graviy",
    "гравийный грунт": "graviy",
    "насыпной": "nasipnoy",
    "насыпной грунт": "nasipnoy",
    "песок": "pesok",
    "песчаный грунт": "pesok",
    "гравелистый песок": "pesok_graviy",
    "песок гравелистый": "pesok_graviy",
    "песок с гравием": "pesok_graviy",
    "суглинок": "suglinok",
    "супесь": "supes",
    "торф": "torf",
}

# Backward-compatible aliases for existing JSON-driven preview/editor code.
SOIL_TYPE_TO_HATCH_FILE: dict[str, str] = {
    soil_type: HATCH_ASSETS[asset_key].json_file for soil_type, asset_key in SOIL_TYPE_TO_HATCH_ASSET.items()
}
SOIL_TYPE_TO_PAT_FILE: dict[str, str] = {
    soil_type: HATCH_ASSETS[asset_key].pat_file for soil_type, asset_key in SOIL_TYPE_TO_HATCH_ASSET.items()
}


def normalize_soil_type(value: str | None) -> str:
    return str(value or "").strip().lower().replace("ё", "е")


def resolve_hatch_asset(soil_type: str) -> HatchAssetSpec | None:
    raw = normalize_soil_type(soil_type)
    asset_key = SOIL_TYPE_TO_HATCH_ASSET.get(raw)
    if not asset_key:
        return None
    return HATCH_ASSETS.get(asset_key)


@lru_cache(maxsize=None)
def load_registered_hatch(soil_type: str) -> HatchPattern | None:
    asset = resolve_hatch_asset(soil_type)
    if asset is None or not asset.json_path.exists():
        return None
    return load_hatch_pattern(asset.json_path, name=asset.stem.lower(), title=asset.stem)


@lru_cache(maxsize=None)
def load_registered_pat_pattern(soil_type: str) -> PatPattern | None:
    asset = resolve_hatch_asset(soil_type)
    if asset is None or not asset.pat_path.exists():
        return None
    return load_pat_pattern(asset.pat_path, name=asset.stem.lower(), title=asset.stem)
