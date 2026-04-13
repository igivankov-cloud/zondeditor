from __future__ import annotations

import math
from pathlib import Path

from src.zondeditor.export.cad.dxf_writer import write_cad_scenes_to_dxf
from src.zondeditor.export.cad.schema import CadHatch, CadScene
from src.zondeditor.domain.hatching import clip_segment_to_rect


def export_protocols_to_dxf(*, scenes: list[CadScene], heights_mm: list[float], out_path: str | Path, gap_mm: float = 10.0) -> Path:
    y_cursor = 0.0
    stacked: list[CadScene] = []
    for scene, h in zip(scenes, heights_mm):
        stacked.append(CadScene(layers=scene.layers, block=scene.block, insertion_point=(0.0, y_cursor, 0.0)))
        y_cursor -= float(h) + float(gap_mm)
    try:
        return write_cad_scenes_to_dxf(
            stacked,
            out_path,
            x_step_mm=0.0,
            require_ezdxf=True,
            validate_after_write=True,
            explode_blocks=True,
        )
    except Exception as exc:
        raise RuntimeError(f"Protocol DXF export failed at writer stage: {type(exc).__name__}: {exc}") from exc


_A4_WIDTH_MM = 210.0
_A4_HEIGHT_MM = 297.0
_PAGE_MARGIN_MM = 10.0


def _resolve_scene_bounds(scene: CadScene, fallback_height_mm: float) -> tuple[float, float, float, float]:
    min_x = 0.0
    max_x = 0.0
    min_y = -float(fallback_height_mm)
    max_y = 0.0

    def _include_point(x: float, y: float) -> None:
        nonlocal min_x, max_x, min_y, max_y
        min_x = min(min_x, float(x))
        max_x = max(max_x, float(x))
        min_y = min(min_y, float(y))
        max_y = max(max_y, float(y))

    for ln in scene.block.lines:
        _include_point(*ln.start)
        _include_point(*ln.end)
    for pl in scene.block.polylines:
        for pt in pl.points:
            _include_point(*pt)
    for hatch in scene.block.hatches:
        for pt in hatch.boundary:
            _include_point(*pt)
    for txt in scene.block.texts:
        _include_point(txt.x_mm, txt.y_mm)

    return (min_x, min_y, max_x, max_y)


def _rect_boundary(boundary: list[tuple[float, float]], tol: float = 1e-6) -> tuple[float, float, float, float] | None:
    if len(boundary) < 4:
        return None
    xs = [float(pt[0]) for pt in boundary]
    ys = [float(pt[1]) for pt in boundary]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    corners = {
        (min_x, min_y),
        (min_x, max_y),
        (max_x, min_y),
        (max_x, max_y),
    }
    for x, y in boundary:
        if not any(abs(float(x) - cx) <= tol and abs(float(y) - cy) <= tol for cx, cy in corners):
            return None
    return (min_x, min_y, max_x, max_y)


def _pattern_sequence_segments(
    *,
    anchor_x: float,
    anchor_y: float,
    ux: float,
    uy: float,
    t1: float,
    t2: float,
    dash_items: list[float],
) -> tuple[list[tuple[tuple[float, float], tuple[float, float]]], list[tuple[float, float]]]:
    if not dash_items:
        return ([((anchor_x + (t1 * ux), anchor_y + (t1 * uy)), (anchor_x + (t2 * ux), anchor_y + (t2 * uy)))], [])

    total = sum(abs(float(item)) for item in dash_items)
    if total <= 1e-9:
        return ([((anchor_x + (t1 * ux), anchor_y + (t1 * uy)), (anchor_x + (t2 * ux), anchor_y + (t2 * uy)))], [])

    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    dots: list[tuple[float, float]] = []
    n_start = int(math.floor(t1 / total)) - 1
    n_end = int(math.ceil(t2 / total)) + 1
    for n in range(n_start, n_end + 1):
        cursor = n * total
        for item in dash_items:
            value = float(item)
            if value > 0.0:
                seg_start = cursor
                seg_end = cursor + value
                if seg_end >= t1 and seg_start <= t2 and seg_end > seg_start:
                    start_t = max(t1, seg_start)
                    end_t = min(t2, seg_end)
                    if end_t > start_t:
                        segments.append(
                            (
                                (anchor_x + (start_t * ux), anchor_y + (start_t * uy)),
                                (anchor_x + (end_t * ux), anchor_y + (end_t * uy)),
                            )
                        )
                cursor += value
            elif value < 0.0:
                cursor += abs(value)
            else:
                if t1 <= cursor <= t2:
                    dots.append((anchor_x + (cursor * ux), anchor_y + (cursor * uy)))
    return (segments, dots)


def _render_pattern_hatch(ax, hatch: CadHatch) -> None:
    from matplotlib.patches import Circle  # type: ignore

    rect = _rect_boundary(hatch.boundary)
    if rect is None:
        xs = [pt[0] for pt in hatch.boundary] + [hatch.boundary[0][0]]
        ys = [pt[1] for pt in hatch.boundary] + [hatch.boundary[0][1]]
        ax.plot(xs, ys, color="black", linewidth=0.4, zorder=1.5)
        return

    x0, y0, x1, y1 = rect
    corners = ((x0, y0), (x0, y1), (x1, y0), (x1, y1))
    dot_radius = 0.22
    for angle_deg, base_point, offset, dash_items in hatch.pattern_definition:
        angle_rad = math.radians(float(angle_deg))
        ux = math.cos(angle_rad)
        uy = math.sin(angle_rad)
        nx = -math.sin(angle_rad)
        ny = math.cos(angle_rad)
        off_x = float(offset[0])
        off_y = float(offset[1])
        k_bounds: list[float] = []
        if abs(off_x) > 1e-9:
            xs = [x0, x1]
            k_bounds.extend((xx - float(base_point[0])) / off_x for xx in xs)
        if abs(off_y) > 1e-9:
            ys = [y0, y1]
            k_bounds.extend((yy - float(base_point[1])) / off_y for yy in ys)
        offset_proj = (off_x * nx) + (off_y * ny)
        if abs(offset_proj) > 1e-9:
            rect_min = min((cx * nx) + (cy * ny) for cx, cy in corners)
            rect_max = max((cx * nx) + (cy * ny) for cx, cy in corners)
            base_proj = (float(base_point[0]) * nx) + (float(base_point[1]) * ny)
            k_bounds.extend([(rect_min - base_proj) / offset_proj, (rect_max - base_proj) / offset_proj])
        if not k_bounds:
            k_values = range(0, 1)
        else:
            k0 = int(math.floor(min(k_bounds))) - 4
            k1 = int(math.ceil(max(k_bounds))) + 4
            if k1 < k0:
                k0, k1 = k1, k0
            k_values = range(k0, k1 + 1)

        for k in k_values:
            anchor_x = float(base_point[0]) + (k * float(offset[0]))
            anchor_y = float(base_point[1]) + (k * float(offset[1]))
            half_len = max(math.hypot(cx - anchor_x, cy - anchor_y) for cx, cy in corners) + 1.0
            clipped = clip_segment_to_rect(
                anchor_x - (ux * half_len),
                anchor_y - (uy * half_len),
                anchor_x + (ux * half_len),
                anchor_y + (uy * half_len),
                x0,
                y0,
                x1,
                y1,
            )
            if not clipped:
                continue
            cx1, cy1, cx2, cy2 = clipped
            t1 = ((cx1 - anchor_x) * ux) + ((cy1 - anchor_y) * uy)
            t2 = ((cx2 - anchor_x) * ux) + ((cy2 - anchor_y) * uy)
            if t2 < t1:
                t1, t2 = t2, t1
            segments, dots = _pattern_sequence_segments(
                anchor_x=anchor_x,
                anchor_y=anchor_y,
                ux=ux,
                uy=uy,
                t1=t1,
                t2=t2,
                dash_items=[float(item) for item in dash_items],
            )
            for start, end in segments:
                ax.plot([start[0], end[0]], [start[1], end[1]], color="black", linewidth=0.35, zorder=1.5)
            for dot_x, dot_y in dots:
                ax.add_patch(Circle((dot_x, dot_y), radius=dot_radius, facecolor="black", edgecolor="black", linewidth=0.0, zorder=1.5))


def export_protocols_to_pdf(*, scenes: list[CadScene], heights_mm: list[float], out_path: str | Path) -> Path:
    import matplotlib.pyplot as plt  # type: ignore
    from matplotlib.backends.backend_pdf import PdfPages  # type: ignore

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(target) as pdf:
        for scene, h in zip(scenes, heights_mm):
            min_x, min_y, max_x, max_y = _resolve_scene_bounds(scene, float(h))
            content_w_mm = max(1.0, max_x - min_x)
            content_h_mm = max(1.0, max_y - min_y)
            page_w_mm = max(_A4_WIDTH_MM, content_w_mm + (_PAGE_MARGIN_MM * 2.0))
            page_h_mm = max(_A4_HEIGHT_MM, content_h_mm + (_PAGE_MARGIN_MM * 2.0))
            fig_w = max(4.0, page_w_mm / 25.4)
            fig_h = max(4.0, page_h_mm / 25.4)
            fig, ax = plt.subplots(figsize=(fig_w, fig_h))
            ax.set_aspect("equal")

            def _layer_color(layer: str) -> str:
                if layer in {"ZE_PROTO_QC"}:
                    return "#0b8f2a"
                if layer in {"ZE_PROTO_FS"}:
                    return "#0b45ff"
                if layer in {"ZE_PROTO_GRID"}:
                    return "#b7b7b7"
                return "black"

            for ln in scene.block.lines:
                ax.plot([ln.start[0], ln.end[0]], [ln.start[1], ln.end[1]], color=_layer_color(ln.layer), linewidth=0.5, zorder=2.0)
            for hatch in getattr(scene.block, "hatches", []):
                if len(hatch.boundary) < 3:
                    continue
                xs = [p[0] for p in hatch.boundary] + [hatch.boundary[0][0]]
                ys = [p[1] for p in hatch.boundary] + [hatch.boundary[0][1]]
                col = _layer_color(hatch.layer)
                if getattr(hatch, "rgb", None) is not None:
                    rr, gg, bb = hatch.rgb
                    col = f"#{int(rr):02x}{int(gg):02x}{int(bb):02x}"
                if hatch.solid:
                    fill_zorder = 3.5 if hatch.layer == "ZE_PROTO_MASK" else 0.8
                    ax.fill(xs, ys, color=col, linewidth=0, zorder=fill_zorder)
                    continue
                if hatch.pattern_definition:
                    _render_pattern_hatch(ax, hatch)
                    continue
                ax.plot(xs, ys, color=col, linewidth=0.4, zorder=1.2)
            for pl in scene.block.polylines:
                if not pl.points:
                    continue
                xs = [p[0] for p in pl.points]
                ys = [p[1] for p in pl.points]
                if pl.closed and pl.points:
                    xs.append(pl.points[0][0])
                    ys.append(pl.points[0][1])
                color = _layer_color(pl.layer)
                ax.plot(xs, ys, color=color, linewidth=0.8, zorder=4.0)
            for txt in scene.block.texts:
                ha = {"LEFT": "left", "CENTER": "center", "RIGHT": "right"}.get(txt.align, "left")
                ax.text(
                    txt.x_mm,
                    txt.y_mm,
                    txt.text,
                    fontsize=5,
                    ha=ha,
                    va="center",
                    color=_layer_color(txt.layer),
                    rotation=float(getattr(txt, "rotation_deg", 0.0) or 0.0),
                    zorder=5.0,
                )

            ax.set_xlim(min_x - _PAGE_MARGIN_MM, max_x + _PAGE_MARGIN_MM)
            ax.set_ylim(min_y - _PAGE_MARGIN_MM, max_y + _PAGE_MARGIN_MM)
            ax.axis("off")
            pdf.savefig(fig)
            plt.close(fig)

    return target
