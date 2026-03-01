# src/zondeditor/io/k2_reader.py
from __future__ import annotations

import re
from typing import Any, Optional

# Matches GeoExplorer headers (FF FF <id> 1E 0A or 1E 14, sometimes with extra FF FF)
HEADER_RE = re.compile(b"\xFF\xFF(?:\xFF\xFF)?(.)\x1E(\x0A|\x14)")

def _bcd_to_int(b: int) -> int:
    hi, lo = (b >> 4) & 0xF, b & 0xF
    if hi > 9 or lo > 9:
        return -1
    return hi * 10 + lo

def _parse_datetime_bcd(data: bytes, pos: int) -> Optional[str]:
    # Expected order (as used in monolith): ss mm HH DD MO YY
    if pos + 6 > len(data):
        return None
    ss = _bcd_to_int(data[pos + 0])
    mm = _bcd_to_int(data[pos + 1])
    HH = _bcd_to_int(data[pos + 2])
    DD = _bcd_to_int(data[pos + 3])
    MO = _bcd_to_int(data[pos + 4])
    YY = _bcd_to_int(data[pos + 5])
    if -1 in (ss, mm, HH, DD, MO, YY):
        return None
    if not (0 <= ss <= 59 and 0 <= mm <= 59 and 0 <= HH <= 23 and 1 <= DD <= 31 and 1 <= MO <= 12):
        return None
    year = 2000 + YY
    return f"{year:04d}-{MO:02d}-{DD:02d} {HH:02d}:{mm:02d}:{ss:02d}"

def parse_geo_with_blocks(
    data: bytes,
    TestDataCls: Any,
    GeoBlockInfoCls: Any,
):
    """K2 GEO parser extracted from monolith.

    Returns (tests, meta_rows) exactly like the monolith version.
    UI types are injected (TestDataCls, GeoBlockInfoCls) to keep this module tkinter-free.
    """
    """Parse geo and return tests + meta rows with block infos for save-back."""
    headers = []
    for m in HEADER_RE.finditer(data):
        hs = m.start()
        # detect id position depending on optional extra FF FF
        # pattern: FF FF [FF FF]? id 1E marker
        # if there is extra FF FF, id byte is at hs+4, else hs+2
        id_pos = hs + (4 if data[hs:hs+4] == b"\xFF\xFF\xFF\xFF" else 2)
        test_id = data[id_pos]
        marker_pos = id_pos + 2  # id + 1E
        marker = data[marker_pos]
        header_end = m.end()
        dt_pos = header_end  # after marker
        dt = _parse_datetime_bcd(data, dt_pos)
        headers.append((hs, header_end, id_pos, dt_pos, test_id, marker))

    if not headers:
        raise ValueError(
            "Не найдены заголовки опытов.\n"
            "Ожидались маркеры: FF FF <id> 1E 0A или FF FF <id> 1E 14."
        )

    tests_out: list[TestData] = []
    meta_rows: list[dict] = []

    for i, (hs, header_end, id_pos, dt_pos, test_id, marker) in enumerate(headers):
        second = data.find(b"\xFF\xFF", header_end)
        if second == -1:
            continue
        data_start = second + 2
        data_end = headers[i + 1][0] if i + 1 < len(headers) else len(data)
        if data_end <= hs:
            continue
        block = data[data_start:data_end]
        if len(block) < 2:
            pairs = []
        else:
            if len(block) % 2 == 1:
                block = block[:-1]
            pairs = [(block[j], block[j + 1]) for j in range(0, len(block), 2)]

        bid = GeoBlockInfoCls(
            order_index=i,
            header_start=hs,
            header_end=header_end,
            id_pos=id_pos,
            dt_pos=dt_pos,
            data_start=data_start,
            data_end=data_end,
            marker_byte=marker,
            orig_id=int(test_id),
            raw_block_bytes=bytes(data[hs:data_end]),
        )

        dt_str = _parse_datetime_bcd(data, dt_pos) or ""
        t = TestDataCls(
            tid=int(test_id),
            dt=dt_str,
            depth=[],
            qc=[str(int(p[0])) for p in pairs],
            fs=[str(int(p[1])) for p in pairs],
            marker=f"0x{marker:02X}",
            header_pos=str(hs),
            orig_id=int(test_id),
            block=bid,
        )
        tests_out.append(t)
        meta_rows.append({
            "test_id": int(test_id),
            "datetime": dt_str,
            "marker": f"0x{marker:02X}",
            "header_pos": hs,
            "points": len(pairs),
        })

    if not tests_out:
        raise ValueError("Опытов не извлечено. Возможно другой вариант кодирования данных в GEO.")
    return tests_out, meta_rows




# ---------------- UI helpers: validation + calendar ----------------

