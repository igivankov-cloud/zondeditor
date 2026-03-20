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

    def __init__(self, master, *, test_index: int, geometry: SoundingCardGeometry):
        self.test_index = int(test_index)
        self.geometry = geometry
        self.host = ttk.Frame(master)
        self.header_frame = ttk.Frame(self.host)
        self.body_canvas = tk.Canvas(self.host, highlightthickness=0, background="white")
        self.footer_frame = ttk.Frame(self.host)

    def world_to_local(self, x: float, y: float) -> tuple[float, float]:
        return self.geometry.world_to_local(x, y)

    def anchor_world(self, *, dx: float = 0.0, dy: float = 0.0) -> tuple[float, float]:
        return self.geometry.header_anchor_world(dx=dx, dy=dy)

    def cell_bbox_world(self, row_y0: float, row_y1: float, field: str) -> tuple[float, float, float, float]:
        return self.geometry.cell_bbox_world(row_y0, row_y1, field)

    def graph_bbox_world(self, *, y0: float = 0.0, y1: float | None = None) -> tuple[float, float, float, float]:
        return self.geometry.graph_bbox_world(y0=y0, y1=y1)
