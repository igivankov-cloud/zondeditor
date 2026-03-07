from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Sequence

from src.zondeditor.domain.models import TestData
from src.zondeditor.io.geo_writer import save_geo_as


def _sanitize_ascii_stem(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_only).strip("._-")
    return stem or "geo_export"


def bundle_geo_filename(*, source_geo_path: str | Path | None, fallback_name: str = "geo_export") -> str:
    src = Path(source_geo_path).stem if source_geo_path else ""
    stem = _sanitize_ascii_stem(src) if src else _sanitize_ascii_stem(fallback_name)
    return f"{stem}.GEO"


def prepare_geo_tests(tests: Sequence[TestData]) -> list[TestData]:
    prepared: list[TestData] = []
    for t in tests:
        try:
            d = list(getattr(t, "depth", []) or [])
            qc = list(getattr(t, "qc", []) or [])
            fs = list(getattr(t, "fs", []) or [])
            rows = []
            n = max(len(d), len(qc), len(fs))
            for k in range(n):
                dv = d[k] if k < len(d) else ""
                qv = qc[k] if k < len(qc) else ""
                fv = fs[k] if k < len(fs) else ""
                ds = str(dv).strip()
                if ds == "" and str(qv).strip() == "" and str(fv).strip() == "":
                    continue
                rows.append((dv, qv, fv))
            prepared.append(TestData(
                tid=int(getattr(t, "tid", 0) or 0),
                dt=str(getattr(t, "dt", "") or ""),
                depth=[r[0] for r in rows],
                qc=[r[1] for r in rows],
                fs=[r[2] for r in rows],
                marker=str(getattr(t, "marker", "") or ""),
                header_pos=str(getattr(t, "header_pos", "") or ""),
                orig_id=getattr(t, "orig_id", None),
                block=getattr(t, "block", None),
            ))
        except Exception:
            prepared.append(t)
    return prepared


def export_bundle_geo(
    out_path: Path,
    *,
    tests: Sequence[TestData],
    source_bytes: bytes,
    blocks_info: Sequence[object],
) -> None:
    save_geo_as(out_path, prepare_geo_tests(tests), source_bytes=source_bytes, blocks_info=blocks_info)

