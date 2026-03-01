# src/zondeditor/export/gxl_export.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Any, Optional

from src.zondeditor.export.selection import select_export_tests


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


def export_gxl_generated(
    tests: Iterable[Any],
    *,
    out_path: Path,
    object_code: str = "OBJ",
    include_only_export_on: bool = True,
) -> None:
    """Сформировать GXL, совместимый с GeoExplorer (<exportfile>/<object>/<test>)."""
    if include_only_export_on:
        tests_list = select_export_tests(tests).tests
    else:
        tests_list = list(tests or [])

    def xml_escape(t: str) -> str:
        t = '' if t is None else str(t)
        return (t.replace('&', '&amp;')
                 .replace('<', '&lt;')
                 .replace('>', '&gt;')
                 .replace('"', '&quot;')
                 .replace("'", '&apos;'))

    def fmt_comma_num(x, ndp=2):
        try:
            x = float(x)
        except Exception:
            x = 0.0
        s = f"{x:.{ndp}f}".rstrip('0').rstrip('.')
        return (s or "0").replace('.', ',')

    def parse_d(x):
        return _parse_depth_float(x)

    def make_dat(t, step_m=0.1):
        ds = [parse_d(v) for v in (getattr(t, 'depth', []) or [])]
        qc = getattr(t, 'qc', []) or []
        fs = getattr(t, 'fs', []) or []

        ds2 = [d for d in ds if d is not None]
        if not ds2:
            return ["0;0;0;0;0;"], 0.0, step_m

        deepbegin = min(ds2)
        step = step_m
        if len(ds2) >= 2:
            st = abs(ds2[1] - ds2[0])
            if 0.045 <= st <= 0.055:
                step = 0.05
            elif 0.095 <= st <= 0.105:
                step = 0.10

        endd = max(ds2)
        n = max(1, int(round((endd - deepbegin) / step)) + 1)
        grid_local = [round(deepbegin + i * step, 2) for i in range(n)]

        m = {}
        for i, d in enumerate(ds):
            if d is None:
                continue
            key = round(d, 2)
            q = _parse_cell_int(qc[i]) if i < len(qc) else 0
            f = _parse_cell_int(fs[i]) if i < len(fs) else 0
            m[key] = (max(0, int(q or 0)), max(0, int(f or 0)))

        return [f"{m.get(d,(0,0))[0]};{m.get(d,(0,0))[1]};0;0;0;" for d in grid_local], deepbegin, step

    out = []
    out.append('<?xml version="1.0" encoding="windows-1251"?>\r\n')
    out.append('<exportfile>\r\n')
    out.append('  <verfile>3</verfile>\r\n')
    out.append('  <verprogram>GeoExplorer v3.0.14.523</verprogram>\r\n')
    out.append('  <object>\r\n')
    out.append('    <id>60</id>\r\n')
    out.append(f'    <name>{xml_escape(object_code or "OBJ")}</name>\r\n')

    for idx, t in enumerate(tests_list, start=1):
        numtest = int(getattr(t, 'tid', idx) or idx)
        dat_lines, deepbegin_val, step_for_test = make_dat(t)
        out.append('    <test>\r\n')
        out.append(f'      <numtest>{numtest}</numtest>\r\n')
        out.append('      <date></date>\r\n')
        out.append(f"      <deepbegin>{fmt_comma_num(deepbegin_val, 1)}</deepbegin>\r\n")
        out.append(f"      <stepzond>{fmt_comma_num(step_for_test, 2)}</stepzond>\r\n")
        out.append('      <scale>250</scale>\r\n')
        out.append('      <controllertype>1</controllertype>\r\n')
        out.append('      <dat>')
        out.append(dat_lines[0] + '\r\n')
        for ln in dat_lines[1:]:
            out.append(ln + '\r\n')
        out.append('      </dat>\r\n')
        out.append('    </test>\r\n')

    out.append('  </object>\r\n')
    out.append('</exportfile>\r\n')

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(''.join(out).encode('cp1251', errors='replace'))
