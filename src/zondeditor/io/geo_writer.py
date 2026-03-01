from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

from src.zondeditor.domain.models import TestData, TestSeries, series_to_testdata


def _to_byte(v: Any) -> int:
    try:
        x = int(float(str(v).strip().replace(",", ".")))
    except Exception:
        x = 0
    return max(0, min(255, x))


def _to_u16_le(v: Any) -> tuple[int, int]:
    try:
        x = int(float(str(v).strip().replace(",", ".")))
    except Exception:
        x = 0
    x = max(0, min(65535, x))
    return (x // 100) & 0xFF, x % 100


def _get_attr(obj: Any, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


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
        td.tid = min(65535, max(1, int(getattr(td, "tid", idx) or idx)))
        prepared.append(td)
    return prepared


def _block_payload_bounds(block: Any, n_bytes: int) -> tuple[int, int, int]:
    ds = int(_get_attr(block, "data_start", 0) or 0)
    de = int(_get_attr(block, "data_end", ds) or ds)
    dl = int(_get_attr(block, "data_len", max(0, de - ds)) or 0)
    bpr = int(_get_attr(block, "bytes_per_row", 2) or 2)

    if bpr <= 0:
        raise ValueError("bytes_per_row must be > 0")
    if dl < 0:
        raise ValueError("data_len must be >= 0")
    if dl % bpr != 0:
        raise ValueError(f"data_len ({dl}) is not divisible by bytes_per_row ({bpr})")
    if not (0 <= ds <= n_bytes):
        raise ValueError(f"data_start out of range: {ds}")
    if not (0 <= de <= n_bytes):
        raise ValueError(f"data_end out of range: {de}")

    pe = ds + dl
    if pe > de:
        raise ValueError(f"payload range [{ds}:{pe}) exceeds block end {de}")
    return ds, pe, bpr


def _payload_from_test(test: Any, *, bytes_per_row: int, rows: int) -> bytes:
    qc = list(getattr(test, "qc", []) or [])
    fs = list(getattr(test, "fs", []) or [])
    incl = list(getattr(test, "incl", []) or []) if getattr(test, "incl", None) is not None else []

    if max(len(qc), len(fs), len(incl)) != rows:
        raise ValueError(
            f"rows mismatch for test id={getattr(test, 'tid', '?')}: expected {rows}, got "
            f"qc={len(qc)} fs={len(fs)} incl={len(incl)}"
        )

    payload = bytearray()
    if bytes_per_row == 2:
        for i in range(rows):
            payload.append(_to_byte(qc[i]))
            payload.append(_to_byte(fs[i]))
        return bytes(payload)

    if bytes_per_row == 9:
        for i in range(rows):
            qh, ql = _to_u16_le(qc[i])
            fh, fl = _to_u16_le(fs[i])
            uh, ul = _to_u16_le(incl[i] if i < len(incl) else 0)
            payload.extend((qh, ql, 0, 0, fh, fl, ul, uh, 0))
        return bytes(payload)

    raise ValueError(f"Unsupported bytes_per_row: {bytes_per_row}")




def _decode_payload_values(payload: bytes, bytes_per_row: int) -> tuple[list[int], list[int], list[int]]:
    qc: list[int] = []
    fs: list[int] = []
    incl: list[int] = []
    if bytes_per_row == 2:
        for i in range(0, len(payload), 2):
            qc.append(payload[i])
            fs.append(payload[i + 1])
            incl.append(0)
        return qc, fs, incl
    if bytes_per_row == 9:
        for i in range(0, len(payload), 9):
            row = payload[i:i + 9]
            qc.append(row[0] * 100 + row[1])
            fs.append(row[4] * 100 + row[5])
            incl.append(row[6] + 256 * row[7])
        return qc, fs, incl
    raise ValueError(f"Unsupported bytes_per_row: {bytes_per_row}")


def _is_no_change_export(original: bytes, blocks_info: Sequence[Any], prepared_tests: Sequence[Any]) -> bool:
    if len(prepared_tests) != len(list(blocks_info or [])):
        return False

    by_span, by_orig = _build_test_block_map(prepared_tests)
    for block in blocks_info or []:
        span = _resolve_block_key(block)
        t = by_span.get(span)
        if t is None:
            oid = int(_get_attr(block, "orig_test_id", 0) or 0)
            if oid > 0:
                t = by_orig.get(oid)
        if t is None:
            return False

        ds, pe, bpr = _block_payload_bounds(block, len(original))
        raw = original[ds:pe]
        qc0, fs0, incl0 = _decode_payload_values(raw, bpr)

        try:
            qc1 = [int(float(str(v).replace(",", "."))) for v in (getattr(t, "qc", []) or [])]
            fs1 = [int(float(str(v).replace(",", "."))) for v in (getattr(t, "fs", []) or [])]
            incl_src = (getattr(t, "incl", []) or []) if getattr(t, "incl", None) is not None else []
            incl1 = [int(float(str(v).replace(",", "."))) for v in incl_src]
        except Exception:
            return False

        if bpr == 2:
            incl1 = [0] * len(qc1)
        if qc0 != qc1 or fs0 != fs1 or incl0 != incl1:
            return False

    return True


def _resolve_block_key(block: Any) -> tuple[int, int]:
    start = int(_get_attr(block, "raw_block_start", _get_attr(block, "header_start", 0)) or 0)
    end = int(_get_attr(block, "raw_block_end", _get_attr(block, "data_end", 0)) or 0)
    return start, end


def _build_test_block_map(prepared_tests: Sequence[Any]) -> dict[tuple[int, int], Any]:
    by_span: dict[tuple[int, int], Any] = {}
    by_orig: dict[int, Any] = {}

    for t in prepared_tests:
        tb = getattr(t, "block", None)
        if tb is not None:
            by_span[_resolve_block_key(tb)] = t

        try:
            oid = int(getattr(t, "orig_id", 0) or 0)
        except Exception:
            oid = 0
        if oid > 0 and oid not in by_orig:
            by_orig[oid] = t

    return by_span, by_orig


def build_geo_from_template(original: bytes, blocks_info: Sequence[Any], prepared_tests: Sequence[Any]) -> bytes:
    if not prepared_tests:
        return bytes(original)

    out = bytearray(original)
    by_span, by_orig = _build_test_block_map(prepared_tests)

    for block in blocks_info or []:
        span = _resolve_block_key(block)
        t = by_span.get(span)
        if t is None:
            try:
                oid = int(_get_attr(block, "orig_test_id", 0) or 0)
            except Exception:
                oid = 0
            if oid > 0:
                t = by_orig.get(oid)
        if t is None:
            continue  # excluded/hidden/deleted: keep original bytes untouched

        ds, pe, bpr = _block_payload_bounds(block, len(original))
        rows = (pe - ds) // bpr
        payload = _payload_from_test(t, bytes_per_row=bpr, rows=rows)
        if len(payload) != (pe - ds):
            raise ValueError("Payload size mismatch for template replacement")
        out[ds:pe] = payload

    return bytes(out)


def build_k2_geo_from_template(original: bytes, blocks_info: Sequence[Any], prepared_tests: Sequence[Any]) -> bytes:
    return build_geo_from_template(original, blocks_info, prepared_tests)


def save_geo_as(
    path: str | Path,
    tests: Sequence[TestSeries | TestData | Any],
    *,
    source_bytes: bytes,
    blocks_info: Sequence[Any],
) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    prepared = _normalize_prepared_tests(tests)
    if not prepared:
        out_path.write_bytes(source_bytes)
        return

    if _is_no_change_export(source_bytes, blocks_info, prepared):
        out_path.write_bytes(source_bytes)
        return

    payload = build_geo_from_template(source_bytes, blocks_info, prepared)
    out_path.write_bytes(payload)


def save_k2_geo_from_template(path_out: Path, original: bytes, blocks_info: Sequence[Any], prepared_tests: Sequence[Any]) -> None:
    path_out.parent.mkdir(parents=True, exist_ok=True)
    path_out.write_bytes(build_geo_from_template(original, blocks_info, prepared_tests))


# Older writer API (roundtrip module) kept for tests

def build_k2_geo_bytes(original: bytes, tests: Iterable[Any]) -> bytes:
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
