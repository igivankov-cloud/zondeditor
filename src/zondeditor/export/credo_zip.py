# src/zondeditor/export/credo_zip.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Any, Optional
import zipfile

from src.zondeditor.processing.calibration import calc_qc_fs, Calibration, K2_DEFAULT, K4_DEFAULT

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

def _fmt_depth(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")

def _fmt_comma(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}".replace(".", ",")

def export_credo_zip(
    tests: Iterable[Any],
    *,
    out_zip_path: Path,
    geo_kind: str = "K2",
    cal: Calibration | None = None,
    include_only_export_on: bool = True,
) -> None:
    """Экспорт ZIP для CREDO: две CSV на опыт (лоб/бок).

    По умолчанию:
      K2 -> K2_DEFAULT, K4 -> K4_DEFAULT (можно переопределить через cal)
    """
    g = (geo_kind or "K2").upper()
    if cal is None:
        cal = K4_DEFAULT if g == "K4" else K2_DEFAULT

    tests_list = []
    for t in tests:
        if include_only_export_on and not bool(getattr(t, "export_on", True)):
            continue
        tests_list.append(t)

    out_zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(str(out_zip_path), "w", compression=zipfile.ZIP_DEFLATED) as z:
        for t in tests_list:
            tid = str(getattr(t, "tid", ""))
            qc_lines = []
            fs_lines = []
            depth_arr = list(getattr(t, "depth", []) or [])
            qc_arr = list(getattr(t, "qc", []) or [])
            fs_arr = list(getattr(t, "fs", []) or [])
            n = max(len(depth_arr), len(qc_arr), len(fs_arr))
            for i in range(n):
                d = _parse_depth_float(depth_arr[i]) if i < len(depth_arr) else None
                if d is None:
                    continue
                qv = _parse_cell_int(qc_arr[i]) if i < len(qc_arr) else 0
                fv = _parse_cell_int(fs_arr[i]) if i < len(fs_arr) else 0
                qv = 0 if qv is None else int(qv)
                fv = 0 if fv is None else int(fv)
                qc_mpa, fs_kpa = calc_qc_fs(qv, fv, geo_kind=g, cal=cal)
                qc_lines.append(f"{_fmt_depth(d)};{_fmt_comma(qc_mpa, 2)}")
                fs_lines.append(f"{_fmt_depth(d)};{int(round(fs_kpa))}")

            z.writestr(f"СЗ-{tid} лоб.csv", "\n".join(qc_lines))
            z.writestr(f"СЗ-{tid} бок.csv", "\n".join(fs_lines))
