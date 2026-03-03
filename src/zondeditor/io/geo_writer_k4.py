# -*- coding: utf-8 -*-
"""
K4 GEO export (separate writer) — rebuild-based.

Goal:
- Robust K4 export when algorithm changes, rows change, tests are deleted/copy-created.
- Do NOT affect K2 export.

Approach:
- Parse template headers by marker FF FF <id> 1E 14 (and 1E 0A fallback).
- Rebuild output from prefix + blocks for EACH prepared/exported test (in provided order).
- For new tests (copied): clone a base 22-byte header and replace test_id in marker.
- Payload is generated in bytes_per_row=9 layout: qh ql 00 00 fh fl ul uh 00
  where hi/lo follow project convention: value = hi*100 + lo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence, Dict, List, Tuple

from src.zondeditor.domain.models import TestData, TestSeries, series_to_testdata


def _to_int(v: Any, default: int = 0) -> int:
    try:
        if v is None:
            return default
        s = str(v).strip().replace(",", ".")
        if s == "":
            return default
        return int(float(s))
    except Exception:
        return default


def _to_u16(v: Any) -> int:
    x = _to_int(v, 0)
    if x < 0:
        x = 0
    if x > 65535:
        x = 65535
    return x


def _u16_to_hl(x: int) -> Tuple[int, int]:
    hi = (x // 100) & 0xFF
    lo = x % 100
    return hi, lo


def _as_testdata_list(tests: Sequence[TestSeries | TestData | Any]) -> List[TestData]:
    out: List[TestData] = []
    for idx, t in enumerate(tests or [], start=1):
        if isinstance(t, TestData):
            td = t
        elif isinstance(t, TestSeries):
            td = series_to_testdata(t)
        else:
            td = TestData(
                tid=_to_int(getattr(t, "tid", None) or getattr(t, "test_id", None) or getattr(t, "id", None), idx),
                dt=str(getattr(t, "dt", "") or getattr(t, "date", "") or ""),
                depth=list(getattr(t, "depth", []) or []),
                qc=list(getattr(t, "qc", []) or getattr(t, "qc_raw", []) or []),
                fs=list(getattr(t, "fs", []) or getattr(t, "fs_raw", []) or []),
                incl=list(getattr(t, "incl", []) or getattr(t, "incl_raw", []) or []),
            )
        td.tid = max(1, min(255, _to_int(getattr(td, "tid", idx), idx)))
        out.append(td)
    return out


def _scan_template_headers(source: bytes) -> Tuple[bytes, Dict[int, bytes], int]:
    if not source:
        return b"", {}, 0x14

    starts: List[int] = []
    b = source
    for i in range(0, len(b) - 5):
        if b[i] == 0xFF and b[i+1] == 0xFF and b[i+3] == 0x1E and b[i+4] in (0x14, 0x0A):
            starts.append(i)
    if not starts:
        return source, {}, 0x14

    starts = sorted(set(starts))
    prefix = b[:starts[0]]
    headers: Dict[int, bytes] = {}
    marker_tail = 0x14
    for st in starts:
        tid = b[st+2]
        mt = b[st+4]
        if mt == 0x14:
            marker_tail = 0x14
        header = b[st: st+22]
        if len(header) < 22:
            header = header + b"\x00" * (22 - len(header))
        headers[int(tid)] = bytes(header)
    if marker_tail != 0x14:
        marker_tail = b[starts[0]+4]
    return prefix, headers, marker_tail


def _make_header(base: bytes, tid: int, marker_tail: int) -> bytes:
    h = bytearray(base[:22])
    h[0] = 0xFF
    h[1] = 0xFF
    h[2] = int(tid) & 0xFF
    h[3] = 0x1E
    h[4] = int(marker_tail) & 0xFF
    return bytes(h)


def _payload_9(qc: Sequence[Any], fs: Sequence[Any], incl: Sequence[Any]) -> bytes:
    qc_i = [_to_u16(x) for x in (qc or [])]
    fs_i = [_to_u16(x) for x in (fs or [])]
    u_i  = [_to_u16(x) for x in (incl or [])]
    n = max(len(qc_i), len(fs_i), len(u_i))
    if n == 0:
        return b""
    if len(qc_i) < n: qc_i += [0] * (n - len(qc_i))
    if len(fs_i) < n: fs_i += [0] * (n - len(fs_i))
    if len(u_i)  < n: u_i  += [0] * (n - len(u_i))

    out = bytearray()
    for i in range(n):
        qh, ql = _u16_to_hl(qc_i[i])
        fh, fl = _u16_to_hl(fs_i[i])
        uh, ul = _u16_to_hl(u_i[i])
        out.extend((qh, ql, 0, 0, fh, fl, ul, uh, 0))
    return bytes(out)


def build_k4_geo_bytes(source_bytes: bytes, tests: Sequence[TestSeries | TestData | Any]) -> bytes:
    tests_td = _as_testdata_list(tests)
    prefix, headers_by_tid, marker_tail = _scan_template_headers(source_bytes)
    if not headers_by_tid:
        return source_bytes

    base_tid = sorted(headers_by_tid.keys())[0]
    base_header = headers_by_tid[base_tid]

    out = bytearray()
    out += prefix

    for t in tests_td:
        tid = int(getattr(t, "tid", 0) or 0) & 0xFF
        if tid == 0:
            continue
        header = headers_by_tid.get(tid, base_header)
        header = _make_header(header, tid, marker_tail)
        payload = _payload_9(getattr(t, "qc", []), getattr(t, "fs", []), getattr(t, "incl", []) or [])
        out += header + payload

    return bytes(out)


def save_k4_geo_as(path: str | Path, tests: Sequence[TestSeries | TestData | Any], *, source_bytes: bytes) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(build_k4_geo_bytes(source_bytes, tests))
