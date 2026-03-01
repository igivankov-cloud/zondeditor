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

    for idx, p in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(data)
        block = data[p:end]

        try:
            exp = struct.unpack_from("<H", block, 2)[0]
        except Exception:
            continue

        # Skip service/internal records
        if exp > 300:
            continue

        marker = block[4:8]
        start_m = marker[0] / 100.0
        step_m = marker[1] / 1000.0

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
            t = TestDataCls(int(exp), ts, [], [], [], marker.hex(" "), str(p))
            t.incl = []
            if GeoBlockInfoCls is not None:
                t.block = GeoBlockInfoCls(
                    order_index=idx,
                    header_start=p,
                    header_end=p + 13,
                    id_pos=p + 2,
                    dt_pos=p + 8,
                    data_start=end,
                    data_end=end,
                    marker_byte=block[4] if len(block) > 4 else 0,
                    data_len=0,
                    bytes_per_row=9,
                    layout="K4_QC_FS_U",
                )
            tests.append(t)
            continue

        payload_start = p + k + len(K4_SIG)
        payload = block[k + len(K4_SIG):]
        n = len(payload) // 9
        payload_len = n * 9

        qc: list[str] = []
        fs: list[str] = []
        U: list[str] = []
        for i in range(n):
            b = payload[i*9:(i+1)*9]
            qc.append(str(b[0] * 100 + b[1]))
            fs.append(str(b[4] * 100 + b[5]))
            U.append(str(b[6] + 256 * b[7]))

        depth = [f"{(start_m + i * step_m):.2f}".replace(".", ",") for i in range(n)]

        t = TestDataCls(int(exp), ts, depth, qc, fs, marker.hex(" "), str(p))
        t.incl = U
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
            )
        tests.append(t)

    try:
        tests.sort(key=lambda t: (t.dt, t.tid))
    except Exception:
        pass
    return tests
