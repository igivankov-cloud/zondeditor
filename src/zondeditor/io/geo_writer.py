# src/zondeditor/io/geo_writer.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Any, Sequence

from src.zondeditor.domain.models import TestData, TestSeries, series_to_testdata


def _to_byte(v: Any) -> int:
    try:
        x = int(float(str(v).strip().replace(",", ".")))
    except Exception:
        x = 0
    return max(0, min(255, x))


def _get_attr(obj: Any, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def build_k2_geo_from_template(original: bytes, blocks_info: Sequence[Any], prepared_tests: Sequence[Any]) -> bytes:
    """K2 GEO rebuild using existing template blocks_info (from monolith)."""
    out = bytearray(original)
    n_orig = len(original)

    n = min(len(blocks_info), len(prepared_tests))
    for i in range(n):
        bi = blocks_info[i]
        t = prepared_tests[i]

        ds = _get_attr(bi, "data_start", None)
        de = _get_attr(bi, "data_end", None)
        if ds is None or de is None:
            ds = _get_attr(bi, "dataStart", None)
            de = _get_attr(bi, "dataEnd", None)
        if ds is None or de is None:
            continue

        try:
            ds = int(ds)
            de = int(de)
        except Exception:
            continue

        ds = max(0, min(n_orig, ds))
        de = max(0, min(n_orig, de))
        if de < ds:
            continue

        qc = list(getattr(t, "qc", []) or [])
        fs = list(getattr(t, "fs", []) or [])
        m = max(len(qc), len(fs))

        payload = bytearray()
        for j in range(m):
            qv = _to_byte(qc[j]) if j < len(qc) else 0
            fv = _to_byte(fs[j]) if j < len(fs) else 0
            payload.append(qv)
            payload.append(fv)

        out = out[:ds] + payload + out[de:]
        n_orig = len(out)

    return bytes(out)


def _apply_test_ids_to_headers(geo_bytes: bytes, blocks_info: Sequence[Any], prepared_tests: Sequence[Any]) -> bytes:
    out = bytearray(geo_bytes)
    n = min(len(blocks_info), len(prepared_tests))
    for idx in range(n):
        bi = blocks_info[idx]
        t = prepared_tests[idx]
        id_pos = _get_attr(bi, "id_pos", None)
        if id_pos is None:
            continue
        try:
            pos = int(id_pos)
        except Exception:
            continue
        if not (0 <= pos < len(out)):
            continue
        tid = int(getattr(t, "tid", 0) or getattr(t, "test_id", 0) or (idx + 1))
        tid = min(255, max(1, tid))
        out[pos] = tid
    return bytes(out)


def _normalize_prepared_tests(tests: Sequence[TestSeries | TestData | Any]) -> list[TestData]:
    prepared: list[TestData] = []
    for idx, t in enumerate(tests, start=1):
        if isinstance(t, TestSeries):
            td = series_to_testdata(t)
        elif isinstance(t, TestData):
            td = t
        else:
            td = TestData(
                tid=int(getattr(t, "tid", 0) or getattr(t, "test_id", 0) or idx),
                dt=str(getattr(t, "dt", "") or ""),
                depth=list(getattr(t, "depth", []) or []),
                qc=list(getattr(t, "qc", []) or []),
                fs=list(getattr(t, "fs", []) or []),
                incl=list(getattr(t, "incl", []) or []) if getattr(t, "incl", None) is not None else None,
                marker=str(getattr(t, "marker", "") or ""),
                header_pos=str(getattr(t, "header_pos", "") or ""),
                orig_id=getattr(t, "orig_id", None),
                block=getattr(t, "block", None),
            )
        td.tid = min(255, max(1, int(getattr(td, "tid", idx) or idx)))
        prepared.append(td)
    return prepared


def save_geo_as(
    path: str | Path,
    tests: Sequence[TestSeries | TestData | Any],
    *,
    source_bytes: bytes,
    blocks_info: Sequence[Any],
) -> None:
    """Save GEO using template bytes and block metadata."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    prepared = _normalize_prepared_tests(tests)
    payload = build_k2_geo_from_template(source_bytes, blocks_info, prepared)
    payload = _apply_test_ids_to_headers(payload, blocks_info, prepared)
    out_path.write_bytes(payload)


def save_k2_geo_from_template(path_out: Path, original: bytes, blocks_info: Sequence[Any], prepared_tests: Sequence[Any]) -> None:
    path_out.parent.mkdir(parents=True, exist_ok=True)
    path_out.write_bytes(build_k2_geo_from_template(original, blocks_info, prepared_tests))


# Older writer API (roundtrip module) kept for tests
def build_k2_geo_bytes(original: bytes, tests: Iterable[Any]) -> bytes:
    """Rebuild K2 GEO bytes by replacing qc/fs payload using test.block mapping."""
    items = []
    for t in tests:
        b = getattr(t, "block", None)
        if b is None:
            continue
        try:
            ds = int(getattr(b, "data_start"))
            de = int(getattr(b, "data_end"))
            oi = int(getattr(b, "order_index", 0))
        except Exception:
            continue
        items.append((ds, de, oi, t))
    items.sort(key=lambda x: (x[0], x[2]))

    out = bytearray()
    cur = 0
    n_orig = len(original)

    for ds, de, _oi, t in items:
        ds = max(0, min(n_orig, ds))
        de = max(0, min(n_orig, de))
        if ds < cur:
            continue
        out += original[cur:ds]

        qc = list(getattr(t, "qc", []) or [])
        fs = list(getattr(t, "fs", []) or [])
        m = max(len(qc), len(fs))
        payload = bytearray()
        for i in range(m):
            payload.append(_to_byte(qc[i]) if i < len(qc) else 0)
            payload.append(_to_byte(fs[i]) if i < len(fs) else 0)

        out += payload
        cur = de

    out += original[cur:]
    return bytes(out)


def save_k2_geo(path_out: Path, original: bytes, tests: Iterable[Any]) -> None:
    path_out.parent.mkdir(parents=True, exist_ok=True)
    path_out.write_bytes(build_k2_geo_bytes(original, tests))
