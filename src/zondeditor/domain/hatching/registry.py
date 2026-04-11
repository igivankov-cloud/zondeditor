from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .loader import load_hatch_pattern
from .models import HatchPattern

ASSET_DIR = Path(__file__).resolve().parents[2] / 'assets' / 'hatches'
SOIL_TYPE_TO_HATCH_FILE: dict[str, str] = {
    'песчаник': 'Peschanik.json',
    'аргиллит': 'Argillit.json',
    'аргилит': 'Argillit.json',
    'глина': 'Glina.json',
    'гравий': 'graviy.json',
    'гравийный грунт': 'graviy.json',
    'насыпной': 'Nasipnoy.json',
    'насыпной грунт': 'Nasipnoy.json',
    'песок': 'Pesok.json',
    'песчаный грунт': 'Pesok.json',
    'гравелистый песок': 'PesokGraviy.json',
    'песок гравелистый': 'PesokGraviy.json',
    'песок с гравием': 'PesokGraviy.json',
    'суглинок': 'Suglinok.json',
    'супесь': 'Supes.json',
    'торф': 'Torf.json',
}


def normalize_soil_type(value: str | None) -> str:
    return str(value or '').strip().lower().replace('ё', 'е')


@lru_cache(maxsize=None)
def load_registered_hatch(soil_type: str) -> HatchPattern | None:
    raw = normalize_soil_type(soil_type)
    rel = SOIL_TYPE_TO_HATCH_FILE.get(raw)
    if not rel:
        return None
    path = ASSET_DIR / rel
    if not path.exists():
        return None
    return load_hatch_pattern(path, name=Path(rel).stem.lower(), title=Path(rel).stem)
