from __future__ import annotations

from dataclasses import dataclass
import sys
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
    """Card-local UI owner for geometry, render lifecycle and vertical scroll state."""

    HEADER_CONTROLS = ("export", "lock", "edit", "dup", "trash")
    REDRAW_PARTS = ("body", "graph", "layers", "overlays")

    def __init__(self, master, *, editor, test_index: int, geometry: SoundingCardGeometry):
        self.editor = editor
        self.test_index = int(test_index)
        self.geometry = geometry
        self._body_view_height = float(getattr(geometry, "body_height", 0.0) or 0.0)
        self._body_content_height = float(getattr(geometry, "body_height", 0.0) or 0.0)
        self._body_y0 = 0.0
        self._invalid_parts = set(self.REDRAW_PARTS)
        self._redraw_callbacks: dict[str, object] = {}
        if master is None:
            self.host = None
            self.header_frame = None
            self.footer_frame = None
        else:
            self.host = ttk.Frame(master)
            self.header_frame = ttk.Frame(self.host)
            self.footer_frame = ttk.Frame(self.host)
        self.header_canvas = None
        self.body_canvas = None
        self._header_window_id = None
        self._body_window_id = None
        self._header_host = None
        self._body_host = None

    def update_geometry(self, geometry: SoundingCardGeometry):
        self.geometry = geometry

    def _widget_master(self, widget):
        if widget is None:
            return None
        master = getattr(widget, "master", None)
        if master is not None:
            return master
        try:
            return widget.nametowidget(widget.winfo_parent())
        except Exception:
            return None

    def _log_mount_error(self, target: str, exc: Exception, *, host=None, widget=None):
        print(
            f"[SoundingCard.mount_targets] {target} failed for card={self.test_index}: {exc}; "
            f"host={host!r} host_widget={getattr(host, 'widgetName', None)!r} "
            f"widget={widget!r} widget_master={self._widget_master(widget)!r}",
            file=sys.stderr,
        )

    def _ensure_canvas_parent(self, attr_name: str, host, **kwargs):
        canvas = getattr(self, attr_name)
        master = self._widget_master(canvas)
        if canvas is not None and host is not None and master is not host:
            print(
                f"[SoundingCard.mount_targets] recreating {attr_name} for card={self.test_index}: "
                f"wrong_master={master!r} expected_host={host!r}",
                file=sys.stderr,
            )
            try:
                canvas.destroy()
            except Exception as exc:
                self._log_mount_error(f"destroy {attr_name}", exc, host=host, widget=canvas)
            canvas = None
            setattr(self, attr_name, None)
        if canvas is None and host is not None:
            try:
                canvas = tk.Canvas(host, highlightthickness=0, background="white")
                setattr(self, attr_name, canvas)
            except Exception as exc:
                self._log_mount_error(f"create {attr_name}", exc, host=host, widget=canvas)
                return None
        if canvas is not None:
            try:
                canvas.configure(**kwargs)
            except Exception as exc:
                self._log_mount_error(f"configure {attr_name}", exc, host=host, widget=canvas)
        return canvas

    def mount_targets(self, *, header_host=None, body_host=None, body_view_height: float | None = None):
        self._header_host = header_host or self._header_host
        self._body_host = body_host or self._body_host
        if body_view_height is not None:
            self.set_body_scroll_context(view_height=float(body_view_height))
        header_canvas = self._ensure_canvas_parent(
            "header_canvas",
            self._header_host,
            width=int(self.geometry.table_width),
            height=int(self.geometry.header_height),
            scrollregion=(0, 0, int(self.geometry.table_width), int(self.geometry.header_height)),
        )
        body_canvas = self._ensure_canvas_parent(
            "body_canvas",
            self._body_host,
            width=int(self.geometry.card_width),
            height=int(max(1.0, float(self._body_view_height or self.geometry.body_height))),
            scrollregion=(0, 0, int(self.geometry.card_width), int(max(self.geometry.body_height, self._body_content_height))),
            yscrollincrement=1,
        )
        if header_canvas is not None and self._header_host is not None:
            try:
                if self._header_window_id is None:
                    self._header_window_id = self._header_host.create_window((float(self.geometry.card_x0), 0.0), window=header_canvas, anchor="nw")
                else:
                    self._header_host.coords(self._header_window_id, float(self.geometry.card_x0), 0.0)
            except Exception as exc:
                self._log_mount_error("header create_window", exc, host=self._header_host, widget=header_canvas)
        if body_canvas is not None and self._body_host is not None:
            try:
                if self._body_window_id is None:
                    self._body_window_id = self._body_host.create_window((float(self.geometry.card_x0), 0.0), window=body_canvas, anchor="nw")
                else:
                    self._body_host.coords(self._body_window_id, float(self.geometry.card_x0), 0.0)
            except Exception as exc:
                self._log_mount_error("body create_window", exc, host=self._body_host, widget=body_canvas)
        self._sync_body_canvas_view()

    def world_to_local(self, x: float, y: float) -> tuple[float, float]:
        return self.geometry.world_to_local(x, y)

    def set_body_scroll_context(self, *, view_height: float | None = None, content_height: float | None = None, y0: float | None = None):
        if view_height is not None:
            self._body_view_height = max(0.0, float(view_height))
        if content_height is not None:
            self._body_content_height = max(self._body_view_height, float(content_height))
        max_y0 = self.max_body_y0()
        if y0 is None:
            y0 = self._body_y0
        self._body_y0 = min(max(float(y0), 0.0), max_y0)
        self._sync_body_canvas_view()
        return self.body_yview()

    def max_body_y0(self) -> float:
        return max(0.0, float(self._body_content_height) - float(self._body_view_height))

    def _body_viewport_top(self) -> float:
        if self.body_canvas is not None and hasattr(self.body_canvas, "canvasy"):
            try:
                return float(self.body_canvas.canvasy(0))
            except Exception:
                pass
        return float(self._body_y0)

    def _sync_body_canvas_view(self):
        if self.body_canvas is None:
            return
        try:
            self.body_canvas.configure(
                height=int(max(1.0, float(self._body_view_height or self.geometry.body_height))),
                scrollregion=(0, 0, int(self.geometry.card_width), int(max(self.geometry.body_height, self._body_content_height))),
            )
        except Exception as exc:
            self._log_mount_error("sync body_canvas", exc, host=self._body_host, widget=self.body_canvas)
        if hasattr(self.body_canvas, "yview_moveto"):
            total = max(1.0, float(self._body_content_height))
            frac = min(max(float(self._body_y0) / total, 0.0), 1.0)
            try:
                self.body_canvas.yview_moveto(frac)
            except Exception as exc:
                self._log_mount_error("sync body_canvas yview", exc, host=self._body_host, widget=self.body_canvas)

    def body_yview(self) -> tuple[float, float]:
        total = max(1.0, float(self._body_content_height))
        top = self._body_viewport_top()
        self._body_y0 = min(max(float(top), 0.0), self.max_body_y0())
        start = min(max(float(self._body_y0) / total, 0.0), 1.0)
        end = min(max((float(self._body_y0) + float(self._body_view_height)) / total, start), 1.0)
        return (start, end)

    def body_yview_moveto(self, fraction: float):
        total = max(1.0, float(self._body_content_height))
        self._body_y0 = min(max(float(fraction) * total, 0.0), self.max_body_y0())
        self._sync_body_canvas_view()
        return self.body_yview()

    def body_yview_scroll(self, number: int, what: str = "units"):
        step = 24.0 if str(what) == "units" else max(1.0, float(self._body_view_height) * 0.9)
        self._body_y0 = min(max(float(self._body_y0) + (float(number) * step), 0.0), self.max_body_y0())
        self._sync_body_canvas_view()
        return self.body_yview()

    def body_canvasy(self, value: float) -> float:
        return float(self._body_viewport_top()) + float(value)

    def body_world_to_local(self, x: float, y: float) -> tuple[float, float]:
        return float(x) - float(self.geometry.card_x0), float(y) - float(self._body_viewport_top())

    def body_local_to_world(self, x: float, y: float) -> tuple[float, float]:
        return float(self.geometry.card_x0) + float(x), float(self._body_viewport_top()) + float(y)

    def body_world_to_root(self, x: float, y: float) -> tuple[int, int]:
        if self.body_canvas is not None:
            lx, ly = self.body_world_to_local(x, y)
            return int(self.body_canvas.winfo_rootx() + lx), int(self.body_canvas.winfo_rooty() + ly)
        try:
            return self.editor._body_world_to_root(x, y, ti=self.test_index)
        except TypeError:
            return self.editor._body_world_to_root(x, y)

    def body_render_canvas(self, canvas=None):
        return self.body_canvas if canvas is None else canvas

    def header_render_canvas(self, canvas=None):
        return self.header_canvas if canvas is None else canvas

    def header_world_to_local(self, x: float, y: float) -> tuple[float, float]:
        return float(x) - float(self.geometry.card_x0), float(y) - float(self.geometry.card_y0)

    def _uses_header_canvas_coords(self, canvas) -> bool:
        return canvas is not None and canvas is self.header_canvas

    def _map_header_point(self, canvas, x: float, y: float) -> tuple[float, float]:
        if self._uses_header_canvas_coords(canvas):
            return self.header_world_to_local(x, y)
        return float(x), float(y)

    def _map_header_rect(self, canvas, rect: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        x0, y0 = self._map_header_point(canvas, rect[0], rect[1])
        x1, y1 = self._map_header_point(canvas, rect[2], rect[3])
        return (x0, y0, x1, y1)

    def clear_body_render_layers(self, *tags: str):
        canvas = self.body_render_canvas()
        if canvas is None:
            return
        for tag in tags or ("graph_axes", "graph_qc", "graph_fs", "graph_nodata", "layers_overlay", "layer_handles"):
            try:
                canvas.delete(tag)
            except Exception:
                pass

    def _uses_body_canvas_coords(self, canvas) -> bool:
        return canvas is not None and canvas is self.body_canvas

    def _map_body_point(self, canvas, x: float, y: float) -> tuple[float, float]:
        if self._uses_body_canvas_coords(canvas):
            return self.body_world_to_local(x, y)
        return float(x), float(y)

    def _map_body_rect(self, canvas, rect: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        x0, y0 = self._map_body_point(canvas, rect[0], rect[1])
        x1, y1 = self._map_body_point(canvas, rect[2], rect[3])
        return (x0, y0, x1, y1)

    def invalidate_body(self, *parts: str):
        targets = parts or ("body",)
        self._invalid_parts.update(str(part) for part in targets)

    def invalidate_graph(self, *parts: str):
        self.invalidate_body(*(parts or ("graph",)))

    def invalidate_layers(self, *parts: str):
        self.invalidate_body(*(parts or ("layers",)))

    def invalidate_overlays(self, *parts: str):
        self.invalidate_body(*(parts or ("overlays",)))

    def bind_redraw_callback(self, part: str, callback):
        self._redraw_callbacks[str(part)] = callback

    def redraw_if_needed(self, *parts: str) -> tuple[str, ...]:
        requested = {str(part) for part in (parts or self.REDRAW_PARTS)}
        ready = tuple(part for part in self.REDRAW_PARTS if part in requested and part in self._invalid_parts)
        if bool(getattr(getattr(self, "editor", None), "__dict__", {}).get("_viewport_selfcheck_debug", False)):
            try:
                print(f"[CARDREDRAW] before card={self.test_index} requested={sorted(requested)} invalid={sorted(self._invalid_parts)}")
            except Exception:
                pass
        for part in ready:
            callback = self._redraw_callbacks.get(part)
            if callable(callback):
                callback()
            self._invalid_parts.discard(part)
        if bool(getattr(getattr(self, "editor", None), "__dict__", {}).get("_viewport_selfcheck_debug", False)):
            try:
                header_items = (len(self.header_canvas.find_all()) if self.header_canvas is not None and hasattr(self.header_canvas, "find_all") else None)
                body_items = (len(self.body_canvas.find_all()) if self.body_canvas is not None and hasattr(self.body_canvas, "find_all") else None)
                print(f"[CARDREDRAW] after card={self.test_index} redrawn={list(ready)} invalid={sorted(self._invalid_parts)} header_items={header_items} body_items={body_items}")
            except Exception:
                pass
        return ready

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
        return self.body_world_to_root(x, y)

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
        canvas=None,
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
        canvas = self.header_render_canvas(canvas)
        x0, y0, x1, y1 = self._map_header_rect(canvas, self.geometry.header_bounds_world)
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

    def render_body_cell(self, canvas=None, *, row_y0: float, row_y1: float, field: str, text: str, fill: str, text_color: str):
        canvas = self.body_render_canvas(canvas)
        x0, y0, x1, y1 = self._map_body_rect(canvas, self.geometry.cell_bbox_world(row_y0, row_y1, field))
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
            "sections": {
                "header": "SoundingCard",
                "body_table": "SoundingCard",
                "graphs": "SoundingCard",
                "ige_layers": "SoundingCard",
                "overlays": "SoundingCard",
                "popup_anchors": "SoundingCard",
                "vertical_viewport": "SoundingCard",
                "redraw_lifecycle": "SoundingCard",
            },
            "owned": [
                "header",
                "body_canvas",
                "body_vertical_scroll_state",
                "body_table_cells",
                "graphs",
                "ige_layers",
                "overlays",
                "card_hit_testing",
                "editor_rects",
                "popup_anchors",
                "card_redraw_lifecycle",
            ],
            "legacy": ["outer_viewport_x", "global_scheduling", "shared_model_coordination"],
            "body_yview": self.body_yview(),
            "invalid_parts": sorted(self._invalid_parts),
        }

    def dev_selfcheck_snapshot(self) -> dict[str, object]:
        scrollregion = None
        if self.body_canvas is not None and hasattr(self.body_canvas, "cget"):
            try:
                scrollregion = self.body_canvas.cget("scrollregion")
            except Exception:
                scrollregion = None
        return {
            "card": int(self.test_index),
            "body_view_height": float(self._body_view_height),
            "body_content_height": float(self._body_content_height),
            "body_y0": float(self._body_y0),
            "body_view_top": float(self._body_viewport_top()),
            "body_yview": self.body_yview(),
            "body_scrollregion": scrollregion,
            "invalid_parts": sorted(self._invalid_parts),
        }

    def future_graph_interface(self) -> dict[str, str]:
        return {
            "graph_rect": "card.graph_bbox_world(...)",
            "layer_overlay_targets": "card.render_ige(...) + card.render_overlays(...)",
            "graph_lines": "card.render_graph(...)",
        }

    def render_graph(
        self,
        canvas=None,
        *,
        rect: tuple[float, float, float, float],
        visible: bool = True,
        y_points: list[float],
        qc_values: list[float],
        fs_values: list[float],
        qmax: float,
        fmax: float,
        qc_color: str,
        fs_color: str,
        frame_fill: str,
        frame_outline: str,
        groundwater_level: float | None = None,
        groundwater_color: str = "#2f6fff",
        nodata_text: str = "нет данных",
    ):
        if not visible:
            return rect
        canvas = self.body_render_canvas(canvas)
        x0, y0, x1, y1 = self._map_body_rect(canvas, tuple(float(v) for v in rect))
        canvas.create_rectangle(x0, y0, x1, y1, fill=frame_fill, outline=frame_outline)
        if groundwater_level is not None:
            _gx, groundwater_level = self._map_body_point(canvas, rect[0], float(groundwater_level))
        if groundwater_level is not None and y0 <= float(groundwater_level) <= y1:
            canvas.create_line(x0 + 2, float(groundwater_level), x1 - 2, float(groundwater_level), fill=groundwater_color, width=2, dash=(6, 3))
        if not y_points:
            canvas.create_text((x0 + x1) / 2.0, (y0 + y1) / 2.0, text=nodata_text, fill="#666", font=("Segoe UI", 8))
            return rect

        qmax = max(float(qmax), 0.1)
        fmax = max(float(fmax), 1.0)
        pad = 8.0
        xa0 = x0 + pad
        xa1 = x1 - pad

        def _sx(v, vmax):
            return xa0 + (max(0.0, min(float(v), vmax)) / vmax) * (xa1 - xa0)

        qc_pts = []
        fs_pts = []
        for yy, qv, fv in zip(y_points, qc_values, fs_values):
            _pyx, pyy = self._map_body_point(canvas, rect[0], yy)
            if pyy < y0 - 1e-6 or pyy > y1 + 1e-6:
                continue
            qc_pts.extend([_sx(qv, qmax), float(pyy)])
            fs_pts.extend([_sx(fv, fmax), float(pyy)])

        if len(qc_pts) >= 4:
            canvas.create_line(*qc_pts, fill=qc_color, width=2, smooth=False)
        if len(fs_pts) >= 4:
            canvas.create_line(*fs_pts, fill=fs_color, width=2, smooth=False)
        return rect

    def render_ige(
        self,
        canvas=None,
        *,
        intervals: list[dict],
        visible: bool = True,
        fill_resolver,
        hatch_drawer,
        label_font_factory,
        layer_ui_colors: dict[str, str],
    ) -> tuple[list[dict], list[dict]]:
        if not visible:
            return [], []
        canvas = self.body_render_canvas(canvas)
        label_spans: list[dict] = []
        plot_hitboxes: list[dict] = []
        for interval in intervals:
            world_rect = (float(interval["x0"]), float(interval["y0"]), float(interval["x1"]), float(interval["y1"]))
            x0, y0, x1, y1 = self._map_body_rect(canvas, world_rect)
            soil_type = str(interval.get("soil_type") or "")
            fill_color = str(fill_resolver(soil_type))
            canvas.create_rectangle(x0, y0, x1, y1, fill=fill_color, outline="")
            hatch_drawer(x0, y0, x1, y1, soil_type, canvas=canvas, logical_rect=world_rect)
            plot_hitboxes.append(self.make_hitbox(kind="interval", bbox=world_rect, extra={"interval_index": int(interval.get("interval_index", 0)), "ige_id": interval.get("ige_id"), "top": float(interval.get("top", 0.0)), "bot": float(interval.get("bot", 0.0))}))
            text = str(interval.get("ige_id") or "")
            if text and (y1 - y0) >= 8.0:
                cx = (x0 + x1) * 0.5
                cy = (y0 + y1) * 0.5
                max_w = max(8.0, (x1 - x0) - 8.0)
                max_h = max(8.0, (y1 - y0) - 2.0)
                for font_size in (8, 7, 6):
                    font = label_font_factory(font_size)
                    tw = float(font.measure(text))
                    th = float(font.metrics("linespace"))
                    chip_w = tw + 8.0
                    chip_h = th + 4.0
                    if chip_w <= max_w and chip_h <= max_h:
                        bbox = (cx - chip_w * 0.5, cy - chip_h * 0.5, cx + chip_w * 0.5, cy + chip_h * 0.5)
                        canvas.create_rectangle(*bbox, fill=layer_ui_colors["fill"], outline=layer_ui_colors["outline"], width=1, activefill=layer_ui_colors["fill_active"], activeoutline=layer_ui_colors["outline_active"])
                        canvas.create_text(cx, cy, text=text, fill=layer_ui_colors["text"], activefill=layer_ui_colors["text"], font=("Segoe UI", font_size, "bold"))
                        label_spans.append(self.make_hitbox(kind="label", bbox=(world_rect[0], world_rect[1], world_rect[2], world_rect[3]), extra={"depth": float(interval.get("depth", 0.0))}))
                        break
        return plot_hitboxes, label_spans

    def render_overlays(
        self,
        canvas=None,
        *,
        overlay_specs: list[dict],
        layer_ui_colors: dict[str, str],
        visible: bool = True,
    ) -> tuple[list[dict], list[dict]]:
        if not visible:
            return [], []
        canvas = self.body_render_canvas(canvas)
        handle_hits: list[dict] = []
        depth_hits: list[dict] = []
        for spec in overlay_specs:
            kind = str(spec.get("kind") or "")
            if kind == "line":
                x0, y0 = self._map_body_point(canvas, spec["points"][0], spec["points"][1])
                x1, y1 = self._map_body_point(canvas, spec["points"][2], spec["points"][3])
                canvas.create_line(x0, y0, x1, y1, fill=spec.get("fill", layer_ui_colors["line"]), width=spec.get("width", 1), dash=spec.get("dash"))
                continue
            if kind == "handle":
                world_bbox = tuple(float(v) for v in spec["bbox"])
                x0, y0, x1, y1 = self._map_body_rect(canvas, world_bbox)
                canvas.create_rectangle(x0, y0, x1, y1, fill=layer_ui_colors["fill"], outline=layer_ui_colors["outline"], width=1, activefill=layer_ui_colors["fill_active"], activeoutline=layer_ui_colors["outline_active"], activewidth=2)
                handle_hits.append(self.make_hitbox(kind=str(spec.get("hit_kind", "boundary")), bbox=(world_bbox[0] - 1, world_bbox[1] - 1, world_bbox[2] + 1, world_bbox[3] + 1), boundary=spec.get("boundary"), extra={"tag": spec.get("tag")}))
                continue
            if kind == "depth_box":
                world_bbox = tuple(float(v) for v in spec["bbox"])
                x0, y0, x1, y1 = self._map_body_rect(canvas, world_bbox)
                canvas.create_rectangle(x0, y0, x1, y1, fill=layer_ui_colors["fill"], outline=layer_ui_colors["outline"], width=1, activefill=layer_ui_colors["fill_active"], activeoutline=layer_ui_colors["outline_active"])
                canvas.create_text((x0 + x1) / 2.0, (y0 + y1) / 2.0, text=str(spec.get("text", "")), fill=layer_ui_colors["text"], activefill=layer_ui_colors["text"], font=("Segoe UI", 7))
                depth_hits.append(self.make_hitbox(kind=str(spec.get("hit_kind", "boundary_depth_edit")), bbox=(world_bbox[0], world_bbox[1] - 1.0, world_bbox[2], world_bbox[3] + 1.0), boundary=spec.get("boundary")))
                continue
            if kind in {"plus", "minus"}:
                world_bbox = tuple(float(v) for v in spec["bbox"])
                x0, y0, x1, y1 = self._map_body_rect(canvas, world_bbox)
                canvas.create_rectangle(x0, y0, x1, y1, fill=layer_ui_colors["fill"], outline=layer_ui_colors["outline"], width=1, activefill=layer_ui_colors["fill_active"], activeoutline=layer_ui_colors["outline_active"])
                canvas.create_text((x0 + x1) / 2.0, (y0 + y1) / 2.0, text=("+" if kind == "plus" else "−"), fill=layer_ui_colors["text"], activefill=layer_ui_colors["text"], font=("Segoe UI", 9, "bold"))
                handle_hits.append(self.make_hitbox(kind=str(spec.get("hit_kind", kind)), bbox=(world_bbox[0] - 4.0, world_bbox[1] - 4.0, world_bbox[2] + 4.0, world_bbox[3] + 4.0), boundary=spec.get("boundary"), extra={"tag": spec.get("tag")}))
        return handle_hits, depth_hits
