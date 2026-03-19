from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .layers import MIN_LAYER_THICKNESS_M, SNAP_STEP_M, snap_depth


@dataclass
class ColumnInterval:
    from_depth: float
    to_depth: float
    ige_id: str = ""
    ige_name: str = ""


@dataclass
class ExperienceColumn:
    column_depth_start: float = 0.0
    column_depth_end: float = 0.0
    intervals: list[ColumnInterval] = field(default_factory=list)


def column_interval_to_dict(interval: ColumnInterval) -> dict[str, Any]:
    return {
        "from_depth": float(interval.from_depth),
        "to_depth": float(interval.to_depth),
        "ige_id": str(interval.ige_id or ""),
        "ige_name": str(interval.ige_name or ""),
    }


def column_interval_from_dict(data: dict[str, Any]) -> ColumnInterval:
    return ColumnInterval(
        from_depth=float(data.get("from_depth", 0.0) or 0.0),
        to_depth=float(data.get("to_depth", 0.0) or 0.0),
        ige_id=str(data.get("ige_id") or ""),
        ige_name=str(data.get("ige_name") or ""),
    )


def column_to_dict(column: ExperienceColumn) -> dict[str, Any]:
    return {
        "column_depth_start": float(column.column_depth_start),
        "column_depth_end": float(column.column_depth_end),
        "intervals": [column_interval_to_dict(item) for item in (column.intervals or [])],
    }


def column_from_dict(data: dict[str, Any]) -> ExperienceColumn:
    intervals = [column_interval_from_dict(item) for item in list(data.get("intervals") or []) if isinstance(item, dict)]
    return normalize_column(
        ExperienceColumn(
            column_depth_start=float(data.get("column_depth_start", 0.0) or 0.0),
            column_depth_end=float(data.get("column_depth_end", 0.0) or 0.0),
            intervals=intervals,
        )
    )


def validate_column(column: ExperienceColumn) -> None:
    if abs(float(column.column_depth_start)) > 1e-9:
        raise ValueError("Column must start at 0.0 m")
    prev = float(column.column_depth_start)
    for item in column.intervals:
        if float(item.from_depth) < prev - 1e-9:
            raise ValueError("Column intervals overlap")
        if abs(float(item.from_depth) - prev) > 1e-9:
            raise ValueError("Column intervals must be continuous")
        if float(item.to_depth) - float(item.from_depth) < MIN_LAYER_THICKNESS_M - 1e-9:
            raise ValueError("Column interval is thinner than minimal thickness")
        prev = float(item.to_depth)
    if column.intervals and abs(prev - float(column.column_depth_end)) > 1e-9:
        raise ValueError("Column intervals must end at column_depth_end")


def normalize_column(column: ExperienceColumn, *, default_ige_id: str = "ИГЭ-1") -> ExperienceColumn:
    start = 0.0
    end = max(start + MIN_LAYER_THICKNESS_M, snap_depth(float(column.column_depth_end or 0.0)))
    ordered = sorted(list(column.intervals or []), key=lambda item: float(item.from_depth))
    normalized: list[ColumnInterval] = []
    cursor = start
    last_ige = default_ige_id
    for raw in ordered:
        ige_id = str(raw.ige_id or last_ige or default_ige_id)
        ige_name = str(raw.ige_name or "")
        raw_from = max(start, snap_depth(float(raw.from_depth)))
        raw_to = min(end, snap_depth(float(raw.to_depth)))
        if raw_to - raw_from < MIN_LAYER_THICKNESS_M - 1e-9:
            continue
        if raw_from > cursor + 1e-9:
            normalized.append(ColumnInterval(from_depth=cursor, to_depth=raw_from, ige_id=last_ige, ige_name=""))
            cursor = raw_from
        adj_from = cursor
        adj_to = max(adj_from + MIN_LAYER_THICKNESS_M, raw_to)
        if adj_to > end:
            adj_to = end
        if adj_to - adj_from < MIN_LAYER_THICKNESS_M - 1e-9:
            continue
        normalized.append(ColumnInterval(from_depth=adj_from, to_depth=adj_to, ige_id=ige_id, ige_name=ige_name))
        cursor = adj_to
        last_ige = ige_id
        if cursor >= end - 1e-9:
            break
    if not normalized:
        normalized = [ColumnInterval(from_depth=start, to_depth=end, ige_id=default_ige_id, ige_name="")]
    elif cursor < end - 1e-9:
        normalized.append(ColumnInterval(from_depth=cursor, to_depth=end, ige_id=last_ige, ige_name=""))

    merged: list[ColumnInterval] = []
    for item in normalized:
        if merged and merged[-1].ige_id == item.ige_id and abs(float(merged[-1].to_depth) - float(item.from_depth)) <= 1e-9:
            merged[-1].to_depth = float(item.to_depth)
            if not merged[-1].ige_name:
                merged[-1].ige_name = str(item.ige_name or "")
        else:
            merged.append(item)

    out = ExperienceColumn(column_depth_start=start, column_depth_end=end, intervals=merged)
    validate_column(out)
    return out


def build_column_from_layers(layers: list[Any], *, sounding_top: float, sounding_bottom: float, default_ige_id: str = "ИГЭ-1") -> ExperienceColumn:
    intervals: list[ColumnInterval] = []
    ordered = sorted(list(layers or []), key=lambda item: float(getattr(item, "top_m", 0.0)))
    if ordered:
        first_ige = str(getattr(ordered[0], "ige_id", "") or default_ige_id)
        top = max(0.0, snap_depth(float(sounding_top or 0.0)))
        if top > 0.0:
            intervals.append(ColumnInterval(0.0, top, first_ige, first_ige))
        for item in ordered:
            intervals.append(
                ColumnInterval(
                    from_depth=max(0.0, float(getattr(item, "top_m", 0.0))),
                    to_depth=max(0.0, float(getattr(item, "bot_m", 0.0))),
                    ige_id=str(getattr(item, "ige_id", "") or default_ige_id),
                    ige_name=str(getattr(item, "ige_id", "") or default_ige_id),
                )
            )
    else:
        end = max(MIN_LAYER_THICKNESS_M, float(sounding_bottom or 0.0))
        intervals.append(ColumnInterval(0.0, end, default_ige_id, default_ige_id))
    return normalize_column(
        ExperienceColumn(
            column_depth_start=0.0,
            column_depth_end=max(MIN_LAYER_THICKNESS_M, float(sounding_bottom or 0.0)),
            intervals=intervals,
        ),
        default_ige_id=default_ige_id,
    )


def move_column_boundary(column: ExperienceColumn, boundary_index: int, new_depth_m: float) -> ExperienceColumn:
    intervals = [ColumnInterval(**column_interval_to_dict(item)) for item in column.intervals]
    if boundary_index <= 0 or boundary_index >= len(intervals):
        raise ValueError("Boundary index out of range")
    snapped = snap_depth(new_depth_m)
    low = float(intervals[boundary_index - 1].from_depth) + MIN_LAYER_THICKNESS_M
    high = float(intervals[boundary_index].to_depth) - MIN_LAYER_THICKNESS_M
    clamped = max(low, min(high, snapped))
    intervals[boundary_index - 1].to_depth = clamped
    intervals[boundary_index].from_depth = clamped
    return normalize_column(ExperienceColumn(column_depth_start=0.0, column_depth_end=column.column_depth_end, intervals=intervals))


def split_column_interval(column: ExperienceColumn, interval_index: int, *, from_bottom: bool = False, new_ige_id: str = "ИГЭ-1") -> ExperienceColumn:
    intervals = [ColumnInterval(**column_interval_to_dict(item)) for item in column.intervals]
    if interval_index < 0 or interval_index >= len(intervals):
        raise ValueError("Interval index out of range")
    base = intervals[interval_index]
    if float(base.to_depth) - float(base.from_depth) < (MIN_LAYER_THICKNESS_M * 2.0) - 1e-9:
        raise ValueError("Interval is too thin to split")
    if from_bottom:
        mid = snap_depth(float(base.to_depth) - min(1.0, float(base.to_depth) - float(base.from_depth) - MIN_LAYER_THICKNESS_M))
    else:
        mid = snap_depth(float(base.from_depth) + min(1.0, float(base.to_depth) - float(base.from_depth) - MIN_LAYER_THICKNESS_M))
    mid = max(float(base.from_depth) + MIN_LAYER_THICKNESS_M, min(float(base.to_depth) - MIN_LAYER_THICKNESS_M, mid))
    new_interval = ColumnInterval(mid, float(base.to_depth), new_ige_id, new_ige_id) if from_bottom else ColumnInterval(float(base.from_depth), mid, new_ige_id, new_ige_id)
    if from_bottom:
        base.to_depth = mid
        intervals.insert(interval_index + 1, new_interval)
    else:
        base.from_depth = mid
        intervals.insert(interval_index, new_interval)
    return normalize_column(ExperienceColumn(column_depth_start=0.0, column_depth_end=column.column_depth_end, intervals=intervals))


def remove_column_interval(column: ExperienceColumn, interval_index: int) -> ExperienceColumn:
    intervals = [ColumnInterval(**column_interval_to_dict(item)) for item in column.intervals]
    if len(intervals) <= 1:
        raise ValueError("Cannot remove the last interval")
    removed = intervals.pop(interval_index)
    if interval_index <= 0:
        intervals[0].from_depth = float(removed.from_depth)
    else:
        intervals[max(0, interval_index - 1)].to_depth = float(removed.to_depth)
    return normalize_column(ExperienceColumn(column_depth_start=0.0, column_depth_end=column.column_depth_end, intervals=intervals))
