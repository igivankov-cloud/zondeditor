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


def _looks_like_k4(source_bytes: bytes, blocks_info: Sequence[object]) -> bool:
    # Heuristic 1: marker 1E 14 present (common for K4)
    try:
        if (source_bytes or b"").find(b"\x1E\x14") != -1:
            return True
    except Exception:
        pass
    # Heuristic 2: blocks_info bytes_per_row==9 (u16 qc/fs/incl layout)
    try:
        for blk in (blocks_info or []):
            bpr = getattr(blk, "bytes_per_row", None)
            if bpr is None and isinstance(blk, dict):
                bpr = blk.get("bytes_per_row")
            if int(bpr or 0) == 9:
                return True
    except Exception:
        pass
    return False


def prepare_geo_tests(tests: Sequence[TestData]) -> list[TestData]:
    prepared: list[TestData] = []
    for t in tests:
        try:
            d = list(getattr(t, "depth", []) or [])
            qc = list(getattr(t, "qc", []) or [])
            fs = list(getattr(t, "fs", []) or [])
            incl_src = getattr(t, "incl", None)
            incl = list(incl_src or []) if incl_src is not None else None

            rows = []
            n = max(len(d), len(qc), len(fs), len(incl or []))
            for k in range(n):
                dv = d[k] if k < len(d) else ""
                qv = qc[k] if k < len(qc) else ""
                fv = fs[k] if k < len(fs) else ""
                uv = (incl[k] if (incl is not None and k < len(incl)) else (0 if incl is not None else None))

                ds = str(dv).strip()
                if ds == "" and str(qv).strip() == "" and str(fv).strip() == "" and (str(uv).strip() == "" if incl is not None else True):
                    continue
                rows.append((dv, qv, fv, uv))
            prepared.append(TestData(
                tid=int(getattr(t, "tid", 0) or 0),
                dt=str(getattr(t, "dt", "") or ""),
                depth=[r[0] for r in rows],
                qc=[r[1] for r in rows],
                fs=[r[2] for r in rows],
                incl=([r[3] for r in rows] if incl is not None else None),
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
    prepared = prepare_geo_tests(tests)
    # K4: separate exporter (rebuild-based), does NOT affect K2
    if _looks_like_k4(source_bytes, blocks_info):
        from src.zondeditor.io.geo_writer_k4 import save_k4_geo_as
        save_k4_geo_as(out_path, prepared, source_bytes=source_bytes, blocks_info=blocks_info)
        return
    # K2: existing stable path
    save_geo_as(out_path, prepared, source_bytes=source_bytes, blocks_info=blocks_info)
