from .loader import load_hatch_pattern
from .math import clip_segment_to_rect, clock_basis, infer_line_type, local_to_world, normalize_segments, parse_angle_deg
from .models import HatchLine, HatchPattern, HatchSegment
from .registry import SOIL_TYPE_TO_HATCH_FILE, load_registered_hatch
from .render_scale import (
    DEFAULT_HATCH_USAGE,
    HATCH_RENDER_MULTIPLIERS,
    HATCH_USAGE_EDITOR_COLLAPSED,
    HATCH_USAGE_EDITOR_EXPANDED,
    HATCH_USAGE_PROTOCOL_EXPORT,
    HatchRenderScale,
    resolve_hatch_render_scale,
)

__all__ = [
    'HatchSegment',
    'HatchLine',
    'HatchPattern',
    'SOIL_TYPE_TO_HATCH_FILE',
    'load_hatch_pattern',
    'load_registered_hatch',
    'HatchRenderScale',
    'DEFAULT_HATCH_USAGE',
    'HATCH_RENDER_MULTIPLIERS',
    'HATCH_USAGE_EDITOR_EXPANDED',
    'HATCH_USAGE_EDITOR_COLLAPSED',
    'HATCH_USAGE_PROTOCOL_EXPORT',
    'resolve_hatch_render_scale',
    'parse_angle_deg',
    'clock_basis',
    'local_to_world',
    'clip_segment_to_rect',
    'normalize_segments',
    'infer_line_type',
]
