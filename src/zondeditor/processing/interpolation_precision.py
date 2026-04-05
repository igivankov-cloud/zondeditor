from __future__ import annotations

from collections import Counter
import math
from typing import Any, Iterable

from src.zondeditor.processing.value_semantics import parse_measurement


def _to_float(value: Any) -> float | None:
    try:
        return parse_measurement(value)
    except Exception:
        return None


def _is_integer_like(value: Any) -> bool:
    fv = _to_float(value)
    if fv is None or not math.isfinite(fv):
        return False
    return abs(fv - round(fv)) <= 1e-9


def _decimal_places(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return 0
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        if abs(value - round(value)) <= 1e-9:
            return 0
        text = f"{value:.10f}".rstrip("0").rstrip(".")
        if "." not in text:
            return 0
        return max(0, len(text.split(".", 1)[1]))
    text = str(value).strip().replace(",", ".")
    if text == "":
        return None
    if "e" in text.lower():
        try:
            fv = float(text)
            text = f"{fv:.10f}".rstrip("0").rstrip(".")
        except Exception:
            return None
    if "." not in text:
        return 0
    return max(0, len(text.split(".", 1)[1]))


def _most_common_decimals(values: Iterable[Any]) -> int | None:
    dec = [_decimal_places(v) for v in values]
    dec = [d for d in dec if d is not None]
    if not dec:
        return None
    return Counter(dec).most_common(1)[0][0]


def infer_series_precision(local_samples: Iterable[Any], series_samples: Iterable[Any], *, field_name: str = "") -> int:
    field = str(field_name or "").lower()
    local_values = [v for v in local_samples if _to_float(v) is not None]
    local_int_count = sum(1 for v in local_values if _is_integer_like(v))
    if local_values and (local_int_count * 2 >= len(local_values)):
        return 0

    local_mode = _most_common_decimals(local_values)
    if local_mode is not None:
        return local_mode

    series_values = [v for v in series_samples if _to_float(v) is not None]
    series_int_count = sum(1 for v in series_values if _is_integer_like(v))
    if series_values and field == "fs" and (series_int_count * 2 >= len(series_values)):
        return 0

    series_mode = _most_common_decimals(series_values)
    if series_mode is not None:
        return series_mode

    if field == "fs":
        return 0
    return 2


def normalize_interpolated_value(
    raw_value: float,
    *,
    local_samples: Iterable[Any],
    series_samples: Iterable[Any],
    field_name: str = "",
) -> float:
    decimals = infer_series_precision(local_samples, series_samples, field_name=field_name)
    value = round(float(raw_value), int(decimals))
    if decimals <= 0:
        return float(int(round(value)))
    return float(value)
