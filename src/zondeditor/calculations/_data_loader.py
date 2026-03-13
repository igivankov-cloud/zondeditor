from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_data_file(name: str) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    return json.loads((root / "data" / name).read_text(encoding="utf-8"))
