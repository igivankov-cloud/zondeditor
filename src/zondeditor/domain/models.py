# src/zondeditor/domain/models.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass
class TestFlags:
    invalid: bool
    interp_cells: set[tuple[int, str]]  # (row, 'qc'/'fs')
    force_cells: set[tuple[int, str]]   # (row, 'qc'/'fs')
    user_cells: set[tuple[int, str]]    # manual edits (purple)
    algo_cells: set[tuple[int, str]]    # changed by algorithm (green)
    force_tail_rows: set[int]           # suggested tail rows (blue)

@dataclass
class GeoBlockInfo:
    # K2 GEO block layout (absolute positions in original file)
    order_index: int
    header_start: int
    header_end: int
    id_pos: int          # absolute pos of id byte
    dt_pos: int          # absolute pos of first datetime BCD byte (6 bytes)
    data_start: int      # absolute pos of first qc/fs byte
    data_end: int        # absolute pos of end of block (start of next header or EOF)
    marker_byte: int

@dataclass
class TestData:
    tid: int
    dt: str
    depth: list[str]     # meters as string (comma decimal)
    qc: list[str]
    fs: list[str]
    incl: Optional[list[str]] = None    # K4: U-channel/inclinometer
    marker: str = ""
    header_pos: str = ""                # binding to original GEO (for save-back)
    orig_id: Optional[int] = None
    block: Optional[GeoBlockInfo] = None
