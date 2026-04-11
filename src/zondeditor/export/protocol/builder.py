from __future__ import annotations

import math
import os
import re
from datetime import datetime
from dataclasses import dataclass

from src.zondeditor.domain.experience_column import ExperienceColumn, build_column_from_layers
from src.zondeditor.domain.hatching.registry import SOIL_TYPE_TO_HATCH_FILE, load_registered_pat_pattern, normalize_soil_type, resolve_hatch_asset
from src.zondeditor.domain.models import TestData
from src.zondeditor.export.cad.logging import get_cad_logger
from src.zondeditor.processing.calibration import Calibration, calc_qc_fs
from src.zondeditor.export.cad.schema import CadBlock, CadHatch, CadLayerSpec, CadLine, CadPolyline, CadScene, TextLabel

from .layout import DEFAULT_PROTOCOL_LAYOUT, ProtocolLayout
from .models import ProtocolBuildPack, ProtocolDocument, ProtocolLayerRow

_log = get_cad_logger()


PROTOCOL_LAYERS: tuple[CadLayerSpec, ...] = (
    CadLayerSpec("ZE_PROTO_FRAME", color_aci=7),
    CadLayerSpec("ZE_PROTO_TEXT", color_aci=7),
    CadLayerSpec("ZE_PROTO_GRID", color_aci=8, rgb=(186, 186, 186)),
    CadLayerSpec("ZE_PROTO_QC", color_aci=3, rgb=(22, 163, 74)),
    CadLayerSpec("ZE_PROTO_FS", color_aci=5, rgb=(37, 99, 235)),
    CadLayerSpec("ZE_PROTO_CUT", color_aci=8),
    CadLayerSpec("ZE_PROTO_MASK", color_aci=7, rgb=(255, 255, 255)),
    CadLayerSpec("ZE_PROTO_RULER", color_aci=7, rgb=(0, 0, 0)),
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


def _hatch_debug_enabled() -> bool:
    return str(os.getenv("ZOND_PROTO_HATCH_DEBUG", "")).strip().lower() in {"1", "true", "yes", "on"}


def _hatch_debug(event: str, **payload: object) -> None:
    if not _hatch_debug_enabled():
        return
    parts = [f"{k}={payload[k]!r}" for k in sorted(payload.keys())]
    _log.info("proto_hatch_debug %s %s", event, " ".join(parts))


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


def _infer_soil_type(*, explicit: str, description: str, ige_name: str) -> str:
    raw = normalize_soil_type(explicit)
    if raw in SOIL_TYPE_TO_HATCH_FILE:
        return raw
    hay = " ".join([str(description or ""), str(ige_name or "")]).lower().replace("\u0451", "\u0435")
    # Prefer longer keys first to avoid partial clashes (e.g., "\u043f\u0435\u0441\u043e\u043a" inside longer aliases).
    for soil_key in sorted(SOIL_TYPE_TO_HATCH_FILE.keys(), key=len, reverse=True):
        if soil_key in hay:
            return soil_key
    return raw


def _canonical_ige_key(value: str) -> str:
    raw = str(value or "").strip().lower().replace("\u0451", "\u0435")
    return "".join(ch for ch in raw if ch.isalnum())


def _extract_ige_num(value: str) -> str:
    m = re.findall(r"\d+", str(value or ""))
    return m[-1] if m else ""


def _resolve_ige_entry(registry: dict[str, dict[str, object]], ige_id: str) -> dict[str, object]:
    if ige_id in registry:
        _hatch_debug("ige_match_exact", ige_id=ige_id)
        return dict(registry.get(ige_id) or {})
    want_canon = _canonical_ige_key(ige_id)
    want_num = _extract_ige_num(ige_id)
    for key, ent in registry.items():
        key_s = str(key or "")
        if _canonical_ige_key(key_s) == want_canon:
            _hatch_debug("ige_match_canonical", ige_id=ige_id, registry_key=key_s)
            return dict(ent or {})
        if want_num and _extract_ige_num(key_s) == want_num:
            _hatch_debug("ige_match_num_key", ige_id=ige_id, registry_key=key_s, ige_num=want_num)
            return dict(ent or {})
        label = str((ent or {}).get("label") or "")
        if label and _canonical_ige_key(label) == want_canon:
            _hatch_debug("ige_match_label_canonical", ige_id=ige_id, registry_key=key_s, label=label)
            return dict(ent or {})
        if want_num and label and _extract_ige_num(label) == want_num:
            _hatch_debug("ige_match_num_label", ige_id=ige_id, registry_key=key_s, label=label, ige_num=want_num)
            return dict(ent or {})
    _hatch_debug("ige_match_miss", ige_id=ige_id)
    return {}


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
            ent = _resolve_ige_entry(reg, ige_id)
            descr = str(ent.get("notes") or ent.get("manual_notes") or ent.get("note") or getattr(it, "ige_name", "") or ige_id)
            rows.append(
                ProtocolLayerRow(
                    idx=idx,
                    from_depth_m=float(getattr(it, "from_depth", 0.0) or 0.0),
                    to_depth_m=float(getattr(it, "to_depth", 0.0) or 0.0),
                    ige_id=ige_id,
                    description=descr,
                    soil_type=_infer_soil_type(
                        explicit=str(ent.get("soil_type") or ""),
                        description=descr,
                        ige_name=str(getattr(it, "ige_name", "") or ""),
                    ),
                    abs_mark_text="",  # temporary: absolute elevation is not in data model yet
                )
            )
            _hatch_debug(
                "protocol_layer_row",
                idx=idx,
                ige_id=ige_id,
                soil_type=str(rows[-1].soil_type or ""),
                note_source=descr[:120],
            )
        max_depth = max(_max_depth(test), max((r.to_depth_m for r in rows), default=0.0))
        docs.append(
            ProtocolDocument(
                test=test,
                title=f"\u0422\u043e\u0447\u043a\u0430 \u0438\u0441\u043f\u044b\u0442\u0430\u043d\u0438\u044f: \u0422\u0421\u0417 {int(getattr(test, 'tid', 0) or 0)}",
                date_text=f"\u0414\u0430\u0442\u0430 \u0438\u0441\u043f\u044b\u0442\u0430\u043d\u0438\u044f: {_format_test_date(str(getattr(test, 'dt', '') or ''))}",
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


def _to_dxf_pattern_definition(soil_type: str) -> tuple[str, list[tuple[float, tuple[float, float], tuple[float, float], list[float]]]] | None:
    pat = load_registered_pat_pattern(soil_type)
    if pat is None:
        _hatch_debug("pattern_not_found", soil_type=soil_type)
        return None
    rows: list[tuple[float, tuple[float, float], tuple[float, float], list[float]]] = []
    for angle_deg, base_point, offset, dash_items in list(getattr(pat, "definition", ()) or ()):
        angle_rad = math.radians(float(angle_deg))
        ex_x = math.cos(angle_rad)
        ex_y = math.sin(angle_rad)
        ey_x = -math.sin(angle_rad)
        ey_y = math.cos(angle_rad)
        offset_x = float(offset[0]) * ex_x + float(offset[1]) * ey_x
        offset_y = float(offset[0]) * ex_y + float(offset[1]) * ey_y
        rows.append(
            (
                float(angle_deg),
                (float(base_point[0]), float(base_point[1])),
                (float(offset_x), float(offset_y)),
                [float(item) for item in dash_items],
            )
        )
    if not rows:
        _hatch_debug("pattern_empty_rows", soil_type=soil_type, pattern_name=str(getattr(pat, "name", "")))
        return None
    # DXF custom PATs should keep the real PAT name, not an internal UI alias.
    raw_name = str(getattr(pat, "name", "USER") or "USER")
    safe_name = "".join(ch for ch in raw_name if ch.isalnum() or ch == "_") or "USER"
    _hatch_debug(
        "pattern_built",
        soil_type=soil_type,
        pattern_name=safe_name,
        rows=len(rows),
        pat_source=str(getattr(pat, "source_file", "")),
    )
    return (safe_name, rows)


def _hex_to_rgb(value: str | None) -> tuple[int, int, int] | None:
    raw = str(value or "").strip()
    if not raw.startswith("#") or len(raw) != 7:
        return None
    try:
        return (int(raw[1:3], 16), int(raw[3:5], 16), int(raw[5:7], 16))
    except Exception:
        return None


def _section_fill_rgb(soil_type: str) -> tuple[int, int, int] | None:
    asset = resolve_hatch_asset(soil_type)
    if asset is None:
        return None
    fill_by_stem = {
        "Glina": (168, 142, 122),
        "Suglinok": (201, 162, 126),
        "Supes": (217, 194, 163),
        "Pesok": (238, 216, 168),
        "PesokGraviy": (217, 196, 140),
        "Torf": (110, 79, 58),
        "graviy": (167, 155, 138),
        "Peschanik": (207, 165, 109),
        "Argillit": (156, 107, 90),
        "Nasipnoy": (178, 154, 132),
    }
    return fill_by_stem.get(str(getattr(asset, "stem", "") or ""))


def build_protocol_scene(
    *,
    doc: ProtocolDocument,
    calibration: Calibration,
    block_name: str,
    layout: ProtocolLayout = DEFAULT_PROTOCOL_LAYOUT,
    colorize_sections: bool = False,
) -> ProtocolCadResult:
    lines: list[CadLine] = []
    hatches: list[CadHatch] = []
    texts: list[TextLabel] = []
    polys: list[CadPolyline] = []

    y_bottom = layout.y_for_depth(doc.max_depth_m)
    disable_solid = str(os.getenv("ZOND_PROTO_DISABLE_SOLID", "")).strip().lower() in {"1", "true", "yes", "on"}

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
            TextLabel("ZE_PROTO_TEXT", "\u0413\u0440\u0430\u0444\u0438\u043a \u0441\u0442\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u043e\u0433\u043e \u0437\u043e\u043d\u0434\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f", 55.0, -10.7, 2.3, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", doc.title, 55.0, -18.8, 2.3, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", "\u0421\u043e\u043f\u0440\u043e\u0442\u0438\u0432\u043b\u0435\u043d\u0438\u0435 \u043a\u043e\u043d\u0443\u0441\u0430 \u0438 \u043c\u0443\u0444\u0442\u044b  Sf = 350 \u0441\u043c.\u043a\u0432  Sq = 10 \u0441\u043c.\u043a\u0432", 55.0, -26.8, 2.3, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", doc.date_text, 55.0, -34.8, 2.3, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", "\u2116 \u043f.\u043f.", ((layout.x_no + layout.x_abs) / 2.0) + 0.25, -47.5, 1.8, rotation_deg=90.0, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", "\u0410\u0431\u0441. \u043e\u0442\u043c, \u043c", (layout.x_abs + layout.x_thickness) / 2.0, -47.5, 1.8, rotation_deg=90.0, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", "\u041c\u043e\u0449\u043d\u043e\u0441\u0442\u044c", (layout.x_thickness + layout.x_description) / 2.0, -47.5, 1.8, rotation_deg=90.0, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", "\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u0433\u0440\u0443\u043d\u0442\u0430", (layout.x_description + layout.x_section) / 2.0, -42.4, 1.9, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", "\u0420\u0430\u0437\u0440\u0435\u0437", (layout.x_section + layout.x_depth) / 2.0, -47.5, 1.8, rotation_deg=90.0, align="CENTER"),
            TextLabel("ZE_PROTO_TEXT", "\u0413\u043b\u0443\u0431\u0438\u043d\u0430", (layout.x_depth + layout.x_graph) / 2.0, -47.5, 1.8, align="CENTER", rotation_deg=90.0),
        ]
    )
    for x in (layout.x_no, layout.x_abs, layout.x_thickness, layout.x_description, layout.x_section, layout.x_depth, layout.x_graph):
        lines.append(CadLine("ZE_PROTO_FRAME", (x, layout.header_row_4), (x, layout.header_bottom_y_mm)))

    # depth grid (right graph area only, light-gray)
    max_int = int(math.floor(max(doc.max_depth_m, 0.0)))
    for d in range(0, max_int + 1):
        y = layout.y_for_depth(float(d))
        if d != 0:
            lines.append(CadLine("ZE_PROTO_GRID", (layout.x_graph, y), (layout.x_right, y)))
        # depth ruler: black/white alternating bars in 1m steps
        if d < max_int:
            y_next = layout.y_for_depth(float(d + 1))
            # clean black rectangular fill for ruler band every second meter
            if d % 2 == 0 and not disable_solid:
                hatches.append(
                    CadHatch(
                        "ZE_PROTO_RULER",
                        [
                            (layout.x_depth_ruler_black, y),
                            (layout.x_depth_ruler_white, y),
                            (layout.x_depth_ruler_white, y_next),
                            (layout.x_depth_ruler_black, y_next),
                        ],
                        color_aci=7,
                        rgb=(0, 0, 0),
                        solid=True,
                    )
                )
            lines.append(CadLine("ZE_PROTO_CUT", (layout.x_depth_ruler_black, y), (layout.x_depth_ruler_white, y)))
            lines.append(CadLine("ZE_PROTO_CUT", (layout.x_depth_ruler_black, y_next), (layout.x_depth_ruler_white, y_next)))
        if d % 2 == 0 and d != 0:
            texts.append(TextLabel("ZE_PROTO_TEXT", _fmt_tick(d), 104.1, y, 1.8, align="CENTER"))

    # layers table and section
    for row in doc.layers:
        y0 = layout.y_for_depth(row.from_depth_m)
        y1 = layout.y_for_depth(row.to_depth_m)
        # left body boundaries only by real geological intervals (no extra slicing)
        lines.append(CadLine("ZE_PROTO_FRAME", (layout.x_no, y1), (layout.x_depth, y1)))
        thickness = max(0.0, row.to_depth_m - row.from_depth_m)
        y_cell = (y0 + y1) / 2.0
        texts.append(TextLabel("ZE_PROTO_TEXT", str(row.idx), (layout.x_no + layout.x_abs) / 2.0, y_cell, 1.8, align="CENTER"))
        texts.append(TextLabel("ZE_PROTO_TEXT", row.abs_mark_text, (layout.x_abs + layout.x_thickness) / 2.0, y_cell, 1.8, align="CENTER"))
        texts.append(TextLabel("ZE_PROTO_TEXT", f"{thickness:.2f}".replace('.', ','), (layout.x_thickness + layout.x_description) / 2.0, y_cell, 1.8, align="CENTER"))

        # section: area hatch per interval (no manual line bundles)
        section_boundary = [
            (layout.x_section + 0.2, y0),
            (layout.x_depth - 0.2, y0),
            (layout.x_depth - 0.2, y1),
            (layout.x_section + 0.2, y1),
        ]
        if colorize_sections:
            fill_rgb = _section_fill_rgb(row.soil_type)
            if fill_rgb is not None:
                hatches.append(
                    CadHatch(
                        "ZE_PROTO_CUT",
                        section_boundary,
                        color_aci=7,
                        rgb=fill_rgb,
                        solid=True,
                    )
                )
        dxf_pattern = _to_dxf_pattern_definition(row.soil_type)
        if dxf_pattern is not None:
            pattern_name, pattern_rows = dxf_pattern
            _hatch_debug(
                "section_hatch_apply",
                row_idx=row.idx,
                ige_id=row.ige_id,
                soil_type=row.soil_type,
                pattern_name=pattern_name,
                rows=len(pattern_rows),
                boundary=section_boundary,
            )
            hatches.append(
                CadHatch(
                    "ZE_PROTO_CUT",
                    section_boundary,
                    color_aci=7,
                    rgb=(0, 0, 0),
                    solid=False,
                    pattern_name=pattern_name,
                    pattern_definition=pattern_rows,
                )
            )

        circle_cx = 94.2
        circle_cy = (y0 + y1) / 2.0
        radius = 2.2
        # white circular solid mask (overlay over section hatch)
        circle_mask = []
        for i in range(24):
            a = 2.0 * math.pi * float(i) / 24.0
            circle_mask.append((circle_cx + radius * math.cos(a), circle_cy + radius * math.sin(a)))
        if not disable_solid:
            hatches.append(CadHatch("ZE_PROTO_MASK", circle_mask, color_aci=7, rgb=(255, 255, 255), solid=True))
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

    texts.append(TextLabel("ZE_PROTO_FS", "\u0421\u043e\u043f\u0440\u043e\u0442\u0438\u0432\u043b\u0435\u043d\u0438\u0435 \u043d\u0430 \u0431\u043e\u043a\u043e\u0432\u043e\u0439 \u043f\u043e\u0432\u0435\u0440\u0445\u043d\u043e\u0441\u0442\u0438, Fs, \u043a\u041f\u0430", 146.0, -16.5, 2.2, align="CENTER"))
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
    texts.append(TextLabel("ZE_PROTO_QC", "\u0421\u043e\u043f\u0440\u043e\u0442\u0438\u0432\u043b\u0435\u043d\u0438\u0435 \u043f\u043e\u0434 \u043d\u0430\u043a\u043e\u043d\u0435\u0447\u043d\u0438\u043a\u043e\u043c, Qs, \u041c\u041f\u0430", 146.0, -31.5, 2.2, align="CENTER"))
    lines.append(CadLine("ZE_PROTO_QC", (layout.x_graph + 0.5, layout.qc_axis_y), (180.0, layout.qc_axis_y)))
    qc_major = 10 if is_k4 else 5
    for v in range(0, int(qc_max) + 1, qc_major):
        x = _value_to_x(v, x0=layout.x_graph + 0.5, x1=180.0, vmax=qc_max)
        lines.append(CadLine("ZE_PROTO_QC", (x, layout.qc_axis_y - 1.8), (x, layout.qc_axis_y + 1.8)))
        if v != 0:
            texts.append(TextLabel("ZE_PROTO_QC", _fmt_tick(v), x, layout.qc_axis_y - 4.0, 1.8, align="CENTER"))
    # no dense intermediate ticks for Qs: keep only major marks

    # graph area frame and grid
    for d in range(0, max_int + 1):
        y = layout.y_for_depth(float(d))
        if d != 0:
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
        block=CadBlock(name=block_name, base_point=(0.0, 0.0, 0.0), lines=lines, polylines=polys, hatches=hatches, texts=texts),
    )
    return ProtocolCadResult(document=doc, scene=scene, height_mm=layout.total_height_for_depth(doc.max_depth_m))

