from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProtocolLayout:
    # Reference template: docs/reference/cpt_protocol/tsz1.dxf
    width_mm: float = 183.1
    top_y_mm: float = -6.9
    header_bottom_y_mm: float = -56.0
    body_start_y_mm: float = -56.0
    depth_scale_mm_per_m: float = 10.0

    # Main vertical columns (taken from reference geometry)
    x_no: float = 0.1
    x_abs: float = 4.1
    x_thickness: float = 15.2
    x_description: float = 25.1
    x_section: float = 89.1
    x_depth: float = 99.1
    x_graph: float = 110.1
    x_right: float = 183.1

    # Graph scale rows in header area
    qc_axis_y: float = -44.7
    fs_axis_y: float = -25.3

    @property
    def table_bottom_y(self) -> float:
        return self.body_start_y_mm

    def y_for_depth(self, depth_m: float) -> float:
        return self.body_start_y_mm - float(depth_m) * self.depth_scale_mm_per_m

    def total_height_for_depth(self, max_depth_m: float) -> float:
        return abs(self.top_y_mm - self.y_for_depth(max_depth_m))


DEFAULT_PROTOCOL_LAYOUT = ProtocolLayout()
