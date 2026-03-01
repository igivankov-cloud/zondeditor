from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from src.zondeditor.domain.models import TestData


class GxlParseError(ValueError):
    """Raised when a GXL file is unsupported or malformed."""


def _txt(node: ET.Element | None, tag: str, default: str = "") -> str:
    if node is None:
        return default
    el = node.find(tag)
    if el is None or el.text is None:
        return default
    return str(el.text).strip()


def _to_float(text: str, default: float = 0.0) -> float:
    t = str(text or "").strip().replace(",", ".")
    if not t:
        return default
    try:
        return float(t)
    except Exception:
        return default


def _to_int(text: str, default: int = 0) -> int:
    try:
        return int(round(_to_float(text, float(default))))
    except Exception:
        return default


def parse_gxl_file(path: str | Path) -> tuple[list[TestData], list[dict]]:
    """Parse GeoExplorer GXL export into TestData list and key/value meta rows."""
    gxl_path = Path(path)
    try:
        raw = gxl_path.read_bytes()
    except Exception as exc:
        raise GxlParseError(f"Не удалось прочитать GXL: {exc}") from exc

    root = None
    parse_errors: list[str] = []
    for payload in (raw, raw.decode("cp1251", errors="replace"), raw.decode("utf-8", errors="replace")):
        try:
            if isinstance(payload, bytes):
                root = ET.fromstring(payload)
            else:
                root = ET.fromstring(payload.encode("utf-8"))
            break
        except ET.ParseError as exc:
            parse_errors.append(str(exc))

    if root is None:
        reason = parse_errors[0] if parse_errors else "unknown parse error"
        raise GxlParseError(f"Файл GXL поврежден или не является корректным XML: {reason}")
    if root.tag.lower() not in {"exportfile", "gxl"}:
        raise GxlParseError(
            "Неподдерживаемый формат GXL: ожидается корневой тег <exportfile> или <gxl>."
        )

    obj = root.find("object") if root.tag.lower() == "exportfile" else root.find("object")
    if obj is None:
        raise GxlParseError("В GXL отсутствует блок <object> с данными зондирований.")

    tests: list[TestData] = []
    meta_rows: list[dict] = []

    for test_node in obj.findall("test"):
        tid = _to_int(_txt(test_node, "numtest", "0"), 0)
        date_s = _txt(test_node, "date", "")
        deepbegin = _to_float(_txt(test_node, "deepbegin", "0"), 0.0)
        step = _to_float(_txt(test_node, "stepzond", "0.1"), 0.1)
        dat_raw = _txt(test_node, "dat", "")
        if not dat_raw:
            continue

        qc: list[str] = []
        fs: list[str] = []
        incl: list[str] = []
        depth: list[str] = []

        rows = [ln.strip() for ln in dat_raw.splitlines() if ln.strip()]
        for idx, row in enumerate(rows):
            cols = [c.strip() for c in row.split(";")]
            if not cols:
                continue
            qc.append(str(_to_int(cols[0] if len(cols) > 0 else "0", 0)))
            fs.append(str(_to_int(cols[1] if len(cols) > 1 else "0", 0)))
            incl.append(str(_to_int(cols[3] if len(cols) > 3 else "0", 0)))
            depth.append(f"{(deepbegin + idx * step):g}")

        if not depth:
            continue

        is_k4 = _to_int(_txt(test_node, "controllertype", "1"), 1) == 2
        tests.append(
            TestData(
                tid=(tid if tid > 0 else len(tests) + 1),
                dt=date_s,
                depth=depth,
                qc=qc,
                fs=fs,
                incl=(incl if is_k4 else None),
                marker="",
                header_pos="",
                orig_id=None,
                block=None,
            )
        )

        for key in ("scale", "scaleostria", "scalemufta", "deepbegin", "stepzond"):
            val = _txt(test_node, key, "")
            if val:
                meta_rows.append({"key": key, "value": val})

    if not tests:
        raise GxlParseError(
            "В GXL не найдены зондирования (<test>/<dat>) или их вариант не поддерживается."
        )

    return tests, meta_rows
