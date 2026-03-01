from __future__ import annotations

from pathlib import Path

from src.zondeditor.domain.models import (
    GeoBlockInfo,
    TestData,
    TestSeries,
    testdata_to_series,
)
from src.zondeditor.io.k2_reader import parse_geo_with_blocks
from src.zondeditor.io.k4_reader import detect_geo_kind, parse_k4_geo_strict


class GeoParseError(ValueError):
    """Raised when GEO/GE0 cannot be parsed."""


def load_geo(path: str | Path) -> list[TestSeries]:
    """Load GEO/GE0 file into unified CPT domain model (list[TestSeries])."""
    tests, _meta, _kind = parse_geo_file(path)
    return [testdata_to_series(t) for t in tests]


def parse_geo_file(path: str | Path) -> tuple[list[TestData], list[dict], str]:
    """Parse GEO/GE0 file and auto-detect K2/K4 payload kind.

    Returns (tests, meta_rows, geo_kind), where geo_kind is "K2" or "K4".
    """
    geo_path = Path(path)
    try:
        data = geo_path.read_bytes()
    except Exception as exc:
        raise GeoParseError(f"Не удалось прочитать GEO/GE0: {exc}") from exc

    return parse_geo_bytes(data)


def parse_geo_bytes(data: bytes) -> tuple[list[TestData], list[dict], str]:
    """Parse GEO/GE0 payload from bytes and return (tests, meta_rows, geo_kind)."""
    try:
        geo_kind = detect_geo_kind(data)
        if geo_kind == "K4":
            tests = parse_k4_geo_strict(data, TestData, GeoBlockInfo)
            return tests, [], geo_kind
        tests, meta_rows = parse_geo_with_blocks(data, TestData, GeoBlockInfo)
        return tests, meta_rows, geo_kind
    except Exception as exc:
        raise GeoParseError(str(exc)) from exc
