from __future__ import annotations

from pathlib import Path
import math

from .logging import get_cad_logger
from .schema import CadLayerSpec, CadScene

_log = get_cad_logger()

# Geological protocol hatches embed full PAT line descriptors, so AutoCAD
# should treat them as custom-defined patterns rather than simple user-defined
# angle/spacing hatches.
EMBEDDED_PAT_PATTERN_TYPE = 2


def _entity_polyline_lineweight(layer_name: str) -> int | None:
    if layer_name in {"ZE_PROTO_QC", "ZE_PROTO_FS"}:
        return 30
    return None


def _offset_pattern_definition(
    definition: list[tuple[float, tuple[float, float], tuple[float, float], list[float]]] | tuple,
    *,
    dx: float,
    dy: float,
) -> list[tuple[float, tuple[float, float], tuple[float, float], list[float]]]:
    rows: list[tuple[float, tuple[float, float], tuple[float, float], list[float]]] = []
    for angle_deg, base_point, offset, dash_items in list(definition or []):
        rows.append(
            (
                float(angle_deg),
                (float(base_point[0]) + float(dx), float(base_point[1]) + float(dy)),
                (float(offset[0]), float(offset[1])),
                [float(item) for item in dash_items],
            )
        )
    return rows


def _pair(code: int, value: object) -> list[str]:
    return [f"{int(code)}\n", f"{value}\n"]


def _dxf_escape_text(text: str) -> str:
    out: list[str] = []
    for ch in str(text):
        c = ord(ch)
        if c < 128:
            out.append(ch)
        else:
            out.append(f"\\U+{c:04X}")
    return "".join(out)


def _scene_extents(scenes: list[CadScene], x_step_mm: float) -> tuple[float, float, float, float]:
    min_x = math.inf
    min_y = math.inf
    max_x = -math.inf
    max_y = -math.inf

    def _touch(x: float, y: float):
        nonlocal min_x, min_y, max_x, max_y
        min_x = min(min_x, float(x))
        min_y = min(min_y, float(y))
        max_x = max(max_x, float(x))
        max_y = max(max_y, float(y))

    for i, scene in enumerate(scenes):
        dx = float(scene.insertion_point[0]) + float(i * x_step_mm)
        dy = float(scene.insertion_point[1])
        for line in scene.block.lines:
            _touch(dx + float(line.start[0]), dy + float(line.start[1]))
            _touch(dx + float(line.end[0]), dy + float(line.end[1]))
        for poly in scene.block.polylines:
            for px, py in poly.points:
                _touch(dx + float(px), dy + float(py))
        for hatch in getattr(scene.block, "hatches", []):
            for px, py in hatch.boundary:
                _touch(dx + float(px), dy + float(py))
        for point in scene.block.points:
            _touch(dx + float(point.position[0]), dy + float(point.position[1]))
        for text in scene.block.texts:
            _touch(dx + float(text.x_mm), dy + float(text.y_mm))

    if not math.isfinite(min_x) or not math.isfinite(min_y) or not math.isfinite(max_x) or not math.isfinite(max_y):
        return (0.0, 0.0, 100.0, 100.0)
    pad = 20.0
    return (min_x - pad, min_y - pad, max_x + pad, max_y + pad)


def _write_ascii_fallback(scenes: list[CadScene], target: Path, x_step_mm: float) -> None:
    lines: list[str] = []
    ext_min_x, ext_min_y, ext_max_x, ext_max_y = _scene_extents(scenes, x_step_mm)

    def add(code: int, value: object):
        lines.extend(_pair(code, value))

    layers_map: dict[str, CadLayerSpec] = {"0": CadLayerSpec("0", color_aci=7)}
    for scene in scenes:
        for layer in scene.layers:
            layers_map[layer.name] = layer

    add(0, "SECTION")
    add(2, "HEADER")
    add(9, "$INSUNITS")
    add(70, 4)
    add(9, "$EXTMIN")
    add(10, ext_min_x)
    add(20, ext_min_y)
    add(30, 0.0)
    add(9, "$EXTMAX")
    add(10, ext_max_x)
    add(20, ext_max_y)
    add(30, 0.0)
    add(0, "ENDSEC")

    add(0, "SECTION")
    add(2, "TABLES")
    add(0, "TABLE")
    add(2, "LAYER")
    add(70, len(layers_map))
    for layer in layers_map.values():
        add(0, "LAYER")
        add(2, layer.name)
        add(70, 0)
        add(62, int(layer.color_aci))
        add(6, layer.linetype)
        if layer.lineweight is not None:
            add(370, int(layer.lineweight))
    add(0, "ENDTAB")

    add(0, "TABLE")
    add(2, "STYLE")
    add(70, 1)
    add(0, "STYLE")
    add(2, "ZE_CYR")
    add(70, 0)
    add(40, 0)
    add(41, 1)
    add(50, 0)
    add(71, 0)
    add(42, 2.5)
    add(3, "arial.ttf")
    add(4, "")
    add(0, "ENDTAB")
    add(0, "ENDSEC")

    add(0, "SECTION")
    add(2, "BLOCKS")
    for scene in scenes:
        add(0, "BLOCK")
        add(8, "0")
        add(2, scene.block.name)
        add(70, 0)
        add(10, scene.block.base_point[0])
        add(20, scene.block.base_point[1])
        add(30, scene.block.base_point[2])
        add(3, scene.block.name)
        add(1, "")

        for line in scene.block.lines:
            add(0, "LINE")
            add(8, line.layer)
            add(62, 256)
            add(10, line.start[0])
            add(20, line.start[1])
            add(30, 0.0)
            add(11, line.end[0])
            add(21, line.end[1])
            add(31, 0.0)

        for poly in scene.block.polylines:
            if len(poly.points) < 2:
                continue
            add(0, "POLYLINE")
            add(8, poly.layer)
            add(62, 256)
            poly_lineweight = _entity_polyline_lineweight(poly.layer)
            if poly_lineweight is not None:
                add(370, poly_lineweight)
            add(66, 1)
            add(70, 1 if poly.closed else 0)
            for p in poly.points:
                add(0, "VERTEX")
                add(8, poly.layer)
                add(10, p[0])
                add(20, p[1])
                add(30, 0.0)
            add(0, "SEQEND")
            add(8, poly.layer)

        # ASCII fallback keeps solid areas as closed polylines only.
        for hatch in getattr(scene.block, "hatches", []):
            if len(hatch.boundary) < 3:
                continue
            add(0, "POLYLINE")
            add(8, hatch.layer)
            add(62, int(hatch.color_aci) if hatch.color_aci is not None else 256)
            add(66, 1)
            add(70, 1)
            for p in hatch.boundary:
                add(0, "VERTEX")
                add(8, hatch.layer)
                add(10, p[0])
                add(20, p[1])
                add(30, 0.0)
            add(0, "SEQEND")
            add(8, hatch.layer)

        for point in scene.block.points:
            add(0, "POINT")
            add(8, point.layer)
            add(62, int(point.color_aci) if point.color_aci is not None else 256)
            add(10, point.position[0])
            add(20, point.position[1])
            add(30, point.position[2])

        for text in scene.block.texts:
            add(0, "TEXT")
            add(8, text.layer)
            add(7, "ZE_CYR")
            add(62, int(text.color_aci) if text.color_aci is not None else 256)
            add(10, text.x_mm)
            add(20, text.y_mm)
            add(30, 0.0)
            add(40, text.height_mm)
            add(50, float(getattr(text, "rotation_deg", 0.0) or 0.0))
            add(1, _dxf_escape_text(text.text))
            align = text.align.upper()
            if align == "CENTER":
                add(72, 1)
                add(11, text.x_mm)
                add(21, text.y_mm)
                add(31, 0.0)
            elif align == "RIGHT":
                add(72, 2)
                add(11, text.x_mm)
                add(21, text.y_mm)
                add(31, 0.0)

        add(0, "ENDBLK")
    add(0, "ENDSEC")

    add(0, "SECTION")
    add(2, "ENTITIES")
    for i, scene in enumerate(scenes):
        add(0, "INSERT")
        add(8, "ZE_CPT_TITLE")
        add(2, scene.block.name)
        add(62, 256)
        add(10, scene.insertion_point[0] + i * x_step_mm)
        add(20, scene.insertion_point[1])
        add(30, scene.insertion_point[2])
    add(0, "ENDSEC")
    add(0, "EOF")

    target.write_text("".join(lines), encoding="utf-8")


def _write_ascii_exploded(scenes: list[CadScene], target: Path, x_step_mm: float) -> None:
    lines: list[str] = []
    ext_min_x, ext_min_y, ext_max_x, ext_max_y = _scene_extents(scenes, x_step_mm)

    def add(code: int, value: object):
        lines.extend(_pair(code, value))

    layers_map: dict[str, CadLayerSpec] = {"0": CadLayerSpec("0", color_aci=7)}
    for scene in scenes:
        for layer in scene.layers:
            layers_map[layer.name] = layer

    add(0, "SECTION")
    add(2, "HEADER")
    add(9, "$INSUNITS")
    add(70, 4)
    add(9, "$EXTMIN")
    add(10, ext_min_x)
    add(20, ext_min_y)
    add(30, 0.0)
    add(9, "$EXTMAX")
    add(10, ext_max_x)
    add(20, ext_max_y)
    add(30, 0.0)
    add(0, "ENDSEC")

    add(0, "SECTION")
    add(2, "TABLES")
    add(0, "TABLE")
    add(2, "LAYER")
    add(70, len(layers_map))
    for layer in layers_map.values():
        add(0, "LAYER")
        add(2, layer.name)
        add(70, 0)
        add(62, int(layer.color_aci))
        add(6, layer.linetype)
        if layer.lineweight is not None:
            add(370, int(layer.lineweight))
    add(0, "ENDTAB")

    add(0, "TABLE")
    add(2, "STYLE")
    add(70, 1)
    add(0, "STYLE")
    add(2, "ZE_CYR")
    add(70, 0)
    add(40, 0)
    add(41, 1)
    add(50, 0)
    add(71, 0)
    add(42, 2.5)
    add(3, "arial.ttf")
    add(4, "")
    add(0, "ENDTAB")
    add(0, "ENDSEC")

    add(0, "SECTION")
    add(2, "ENTITIES")
    for i, scene in enumerate(scenes):
        dx = float(scene.insertion_point[0]) + float(i * x_step_mm)
        dy = float(scene.insertion_point[1])
        for line in scene.block.lines:
            add(0, "LINE")
            add(8, line.layer)
            add(62, 256)
            add(10, dx + line.start[0])
            add(20, dy + line.start[1])
            add(30, 0.0)
            add(11, dx + line.end[0])
            add(21, dy + line.end[1])
            add(31, 0.0)

        for poly in scene.block.polylines:
            if len(poly.points) < 2:
                continue
            add(0, "POLYLINE")
            add(8, poly.layer)
            add(62, 256)
            poly_lineweight = _entity_polyline_lineweight(poly.layer)
            if poly_lineweight is not None:
                add(370, poly_lineweight)
            add(66, 1)
            add(70, 1 if poly.closed else 0)
            for px, py in poly.points:
                add(0, "VERTEX")
                add(8, poly.layer)
                add(10, dx + px)
                add(20, dy + py)
                add(30, 0.0)
            add(0, "SEQEND")
            add(8, poly.layer)

        for hatch in getattr(scene.block, "hatches", []):
            if len(hatch.boundary) < 3:
                continue
            add(0, "POLYLINE")
            add(8, hatch.layer)
            add(62, int(hatch.color_aci) if hatch.color_aci is not None else 256)
            add(66, 1)
            add(70, 1)
            for px, py in hatch.boundary:
                add(0, "VERTEX")
                add(8, hatch.layer)
                add(10, dx + px)
                add(20, dy + py)
                add(30, 0.0)
            add(0, "SEQEND")
            add(8, hatch.layer)

        for point in scene.block.points:
            add(0, "POINT")
            add(8, point.layer)
            add(62, int(point.color_aci) if point.color_aci is not None else 256)
            add(10, dx + point.position[0])
            add(20, dy + point.position[1])
            add(30, point.position[2])

        for text in scene.block.texts:
            add(0, "TEXT")
            add(8, text.layer)
            add(7, "ZE_CYR")
            add(62, int(text.color_aci) if text.color_aci is not None else 256)
            add(10, dx + text.x_mm)
            add(20, dy + text.y_mm)
            add(30, 0.0)
            add(40, text.height_mm)
            add(50, float(getattr(text, "rotation_deg", 0.0) or 0.0))
            add(1, _dxf_escape_text(text.text))
            align = text.align.upper()
            if align == "CENTER":
                add(72, 1)
                add(11, dx + text.x_mm)
                add(21, dy + text.y_mm)
                add(31, 0.0)
            elif align == "RIGHT":
                add(72, 2)
                add(11, dx + text.x_mm)
                add(21, dy + text.y_mm)
                add(31, 0.0)
    add(0, "ENDSEC")
    add(0, "EOF")

    target.write_text("".join(lines), encoding="utf-8")


def _ensure_text_style(doc) -> None:
    if "ZE_CYR" in doc.styles:
        return
    style = doc.styles.new("ZE_CYR", dxfattribs={"font": "arial.ttf"})
    style.dxf.bigfont = ""


def _apply_layer(doc, layer: CadLayerSpec) -> None:
    if layer.name in doc.layers:
        return
    dxfattribs = {"color": int(layer.color_aci), "linetype": layer.linetype}
    if layer.lineweight is not None:
        dxfattribs["lineweight"] = int(layer.lineweight)
    layer_obj = doc.layers.new(name=layer.name, dxfattribs=dxfattribs)
    if layer.rgb is not None:
        layer_obj.rgb = tuple(int(c) for c in layer.rgb)


def write_cad_scenes_to_dxf(
    scenes: list[CadScene],
    out_path: str | Path,
    *,
    x_step_mm: float = 120.0,
    require_ezdxf: bool = False,
    validate_after_write: bool = False,
    explode_blocks: bool = False,
) -> Path:
    if not scenes:
        raise ValueError("No CAD scenes to write")

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _log.info("write_cad_scenes_to_dxf start target=%s scenes=%s", target, len(scenes))

    try:
        import ezdxf  # type: ignore
    except Exception as exc:  # pragma: no cover
        if require_ezdxf:
            raise RuntimeError("DXF export requires ezdxf runtime (fallback writer disabled for this export mode).") from exc
        _log.warning("ezdxf unavailable (%s), using ascii fallback writer", exc)
        if explode_blocks:
            _write_ascii_exploded(scenes, target, x_step_mm)
        else:
            _write_ascii_fallback(scenes, target, x_step_mm)
        if validate_after_write:
            _validate_ascii_structure(target)
        _log.info("write_cad_scenes_to_dxf done target=%s mode=fallback", target)
        return target

    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4
    ext_min_x, ext_min_y, ext_max_x, ext_max_y = _scene_extents(scenes, x_step_mm)
    doc.header["$EXTMIN"] = (ext_min_x, ext_min_y, 0.0)
    doc.header["$EXTMAX"] = (ext_max_x, ext_max_y, 0.0)
    _ensure_text_style(doc)

    def _add_scene_entities(container, scene: CadScene, *, dx: float = 0.0, dy: float = 0.0) -> None:
        for line in scene.block.lines:
            container.add_line((dx + line.start[0], dy + line.start[1]), (dx + line.end[0], dy + line.end[1]), dxfattribs={"layer": line.layer, "color": 256})
        for hatch in getattr(scene.block, "hatches", []):
            if len(hatch.boundary) < 3:
                continue
            try:
                hatch_entity = container.add_hatch(
                    color=(int(hatch.color_aci) if hatch.color_aci is not None else 256),
                    dxfattribs={"layer": hatch.layer},
                )
                hatch_entity.paths.add_polyline_path([(dx + px, dy + py) for px, py in hatch.boundary], is_closed=True)
                has_pattern = bool(getattr(hatch, "pattern_name", None) or getattr(hatch, "pattern_definition", None))
                if has_pattern:
                    pattern_name = str(getattr(hatch, "pattern_name", None) or "USER")
                    definition = _offset_pattern_definition(
                        list(getattr(hatch, "pattern_definition", []) or []),
                        dx=dx,
                        dy=dy,
                    )
                    _log.info(
                        "dxf_hatch_pattern layer=%s block=%s pattern=%s rows=%s boundary_points=%s",
                        hatch.layer,
                        scene.block.name,
                        pattern_name,
                        len(definition),
                        len(hatch.boundary),
                    )
                    hatch_entity.set_pattern_fill(
                        name=pattern_name,
                        color=(int(hatch.color_aci) if hatch.color_aci is not None else 256),
                        angle=0.0,
                        scale=1.0,
                        # Complex PAT rows should stay a custom hatch definition so
                        # AutoCAD preserves the PAT semantics instead of collapsing
                        # them into a simple user-defined hatch.
                        pattern_type=EMBEDDED_PAT_PATTERN_TYPE,
                        definition=definition,
                    )
                else:
                    hatch_entity.set_solid_fill(
                        color=(int(hatch.color_aci) if hatch.color_aci is not None else 256),
                        rgb=(tuple(int(c) for c in hatch.rgb) if hatch.rgb is not None else None),
                    )
            except Exception as exc:
                raise RuntimeError(
                    f"DXF hatch export failed (layer={hatch.layer}, points={len(hatch.boundary)}, block={scene.block.name})"
                ) from exc
        for poly in scene.block.polylines:
            if len(poly.points) < 2:
                continue
            p_attr = {"layer": poly.layer, "color": 256}
            poly_lineweight = _entity_polyline_lineweight(poly.layer)
            if poly_lineweight is not None:
                p_attr["lineweight"] = poly_lineweight
            container.add_lwpolyline([(dx + px, dy + py) for px, py in poly.points], close=bool(poly.closed), dxfattribs=p_attr)
        for point in scene.block.points:
            container.add_point(
                (dx + point.position[0], dy + point.position[1], point.position[2]),
                dxfattribs={"layer": point.layer, "color": (int(point.color_aci) if point.color_aci is not None else 256)},
            )
        for text in scene.block.texts:
            entity = container.add_text(
                text.text,
                dxfattribs={
                    "layer": text.layer,
                    "height": text.height_mm,
                    "color": (int(text.color_aci) if text.color_aci is not None else 256),
                    "style": "ZE_CYR",
                    "rotation": float(getattr(text, "rotation_deg", 0.0) or 0.0),
                },
            )
            align = text.align.upper()
            try:
                from ezdxf.enums import TextEntityAlignment  # type: ignore

                if align == "CENTER":
                    entity.set_placement((dx + text.x_mm, dy + text.y_mm), align=TextEntityAlignment.MIDDLE_CENTER)
                elif align == "RIGHT":
                    entity.set_placement((dx + text.x_mm, dy + text.y_mm), align=TextEntityAlignment.MIDDLE_RIGHT)
                else:
                    entity.set_placement((dx + text.x_mm, dy + text.y_mm), align=TextEntityAlignment.MIDDLE_LEFT)
            except Exception:
                if align == "CENTER":
                    entity.set_placement((dx + text.x_mm, dy + text.y_mm), align="MIDDLE_CENTER")
                elif align == "RIGHT":
                    entity.set_placement((dx + text.x_mm, dy + text.y_mm), align="MIDDLE_RIGHT")
                else:
                    entity.set_placement((dx + text.x_mm, dy + text.y_mm), align="MIDDLE_LEFT")

    for scene in scenes:
        for layer in scene.layers:
            _apply_layer(doc, layer)

    msp = doc.modelspace()
    if explode_blocks:
        for i, scene in enumerate(scenes):
            _add_scene_entities(
                msp,
                scene,
                dx=scene.insertion_point[0] + i * x_step_mm,
                dy=scene.insertion_point[1],
            )
    else:
        for scene in scenes:
            block = doc.blocks.new(name=scene.block.name, base_point=scene.block.base_point)
            _add_scene_entities(block, scene)
        for i, scene in enumerate(scenes):
            msp.add_blockref(
                scene.block.name,
                (scene.insertion_point[0] + i * x_step_mm, scene.insertion_point[1], scene.insertion_point[2]),
                dxfattribs={"layer": "ZE_CPT_TITLE", "color": 256},
            )

    try:
        doc.saveas(target)
    except Exception as exc:
        raise RuntimeError(f"DXF save failed for '{target}'") from exc
    if validate_after_write:
        try:
            _validate_ezdxf_file(target)
        except Exception as exc:
            raise RuntimeError(f"DXF post-write validation failed for '{target}'") from exc
    _log.info("write_cad_scenes_to_dxf done target=%s mode=ezdxf", target)
    return target


def write_cad_scene_to_dxf(scene: CadScene, out_path: str | Path) -> Path:
    return write_cad_scenes_to_dxf([scene], out_path)


def _validate_ascii_structure(path: Path) -> None:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RuntimeError("DXF contains UTF-8 BOM header, which is not allowed for fallback ASCII DXF.")
    text = raw.decode("utf-8", errors="strict")
    lines = text.splitlines()
    if not lines or lines[-1].strip() != "EOF":
        raise RuntimeError("DXF fallback file is missing EOF terminator.")
    if "SECTION" not in text or "ENDSEC" not in text:
        raise RuntimeError("DXF fallback file has invalid section structure.")
    if "ENTITIES" not in text:
        raise RuntimeError("DXF fallback file has no ENTITIES section.")


def _validate_ezdxf_file(path: Path) -> None:
    import ezdxf  # type: ignore

    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    if len(msp) <= 0:
        raise RuntimeError("DXF validation failed: ENTITIES section is empty.")
