from __future__ import annotations

# === FILE MAP BEGIN ===
# FILE MAP (обновляй при правках; указывай строки Lx–Ly)
# - parse_measurement/is_missing_value: L10–L31 — единая нормализация и определение missing.
# - is_effective_zero/is_positive_measurement: L34–L46 — корректная классификация нуля и валидных малых значений.
# - max_zero_run/scan_zero_runs: L49–L73 — поиск серий реальных нулей с EPS-допуском.
# === FILE MAP END ===

import math
from typing import Any, Iterable

EPS_ZERO = 1e-9


def parse_measurement(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        fv = float(value)
    else:
        text = str(value).strip().replace(",", ".")
        if text == "":
            return None
        try:
            fv = float(text)
        except Exception:
            return None
    if math.isnan(fv):
        return None
    return fv


def is_missing_value(value: Any) -> bool:
    return parse_measurement(value) is None


def is_effective_zero(value: Any, *, eps: float = EPS_ZERO) -> bool:
    parsed = parse_measurement(value)
    if parsed is None:
        return False
    return abs(float(parsed)) <= float(eps)


def is_positive_measurement(value: Any, *, eps: float = EPS_ZERO) -> bool:
    parsed = parse_measurement(value)
    if parsed is None:
        return False
    return float(parsed) > float(eps)


def max_zero_run(values: Iterable[Any], *, eps: float = EPS_ZERO) -> int:
    best = 0
    cur = 0
    for value in values:
        if is_effective_zero(value, eps=eps):
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


def scan_zero_runs(values: list[Any], *, min_len: int = 6, eps: float = EPS_ZERO) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    i = 0
    n = len(values)
    while i < n:
        if not is_effective_zero(values[i], eps=eps):
            i += 1
            continue
        j = i
        while j < n and is_effective_zero(values[j], eps=eps):
            j += 1
        if (j - i) >= int(min_len):
            out.append((i, j - 1))
        i = j
    return out
