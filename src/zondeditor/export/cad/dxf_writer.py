from __future__ import annotations

from pathlib import Path

from .logging import get_cad_logger
from .schema import CadScene

_log = get_cad_logger()


def _pair(code: int, value: object) -> list[str]:
    return [f"{int(code)}\n", f"{value}\n"]


def _write_ascii_fallback(scene: CadScene, target: Path) -> None:
    lines: list[str] = []

    def add(code: int, value: object):
        lines.extend(_pair(code, value))

    # HEADER
    add(0, "SECTION")
    add(2, "HEADER")
    add(9, "$INSUNITS")
    add(70, 4)
    add(0, "ENDSEC")

    # TABLES / LAYER
    add(0, "SECTION")
    add(2, "TABLES")
    add(0, "TABLE")
    add(2, "LAYER")
    add(70, len(scene.layers) + 1)

    add(0, "LAYER")
    add(2, "0")
    add(70, 0)
    add(62, 7)
    add(6, "CONTINUOUS")

    for layer in scene.layers:
        add(0, "LAYER")
        add(2, layer.name)
        add(70, 0)
        add(62, int(layer.color_aci))
        add(6, layer.linetype)

    add(0, "ENDTAB")
    add(0, "ENDSEC")

    # BLOCKS
    add(0, "SECTION")
    add(2, "BLOCKS")
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

    for point in scene.block.points:
        add(0, "POINT")
        add(8, point.layer)
        add(62, 256)
        add(10, point.position[0])
        add(20, point.position[1])
        add(30, point.position[2])

    for text in scene.block.texts:
        add(0, "TEXT")
        add(8, text.layer)
        add(62, 256)
        add(10, text.x_mm)
        add(20, text.y_mm)
        add(30, 0.0)
        add(40, text.height_mm)
        add(1, text.text)
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

    # ENTITIES
    add(0, "SECTION")
    add(2, "ENTITIES")
    add(0, "INSERT")
    add(8, "ZE_CPT_SERVICE")
    add(2, scene.block.name)
    add(62, 256)
    add(10, scene.insertion_point[0])
    add(20, scene.insertion_point[1])
    add(30, scene.insertion_point[2])
    add(0, "ENDSEC")
    add(0, "EOF")

    target.write_text("".join(lines), encoding="utf-8")


def write_cad_scene_to_dxf(scene: CadScene, out_path: str | Path) -> Path:
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _log.info("write_cad_scene_to_dxf start target=%s block=%s", target, scene.block.name)

    try:
        import ezdxf  # type: ignore
    except Exception as exc:  # pragma: no cover - runtime dependency
        _log.warning("ezdxf unavailable (%s), using ascii fallback writer", exc)
        _write_ascii_fallback(scene, target)
        _log.info("write_cad_scene_to_dxf done target=%s mode=fallback", target)
        return target

    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4  # millimeters

    for layer in scene.layers:
        if layer.name in doc.layers:
            continue
        layer_obj = doc.layers.new(name=layer.name, dxfattribs={"color": int(layer.color_aci), "linetype": layer.linetype})
        if layer.rgb is not None:
            layer_obj.rgb = tuple(int(c) for c in layer.rgb)

    block = doc.blocks.new(name=scene.block.name, base_point=scene.block.base_point)

    for line in scene.block.lines:
        block.add_line(line.start, line.end, dxfattribs={"layer": line.layer, "color": 256})

    for poly in scene.block.polylines:
        if len(poly.points) < 2:
            continue
        block.add_lwpolyline(poly.points, close=bool(poly.closed), dxfattribs={"layer": poly.layer, "color": 256})

    for point in scene.block.points:
        block.add_point(point.position, dxfattribs={"layer": point.layer, "color": 256})

    for text in scene.block.texts:
        entity = block.add_text(text.text, dxfattribs={"layer": text.layer, "height": text.height_mm, "color": 256})
        align = text.align.upper()
        if align == "CENTER":
            entity.set_placement((text.x_mm, text.y_mm), align="MIDDLE_CENTER")
        elif align == "RIGHT":
            entity.set_placement((text.x_mm, text.y_mm), align="MIDDLE_RIGHT")
        else:
            entity.set_placement((text.x_mm, text.y_mm), align="MIDDLE_LEFT")

    msp = doc.modelspace()
    msp.add_blockref(scene.block.name, scene.insertion_point, dxfattribs={"layer": "ZE_CPT_SERVICE", "color": 256})

    doc.saveas(target)
    _log.info("write_cad_scene_to_dxf done target=%s mode=ezdxf", target)
    return target
