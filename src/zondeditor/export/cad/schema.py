from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class CadLayerSpec:
    name: str
    color_aci: int
    rgb: tuple[int, int, int] | None = None
    linetype: str = "CONTINUOUS"
    lineweight: int | None = None  # hundredths of mm: 30 => 0.30mm


@dataclass(frozen=True)
class CurveScaleSpec:
    min_value: float
    max_value: float
    width_mm: float
    major_tick_step: float
    minor_tick_step: float
    title: str
    unit: str
    x_origin_mm: float
    layer_scale: str
    layer_curve: str


@dataclass(frozen=True)
class CurveSeries:
    layer: str
    points_mm: list[tuple[float, float]]


@dataclass(frozen=True)
class TextLabel:
    layer: str
    text: str
    x_mm: float
    y_mm: float
    height_mm: float
    align: Literal["LEFT", "CENTER", "RIGHT"] = "LEFT"
    color_aci: int | None = None
    rotation_deg: float = 0.0


@dataclass(frozen=True)
class DepthAxisSpec:
    layer: str
    x_mm: float
    max_depth_m: float
    major_step_m: float
    minor_step_m: float
    label_offset_mm: float = 4.0


@dataclass(frozen=True)
class ExportCadOptions:
    vertical_scale: int = 100
    include_grid: bool = True
    output_format: Literal["dxf"] = "dxf"


@dataclass(frozen=True)
class CadLine:
    layer: str
    start: tuple[float, float]
    end: tuple[float, float]


@dataclass(frozen=True)
class CadPoint:
    layer: str
    position: tuple[float, float, float]
    color_aci: int | None = None


@dataclass(frozen=True)
class CadPolyline:
    layer: str
    points: list[tuple[float, float]]
    closed: bool = False


@dataclass(frozen=True)
class CadHatch:
    layer: str
    boundary: list[tuple[float, float]]
    color_aci: int | None = None
    rgb: tuple[int, int, int] | None = None
    solid: bool = True


@dataclass(frozen=True)
class CadBlock:
    name: str
    base_point: tuple[float, float, float]
    lines: list[CadLine] = field(default_factory=list)
    polylines: list[CadPolyline] = field(default_factory=list)
    hatches: list[CadHatch] = field(default_factory=list)
    points: list[CadPoint] = field(default_factory=list)
    texts: list[TextLabel] = field(default_factory=list)


@dataclass(frozen=True)
class CadScene:
    layers: list[CadLayerSpec]
    block: CadBlock
    insertion_point: tuple[float, float, float] = (0.0, 0.0, 0.0)
