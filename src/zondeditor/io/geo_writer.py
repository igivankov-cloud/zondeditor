# src/zondeditor/io/geo_writer.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, Any, Sequence

from src.zondeditor.domain.models import TestData, TestSeries, series_to_testdata

_BYTES_PER_ROW_K2 = 2


def _to_byte(v: Any) -> int:
    try:
        x = int(float(str(v).strip().replace(",", ".")))
    except Exception:
        x = 0
    return max(0, min(255, x))


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return int(default)


def _get_attr(obj: Any, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _bcd(val: int) -> int:
    v = max(0, min(99, int(val)))
    return ((v // 10) << 4) | (v % 10)


def _parse_dt(dt_raw: str) -> datetime | None:
    s = str(dt_raw or "").strip()
    if not s:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%Y-%m-%d",
        "%d.%m.%Y",
    ):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def _patch_dt_in_block(buf: bytearray, dt_off: int, dt_raw: str) -> None:
    dt = _parse_dt(dt_raw)
    if dt is None:
        return
    if dt_off < 0 or dt_off + 6 > len(buf):
        return
    buf[dt_off + 0] = _bcd(dt.second)
    buf[dt_off + 1] = _bcd(dt.minute)
    buf[dt_off + 2] = _bcd(dt.hour)
    buf[dt_off + 3] = _bcd(dt.day)
    buf[dt_off + 4] = _bcd(dt.month)
    buf[dt_off + 5] = _bcd(dt.year % 100)


def _collect_qc_fs_payload(test: Any, rows: int) -> bytes:
    qc = list(getattr(test, "qc", []) or [])
    fs = list(getattr(test, "fs", []) or [])
    payload = bytearray()
    for i in range(rows):
        payload.append(_to_byte(qc[i]) if i < len(qc) else 0)
        payload.append(_to_byte(fs[i]) if i < len(fs) else 0)
    return bytes(payload)


def _patch_id_markers_all(buf: bytearray, tid: int) -> None:
    # FF FF [FF FF]? <id> 1E 0A|14
    n = len(buf)
    i = 0
    while i + 4 < n:
        if buf[i] == 0xFF and buf[i + 1] == 0xFF:
            # with extra FFFF
            if i + 6 < n and buf[i + 2] == 0xFF and buf[i + 3] == 0xFF and buf[i + 5] == 0x1E and buf[i + 6] in (0x0A, 0x14):
                buf[i + 4] = tid
                i += 7
                continue
            # normal
            if buf[i + 3] == 0x1E and buf[i + 4] in (0x0A, 0x14):
                buf[i + 2] = tid
                i += 5
                continue
        i += 1


def _extract_block_meta(original: bytes, block: Any) -> dict[str, Any]:
    hs = _to_int(_get_attr(block, "header_start", 0))
    he = _to_int(_get_attr(block, "header_end", hs))
    ds = _to_int(_get_attr(block, "data_start", 0))
    de = _to_int(_get_attr(block, "data_end", 0))
    ip = _to_int(_get_attr(block, "id_pos", hs + 2))
    dp = _to_int(_get_attr(block, "dt_pos", -1))
    oid = _to_int(_get_attr(block, "orig_id", 0))

    hs = max(0, min(len(original), hs))
    he = max(hs, min(len(original), he))
    ds = max(hs, min(len(original), ds))
    de = max(ds, min(len(original), de))
    ip = max(hs, min(len(original) - 1, ip)) if len(original) else 0

    raw = _get_attr(block, "raw_block_bytes", b"") or b""
    if not raw:
        raw = bytes(original[hs:de])

    return {
        "header_start": hs,
        "header_end": he,
        "data_start": ds,
        "data_end": de,
        "id_pos": ip,
        "dt_pos": dp,
        "orig_id": oid,
        "raw_block": bytes(raw),
        "id_off": ip - hs,
        "dt_off": dp - hs,
        "data_off": ds - hs,
        "data_len": de - ds,
    }


def _validate_block(meta: dict[str, Any], rows: int) -> None:
    block = meta["raw_block"]
    block_len = len(block)
    id_off = _to_int(meta["id_off"], -1)
    dt_off = _to_int(meta["dt_off"], -1)
    data_off = _to_int(meta["data_off"], -1)
    data_len = _to_int(meta["data_len"], -1)

    if not (0 <= id_off < block_len):
        raise ValueError(f"Invalid id_off={id_off} for block len={block_len}")
    if dt_off >= 0 and not (0 <= dt_off < block_len):
        raise ValueError(f"Invalid dt_off={dt_off} for block len={block_len}")
    if not (0 < data_off < block_len):
        raise ValueError(f"Invalid data_off={data_off} for block len={block_len}")
    if not (0 < data_len and data_off + data_len <= block_len):
        raise ValueError(f"Invalid data range off={data_off} len={data_len} block_len={block_len}")

    expected = max(0, int(rows)) * _BYTES_PER_ROW_K2
    if expected != data_len:
        raise ValueError(
            f"Invalid data_len={data_len} for rows={rows}; expected rows*{_BYTES_PER_ROW_K2}={expected}"
        )


def _match_template_blocks(original: bytes, blocks_info: Sequence[Any], prepared_tests: Sequence[Any]) -> list[tuple[dict[str, Any], Any]]:
    blocks_sorted = sorted([_extract_block_meta(original, b) for b in (blocks_info or [])], key=lambda b: b["header_start"])
    if not blocks_sorted:
        return []

    id_to_block: dict[int, dict[str, Any]] = {}
    for b in blocks_sorted:
        oid = _to_int(b.get("orig_id", 0), 0)
        if oid > 0 and oid not in id_to_block:
            id_to_block[oid] = b

    used: set[int] = set()
    out: list[tuple[dict[str, Any], Any]] = []
    for idx, test in enumerate(prepared_tests, start=1):
        candidate = None
        orig_id = _to_int(getattr(test, "orig_id", 0), 0)
        if orig_id > 0:
            c = id_to_block.get(orig_id)
            if c is not None and id(c) not in used:
                candidate = c

        if candidate is None:
            tb = getattr(test, "block", None)
            if tb is not None:
                ths = _to_int(_get_attr(tb, "header_start", -1), -1)
                for b in blocks_sorted:
                    if b["header_start"] == ths and id(b) not in used:
                        candidate = b
                        break

        if candidate is None:
            for b in blocks_sorted:
                if id(b) not in used:
                    candidate = b
                    break

        if candidate is None:
            continue
        used.add(id(candidate))
        out.append((candidate, test))
    return out


def build_k2_geo_from_template(original: bytes, blocks_info: Sequence[Any], prepared_tests: Sequence[Any]) -> bytes:
    """Build K2 GEO from immutable template bytes; patch only id/datetime/data region."""
    pairs = _match_template_blocks(original, blocks_info, prepared_tests)
    if not pairs:
        return bytes(original)

    first_hs = min(p[0]["header_start"] for p in pairs)
    last_de = max(p[0]["data_end"] for p in pairs)
    chunks: list[bytes] = [bytes(original[:first_hs])]

    for meta, test in pairs:
        raw = bytearray(meta["raw_block"])

        rows = max(len(list(getattr(test, "qc", []) or [])), len(list(getattr(test, "fs", []) or [])))
        _validate_block(meta, rows)

        tid = _to_int(getattr(test, "tid", 0) or getattr(test, "test_id", 0) or 1, 1)
        tid = max(1, min(255, tid))

        id_off = _to_int(meta["id_off"], -1)
        raw[id_off] = tid
        _patch_id_markers_all(raw, tid)

        _patch_dt_in_block(raw, _to_int(meta["dt_off"], -1), str(getattr(test, "dt", "") or ""))

        data_off = _to_int(meta["data_off"], 0)
        data_len = _to_int(meta["data_len"], 0)
        payload = _collect_qc_fs_payload(test, rows)
        if len(payload) != data_len:
            raise ValueError(f"Payload len={len(payload)} does not match template data_len={data_len}")
        raw[data_off:data_off + data_len] = payload
        chunks.append(bytes(raw))

    chunks.append(bytes(original[last_de:]))
    return b"".join(chunks)


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
