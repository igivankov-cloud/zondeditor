from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from src.zondeditor.processing.value_semantics import parse_measurement


def _decimal_places(value: Any) -> int | None:
    if value is None:
        return None
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


def infer_series_precision(local_samples: Iterable[Any], series_samples: Iterable[Any], *, field_name: str = "") -> int:
    local_dec = [_decimal_places(v) for v in local_samples]
    local_dec = [d for d in local_dec if d is not None]
    if local_dec:
        return Counter(local_dec).most_common(1)[0][0]

    series_dec = [_decimal_places(v) for v in series_samples if parse_measurement(v) is not None]
    series_dec = [d for d in series_dec if d is not None]
    if series_dec:
        return Counter(series_dec).most_common(1)[0][0]

    field = str(field_name or "").lower()
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
