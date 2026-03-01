from __future__ import annotations

import json
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model import Project, ProjectSettings, SourceInfo


PROJECT_JSON = "project.json"
OPS_JSON = "ops/ops.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_project(path: Path, *, project: Project, source_bytes: bytes | None = None) -> None:
    path = Path(path)
    project.updated_at = _now_iso()
    if not project.created_at:
        project.created_at = project.updated_at

    payload = {
        "formatVersion": int(project.format_version),
        "createdAt": project.created_at,
        "updatedAt": project.updated_at,
        "objectName": project.object_name,
        "source": asdict(project.source),
        "settings": asdict(project.settings),
        "ops": project.ops,
        "state": project.state,
    }

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(PROJECT_JSON, json.dumps(payload, ensure_ascii=False, indent=2))
        zf.writestr(OPS_JSON, json.dumps(project.ops, ensure_ascii=False, indent=2))
        if source_bytes is not None:
            ext = (project.source.ext or "bin").lstrip(".")
            zf.writestr(f"data/source.{ext}", source_bytes)


def load_project(path: Path) -> tuple[Project, bytes | None]:
    path = Path(path)
    with zipfile.ZipFile(path, "r") as zf:
        data = json.loads(zf.read(PROJECT_JSON).decode("utf-8"))
        source = SourceInfo(**(data.get("source") or {}))
        settings = ProjectSettings(**(data.get("settings") or {}))
        project = Project(
            format_version=int(data.get("formatVersion", 1)),
            created_at=str(data.get("createdAt") or ""),
            updated_at=str(data.get("updatedAt") or ""),
            object_name=str(data.get("objectName") or ""),
            source=source,
            settings=settings,
            ops=list(data.get("ops") or []),
            state=dict(data.get("state") or {}),
        )

        source_bytes = None
        ext = (source.ext or "").lstrip(".")
        if ext:
            member = f"data/source.{ext}"
            if member in zf.namelist():
                source_bytes = zf.read(member)

    return project, source_bytes
