# src/zondeditor/io/k4_reader.py
from __future__ import annotations

import datetime
import struct
from typing import Any, List

# Signature used to detect K4 payload in GEO
K4_SIG = b"\x01\x02\x03\xFF\xFF"

def _k4_bcd_to_int(x: int) -> int:
    return (x >> 4) * 10 + (x & 0x0F)

def detect_geo_kind(data: bytes) -> str:
    return "K4" if (K4_SIG in data) else "K2"

def _k4_looks_like_start(buf: bytes, p: int) -> bool:
    if p + 80 > len(buf):
        return False
    if buf[p:p+2] != b"\xFF\xFF":
        return False

    exp = struct.unpack_from("<H", buf, p + 2)[0]
    if exp == 0 or exp == 0xFFFF or exp > 5000:
        return False

    step_mm = buf[p + 5]
    if not (1 <= step_mm <= 200):
        return False

    # BCD datetime sanity
    minute = _k4_bcd_to_int(buf[p + 8])
    hour = _k4_bcd_to_int(buf[p + 9])
    day = _k4_bcd_to_int(buf[p + 10])
    month = _k4_bcd_to_int(buf[p + 11])
    year2 = _k4_bcd_to_int(buf[p + 12])
    if not (0 <= minute <= 59 and 0 <= hour <= 23 and 1 <= day <= 31 and 1 <= month <= 12 and 0 <= year2 <= 99):
        return False

    return (K4_SIG in buf[p:p+80])

def _k4_find_starts(buf: bytes) -> List[int]:
    starts: List[int] = []
    i = 0
    while True:
        j = buf.find(b"\xFF\xFF", i)
        if j < 0:
            break
        if _k4_looks_like_start(buf, j):
            starts.append(j)
        i = j + 2
    return sorted(starts)

def parse_k4_geo_strict(data: bytes, TestDataCls: Any, GeoBlockInfoCls: Any | None = None) -> list:
    """Parse K4 GEO into list[TestDataCls].

    TestDataCls must accept:
      (tid:int, dt:str, depth:list[str], qc:list[str], fs:list[str], marker:str, header_pos:str)
    and returned object must allow attribute .incl (U-column list[str]).
    """
    starts = _k4_find_starts(data)
    tests: list = []
    min_rows = 10

    for idx, p in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(data)
        block = data[p:end]

        try:
            exp = struct.unpack_from("<H", block, 2)[0]
        except Exception:
            continue

        if exp == 0 or exp == 0xFFFF or exp > 300:
            continue

        marker = block[4:8]
        start_m = marker[0] / 100.0
        step_m = block[5] / 1000.0 if len(block) > 5 else 0.0

        # datetime
        try:
            minute = _k4_bcd_to_int(block[8])
            hour = _k4_bcd_to_int(block[9])
            day = _k4_bcd_to_int(block[10])
            month = _k4_bcd_to_int(block[11])
            year = 2000 + _k4_bcd_to_int(block[12])
            ts = datetime.datetime(year, month, day, hour, minute).strftime("%d.%m.%Y %H:%M")
        except Exception:
            ts = ""

        k = block.find(K4_SIG)
        if k < 0:
            continue

        payload_start = p + k + len(K4_SIG)
        payload_len = end - payload_start
        if payload_len <= 0 or payload_len % 9 != 0:
            continue

        payload = block[k + len(K4_SIG):]
        n = payload_len // 9
        if n < min_rows:
            continue

        qc: list[str] = []
        fs: list[str] = []
        U: list[str] = []
        for i in range(n):
            b = payload[i*9:(i+1)*9]
            qc.append(str(b[0] * 100 + b[1]))
            fs.append(str(b[4] * 100 + b[5]))
            U.append(str(b[6] + 256 * b[7]))

        depth = [f"{(start_m + i * step_m):.2f}".replace(".", ",") for i in range(n)]

        t = TestDataCls(
            tid=int(exp),
            dt=ts,
            depth=depth,
            qc=qc,
            fs=fs,
            incl=U,
            marker=marker.hex(" "),
            header_pos=str(p),
            orig_id=int(exp),
        )
        if GeoBlockInfoCls is not None:
            t.block = GeoBlockInfoCls(
                order_index=idx,
                header_start=p,
                header_end=p + 13,
                id_pos=p + 2,
                dt_pos=p + 8,
                data_start=payload_start,
                data_end=end,
                marker_byte=block[4] if len(block) > 4 else 0,
                data_len=payload_len,
                bytes_per_row=9,
                layout="K4_QC_FS_U",
                raw_block_start=p,
                raw_block_end=end,
                data_off=max(0, payload_start - p),
                orig_test_id=int(exp),
            )
        tests.append(t)

    try:
        tests.sort(key=lambda t: (t.dt, t.tid))
    except Exception:
        pass
    return tests
