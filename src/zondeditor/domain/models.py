from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Row:
    depth_m: float
    qc_raw: int
    fs_raw: int
    u_raw: int = 0
    inc_raw: int = 0


@dataclass
class TestSeries:
    test_id: int
    dt: str
    step_m: float
    rows: list[Row] = field(default_factory=list)
    # optional source metadata for GEO template rebuild
    marker: str = ""
    header_pos: str = ""
    orig_id: Optional[int] = None
    block: Optional[Any] = None


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
    # template-rebuild helpers
    orig_id: int = 0
    raw_block_bytes: bytes = b""

    @property
    def id_off(self) -> int:
        return int(self.id_pos - self.header_start)

    @property
    def dt_off(self) -> int:
        return int(self.dt_pos - self.header_start)

    @property
    def data_off(self) -> int:
        return int(self.data_start - self.header_start)

    @property
    def data_len(self) -> int:
        return int(self.data_end - self.data_start)


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


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip().replace(",", "."))
    except Exception:
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(_to_float(value, float(default))))
    except Exception:
        return default


def testdata_to_series(test: TestData) -> TestSeries:
    depth = list(getattr(test, "depth", []) or [])
    qc = list(getattr(test, "qc", []) or [])
    fs = list(getattr(test, "fs", []) or [])
    incl = list(getattr(test, "incl", []) or []) if getattr(test, "incl", None) is not None else []

    n = min(len(depth), len(qc), len(fs)) if depth else max(len(qc), len(fs), len(incl))
    depths = [_to_float(depth[i], float(i) * 0.05) if i < len(depth) else float(i) * 0.05 for i in range(n)]
    step = (depths[1] - depths[0]) if len(depths) > 1 else 0.05
    rows: list[Row] = []
    for i in range(n):
        rows.append(
            Row(
                depth_m=depths[i],
                qc_raw=_to_int(qc[i] if i < len(qc) else 0),
                fs_raw=_to_int(fs[i] if i < len(fs) else 0),
                u_raw=_to_int(incl[i] if i < len(incl) else 0),
                inc_raw=_to_int(incl[i] if i < len(incl) else 0),
            )
        )

    return TestSeries(
        test_id=int(getattr(test, "tid", 0) or 0),
        dt=str(getattr(test, "dt", "") or ""),
        step_m=float(step or 0.05),
        rows=rows,
        marker=str(getattr(test, "marker", "") or ""),
        header_pos=str(getattr(test, "header_pos", "") or ""),
        orig_id=getattr(test, "orig_id", None),
        block=getattr(test, "block", None),
    )


def series_to_testdata(series: TestSeries) -> TestData:
    rows = list(getattr(series, "rows", []) or [])
    depth = [f"{float(r.depth_m):g}" for r in rows]
    qc = [str(int(r.qc_raw)) for r in rows]
    fs = [str(int(r.fs_raw)) for r in rows]
    incl_vals = [int(getattr(r, "u_raw", 0) or getattr(r, "inc_raw", 0) or 0) for r in rows]
    has_incl = any(v != 0 for v in incl_vals)

    return TestData(
        tid=int(getattr(series, "test_id", 0) or 0),
        dt=str(getattr(series, "dt", "") or ""),
        depth=depth,
        qc=qc,
        fs=fs,
        incl=[str(v) for v in incl_vals] if has_incl else None,
        marker=str(getattr(series, "marker", "") or ""),
        header_pos=str(getattr(series, "header_pos", "") or ""),
        orig_id=getattr(series, "orig_id", None),
        block=getattr(series, "block", None),
    )
