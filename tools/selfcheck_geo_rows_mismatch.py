#!/usr/bin/env python3
from __future__ import annotations

from collections import namedtuple
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.zondeditor.domain.models import TestData
from src.zondeditor.io.geo_writer import build_geo_from_template


Block = namedtuple(
    "Block",
    [
        "raw_block_start",
        "raw_block_end",
        "data_start",
        "data_end",
        "data_len",
        "bytes_per_row",
        "rows",
        "orig_test_id",
    ],
)


def main() -> int:
    n_expected = 107
    n_actual = 109
    bpr = 9
    ds = 16
    payload_len = n_actual * bpr
    de = ds + payload_len
    original = bytes([0] * (de + 32))

    blocks = [
        Block(
            raw_block_start=0,
            raw_block_end=de + 8,
            data_start=ds,
            data_end=de,
            data_len=payload_len,
            bytes_per_row=bpr,
            rows=n_expected,
            orig_test_id=0,
        )
    ]

    test = TestData(
        tid=1,
        dt="",
        depth=[0] * n_actual,
        qc=list(range(n_actual)),
        fs=list(range(n_actual)),
        incl=[],
        block=blocks[0],
    )

    out = build_geo_from_template(original, blocks, [test])
    if len(out) != len(original):
        raise AssertionError("Output size changed")
    if blocks[0].rows != n_actual:
        raise AssertionError(f"rows not updated: got {blocks[0].rows}, expected {n_actual}")

    payload = out[ds:de]
    for i in range(n_actual):
        row = payload[i * bpr:(i + 1) * bpr]
        if row[6] != 0 or row[7] != 0:
            raise AssertionError(f"incl bytes must be zero for empty incl, row={i}")

    print("[OK] GEO rows mismatch selfcheck passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
