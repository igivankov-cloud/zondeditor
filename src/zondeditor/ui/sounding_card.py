from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk


@dataclass(slots=True)
class SoundingCardGeometry:
    card_x0: float
    card_y0: float
    card_width: float
    header_height: float
    body_height: float
    footer_height: float
    table_width: float
    graph_width: float
    depth_width: float
    value_width: float
    inclinometer_width: float = 0.0

    @property
    def card_bounds_local(self) -> tuple[float, float, float, float]:
        return (0.0, 0.0, float(self.card_width), float(self.header_height + self.body_height + self.footer_height))

    @property
    def card_bounds_world(self) -> tuple[float, float, float, float]:
        x0 = float(self.card_x0)
        y0 = float(self.card_y0)
        _lx0, _ly0, x1, y1 = self.card_bounds_local
        return (x0, y0, x0 + x1, y0 + y1)

    @property
    def header_bounds_local(self) -> tuple[float, float, float, float]:
        return (0.0, 0.0, float(self.table_width), float(self.header_height))

    @property
    def header_bounds_world(self) -> tuple[float, float, float, float]:
        x0 = float(self.card_x0)
        y0 = float(self.card_y0)
        _lx0, _ly0, x1, y1 = self.header_bounds_local
        return (x0, y0, x0 + x1, y0 + y1)

    @property
    def body_bounds_local(self) -> tuple[float, float, float, float]:
        return (0.0, float(self.header_height), float(self.card_width), float(self.header_height + self.body_height))

    @property
    def body_bounds_world(self) -> tuple[float, float, float, float]:
        x0 = float(self.card_x0)
        y0 = float(self.card_y0)
        _lx0, ly0, x1, y1 = self.body_bounds_local
        return (x0, y0 + ly0, x0 + x1, y0 + y1)

    @property
    def footer_bounds_local(self) -> tuple[float, float, float, float]:
        top = float(self.header_height + self.body_height)
        return (0.0, top, float(self.card_width), top + float(self.footer_height))

    @property
    def footer_bounds_world(self) -> tuple[float, float, float, float]:
        x0 = float(self.card_x0)
        y0 = float(self.card_y0)
        _lx0, ly0, x1, y1 = self.footer_bounds_local
        return (x0, y0 + ly0, x0 + x1, y0 + y1)

    def world_to_local(self, x: float, y: float) -> tuple[float, float]:
        return float(x) - float(self.card_x0), float(y) - float(self.card_y0)

    def local_to_world(self, x: float, y: float) -> tuple[float, float]:
        return float(self.card_x0) + float(x), float(self.card_y0) + float(y)

    def cell_bbox_local(self, row_y0: float, row_y1: float, field: str) -> tuple[float, float, float, float]:
        x0 = 0.0
        if field == "depth":
            return (x0, row_y0, x0 + float(self.depth_width), row_y1)
        if field == "qc":
            x0 = float(self.depth_width)
            return (x0, row_y0, x0 + float(self.value_width), row_y1)
        if field == "fs":
            x0 = float(self.depth_width + self.value_width)
            return (x0, row_y0, x0 + float(self.value_width), row_y1)
        if field == "incl":
            x0 = float(self.depth_width + self.value_width * 2)
            return (x0, row_y0, x0 + float(self.inclinometer_width or self.value_width), row_y1)
        raise ValueError("bad field")

    def cell_bbox_world(self, row_y0: float, row_y1: float, field: str) -> tuple[float, float, float, float]:
        lx0, ly0, lx1, ly1 = self.cell_bbox_local(row_y0, row_y1, field)
        wx0, wy0 = self.local_to_world(lx0, ly0)
        wx1, wy1 = self.local_to_world(lx1, ly1)
        return (wx0, wy0, wx1, wy1)

    def graph_bbox_local(self, *, y0: float = 0.0, y1: float | None = None) -> tuple[float, float, float, float]:
        if y1 is None:
            y1 = float(self.body_height)
        x0 = float(self.table_width)
        return (x0, float(y0), x0 + float(self.graph_width), float(y1))

    def graph_bbox_world(self, *, y0: float = 0.0, y1: float | None = None) -> tuple[float, float, float, float]:
        lx0, ly0, lx1, ly1 = self.graph_bbox_local(y0=y0, y1=y1)
        wx0, wy0 = self.local_to_world(lx0, ly0)
        wx1, wy1 = self.local_to_world(lx1, ly1)
        return (wx0, wy0, wx1, wy1)

    def boundary_handle_world(self, *, y: float, x: float | None = None, size: float = 6.0) -> tuple[float, float, float, float]:
        handle_x = float(self.card_width - 2 if x is None else x)
        return (handle_x - size, float(y) - size, handle_x + size, float(y) + size)

    def depth_box_world(self, *, y: float, x1: float | None = None, width: float = 40.0, height: float = 18.0) -> tuple[float, float, float, float]:
        right = float(self.card_width - 14 if x1 is None else x1)
        left = right - float(width)
        half_h = float(height) / 2.0
        return (left, float(y) - half_h, right, float(y) + half_h)

    def header_anchor_world(self, *, dx: float = 0.0, dy: float = 0.0) -> tuple[float, float]:
        return self.local_to_world(float(dx), float(dy))


class SoundingCard:
    """Pilot wrapper for per-sounding UI/card APIs while the renderer is still global."""

    HEADER_CONTROLS = ("export", "lock", "edit", "dup", "trash")

    def __init__(self, master, *, editor, test_index: int, geometry: SoundingCardGeometry):
        self.editor = editor
        self.test_index = int(test_index)
        self.geometry = geometry
        if master is None:
            self.host = None
            self.header_frame = None
            self.body_canvas = None
            self.footer_frame = None
        else:
            self.host = ttk.Frame(master)
            self.header_frame = ttk.Frame(self.host)
            self.body_canvas = tk.Canvas(self.host, highlightthickness=0, background="white")
            self.footer_frame = ttk.Frame(self.host)

    def world_to_local(self, x: float, y: float) -> tuple[float, float]:
        return self.geometry.world_to_local(x, y)

    def contains_world(self, x: float, y: float) -> bool:
        x0, y0, x1, y1 = self.geometry.card_bounds_world
        return x0 <= float(x) <= x1 and y0 <= float(y) <= y1

    def section_at_world(self, x: float, y: float) -> str | None:
        if not self.contains_world(x, y):
            return None
        if self.geometry.header_bounds_world[1] <= float(y) <= self.geometry.header_bounds_world[3]:
            return "header"
        if self.geometry.body_bounds_world[1] <= float(y) <= self.geometry.body_bounds_world[3]:
            return "body"
        if self.geometry.footer_bounds_world[1] <= float(y) <= self.geometry.footer_bounds_world[3]:
            return "footer"
        return "card"

    def header_control_hit(self, x: float, y: float) -> str | None:
        hx0, hy0, hx1, hy1 = self.geometry.header_bounds_world
        header_top = hy0 + 8.0
        if not (hx0 <= float(x) <= hx1 and hy0 <= float(y) <= hy1):
            return None
        if (hx0 + 6.0) <= float(x) <= (hx0 + 20.0) and header_top <= float(y) <= (header_top + 14.0):
            return "export"
        if (hx1 - 104.0) <= float(x) <= (hx1 - 80.0) and hy0 <= float(y) <= (hy0 + 24.0):
            return "lock"
        if (hx1 - 78.0) <= float(x) <= (hx1 - 54.0) and hy0 <= float(y) <= (hy0 + 24.0):
            return "edit"
        if (hx1 - 52.0) <= float(x) <= (hx1 - 28.0) and hy0 <= float(y) <= (hy0 + 24.0):
            return "dup"
        if (hx1 - 26.0) <= float(x) <= (hx1 - 2.0) and hy0 <= float(y) <= (hy0 + 24.0):
            return "trash"
        return "header"

    def table_field_hit(self, x: float, row_y0: float, row_y1: float) -> str | None:
        lx, _ly = self.world_to_local(x, row_y0)
        if not (0.0 <= lx <= self.geometry.table_width):
            return None
        if lx < self.geometry.depth_width:
            return "depth"
        if lx < (self.geometry.depth_width + self.geometry.value_width):
            return "qc"
        if lx < (self.geometry.depth_width + self.geometry.value_width * 2):
            return "fs"
        return "incl"

    def graph_hit(self, x: float, y: float) -> bool:
        x0, y0, x1, y1 = self.geometry.graph_bbox_world(y0=0.0, y1=float(self.geometry.body_height))
        return x0 <= float(x) <= x1 and y0 <= float(y) <= y1

    def hit_test_hitboxes(self, x: float, y: float, hitboxes: list[dict], *, kinds: tuple[str, ...] | None = None):
        for hit in hitboxes or []:
            if int(hit.get("ti", -1)) != self.test_index:
                continue
            if kinds is not None and str(hit.get("kind") or "") not in kinds:
                continue
            bx0, by0, bx1, by1 = hit.get("bbox", (0.0, 0.0, 0.0, 0.0))
            if bx0 <= float(x) <= bx1 and by0 <= float(y) <= by1:
                return hit
        return None

    def anchor_world(self, *, dx: float = 0.0, dy: float = 0.0) -> tuple[float, float]:
        return self.geometry.header_anchor_world(dx=dx, dy=dy)

    def cell_bbox_world(self, row_y0: float, row_y1: float, field: str) -> tuple[float, float, float, float]:
        return self.geometry.cell_bbox_world(row_y0, row_y1, field)

    def graph_bbox_world(self, *, y0: float = 0.0, y1: float | None = None) -> tuple[float, float, float, float]:
        return self.geometry.graph_bbox_world(y0=y0, y1=y1)

    def cell_editor_rect(self, row_y0: float, row_y1: float, field: str) -> tuple[float, float, float, float]:
        x0, y0, x1, y1 = self.cell_bbox_world(row_y0, row_y1, field)
        return (x0 + 1.0, y0 + 1.0, x1 - 1.0, y1 - 1.0)

    def depth0_editor_rect(self, row_y0: float, row_y1: float) -> tuple[float, float, float, float]:
        return self.cell_editor_rect(row_y0, row_y1, "depth")

    def boundary_editor_rect(self, bbox: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        x0, y0, x1, y1 = bbox
        return (float(x0), float(y0), float(x1), float(y1))

    def header_anchor_root(self, *, dx: float = 0.0, dy: float = 0.0) -> tuple[int, int]:
        x, y = self.anchor_world(dx=dx, dy=dy)
        return self.editor._header_world_to_root(x, y)

    def popup_anchor_root(self, x: float, y: float, *, section: str = "body") -> tuple[int, int]:
        if section == "header":
            return self.editor._header_world_to_root(x, y)
        return self.editor._body_world_to_root(x, y)

    def make_hitbox(self, *, kind: str, bbox: tuple[float, float, float, float], boundary: int | None = None, extra: dict | None = None) -> dict:
        data = {
            "kind": str(kind),
            "ti": int(self.test_index),
            "bbox": tuple(float(v) for v in bbox),
        }
        if boundary is not None:
            data["boundary"] = int(boundary)
        if extra:
            data.update(dict(extra))
        return data

    def render_header(
        self,
        canvas,
        *,
        title: str,
        datetime_text: str,
        header_fill: str,
        header_text: str,
        header_icon: str,
        export_on: bool,
        lock_on: bool,
        hover: tuple | None,
        icon_calendar: str,
        icon_copy: str,
        icon_delete: str,
        icon_font,
        hdr_h: float,
        show_inclinometer: bool,
    ) -> dict[str, tuple[float, float, float, float]]:
        x0, y0, x1, y1 = self.geometry.header_bounds_world
        canvas.create_rectangle(x0, y0, x1, y1, fill=header_fill, outline="#d9d9d9")

        top_pad = 8.0
        row_center_y = y0 + top_pad + 6.0
        cb_s = 14.0
        cb_x0 = x0 + 6.0
        cb_y0 = row_center_y - cb_s / 2.0
        canvas.create_rectangle(cb_x0, cb_y0, cb_x0 + cb_s, cb_y0 + cb_s, fill="white", outline="#b9b9b9")
        if export_on:
            canvas.create_line(cb_x0 + 3, cb_y0 + 7, cb_x0 + 6, cb_y0 + 10, cb_x0 + 11, cb_y0 + 4, fill="#2563eb", width=2, capstyle="round", joinstyle="round")

        title_x = cb_x0 + cb_s + 8.0
        canvas.create_text(title_x, row_center_y, anchor="w", text=title, font=("Segoe UI", 9, "bold"), fill=header_text)
        if datetime_text:
            canvas.create_text(title_x, row_center_y + 18.0, anchor="w", text=datetime_text, font=("Segoe UI", 9), fill=header_text)

        ico_y = y0 + 14.0
        lock_x, edit_x, dup_x, trash_x = (x1 - 92.0), (x1 - 66.0), (x1 - 40.0), (x1 - 14.0)
        box_w, box_h = 22.0, 20.0
        controls = {
            "lock": (lock_x - box_w / 2, ico_y - box_h / 2, lock_x + box_w / 2, ico_y + box_h / 2),
            "edit": (edit_x - box_w / 2, ico_y - box_h / 2, edit_x + box_w / 2, ico_y + box_h / 2),
            "dup": (dup_x - box_w / 2, ico_y - box_h / 2, dup_x + box_w / 2, ico_y + box_h / 2),
            "trash": (trash_x - box_w / 2, ico_y - box_h / 2, trash_x + box_w / 2, ico_y + box_h / 2),
        }
        for kind, rect in controls.items():
            if hover == (kind, self.test_index):
                canvas.create_rectangle(*rect, fill="#e9e9e9", outline="")
        canvas.create_text(lock_x, ico_y, text=("🔒" if lock_on else "🔓"), font=("Segoe UI", 10), fill=header_icon, anchor="center")
        canvas.create_text(edit_x, ico_y, text=icon_calendar, font=icon_font, fill=header_icon, anchor="center")
        canvas.create_text(dup_x, ico_y, text=icon_copy, font=icon_font, fill=header_icon, anchor="center")
        canvas.create_text(trash_x, ico_y, text=icon_delete, font=icon_font, fill=header_icon, anchor="center")

        sh_y = y0 + hdr_h - top_pad
        canvas.create_text(x0 + self.geometry.depth_width / 2, sh_y, text="H, м", font=("Segoe UI", 9), fill=header_text)
        canvas.create_text(x0 + self.geometry.depth_width + self.geometry.value_width / 2, sh_y, text="qc", font=("Segoe UI", 9), fill=header_text)
        canvas.create_text(x0 + self.geometry.depth_width + self.geometry.value_width + self.geometry.value_width / 2, sh_y, text="fs", font=("Segoe UI", 9), fill=header_text)
        if show_inclinometer:
            canvas.create_text(x0 + self.geometry.depth_width + self.geometry.value_width * 2 + self.geometry.value_width / 2, sh_y, text="U", font=("Segoe UI", 9), fill=header_text)
        return {"header": (x0, y0, x1, y1), "export": (cb_x0, cb_y0, cb_x0 + cb_s, cb_y0 + cb_s), **controls}

    def render_body_cell(self, canvas, *, row_y0: float, row_y1: float, field: str, text: str, fill: str, text_color: str):
        x0, y0, x1, y1 = self.geometry.cell_bbox_world(row_y0, row_y1, field)
        canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="#d9d9d9")
        anchor = "e"
        tx = x1 - 4.0
        if field == "depth":
            text_color = text_color or "#555"
        canvas.create_text(tx, (y0 + y1) / 2.0, text=text, anchor=anchor, fill=text_color, font=("Segoe UI", 9))
        return (x0, y0, x1, y1)

    def render_ownership_snapshot(self) -> dict[str, object]:
        return {
            "card": int(self.test_index),
            "owned": ["header", "body_table_cells", "card_hit_testing", "editor_rects", "popup_anchors"],
            "legacy": ["graphs", "ige_layers", "layer_handles", "global_canvas_lifecycle"],
        }

    def future_graph_interface(self) -> dict[str, str]:
        return {
            "graph_rect": "card.graph_bbox_world(...)",
            "layer_overlay_targets": "card.make_hitbox(...) + future card.render_graph_overlay(...)",
            "graph_lines": "future card.render_graph(...)",
        }
