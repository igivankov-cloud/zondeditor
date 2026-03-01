#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

HEADER_RE = re.compile(b"\xFF\xFF(?:\xFF\xFF)?(.)\x1E(\x0A|\x14)")
K4_SIG = b"\x01\x02\x03\xFF\xFF"


@dataclass
class BlockDiag:
    index: int
    start: int
    end: int
    length: int
    signatures: list[tuple[str, int]]
    test_id: int | None
    test_id_how: str
    id_off: int | None
    rows: int | None
    rows_how: str
    rows_off: int | None
    step: float | None
    step_how: str
    step_off: int | None
    data_off: int | None
    data_len: int | None
    bytes_per_row: int | None
    first_rows: list[tuple[str, str, str, str]]
    warnings: list[str]


def _k4_bcd_to_int(x: int) -> int:
    return (x >> 4) * 10 + (x & 0x0F)


def _is_bcd_datetime(buf: bytes, dt_off: int) -> bool:
    if dt_off + 6 > len(buf):
        return False
    mm = _k4_bcd_to_int(buf[dt_off + 1])
    hh = _k4_bcd_to_int(buf[dt_off + 2])
    dd = _k4_bcd_to_int(buf[dt_off + 3])
    mo = _k4_bcd_to_int(buf[dt_off + 4])
    yy = _k4_bcd_to_int(buf[dt_off + 5])
    return 0 <= mm <= 59 and 0 <= hh <= 23 and 1 <= dd <= 31 and 1 <= mo <= 12 and 0 <= yy <= 99


def _detect_k4(data: bytes) -> bool:
    return K4_SIG in data


def _slice_preview(rows: Iterable[tuple[str, str, str, str]], limit: int = 10) -> list[tuple[str, str, str, str]]:
    out: list[tuple[str, str, str, str]] = []
    for i, row in enumerate(rows):
        if i >= limit:
            break
        out.append(row)
    return out


def _warn_data_bounds(block: BlockDiag) -> None:
    if block.data_off is None or block.data_len is None:
        return
    data_end = block.data_off + block.data_len
    if block.data_off < block.start:
        block.warnings.append(
            f"data_off({block.data_off}) < header_start({block.start}) -> payload пересекает заголовок"
        )
    if data_end > block.end:
        block.warnings.append(
            f"data_end({data_end}) > block_end({block.end}) -> payload выходит за границы"
        )


def _probe_k2(data: bytes) -> list[BlockDiag]:
    blocks: list[BlockDiag] = []
    headers = list(HEADER_RE.finditer(data))
    for i, m in enumerate(headers):
        start = m.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(data)
        id_off = start + (4 if data[start:start + 4] == b"\xFF\xFF\xFF\xFF" else 2)
        marker_off = id_off + 2
        marker = data[marker_off] if marker_off < len(data) else None

        second_ff = data.find(b"\xFF\xFF", m.end(), end)
        data_off = second_ff + 2 if second_ff >= 0 else None
        data_len = (end - data_off) if data_off is not None else None
        if data_len is not None:
            data_len -= (data_len % 2)

        rows = (data_len // 2) if data_len is not None else None

        first_rows: list[tuple[str, str, str, str]] = []
        if data_off is not None and data_len is not None:
            payload = data[data_off:data_off + data_len]
            decoded = []
            for r in range(0, len(payload), 2):
                qc = payload[r]
                fs = payload[r + 1]
                decoded.append(("не найдено", str(qc), str(fs), "не найдено"))
            first_rows = _slice_preview(decoded)

        sigs = [("FF FF ?? 1E " + (f"{marker:02X}" if marker is not None else "??"), start)]
        if second_ff >= 0:
            sigs.append(("FF FF (data delimiter)", second_ff))

        block = BlockDiag(
            index=i,
            start=start,
            end=end,
            length=end - start,
            signatures=sigs,
            test_id=data[id_off] if id_off < len(data) else None,
            test_id_how=f"1 byte @ +{id_off-start} от start после FF FF[ FF FF]",
            id_off=id_off,
            rows=rows,
            rows_how="rows = floor(data_len/2), пары [qc, fs]",
            rows_off=data_off,
            step=None,
            step_how="StepZond не найден явным полем в K2-заголовке (гипотеза: шаг не хранится или задан внешне)",
            step_off=None,
            data_off=data_off,
            data_len=data_len,
            bytes_per_row=2,
            first_rows=first_rows,
            warnings=[],
        )
        _warn_data_bounds(block)
        if second_ff < 0:
            block.warnings.append("Не найден delimiter FF FF между заголовком и payload")
        blocks.append(block)
    return blocks


def _probe_k4(data: bytes) -> list[BlockDiag]:
    starts: list[int] = []
    i = 0
    while True:
        j = data.find(b"\xFF\xFF", i)
        if j < 0:
            break
        # conservative start check
        if j + 13 <= len(data) and j + 80 <= len(data) and K4_SIG in data[j:j + 80]:
            exp = struct.unpack_from("<H", data, j + 2)[0]
            step_mm = data[j + 5]
            if exp not in (0, 0xFFFF) and exp <= 5000 and 1 <= step_mm <= 200 and _is_bcd_datetime(data, j + 7):
                starts.append(j)
        i = j + 2

    blocks: list[BlockDiag] = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(data)
        b = data[start:end]

        id_off = start + 2
        test_id = struct.unpack_from("<H", data, id_off)[0] if id_off + 2 <= len(data) else None
        step_off = start + 5
        step = (data[step_off] / 1000.0) if step_off < len(data) else None
        start_m = (data[start + 4] / 100.0) if start + 4 < len(data) else None

        k = b.find(K4_SIG)
        sig_off = start + k if k >= 0 else None
        data_off = (sig_off + len(K4_SIG)) if sig_off is not None else None
        data_len = (end - data_off) if data_off is not None else None
        rows = (data_len // 9) if data_len is not None else None
        if data_len is not None:
            data_len = rows * 9

        first_rows: list[tuple[str, str, str, str]] = []
        if data_off is not None and rows is not None:
            decoded = []
            payload = data[data_off:data_off + rows * 9]
            for r in range(rows):
                row = payload[r * 9:(r + 1) * 9]
                qc = row[0] * 100 + row[1]
                fs = row[4] * 100 + row[5]
                u = row[6] + 256 * row[7]
                depth = "не найдено"
                if start_m is not None and step is not None:
                    depth = f"{start_m + r * step:.3f}"
                decoded.append((depth, str(qc), str(fs), str(u)))
            first_rows = _slice_preview(decoded)

        sigs = [("FF FF (block start)", start)]
        if sig_off is not None:
            sigs.append(("01 02 03 FF FF", sig_off))

        block = BlockDiag(
            index=idx,
            start=start,
            end=end,
            length=end - start,
            signatures=sigs,
            test_id=test_id,
            test_id_how="2 bytes little-endian @ +2",
            id_off=id_off,
            rows=rows,
            rows_how="rows = floor(data_len/9) после сигнатуры 01 02 03 FF FF",
            rows_off=data_off,
            step=step,
            step_how="StepZond = byte @ +5, в метрах = value/1000",
            step_off=step_off,
            data_off=data_off,
            data_len=data_len,
            bytes_per_row=9,
            first_rows=first_rows,
            warnings=[],
        )
        _warn_data_bounds(block)
        if sig_off is None:
            block.warnings.append("Сигнатура 01 02 03 FF FF не найдена в блоке")
        blocks.append(block)
    return blocks


def build_report(path: Path) -> str:
    data = path.read_bytes()
    file_size = len(data)
    kind = "K4" if _detect_k4(data) else "K2"
    blocks = _probe_k4(data) if kind == "K4" else _probe_k2(data)

    lines: list[str] = []
    lines.append(f"GEO probe report for: {path}")
    lines.append(f"Detected kind: {kind}")
    lines.append(f"File size: {file_size} bytes")
    lines.append("")
    lines.append("Blocks:")
    if not blocks:
        lines.append("  not found")
        return "\n".join(lines)

    for b in blocks:
        lines.append(f"- index={b.index} start={b.start} end={b.end} length={b.length}")

    lines.append("")
    lines.append("Per-block details:")
    for b in blocks:
        lines.append(f"\n[block {b.index}]")
        lines.append(f"range: [{b.start}, {b.end}) len={b.length}")
        lines.append("signatures:")
        for name, off in b.signatures:
            lines.append(f"  - {name} @ {off}")
        lines.append(
            f"test_id: {b.test_id if b.test_id is not None else 'не найдено'} ({b.test_id_how}), id_off={b.id_off if b.id_off is not None else 'не найдено'}"
        )
        lines.append(
            f"rows: {b.rows if b.rows is not None else 'не найдено'} ({b.rows_how}), rows_off={b.rows_off if b.rows_off is not None else 'не найдено'}"
        )
        step_val = f"{b.step:.6f}" if b.step is not None else "не найдено"
        lines.append(f"step: {step_val} ({b.step_how}), step_off={b.step_off if b.step_off is not None else 'не найдено'}")
        lines.append(
            f"data_off={b.data_off if b.data_off is not None else 'не найдено'} data_len={b.data_len if b.data_len is not None else 'не найдено'} bytes_per_row={b.bytes_per_row if b.bytes_per_row is not None else 'не найдено'}"
        )
        lines.append("first 10 rows (depth, qc, fs, u):")
        if not b.first_rows:
            lines.append("  - не найдено")
        else:
            for row in b.first_rows:
                lines.append(f"  - {row[0]}, {row[1]}, {row[2]}, {row[3]}")

        if b.warnings:
            lines.append("warnings:")
            for w in b.warnings:
                lines.append(f"  - {w}")
        else:
            lines.append("warnings: none")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostic GEO probe")
    parser.add_argument("geo_path", type=Path, help="Path to GEO file")
    args = parser.parse_args()

    if not args.geo_path.exists():
        raise SystemExit(f"File not found: {args.geo_path}")

    report = build_report(args.geo_path)
    print(report)

    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    out_path = logs_dir / f"geo_probe_{args.geo_path.name}.txt"
    out_path.write_text(report + "\n", encoding="utf-8")
    print(f"\nSaved full report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
