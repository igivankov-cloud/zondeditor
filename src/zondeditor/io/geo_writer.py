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


def _build_qc_fs_payload(test: Any) -> bytes:
    qc = list(getattr(test, "qc", []) or [])
    fs = list(getattr(test, "fs", []) or [])
    m = max(len(qc), len(fs))
    payload = bytearray()
    for i in range(m):
        payload.append(_to_byte(qc[i]) if i < len(qc) else 0)
        payload.append(_to_byte(fs[i]) if i < len(fs) else 0)
    return bytes(payload)


def _block_span(block: Any) -> tuple[int, int, int, int, int]:
    hs = int(_get_attr(block, "header_start", 0))
    ds = int(_get_attr(block, "data_start", 0))
    de = int(_get_attr(block, "data_end", 0))
    dl = int(_get_attr(block, "data_len", max(0, de - ds)) or 0)
    payload_end = min(de, ds + max(0, dl))
    ip = int(_get_attr(block, "id_pos", hs + 2))
    return hs, ds, de, payload_end, ip


def _match_template_blocks(original: bytes, blocks_info: Sequence[Any], prepared_tests: Sequence[Any]) -> list[tuple[Any, Any]]:
    blocks_sorted = sorted(list(blocks_info or []), key=lambda b: _block_span(b)[0])
    if not blocks_sorted:
        return []

    block_by_id: dict[int, list[Any]] = {}
    for b in blocks_sorted:
        try:
            _, _, _, _, ip = _block_span(b)
            bid = int(original[ip]) if 0 <= ip < len(original) else 0
        except Exception:
            bid = 0
        block_by_id.setdefault(bid, []).append(b)

    used: set[int] = set()
    matched: list[tuple[Any, Any]] = []

    for idx, t in enumerate(prepared_tests, start=1):
        candidate = None

        tb = getattr(t, "block", None)
        if tb is not None:
            ths = _get_attr(tb, "header_start", None)
            if ths is not None:
                for b in blocks_sorted:
                    if id(b) in used:
                        continue
                    if int(_get_attr(b, "header_start", -1)) == int(ths):
                        candidate = b
                        break

        if candidate is None:
            for key in (getattr(t, "orig_id", None), getattr(t, "tid", None), idx):
                try:
                    tid = int(key or 0)
                except Exception:
                    continue
                if tid <= 0:
                    continue
                for b in block_by_id.get(tid, []):
                    if id(b) not in used:
                        candidate = b
                        break
                if candidate is not None:
                    break

        if candidate is None:
            for b in blocks_sorted:
                if id(b) not in used:
                    candidate = b
                    break

        if candidate is None:
            continue
        used.add(id(candidate))
        matched.append((candidate, t))

    return matched


def build_k2_geo_from_template(original: bytes, blocks_info: Sequence[Any], prepared_tests: Sequence[Any]) -> bytes:
    """Build K2 GEO using selected tests only (deleted/hidden tests are omitted)."""
    pairs = _match_template_blocks(original, blocks_info, prepared_tests)
    if not pairs:
        return bytes(original)

    all_blocks = sorted(list(blocks_info or []), key=lambda b: _block_span(b)[0])
    first_hs, *_ = _block_span(all_blocks[0])
    _, _, last_de, _, _ = _block_span(all_blocks[-1])

    chunks = [original[:first_hs]]
    for block, test in pairs:
        hs, ds, de, payload_end, ip = _block_span(block)
        hs = max(0, min(len(original), hs))
        ds = max(hs, min(len(original), ds))
        de = max(ds, min(len(original), de))
        seg = bytearray(original[hs:de])

        rel_id = ip - hs
        if 0 <= rel_id < len(seg):
            tid = int(getattr(test, "tid", 0) or getattr(test, "test_id", 0) or 1)
            seg[rel_id] = min(255, max(1, tid))

        rel_ds = ds - hs
        rel_de = max(rel_ds, payload_end - hs)
        payload = _build_qc_fs_payload(test)
        seg = seg[:rel_ds] + payload + seg[rel_de:]
        chunks.append(bytes(seg))

    chunks.append(original[max(0, min(len(original), last_de)):])
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
            dl = int(getattr(b, "data_len", max(0, de - ds)) or 0)
            pe = min(de, ds + max(0, dl))
            oi = int(getattr(b, "order_index", 0))
        except Exception:
            continue
        items.append((ds, pe, de, oi, t))
    items.sort(key=lambda x: (x[0], x[3]))

    out = bytearray()
    cur = 0
    n_orig = len(original)

    for ds, pe, de, _oi, t in items:
        ds = max(0, min(n_orig, ds))
        pe = max(ds, min(n_orig, pe))
        de = max(pe, min(n_orig, de))
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
        out += original[pe:de]
        cur = de

    out += original[cur:]
    return bytes(out)


def save_k2_geo(path_out: Path, original: bytes, tests: Iterable[Any]) -> None:
    path_out.parent.mkdir(parents=True, exist_ok=True)
    path_out.write_bytes(build_k2_geo_bytes(original, tests))
