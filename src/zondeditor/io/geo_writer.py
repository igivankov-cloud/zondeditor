# src/zondeditor/io/geo_writer.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Any

def _to_byte(v: Any) -> int:
    try:
        x = int(float(str(v).strip().replace(",", ".")))
    except Exception:
        x = 0
    return max(0, min(255, x))

def build_k2_geo_bytes(original: bytes, tests: Iterable[Any]) -> bytes:
    """Rebuild K2 GEO bytes by replacing qc/fs payload of each block.

    Requirements:
    - Each test should have .block with fields: header_start, data_start, data_end, order_index
      (as produced by src.zondeditor.io.k2_reader.parse_geo_with_blocks with domain.GeoBlockInfo)
    - Writes qc/fs pairs as bytes in the [data_start:data_end) region for each block.
    - File length may change if point count changes (we rebuild sequentially).
    """
    items = []
    for t in tests:
        b = getattr(t, "block", None)
        if b is None:
            continue
        try:
            hs = int(getattr(b, "header_start"))
            ds = int(getattr(b, "data_start"))
            de = int(getattr(b, "data_end"))
            oi = int(getattr(b, "order_index", 0))
        except Exception:
            continue
        items.append((hs, ds, de, oi, t))
    items.sort(key=lambda x: (x[0], x[3]))

    out = bytearray()
    cur = 0
    n_orig = len(original)

    for hs, ds, de, oi, t in items:
        ds = max(0, min(n_orig, ds))
        de = max(0, min(n_orig, de))
        if ds < cur:
            # overlapping/invalid block mapping - keep original untouched
            continue
        # copy prefix
        out += original[cur:ds]

        qc = list(getattr(t, "qc", []) or [])
        fs = list(getattr(t, "fs", []) or [])
        n = max(len(qc), len(fs))
        payload = bytearray()
        for i in range(n):
            qv = _to_byte(qc[i]) if i < len(qc) else 0
            fv = _to_byte(fs[i]) if i < len(fs) else 0
            payload.append(qv)
            payload.append(fv)

        out += payload
        cur = de

    out += original[cur:]
    return bytes(out)

def save_k2_geo(path_out: Path, original: bytes, tests: Iterable[Any]) -> None:
    """Write rebuilt K2 GEO to disk."""
    path_out.parent.mkdir(parents=True, exist_ok=True)
    path_out.write_bytes(build_k2_geo_bytes(original, tests))
