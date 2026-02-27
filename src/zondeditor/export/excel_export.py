# src/zondeditor/export/excel_export.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Any, Optional

from openpyxl import Workbook

from src.zondeditor.processing.calibration import calc_qc_fs_from_del

def _parse_depth_float(s: Any) -> Optional[float]:
    try:
        ss = str(s).strip().replace(",", ".")
        return float(ss) if ss else None
    except Exception:
        return None

def _parse_cell_int(s: Any) -> Optional[int]:
    try:
        ss = str(s).strip()
        if ss == "":
            return None
        return int(float(ss.replace(",", ".")))
    except Exception:
        return None

def export_excel(
    tests: Iterable[Any],
    *,
    geo_kind: str,
    out_path: Path,
    scale_div: int = 250,
    fcone_kn: float = 30.0,
    fsleeve_kn: float = 10.0,
    include_only_export_on: bool = True,
) -> None:
    """Экспорт в Excel (xlsx) без UI, совместимый с текущей логикой.

    Колонки:
      K2: Depth_m, qc_del, fs_del, qc_MPa, fs_kPa
      K4: Depth_m, qc_del, fs_del, incl_raw, qc_MPa, fs_kPa
    """
    wb = Workbook()
    ws_meta = wb.active
    ws_meta.title = "meta"
    ws_meta.append(["geo_kind", geo_kind])
    ws_meta.append(["scale", scale_div])
    ws_meta.append(["fcone_kN", fcone_kn])
    ws_meta.append(["fsleeve_kN", fsleeve_kn])

    tests_list = []
    for t in tests:
        if include_only_export_on and not bool(getattr(t, "export_on", True)):
            continue
        tests_list.append(t)
    ws_meta.append(["tests", len(tests_list)])

    for t in tests_list:
        tid = str(getattr(t, "tid", ""))
        ws = wb.create_sheet(f"Z{tid}"[:31])
        if geo_kind == "K4":
            ws.append(["Depth_m", "qc_del", "fs_del", "incl_raw", "qc_MPa", "fs_kPa"])
        else:
            ws.append(["Depth_m", "qc_del", "fs_del", "qc_MPa", "fs_kPa"])

        depth_arr = list(getattr(t, "depth", []) or [])
        qc_arr = list(getattr(t, "qc", []) or [])
        fs_arr = list(getattr(t, "fs", []) or [])
        incl_arr = list(getattr(t, "incl", []) or []) if geo_kind == "K4" else []

        n = max(len(depth_arr), len(qc_arr), len(fs_arr), len(incl_arr))
        for i in range(n):
            d = _parse_depth_float(depth_arr[i]) if i < len(depth_arr) else None
            if d is None:
                continue
            qv = _parse_cell_int(qc_arr[i]) if i < len(qc_arr) else 0
            fv = _parse_cell_int(fs_arr[i]) if i < len(fs_arr) else 0
            qv = 0 if qv is None else int(qv)
            fv = 0 if fv is None else int(fv)
            qc_mpa, fs_kpa = calc_qc_fs_from_del(qv, fv, scale_div=scale_div, fcone_kn=fcone_kn, fsleeve_kn=fsleeve_kn)

            if geo_kind == "K4":
                incl = _parse_cell_int(incl_arr[i]) if i < len(incl_arr) else 0
                incl = 0 if incl is None else int(incl)
                ws.append([round(d, 2), qv, fv, incl, round(qc_mpa, 2), int(round(fs_kpa, 0))])
            else:
                ws.append([round(d, 2), qv, fv, round(qc_mpa, 2), int(round(fs_kpa, 0))])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out_path))
