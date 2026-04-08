from __future__ import annotations

import math
from dataclasses import dataclass

from src.zondeditor.domain.experience_column import ExperienceColumn, build_column_from_layers
from src.zondeditor.domain.models import TestData
from src.zondeditor.processing.calibration import Calibration, calc_qc_fs
from src.zondeditor.export.cad.schema import CadBlock, CadLayerSpec, CadLine, CadPolyline, CadScene, TextLabel

from .layout import DEFAULT_PROTOCOL_LAYOUT, ProtocolLayout
from .models import ProtocolBuildPack, ProtocolDocument, ProtocolLayerRow


PROTOCOL_LAYERS: tuple[CadLayerSpec, ...] = (
    CadLayerSpec("ZE_PROTO_FRAME", color_aci=7),
    CadLayerSpec("ZE_PROTO_TEXT", color_aci=7),
    CadLayerSpec("ZE_PROTO_QC", color_aci=1, rgb=(230, 61, 61), lineweight=30),
    CadLayerSpec("ZE_PROTO_FS", color_aci=5, rgb=(37, 99, 235), lineweight=30),
    CadLayerSpec("ZE_PROTO_CUT", color_aci=8),
)


@dataclass(frozen=True)
class ProtocolCadResult:
    document: ProtocolDocument
    scene: CadScene
    height_mm: float


def _parse_float(value) -> float | None:
    try:
        return float(str(value).replace(",", ".").strip())
    except Exception:
        return None


def _max_depth(test: TestData) -> float:
    depths = [_parse_float(v) for v in list(getattr(test, "depth", []) or [])]
    depths = [v for v in depths if v is not None]
    return max(depths) if depths else 0.0


def build_protocol_documents(*, tests: list[TestData], ige_registry: dict[str, dict[str, object]] | None = None) -> ProtocolBuildPack:
    docs: list[ProtocolDocument] = []
    reg = dict(ige_registry or {})
    for test in tests:
        col: ExperienceColumn | None = getattr(test, "experience_column", None)
        if col is None:
            col = build_column_from_layers(getattr(test, "layers", []) or [], sounding_top=0.0, sounding_bottom=_max_depth(test))
        rows: list[ProtocolLayerRow] = []
        for idx, it in enumerate(list(getattr(col, "intervals", []) or []), start=1):
            ige_id = str(getattr(it, "ige_id", "") or "")
            ent = dict(reg.get(ige_id) or {})
            descr = str(ent.get("notes") or ent.get("manual_notes") or ent.get("note") or getattr(it, "ige_name", "") or ige_id)
            rows.append(
                ProtocolLayerRow(
                    idx=idx,
                    from_depth_m=float(getattr(it, "from_depth", 0.0) or 0.0),
                    to_depth_m=float(getattr(it, "to_depth", 0.0) or 0.0),
                    ige_id=ige_id,
                    description=descr,
                    abs_mark_text="",  # temporary: absolute elevation is not in data model yet
                )
            )
        max_depth = max(_max_depth(test), max((r.to_depth_m for r in rows), default=0.0))
        docs.append(
            ProtocolDocument(
                test=test,
                title=f"Точка испытания: ТСЗ {int(getattr(test, 'tid', 0) or 0)}",
                date_text=f"Дата испытания: {str(getattr(test, 'dt', '') or '')}",
                max_depth_m=max_depth,
                layers=rows,
            )
        )
    return ProtocolBuildPack(documents=docs)


def _value_to_x(value: float, *, x0: float, x1: float, vmax: float) -> float:
    if vmax <= 0:
        return x0
    v = max(0.0, min(vmax, float(value)))
    return x0 + (x1 - x0) * (v / vmax)


def _split_text_lines(text: str, line_limit: int = 42) -> list[str]:
    words = str(text or "").split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for w in words:
        cand = f"{current} {w}".strip()
        if len(cand) <= line_limit:
            current = cand
            continue
        if current:
            lines.append(current)
        current = w
    if current:
        lines.append(current)
    return lines


def build_protocol_scene(*, doc: ProtocolDocument, calibration: Calibration, block_name: str, layout: ProtocolLayout = DEFAULT_PROTOCOL_LAYOUT) -> ProtocolCadResult:
    lines: list[CadLine] = []
    texts: list[TextLabel] = []
    polys: list[CadPolyline] = []

    y_bottom = layout.y_for_depth(doc.max_depth_m)

    # frame
    x_columns = [layout.x_no, layout.x_abs, layout.x_thickness, layout.x_description, layout.x_section, layout.x_depth, layout.x_graph, layout.x_right]
    for x in x_columns:
        lines.append(CadLine("ZE_PROTO_FRAME", (x, layout.top_y_mm), (x, y_bottom)))
    lines.append(CadLine("ZE_PROTO_FRAME", (layout.x_no, layout.top_y_mm), (layout.x_right, layout.top_y_mm)))
    lines.append(CadLine("ZE_PROTO_FRAME", (layout.x_no, layout.header_bottom_y_mm), (layout.x_right, layout.header_bottom_y_mm)))
    lines.append(CadLine("ZE_PROTO_FRAME", (layout.x_no, y_bottom), (layout.x_right, y_bottom)))

    # header text
    texts.extend(
        [
            TextLabel("ZE_PROTO_TEXT", "График статического зондирования", 28.2, -6.9, 3.0),
            TextLabel("ZE_PROTO_TEXT", doc.title, 37.1, -13.7, 2.5),
            TextLabel("ZE_PROTO_TEXT", doc.date_text, 36.0, -24.0, 2.5),
            TextLabel("ZE_PROTO_TEXT", "Абс. отм, м", 5.0, -48.9, 1.8),
            TextLabel("ZE_PROTO_TEXT", "Мощность", 16.5, -47.7, 1.8),
            TextLabel("ZE_PROTO_TEXT", "Описание грунта", 44.8, -42.4, 1.8),
            TextLabel("ZE_PROTO_TEXT", "Разрез", 93.8, -48.5, 1.8),
            TextLabel("ZE_PROTO_TEXT", "Глубина скважины", 100.2, -48.2, 1.8, align="CENTER"),
        ]
    )

    # depth grid
    max_int = int(math.ceil(max(doc.max_depth_m, 0.0)))
    for d in range(0, max_int + 1):
        y = layout.y_for_depth(float(d))
        lines.append(CadLine("ZE_PROTO_FRAME", (layout.x_no, y), (layout.x_right, y)))
        if d % 2 == 0:
            texts.append(TextLabel("ZE_PROTO_TEXT", f"{d},0", 104.1, y, 1.8, align="CENTER"))

    # layers table and section
    for row in doc.layers:
        y0 = layout.y_for_depth(row.from_depth_m)
        y1 = layout.y_for_depth(row.to_depth_m)
        lines.append(CadLine("ZE_PROTO_FRAME", (layout.x_no, y1), (layout.x_graph, y1)))
        thickness = max(0.0, row.to_depth_m - row.from_depth_m)
        texts.append(TextLabel("ZE_PROTO_TEXT", str(row.idx), 1.4, y1 + 0.8, 1.8))
        texts.append(TextLabel("ZE_PROTO_TEXT", row.abs_mark_text, 5.3, y1 + 0.8, 1.8))
        texts.append(TextLabel("ZE_PROTO_TEXT", f"{thickness:.2f}".replace('.', ','), 16.8, y1 + 0.8, 1.8))

        # section circle with IGE id number
        circle_cx = 94.5
        circle_cy = (y0 + y1) / 2.0
        radius = 1.8
        circle_pts = []
        for i in range(20):
            a = 2.0 * math.pi * float(i) / 20.0
            circle_pts.append((circle_cx + radius * math.cos(a), circle_cy + radius * math.sin(a)))
        polys.append(CadPolyline("ZE_PROTO_CUT", circle_pts, closed=True))
        ige_num = ''.join(ch for ch in row.ige_id if ch.isdigit()) or row.ige_id
        texts.append(TextLabel("ZE_PROTO_TEXT", str(ige_num), circle_cx, circle_cy, 1.8, align="CENTER"))

        desc_lines = _split_text_lines(row.description, line_limit=48)
        for i, txt in enumerate(desc_lines):
            # allow overflow down like in reference template
            texts.append(TextLabel("ZE_PROTO_TEXT", txt, 26.1, y0 - 3.1 * i - 3.0, 1.8))

    # graph scales in header
    for v in range(0, 31, 5):
        x = _value_to_x(v, x0=layout.x_graph, x1=170.1, vmax=30.0)
        lines.append(CadLine("ZE_PROTO_FRAME", (x, layout.qc_axis_y), (x, layout.qc_axis_y + 1.2)))
        texts.append(TextLabel("ZE_PROTO_TEXT", f"{v},0", x, layout.qc_axis_y, 1.6, align="CENTER"))
    for v in range(0, 151, 50):
        x = _value_to_x(v, x0=layout.x_graph, x1=160.1, vmax=150.0)
        lines.append(CadLine("ZE_PROTO_FRAME", (x, layout.fs_axis_y), (x, layout.fs_axis_y + 1.2)))
        texts.append(TextLabel("ZE_PROTO_TEXT", f"{v},0", x, layout.fs_axis_y, 1.6, align="CENTER"))

    # qc/fs curves (reuse existing calibration pipeline)
    depth_arr = list(getattr(doc.test, "depth", []) or [])
    qc_arr = list(getattr(doc.test, "qc", []) or [])
    fs_arr = list(getattr(doc.test, "fs", []) or [])
    samples_qc: list[tuple[float, float]] = []
    samples_fs: list[tuple[float, float]] = []
    n = max(len(depth_arr), len(qc_arr), len(fs_arr))
    for i in range(n):
        d = _parse_float(depth_arr[i]) if i < len(depth_arr) else None
        q_raw = _parse_float(qc_arr[i]) if i < len(qc_arr) else None
        f_raw = _parse_float(fs_arr[i]) if i < len(fs_arr) else None
        if d is None or q_raw is None or f_raw is None:
            continue
        qc_mpa, fs_kpa = calc_qc_fs(int(round(q_raw)), int(round(f_raw)), cal=calibration)
        y = layout.y_for_depth(d)
        samples_qc.append((_value_to_x(qc_mpa, x0=layout.x_graph, x1=170.1, vmax=30.0), y))
        samples_fs.append((_value_to_x(fs_kpa, x0=layout.x_graph, x1=160.1, vmax=150.0), y))

    if len(samples_qc) >= 2:
        polys.append(CadPolyline("ZE_PROTO_QC", samples_qc))
    if len(samples_fs) >= 2:
        polys.append(CadPolyline("ZE_PROTO_FS", samples_fs))

    scene = CadScene(
        layers=list(PROTOCOL_LAYERS),
        block=CadBlock(name=block_name, base_point=(0.0, 0.0, 0.0), lines=lines, polylines=polys, texts=texts),
    )
    return ProtocolCadResult(document=doc, scene=scene, height_mm=layout.total_height_for_depth(doc.max_depth_m))
