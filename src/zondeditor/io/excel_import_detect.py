from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


ROLE_IGNORE = "ignore"
ROLE_DEPTH = "depth"
ROLE_LOB = "lob"
ROLE_BOK = "bok"
ROLE_OBSHEE = "obshee"
ROLE_QC = "qc_mpa"
ROLE_FS = "fs_kpa"
ROLE_EXTRA = "extra"

MODE_VERTICAL = "vertical"
MODE_BLOCKS_RIGHT = "blocks_right"

ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    ROLE_DEPTH: ("глуб", "depth", "deep"),
    ROLE_LOB: ("лоб", "cone", "tip"),
    ROLE_BOK: ("бок", "sleeve", "трени", "муфт"),
    ROLE_OBSHEE: ("общ", "общее", "total"),
    ROLE_QC: ("qc", "мпа", "mpa"),
    ROLE_FS: ("fs", "кпа", "kpa"),
}


@dataclass(slots=True)
class DetectedImportSettings:
    mode: str
    header_row: int
    data_start_row: int
    column_roles: dict[int, str]
    repeat_first_block: bool


def normalize_header(value: object) -> str:
    txt = "" if value is None else str(value)
    return " ".join(txt.strip().lower().replace("_", " ").split())


def guess_role_from_header(value: object) -> str:
    txt = normalize_header(value)
    if not txt:
        return ROLE_IGNORE
    for role, aliases in ROLE_ALIASES.items():
        if any(token in txt for token in aliases):
            return role
    return ROLE_IGNORE


def try_parse_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    txt = str(value).strip().replace(" ", "").replace(",", ".")
    if not txt:
        return None
    try:
        return float(txt)
    except Exception:
        return None


def _score_header_row(row: list[object]) -> int:
    score = 0
    for cell in row:
        role = guess_role_from_header(cell)
        if role == ROLE_IGNORE:
            continue
        if role == ROLE_DEPTH:
            score += 4
        else:
            score += 2
    return score


def autodetect_header_row(rows: list[list[object]], limit: int = 120) -> int:
    if not rows:
        return 1
    best_idx = 0
    best_score = -1
    for i, row in enumerate(rows[: max(1, limit)]):
        score = _score_header_row(row)
        if score > best_score:
            best_score = score
            best_idx = i
    return best_idx + 1


def detect_column_roles(header: list[object]) -> dict[int, str]:
    return {idx: guess_role_from_header(value) for idx, value in enumerate(header)}


def detect_depth_column(rows: list[list[object]], header_row_1based: int, role_map: dict[int, str]) -> int | None:
    depth_from_header = next((c for c, role in role_map.items() if role == ROLE_DEPTH), None)
    if depth_from_header is not None:
        return depth_from_header

    start = max(0, header_row_1based)
    max_cols = max((len(r) for r in rows), default=0)
    best_col = None
    best_score = -1.0
    for col in range(max_cols):
        vals: list[float] = []
        for row in rows[start : start + 120]:
            if col >= len(row):
                continue
            parsed = try_parse_float(row[col])
            if parsed is not None:
                vals.append(parsed)
        if len(vals) < 3:
            continue
        asc = 0
        for a, b in zip(vals, vals[1:]):
            if b >= a:
                asc += 1
        score = len(vals) + asc / max(1, len(vals) - 1)
        if score > best_score:
            best_score = score
            best_col = col
    return best_col


def autodetect_data_start_row(
    rows: list[list[object]],
    header_row_1based: int,
    depth_col: int | None,
    role_map: dict[int, str],
) -> int:
    if depth_col is None:
        return header_row_1based + 1

    data_cols = [c for c, role in role_map.items() if role not in (ROLE_IGNORE, ROLE_DEPTH)]
    start_idx = max(header_row_1based, 0)
    for i in range(start_idx, len(rows)):
        row = rows[i]
        if depth_col >= len(row):
            continue
        depth_v = try_parse_float(row[depth_col])
        if depth_v is None:
            continue
        if any(c < len(row) and try_parse_float(row[c]) is not None for c in data_cols):
            return i + 1
    return header_row_1based + 1


def _has_repeating_signature(roles: list[str]) -> bool:
    seq = [r for r in roles if r not in (ROLE_IGNORE, ROLE_DEPTH)]
    n = len(seq)
    if n < 4:
        return False
    for width in range(2, min(6, n // 2 + 1)):
        chunk = seq[:width]
        if len(chunk) < 2:
            continue
        repeats = 1
        pos = width
        while pos + width <= n and seq[pos : pos + width] == chunk:
            repeats += 1
            pos += width
        if repeats >= 2:
            return True
    return False


def autodetect_mode(role_map: dict[int, str], depth_col: int | None) -> str:
    if depth_col is None:
        return MODE_VERTICAL
    ordered = [role_map.get(c, ROLE_IGNORE) for c in sorted(role_map)]
    return MODE_BLOCKS_RIGHT if _has_repeating_signature(ordered) else MODE_VERTICAL


def autodetect_settings(rows: list[list[object]]) -> DetectedImportSettings:
    header_row = autodetect_header_row(rows)
    header = rows[header_row - 1] if 0 < header_row <= len(rows) else []
    role_map = detect_column_roles(header)
    depth_col = detect_depth_column(rows, header_row, role_map)
    if depth_col is not None and role_map.get(depth_col) == ROLE_IGNORE:
        role_map[depth_col] = ROLE_DEPTH
    data_start = autodetect_data_start_row(rows, header_row, depth_col, role_map)
    mode = autodetect_mode(role_map, depth_col)
    return DetectedImportSettings(
        mode=mode,
        header_row=header_row,
        data_start_row=data_start,
        column_roles=role_map,
        repeat_first_block=(mode == MODE_BLOCKS_RIGHT),
    )


def infer_type_from_roles(roles: Iterable[str]) -> int | None:
    s = set(roles)
    if ROLE_QC in s and ROLE_FS in s:
        return 3
    if ROLE_LOB in s and ROLE_BOK in s:
        return 2
    if ROLE_LOB in s and ROLE_OBSHEE in s:
        return 1
    return None
