from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .loader import load_hatch_pattern
from .models import HatchPattern

ASSET_DIR = Path(__file__).resolve().parents[2] / 'assets' / 'hatches'
SOIL_TYPE_TO_HATCH_FILE: dict[str, str] = {
    'песчаник': 'Peschanik.json',
}


@lru_cache(maxsize=None)
def load_registered_hatch(soil_type: str) -> HatchPattern | None:
    raw = str(soil_type or '').strip().lower()
    rel = SOIL_TYPE_TO_HATCH_FILE.get(raw)
    if not rel:
        return None
    path = ASSET_DIR / rel
    if not path.exists():
        return None
    return load_hatch_pattern(path, name=Path(rel).stem.lower(), title=Path(rel).stem)
