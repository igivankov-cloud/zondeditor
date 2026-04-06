from __future__ import annotations

from pathlib import Path

from .schema import CadScene


def write_cad_scene_to_dxf(scene: CadScene, out_path: str | Path) -> Path:
    try:
        import ezdxf
    except Exception as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError("DXF export requires ezdxf. Install: pip install ezdxf") from exc

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)

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
    return target
