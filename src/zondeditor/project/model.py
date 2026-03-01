from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceInfo:
    kind: str = ""
    filename: str = ""
    ext: str = ""
    mime: str = "application/octet-stream"


@dataclass
class ProjectSettings:
    scale: str = "250"
    fcone: str = "30"
    fsleeve: str = "10"
    acon: str = "10"
    asleeve: str = "350"
    step_m: float = 0.1
    k2k4_mode: str = ""
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class Project:
    format_version: int = 1
    created_at: str = ""
    updated_at: str = ""
    object_name: str = ""
    source: SourceInfo = field(default_factory=SourceInfo)
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    ops: list[dict[str, Any]] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
