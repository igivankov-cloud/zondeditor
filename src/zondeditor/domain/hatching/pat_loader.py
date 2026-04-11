from __future__ import annotations

from pathlib import Path

from .models import PatPattern


def _strip_pat_comment(line: str) -> str:
    return str(line or "").split(";", 1)[0].strip()


def _parse_pat_float(token: str) -> float:
    raw = str(token or "").strip()
    if not raw:
        raise ValueError("PAT token is empty")
    return float(raw)


def load_pat_pattern(path: str | Path, *, name: str | None = None, title: str | None = None) -> PatPattern:
    src_path = Path(path)
    header_name = src_path.stem
    header_title = src_path.stem
    rows: list[tuple[float, tuple[float, float], tuple[float, float], tuple[float, ...]]] = []
    header_seen = False

    for line_no, raw_line in enumerate(src_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = _strip_pat_comment(raw_line)
        if not line:
            continue
        if line.startswith("*"):
            if header_seen and rows:
                break
            body = line[1:]
            head, sep, tail = body.partition(",")
            header_name = head.strip() or header_name
            header_title = tail.strip() if sep and tail.strip() else header_name
            header_seen = True
            continue
        if not header_seen:
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 5:
            raise ValueError(f"PAT descriptor requires at least 5 fields at {src_path}:{line_no}")
        angle_deg = _parse_pat_float(parts[0])
        base_point = (_parse_pat_float(parts[1]), _parse_pat_float(parts[2]))
        offset = (_parse_pat_float(parts[3]), _parse_pat_float(parts[4]))
        dash_items = tuple(_parse_pat_float(item) for item in parts[5:] if item.strip())
        rows.append((angle_deg, base_point, offset, dash_items))

    return PatPattern(
        name=name or header_name,
        title=title or header_title,
        source_file=str(src_path),
        definition=tuple(rows),
    )
