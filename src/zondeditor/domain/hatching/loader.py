from __future__ import annotations

import json
from pathlib import Path

from .math import infer_line_type, normalize_segments, parse_angle_deg, parse_float
from .models import HatchLine, HatchPattern


def _color_from_hex(value: str | None) -> str:
    s = str(value or "000000").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        s = "000000"
    try:
        int(s, 16)
    except Exception:
        s = "000000"
    return f"#{s.lower()}"


def load_hatch_pattern(path: str | Path, *, name: str | None = None, title: str | None = None) -> HatchPattern:
    src_path = Path(path)
    payload = json.loads(src_path.read_text(encoding='utf-8'))
    rows = payload.get('rows') or []
    lines: list[HatchLine] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        enabled = bool(row.get('enabled', True))
        segments = normalize_segments(row.get('segments'))
        if not segments:
            declared = str(row.get('line_type') or 'Сплошная').strip()
            if declared == 'Точка':
                segments = normalize_segments([{'kind': 'Точка', 'gap': row.get('gap', '1.000000')}])
            elif declared == 'Штрих':
                segments = normalize_segments([{'kind': 'Штрих', 'dash': row.get('dash', '0.300000'), 'gap': row.get('gap', '3.856920')}])
        lines.append(
            HatchLine(
                angle_deg=parse_angle_deg(row.get('angle'), 0.0),
                x=parse_float(row.get('x'), 0.0),
                y=parse_float(row.get('y'), 0.0),
                dx=parse_float(row.get('dx'), 0.0),
                dy=parse_float(row.get('dy'), 0.0),
                segments=segments,
                enabled=enabled,
                color=_color_from_hex(row.get('color')),
                thickness_mm=parse_float(row.get('thickness'), 0.0),
                line_type=infer_line_type(segments) if segments else str(row.get('line_type') or 'Сплошная').strip(),
            )
        )
    stem = src_path.stem
    return HatchPattern(
        name=name or stem.lower(),
        title=title or stem,
        source_file=str(src_path),
        scale=parse_float(payload.get('scale'), 1.0),
        lines=tuple(lines),
    )
