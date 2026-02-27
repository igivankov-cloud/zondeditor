# src/zondeditor/export/gxl_export.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Any, Optional
import xml.etree.ElementTree as ET

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
    """Сформировать GXL (XML) из текущих данных (генератор).

    Создаёт минимально необходимую структуру:
      <gxl><object><code>...</code><test>...</test>...</object></gxl>

    В <test>:
      - <numtest>
      - <deepbegin>
      - <stepzond>
      - <dat> (строки 'qc;fs')
    """
    tests_list = []
    for t in tests:
        if include_only_export_on and not bool(getattr(t, "export_on", True)):
            continue
        tests_list.append(t)

    root = ET.Element("gxl")
    obj = ET.SubElement(root, "object")
    ET.SubElement(obj, "code").text = str(object_code)

    for t in tests_list:
        xt = ET.SubElement(obj, "test")
        tid = int(getattr(t, "tid", 0) or 0)
        ET.SubElement(xt, "numtest").text = str(tid)

        depth_arr = list(getattr(t, "depth", []) or [])
        d0 = _parse_depth_float(depth_arr[0]) if depth_arr else None
        if d0 is None:
            d0 = 0.0
        ET.SubElement(xt, "deepbegin").text = f"{d0:.2f}"

        step = None
        if len(depth_arr) >= 2:
            a = _parse_depth_float(depth_arr[0])
            b = _parse_depth_float(depth_arr[1])
            if a is not None and b is not None:
                step = b - a
        if step is None:
            step = 0.05
        st = f"{step:.2f}".rstrip("0").rstrip(".")
        ET.SubElement(xt, "stepzond").text = st if st else "0.05"

        qc = list(getattr(t, "qc", []) or [])
        fs = list(getattr(t, "fs", []) or [])
        n = min(len(qc), len(fs))
        lines = []
        for i in range(n):
            qv = _parse_cell_int(qc[i])
            fv = _parse_cell_int(fs[i])
            qs = "" if qv is None else str(int(qv))
            fs_s = "" if fv is None else str(int(fv))
            lines.append(f"{qs};{fs_s}")
        ET.SubElement(xt, "dat").text = "\n".join(lines)

    try:
        ET.indent(root, space="  ")
    except Exception:
        pass

    xml_out = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(xml_out)
