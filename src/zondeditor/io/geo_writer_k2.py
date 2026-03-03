# -*- coding: utf-8 -*-
"""
K2 GEO export (separate writer) — rebuild-based.

Purpose:
- Make K2 export independent from K4 and from fragile "template replacement".
- Supports:
  * edited values visible in GeoExplorer
  * new copied tests included (clone base 22-byte header, replace test_id in marker)
  * deleted/disabled/hidden tests excluded (export ONLY provided prepared tests)
  * tails preserved (variable row count)

Marker:
- Typically FF FF <id> 1E 0A for K2 blocks (we also accept 1E 14 just in case).
Payload:
- 2 bytes per row: [qc_byte, fs_byte]
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


def _to_byte(v: Any) -> int:
    x = _to_int(v, 0)
    if x < 0:
        x = 0
    if x > 255:
        x = 255
    return x


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
            )
        td.tid = max(1, min(255, _to_int(getattr(td, "tid", idx), idx)))
        out.append(td)
    return out


def _scan_template_headers(source: bytes) -> Tuple[bytes, Dict[int, bytes], int]:
    """
    Returns: prefix, headers_by_tid, marker_tail (0x0A preferred for K2).
    Accept markers:
      FF FF <id> 1E 0A
      FF FF <id> 1E 14  (rare but accept)
    """
    if not source:
        return b"", {}, 0x0A

    starts: List[int] = []
    b = source
    for i in range(0, len(b) - 5):
        if b[i] == 0xFF and b[i+1] == 0xFF and b[i+3] == 0x1E and b[i+4] in (0x0A, 0x14):
            starts.append(i)
    if not starts:
        return source, {}, 0x0A

    starts = sorted(set(starts))
    prefix = b[:starts[0]]
    headers: Dict[int, bytes] = {}
    marker_tail = 0x0A
    for st in starts:
        tid = b[st+2]
        mt = b[st+4]
        if mt == 0x0A:
            marker_tail = 0x0A
        header = b[st: st+22]
        if len(header) < 22:
            header = header + b"\x00" * (22 - len(header))
        headers[int(tid)] = bytes(header)
    if marker_tail != 0x0A:
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


def _payload_2(qc: Sequence[Any], fs: Sequence[Any]) -> bytes:
    qc_i = [_to_byte(x) for x in (qc or [])]
    fs_i = [_to_byte(x) for x in (fs or [])]
    n = max(len(qc_i), len(fs_i))
    if n == 0:
        return b""
    if len(qc_i) < n: qc_i += [0] * (n - len(qc_i))
    if len(fs_i) < n: fs_i += [0] * (n - len(fs_i))
    out = bytearray()
    for i in range(n):
        out.append(qc_i[i] & 0xFF)
        out.append(fs_i[i] & 0xFF)
    return bytes(out)


def build_k2_geo_bytes(source_bytes: bytes, tests: Sequence[TestSeries | TestData | Any]) -> bytes:
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
        payload = _payload_2(getattr(t, "qc", []), getattr(t, "fs", []))
        out += header + payload

    return bytes(out)


def save_k2_geo_as(path: str | Path, tests: Sequence[TestSeries | TestData | Any], *, source_bytes: bytes) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(build_k2_geo_bytes(source_bytes, tests))
