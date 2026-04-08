from __future__ import annotations

from dataclasses import dataclass, field

from src.zondeditor.domain.models import TestData


@dataclass(frozen=True)
class ProtocolLayerRow:
    idx: int
    from_depth_m: float
    to_depth_m: float
    ige_id: str
    description: str
    soil_type: str = ""
    abs_mark_text: str = ""


@dataclass(frozen=True)
class ProtocolDocument:
    test: TestData
    title: str
    date_text: str
    max_depth_m: float
    layers: list[ProtocolLayerRow] = field(default_factory=list)


@dataclass(frozen=True)
class ProtocolBuildPack:
    documents: list[ProtocolDocument]
