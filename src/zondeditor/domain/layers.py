from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

MIN_LAYER_THICKNESS_M = 0.20
SNAP_STEP_M = 0.10
INSERT_LAYER_THICKNESS_M = 1.00


class CalcMode(str, Enum):
    VALID = "valid"
    LIMITED = "limited"


class SoilType(str, Enum):
    CLAY = "глина"
    LOAM = "суглинок"
    SANDY_LOAM = "супесь"
    SAND = "песок"
    PEAT = "торф"
    GRAVEL = "гравийный грунт"
    GRAVELLY_SAND = "песок гравелистый"
    FILL = "насыпной"
    ARGILLITE = "аргиллит"
    SANDSTONE = "песчаник"


VALID_SOILS = {
    SoilType.CLAY,
    SoilType.LOAM,
    SoilType.SANDY_LOAM,
    SoilType.SAND,
    SoilType.PEAT,
}

SOIL_STYLE: dict[SoilType, dict[str, str]] = {
    SoilType.CLAY: {"color": "#b67a52", "hatch": "diag_dense", "hatch_color": "#000000"},
    SoilType.LOAM: {"color": "#c89b6d", "hatch": "diag_sparse", "hatch_color": "#000000"},
    SoilType.SANDY_LOAM: {"color": "#d8b88a", "hatch": "diag_sparse", "hatch_color": "#000000"},
    SoilType.SAND: {"color": "#f0d76a", "hatch": "dot", "hatch_color": "#000000"},
    SoilType.PEAT: {"color": "#8f8f8f", "hatch": "cross", "hatch_color": "#000000"},
    SoilType.GRAVEL: {"color": "#c7c3ba", "hatch": "cross", "hatch_color": "#000000"},
    SoilType.GRAVELLY_SAND: {"color": "#d8cc98", "hatch": "cross", "hatch_color": "#000000"},
    SoilType.FILL: {"color": "#bda48b", "hatch": "diag_dense", "hatch_color": "#000000"},
    SoilType.ARGILLITE: {"color": "#9e4f43", "hatch": "diag_dense", "hatch_color": "#000000"},
    SoilType.SANDSTONE: {"color": "#c58f62", "hatch": "diag_sparse", "hatch_color": "#000000"},
}

DEFAULT_LAYER_STYLE = SOIL_STYLE


@dataclass
class Layer:
    top_m: float
    bot_m: float
    ige_id: str = "ИГЭ-1"
    soil_type: SoilType = SoilType.SANDY_LOAM
    ige_num: int = 1
    calc_mode: CalcMode = CalcMode.VALID
    style: dict[str, str] = field(default_factory=dict)
    name: str = ""
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def thickness_m(self) -> float:
        return float(self.bot_m - self.top_m)


def calc_mode_for_soil(soil_type: SoilType) -> CalcMode:
    return CalcMode.VALID if soil_type in VALID_SOILS else CalcMode.LIMITED


def snap_depth(value_m: float, step_m: float = SNAP_STEP_M) -> float:
    if step_m <= 0:
        return float(value_m)
    return round(float(value_m) / step_m) * step_m


def layer_to_dict(layer: Layer) -> dict[str, Any]:
    return {
        "top_m": float(layer.top_m),
        "bot_m": float(layer.bot_m),
        "ige_id": str(getattr(layer, "ige_id", "") or f"ИГЭ-{int(getattr(layer, 'ige_num', 1) or 1)}"),
        "soil_type": str(layer.soil_type.value),
        "ige_num": int(layer.ige_num),
        "calc_mode": str(layer.calc_mode.value),
        "style": dict(layer.style or {}),
        "name": str(layer.name or ""),
        "params": dict(layer.params or {}),
    }


def layer_from_dict(data: dict[str, Any]) -> Layer:
    soil = SoilType(str(data.get("soil_type") or SoilType.SANDY_LOAM.value))
    mode_raw = str(data.get("calc_mode") or "")
    calc_mode = CalcMode(mode_raw) if mode_raw in {x.value for x in CalcMode} else calc_mode_for_soil(soil)
    style = dict(SOIL_STYLE.get(soil, {}))
    style.update(dict(data.get("style") or {}))
    raw_ige_id = str(data.get("ige_id") or "").strip()
    if not raw_ige_id:
        raw_ige_id = f"ИГЭ-{int(data.get('ige_num', 1) or 1)}"
    return Layer(
        top_m=float(data.get("top_m", 0.0) or 0.0),
        bot_m=float(data.get("bot_m", 0.0) or 0.0),
        ige_id=raw_ige_id,
        soil_type=soil,
        ige_num=int(data.get("ige_num", 1) or 1),
        calc_mode=calc_mode,
        style=style,
        name=str(data.get("name") or ""),
        params=dict(data.get("params") or {}),
    )


def build_default_layers(depth_top_m: float, depth_bot_m: float) -> list[Layer]:
    top = snap_depth(float(depth_top_m))
    bot = snap_depth(float(depth_bot_m))
    min_total = MIN_LAYER_THICKNESS_M * 2.0
    if bot < top + min_total:
        bot = top + min_total
    mid = snap_depth((top + bot) * 0.5)
    if mid < top + MIN_LAYER_THICKNESS_M:
        mid = top + MIN_LAYER_THICKNESS_M
    if mid > bot - MIN_LAYER_THICKNESS_M:
        mid = bot - MIN_LAYER_THICKNESS_M
    top_soil = SoilType.SANDY_LOAM
    bot_soil = SoilType.SAND
    return [
        Layer(
            top_m=top,
            bot_m=mid,
            ige_id="ИГЭ-1",
            soil_type=top_soil,
            calc_mode=calc_mode_for_soil(top_soil),
            style=dict(SOIL_STYLE.get(top_soil, {})),
            ige_num=1,
        ),
        Layer(
            top_m=mid,
            bot_m=bot,
            ige_id="ИГЭ-2",
            soil_type=bot_soil,
            calc_mode=calc_mode_for_soil(bot_soil),
            style=dict(SOIL_STYLE.get(bot_soil, {})),
            ige_num=2,
        ),
    ]


def normalize_layers(layers: list[Layer]) -> list[Layer]:
    out = sorted(layers, key=lambda x: float(x.top_m))
    for idx, lyr in enumerate(out, start=1):
        lyr.top_m = snap_depth(float(lyr.top_m))
        lyr.bot_m = snap_depth(float(lyr.bot_m))
        try:
            lyr.ige_num = int(lyr.ige_num)
        except Exception:
            lyr.ige_num = idx
        if lyr.ige_num < 1:
            lyr.ige_num = idx
        if not str(getattr(lyr, "ige_id", "") or "").strip():
            lyr.ige_id = f"ИГЭ-{int(lyr.ige_num)}"
        if lyr.bot_m < (lyr.top_m + MIN_LAYER_THICKNESS_M):
            lyr.bot_m = lyr.top_m + MIN_LAYER_THICKNESS_M
        if not lyr.style:
            lyr.style = dict(SOIL_STYLE.get(lyr.soil_type, {}))
    validate_layers(out)
    return out


def validate_layers(layers: list[Layer]) -> None:
    prev_bot = None
    for lyr in layers:
        if lyr.bot_m - lyr.top_m < MIN_LAYER_THICKNESS_M - 1e-9:
            raise ValueError("Layer is thinner than minimal thickness")
        if prev_bot is not None and lyr.top_m < prev_bot - 1e-9:
            raise ValueError("Layers overlap")
        prev_bot = lyr.bot_m


def move_layer_boundary(layers: list[Layer], boundary_index: int, new_depth_m: float) -> list[Layer]:
    if boundary_index <= 0 or boundary_index >= len(layers):
        raise ValueError("Boundary index out of range")
    snapped = snap_depth(new_depth_m)
    prev_l = layers[boundary_index - 1]
    next_l = layers[boundary_index]
    low = prev_l.top_m + MIN_LAYER_THICKNESS_M
    high = next_l.bot_m - MIN_LAYER_THICKNESS_M
    clamped = max(low, min(high, snapped))
    prev_l.bot_m = clamped
    next_l.top_m = clamped
    return normalize_layers(layers)


def insert_layer_between(layers: list[Layer], boundary_index: int) -> list[Layer]:
    if boundary_index <= 0 or boundary_index >= len(layers):
        raise ValueError("Boundary index out of range")
    prev_l = layers[boundary_index - 1]
    next_l = layers[boundary_index]
    gap = next_l.top_m - prev_l.bot_m
    if gap < -1e-9:
        raise ValueError("Layers overlap")
    # contiguous layers; split the upper part if possible
    available = next_l.bot_m - prev_l.bot_m
    required = INSERT_LAYER_THICKNESS_M + MIN_LAYER_THICKNESS_M
    if available < required - 1e-9:
        raise ValueError("Not enough thickness to insert a 1 m layer")

    new_top = prev_l.bot_m
    new_bot = snap_depth(new_top + INSERT_LAYER_THICKNESS_M)
    if new_bot > next_l.bot_m - MIN_LAYER_THICKNESS_M:
        new_bot = next_l.bot_m - MIN_LAYER_THICKNESS_M
    soil = SoilType.SANDY_LOAM
    new_layer = Layer(
        top_m=new_top,
        bot_m=new_bot,
        ige_id=f"ИГЭ-{boundary_index + 1}",
        soil_type=soil,
        calc_mode=calc_mode_for_soil(soil),
        style=dict(SOIL_STYLE.get(soil, {})),
        ige_num=boundary_index + 1,
    )
    next_l.top_m = new_bot
    layers.insert(boundary_index, new_layer)
    return normalize_layers(layers)
