from .loader import load_hatch_pattern
from .pat_loader import load_pat_pattern
from .math import clip_segment_to_rect, clock_basis, infer_line_type, local_to_world, normalize_segments, parse_angle_deg
from .models import HatchLine, HatchPattern, HatchSegment, PatPattern
from .registry import SOIL_TYPE_TO_HATCH_ASSET, SOIL_TYPE_TO_HATCH_FILE, SOIL_TYPE_TO_PAT_FILE, load_registered_hatch, load_registered_pat_pattern, resolve_hatch_asset
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
    'PatPattern',
    'SOIL_TYPE_TO_HATCH_ASSET',
    'SOIL_TYPE_TO_HATCH_FILE',
    'SOIL_TYPE_TO_PAT_FILE',
    'load_hatch_pattern',
    'load_pat_pattern',
    'load_registered_hatch',
    'load_registered_pat_pattern',
    'resolve_hatch_asset',
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
