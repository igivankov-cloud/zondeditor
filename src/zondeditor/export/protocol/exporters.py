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
    return write_cad_scenes_to_dxf(stacked, out_path, x_step_mm=0.0)


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

            for ln in scene.block.lines:
                ax.plot([ln.start[0], ln.end[0]], [ln.start[1], ln.end[1]], color="black", linewidth=0.5)
            for pl in scene.block.polylines:
                if not pl.points:
                    continue
                xs = [p[0] for p in pl.points]
                ys = [p[1] for p in pl.points]
                if pl.closed and pl.points:
                    xs.append(pl.points[0][0])
                    ys.append(pl.points[0][1])
                color = "black"
                if pl.layer == "ZE_PROTO_QC":
                    color = "#d62828"
                elif pl.layer == "ZE_PROTO_FS":
                    color = "#2563eb"
                ax.plot(xs, ys, color=color, linewidth=0.8)
            for txt in scene.block.texts:
                ha = {"LEFT": "left", "CENTER": "center", "RIGHT": "right"}.get(txt.align, "left")
                ax.text(txt.x_mm, txt.y_mm, txt.text, fontsize=5, ha=ha, va="center")

            ax.set_xlim(0.0, width_mm)
            ax.set_ylim(-float(h), 0.0)
            ax.axis("off")
            pdf.savefig(fig, bbox_inches="tight", pad_inches=0)
            plt.close(fig)

    return target
