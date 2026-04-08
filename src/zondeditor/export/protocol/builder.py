from __future__ import annotations

import math
from datetime import datetime
from dataclasses import dataclass

from src.zondeditor.domain.experience_column import ExperienceColumn, build_column_from_layers
from src.zondeditor.domain.hatching.registry import load_registered_hatch
from src.zondeditor.domain.models import TestData
from src.zondeditor.processing.calibration import Calibration, calc_qc_fs
from src.zondeditor.export.cad.schema import CadBlock, CadLayerSpec, CadLine, CadPolyline, CadScene, TextLabel

from .layout import DEFAULT_PROTOCOL_LAYOUT, ProtocolLayout
from .models import ProtocolBuildPack, ProtocolDocument, ProtocolLayerRow


PROTOCOL_LAYERS: tuple[CadLayerSpec, ...] = (
    CadLayerSpec("ZE_PROTO_FRAME", color_aci=7),
    CadLayerSpec("ZE_PROTO_TEXT", color_aci=7),
    CadLayerSpec("ZE_PROTO_GRID", color_aci=8, rgb=(186, 186, 186)),
    CadLayerSpec("ZE_PROTO_QC", color_aci=3, rgb=(22, 163, 74), lineweight=30),
    CadLayerSpec("ZE_PROTO_FS", color_aci=5, rgb=(37, 99, 235), lineweight=30),
    CadLayerSpec("ZE_PROTO_CUT", color_aci=8),
    CadLayerSpec("ZE_PROTO_MASK", color_aci=7, rgb=(255, 255, 255)),
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


def _format_test_date(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    for fmt in ("%d.%m.%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%d.%m.%Y")
        except Exception:
            pass
    if " " in raw:
        raw = raw.split(" ", 1)[0]
    try:
        return datetime.fromisoformat(raw).strftime("%d.%m.%Y")
    except Exception:
        return raw


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
                    soil_type=str(ent.get("soil_type") or ""),
                    abs_mark_text="",  # temporary: absolute elevation is not in data model yet
                )
            )
        max_depth = max(_max_depth(test), max((r.to_depth_m for r in rows), default=0.0))
        docs.append(
            ProtocolDocument(
                test=test,
                title=f"Точка испытания: ТСЗ {int(getattr(test, 'tid', 0) or 0)}",
                date_text=f"Дата испытания: {_format_test_date(str(getattr(test, 'dt', '') or ''))}",
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


def _fmt_tick(v: float | int) -> str:
    try:
        iv = int(round(float(v)))
        return str(iv)
    except Exception:
        return str(v)


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


def _hatch_rect_lines(*, x0: float, x1: float, y_top: float, y_bot: float, spacing: float, angle_deg: float = 45.0) -> list[CadLine]:
    out: list[CadLine] = []
    if x1 <= x0 or y_top <= y_bot:
        return out
    # Clean deterministic hatch (no random/zig-zag artifacts).
    step = max(0.8, float(spacing))
    direction = 1.0 if math.cos(math.radians(angle_deg)) >= 0 else -1.0
    offset = -(y_top - y_bot)
    while offset <= (x1 - x0) + (y_top - y_bot):
        if direction > 0:
            sx = x0 + offset
            sy = y_bot
            ex = sx + (y_top - y_bot)
            ey = y_top
        else:
            sx = x1 - offset
            sy = y_bot
            ex = sx - (y_top - y_bot)
            ey = y_top
        # clip to x-range
        if sx < x0:
            sy += (x0 - sx)
            sx = x0
        if sx > x1:
            sy += (sx - x1)
            sx = x1
        if ex < x0:
            ey -= (x0 - ex)
            ex = x0
        if ex > x1:
            ey -= (ex - x1)
            ex = x1
        if y_bot <= sy <= y_top and y_bot <= ey <= y_top and abs(ex - sx) > 0.05:
            out.append(CadLine("ZE_PROTO_CUT", (sx, sy), (ex, ey)))
        offset += step
    return out


def build_protocol_scene(*, doc: ProtocolDocument, calibration: Calibration, block_name: str, layout: ProtocolLayout = DEFAULT_PROTOCOL_LAYOUT) -> ProtocolCadResult:
    lines: list[CadLine] = []
    texts: list[TextLabel] = []
    polys: list[CadPolyline] = []

    y_bottom = layout.y_for_depth(doc.max_depth_m)

    # frame
    # Header stays visually clean: only outer frame + split between table and graph.
    for x in (layout.x_no, layout.x_graph, layout.x_right):
        lines.append(CadLine("ZE_PROTO_FRAME", (x, layout.top_y_mm), (x, y_bottom)))
    # Inner table columns only in body (under header)
    for x in (layout.x_abs, layout.x_thickness, layout.x_description, layout.x_section, layout.x_depth):
        lines.append(CadLine("ZE_PROTO_FRAME", (x, layout.header_bottom_y_mm), (x, y_bottom)))
    lines.append(CadLine("ZE_PROTO_FRAME", (layout.x_depth_ruler_black, layout.header_bottom_y_mm), (layout.x_depth_ruler_black, y_bottom)))
    lines.append(CadLine("ZE_PROTO_FRAME", (layout.x_depth_ruler_white, layout.header_bottom_y_mm), (layout.x_depth_ruler_white, y_bottom)))
    lines.append(CadLine("ZE_PROTO_FRAME", (layout.x_no, layout.top_y_mm), (layout.x_right, layout.top_y_mm)))
    lines.append(CadLine("ZE_PROTO_FRAME", (layout.x_no, layout.header_bottom_y_mm), (layout.x_right, layout.header_bottom_y_mm)))
    lines.append(CadLine("ZE_PROTO_FRAME", (layout.x_no, y_bottom), (layout.x_right, y_bottom)))
    for yy in (layout.header_row_1, layout.header_row_2, layout.header_row_3, layout.header_row_4):
        lines.append(CadLine("ZE_PROTO_FRAME", (layout.x_no, yy), (layout.x_graph, yy)))

    # header text
    texts.extend(
        [
            TextLabel("ZE_PROTO_TEXT", "График статического зондирования", 55.0, -10.7, 2.3, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", doc.title, 55.0, -18.8, 2.3, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", "Сопротивление конуса и муфты  Sf = 350 см.кв  Sq = 10 см.кв", 55.0, -26.8, 2.3, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", doc.date_text, 55.0, -34.8, 2.3, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", "№ п.п.", ((layout.x_no + layout.x_abs) / 2.0) + 0.25, -47.5, 1.8, rotation_deg=90.0, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", "Абс. отм, м", (layout.x_abs + layout.x_thickness) / 2.0, -47.5, 1.8, rotation_deg=90.0, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", "Мощность", (layout.x_thickness + layout.x_description) / 2.0, -47.5, 1.8, rotation_deg=90.0, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", "Описание грунта", (layout.x_description + layout.x_section) / 2.0, -42.4, 1.9, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", "Разрез", (layout.x_section + layout.x_depth) / 2.0, -47.5, 1.8, rotation_deg=90.0, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", "Глубина", (layout.x_depth + layout.x_graph) / 2.0, -47.5, 1.8, align="CENTER", rotation_deg=90.0),
        ]
    )
    for x in (layout.x_no, layout.x_abs, layout.x_thickness, layout.x_description, layout.x_section, layout.x_depth, layout.x_graph):
        lines.append(CadLine("ZE_PROTO_FRAME", (x, layout.header_row_4), (x, layout.header_bottom_y_mm)))

    # depth grid (right graph area only, light-gray)
    max_int = int(math.floor(max(doc.max_depth_m, 0.0)))
    for d in range(0, max_int + 1):
        y = layout.y_for_depth(float(d))
        lines.append(CadLine("ZE_PROTO_GRID", (layout.x_graph, y), (layout.x_right, y)))
        # depth ruler: black/white alternating bars in 1m steps
        if d < max_int:
            y_next = layout.y_for_depth(float(d + 1))
            if d % 2 == 0:
                lines.extend(
                    [
                        CadLine("ZE_PROTO_CUT", (layout.x_depth_ruler_black, y), (layout.x_depth_ruler_white, y)),
                        CadLine("ZE_PROTO_CUT", (layout.x_depth_ruler_black, y_next), (layout.x_depth_ruler_white, y_next)),
                    ]
                )
                step = 0.22
                yy = y
                while yy > y_next:
                    lines.append(CadLine("ZE_PROTO_CUT", (layout.x_depth_ruler_black, yy), (layout.x_depth_ruler_white, yy)))
                    yy -= step
        if d % 2 == 0 and d != 0:
            texts.append(TextLabel("ZE_PROTO_TEXT", _fmt_tick(d), 104.1, y, 1.8, align="CENTER"))

    # layers table and section
    for row in doc.layers:
        y0 = layout.y_for_depth(row.from_depth_m)
        y1 = layout.y_for_depth(row.to_depth_m)
        # left body boundaries only by real geological intervals (no extra slicing)
        lines.append(CadLine("ZE_PROTO_FRAME", (layout.x_no, y1), (layout.x_graph, y1)))
        thickness = max(0.0, row.to_depth_m - row.from_depth_m)
        y_cell = (y0 + y1) / 2.0
        texts.append(TextLabel("ZE_PROTO_TEXT", str(row.idx), (layout.x_no + layout.x_abs) / 2.0, y_cell, 1.8, align="CENTER"))
        texts.append(TextLabel("ZE_PROTO_TEXT", row.abs_mark_text, (layout.x_abs + layout.x_thickness) / 2.0, y_cell, 1.8, align="CENTER"))
        texts.append(TextLabel("ZE_PROTO_TEXT", f"{thickness:.2f}".replace('.', ','), (layout.x_thickness + layout.x_description) / 2.0, y_cell, 1.8, align="CENTER"))

        # section circle with IGE id number
        # section: green background + hatch per interval
        lines.extend(_hatch_rect_lines(x0=layout.x_section + 0.2, x1=layout.x_depth - 0.2, y_top=y0, y_bot=y1, spacing=1.4))
        hatch = load_registered_hatch(row.soil_type)
        if hatch is not None:
            # keep hatch clean: only first line descriptor for angle/spacing
            ln = list(hatch.lines)[0] if list(hatch.lines) else None
            if ln is not None:
                spacing = max(1.0, min(2.2, abs(float(ln.dx or 1.4))))
                lines.extend(
                    _hatch_rect_lines(
                        x0=layout.x_section + 0.2,
                        x1=layout.x_depth - 0.2,
                        y_top=y0,
                        y_bot=y1,
                        spacing=spacing,
                        angle_deg=float(ln.angle_deg),
                    )
                )

        circle_cx = 94.2
        circle_cy = (y0 + y1) / 2.0
        radius = 2.2
        # white mask under circle so hatch does not shine through
        circle_fill_lines: list[CadLine] = []
        yy = circle_cy - radius
        while yy <= circle_cy + radius:
            dx = max(0.0, radius * radius - (yy - circle_cy) ** 2) ** 0.5
            circle_fill_lines.append(CadLine("ZE_PROTO_MASK", (circle_cx - dx, yy), (circle_cx + dx, yy)))
            yy += 0.24
        lines.extend(circle_fill_lines)
        circle_pts = []
        for i in range(20):
            a = 2.0 * math.pi * float(i) / 20.0
            circle_pts.append((circle_cx + radius * math.cos(a), circle_cy + radius * math.sin(a)))
        polys.append(CadPolyline("ZE_PROTO_CUT", circle_pts, closed=True))
        ige_num = ''.join(ch for ch in row.ige_id if ch.isdigit()) or row.ige_id
        texts.append(TextLabel("ZE_PROTO_TEXT", str(ige_num), circle_cx, circle_cy, 1.8, align="CENTER"))

        desc_lines = _split_text_lines(row.description, line_limit=45)
        for i, txt in enumerate(desc_lines):
            # allow overflow down like in reference template
            texts.append(TextLabel("ZE_PROTO_TEXT", txt, 26.1, y0 - 2.9 * i - 2.6, 1.7))

    # graph scales in header
    is_k4 = int(getattr(calibration, "scale_div", 250) or 250) >= 1000
    fs_max = 500.0 if is_k4 else 300.0
    qc_max = 50.0 if is_k4 else 30.0

    texts.append(TextLabel("ZE_PROTO_FS", "Сопротивление на боковой поверхности, Fs, кПа", 146.0, -16.5, 2.2, align="CENTER"))
    lines.append(CadLine("ZE_PROTO_FS", (layout.x_graph + 0.5, layout.fs_axis_y), (180.0, layout.fs_axis_y)))
    fs_major = 100 if is_k4 else 50
    fs_minor = 50 if is_k4 else 25
    for v in range(0, int(fs_max) + 1, fs_major):
        x = _value_to_x(v, x0=layout.x_graph + 0.5, x1=180.0, vmax=fs_max)
        lines.append(CadLine("ZE_PROTO_FS", (x, layout.fs_axis_y - 1.8), (x, layout.fs_axis_y + 1.8)))
        if v != 0:
            texts.append(TextLabel("ZE_PROTO_FS", _fmt_tick(v), x, layout.fs_axis_y - 4.0, 1.8, align="CENTER", color_aci=5))
    for v in range(0, int(fs_max) + 1, fs_minor):
        x = _value_to_x(v, x0=layout.x_graph + 0.5, x1=180.0, vmax=fs_max)
        lines.append(CadLine("ZE_PROTO_FS", (x, layout.fs_axis_y - 1.0), (x, layout.fs_axis_y + 1.0)))
    texts.append(TextLabel("ZE_PROTO_QC", "Сопротивление под наконечником, Qs, МПа", 146.0, -31.5, 2.2, align="CENTER"))
    lines.append(CadLine("ZE_PROTO_QC", (layout.x_graph + 0.5, layout.qc_axis_y), (180.0, layout.qc_axis_y)))
    qc_major = 10 if is_k4 else 5
    for v in range(0, int(qc_max) + 1, qc_major):
        x = _value_to_x(v, x0=layout.x_graph + 0.5, x1=180.0, vmax=qc_max)
        lines.append(CadLine("ZE_PROTO_QC", (x, layout.qc_axis_y - 1.8), (x, layout.qc_axis_y + 1.8)))
        if v != 0:
            texts.append(TextLabel("ZE_PROTO_QC", _fmt_tick(v), x, layout.qc_axis_y - 4.0, 1.8, align="CENTER", color_aci=3))
    for v in range(0, int(qc_max) + 1):
        x = _value_to_x(v, x0=layout.x_graph + 0.5, x1=180.0, vmax=qc_max)
        lines.append(CadLine("ZE_PROTO_QC", (x, layout.qc_axis_y - 1.0), (x, layout.qc_axis_y + 1.0)))

    # graph area frame and grid
    for d in range(0, max_int + 1):
        y = layout.y_for_depth(float(d))
        lines.append(CadLine("ZE_PROTO_GRID", (layout.x_graph, y), (layout.x_right, y)))
    for v in range(0, int(qc_max) + 1, qc_major):
        x = _value_to_x(v, x0=layout.x_graph + 0.5, x1=180.0, vmax=qc_max)
        lines.append(CadLine("ZE_PROTO_GRID", (x, layout.header_bottom_y_mm), (x, y_bottom)))
    for v in range(0, int(fs_max) + 1, fs_major):
        x = _value_to_x(v, x0=layout.x_graph + 0.5, x1=180.0, vmax=fs_max)
        lines.append(CadLine("ZE_PROTO_GRID", (x, layout.header_bottom_y_mm), (x, y_bottom)))

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
        samples_qc.append((_value_to_x(qc_mpa, x0=layout.x_graph + 0.5, x1=180.0, vmax=qc_max), y))
        samples_fs.append((_value_to_x(fs_kpa, x0=layout.x_graph + 0.5, x1=180.0, vmax=fs_max), y))

    if len(samples_qc) >= 2:
        polys.append(CadPolyline("ZE_PROTO_QC", samples_qc))
    if len(samples_fs) >= 2:
        polys.append(CadPolyline("ZE_PROTO_FS", samples_fs))

    scene = CadScene(
        layers=list(PROTOCOL_LAYERS),
        block=CadBlock(name=block_name, base_point=(0.0, 0.0, 0.0), lines=lines, polylines=polys, texts=texts),
    )
    return ProtocolCadResult(document=doc, scene=scene, height_mm=layout.total_height_for_depth(doc.max_depth_m))
