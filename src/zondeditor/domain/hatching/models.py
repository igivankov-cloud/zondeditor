from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_DASH = "0.300000"
DEFAULT_GAP = "3.856920"
DEFAULT_POINT_GAP = "1.000000"
SEGMENT_TYPES = ("Штрих", "Точка")


@dataclass(frozen=True)
class HatchSegment:
    kind: str = "Штрих"
    dash: float = 0.3
    gap: float = 3.85692


@dataclass(frozen=True)
class HatchLine:
    angle_deg: float
    x: float
    y: float
    dx: float
    dy: float
    segments: tuple[HatchSegment, ...] = field(default_factory=tuple)
    enabled: bool = True
    color: str = "#000000"
    thickness_mm: float = 0.0
    line_type: str = "Сплошная"


@dataclass(frozen=True)
class HatchPattern:
    name: str
    title: str
    source_file: str
    scale: float = 1.0
    lines: tuple[HatchLine, ...] = field(default_factory=tuple)


PatPatternDefinitionRow = tuple[float, tuple[float, float], tuple[float, float], tuple[float, ...]]


@dataclass(frozen=True)
class PatPattern:
    name: str
    title: str
    source_file: str
    definition: tuple[PatPatternDefinitionRow, ...] = field(default_factory=tuple)
