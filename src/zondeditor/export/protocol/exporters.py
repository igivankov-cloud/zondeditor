from __future__ import annotations

from pathlib import Path

from src.zondeditor.export.cad.dxf_writer import write_cad_scenes_to_dxf
from src.zondeditor.export.cad.schema import CadScene


def export_protocols_to_dxf(*, scenes: list[CadScene], heights_mm: list[float], out_path: str | Path, gap_mm: float = 10.0) -> Path:
    y_cursor = 0.0
    stacked: list[CadScene] = []
    for scene, h in zip(scenes, heights_mm):
        stacked.append(CadScene(layers=scene.layers, block=scene.block, insertion_point=(0.0, y_cursor, 0.0)))
        y_cursor -= float(h) + float(gap_mm)
    return write_cad_scenes_to_dxf(stacked, out_path, x_step_mm=0.0, require_ezdxf=True, validate_after_write=True)


def export_protocols_to_pdf(*, scenes: list[CadScene], heights_mm: list[float], out_path: str | Path) -> Path:
    import matplotlib.pyplot as plt  # type: ignore
    from matplotlib.backends.backend_pdf import PdfPages  # type: ignore

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(target) as pdf:
        for scene, h in zip(scenes, heights_mm):
            width_mm = 183.1
            fig_w = max(4.0, width_mm / 25.4)
            fig_h = max(4.0, (float(h) + 8.0) / 25.4)
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
                ax.plot([ln.start[0], ln.end[0]], [ln.start[1], ln.end[1]], color=_layer_color(ln.layer), linewidth=0.5)
            for h in getattr(scene.block, "hatches", []):
                if len(h.boundary) < 3:
                    continue
                xs = [p[0] for p in h.boundary] + [h.boundary[0][0]]
                ys = [p[1] for p in h.boundary] + [h.boundary[0][1]]
                col = _layer_color(h.layer)
                if getattr(h, "rgb", None) is not None:
                    rr, gg, bb = h.rgb
                    col = f"#{int(rr):02x}{int(gg):02x}{int(bb):02x}"
                ax.fill(xs, ys, color=col, linewidth=0)
            for pl in scene.block.polylines:
                if not pl.points:
                    continue
                xs = [p[0] for p in pl.points]
                ys = [p[1] for p in pl.points]
                if pl.closed and pl.points:
                    xs.append(pl.points[0][0])
                    ys.append(pl.points[0][1])
                color = _layer_color(pl.layer)
                ax.plot(xs, ys, color=color, linewidth=0.8)
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
                )

            ax.set_xlim(0.0, width_mm)
            ax.set_ylim(-float(h), 0.0)
            ax.axis("off")
            pdf.savefig(fig, bbox_inches="tight", pad_inches=0)
            plt.close(fig)

    return target
