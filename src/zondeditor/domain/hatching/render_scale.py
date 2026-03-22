from __future__ import annotations

from dataclasses import dataclass

from .models import HatchPattern

HATCH_USAGE_EDITOR_EXPANDED = 'editor_expanded'
HATCH_USAGE_EDITOR_COLLAPSED = 'editor_collapsed'
HATCH_USAGE_EDITOR_INTERACTIVE = 'editor_interactive'
HATCH_USAGE_PROTOCOL_EXPORT = 'protocol_export'
DEFAULT_HATCH_USAGE = HATCH_USAGE_EDITOR_EXPANDED

HATCH_RENDER_MULTIPLIERS: dict[str, float] = {
    HATCH_USAGE_EDITOR_EXPANDED: 0.5,
    HATCH_USAGE_EDITOR_COLLAPSED: 0.5,
    HATCH_USAGE_EDITOR_INTERACTIVE: 2.0,
    HATCH_USAGE_PROTOCOL_EXPORT: 1.0,
}


@dataclass(frozen=True)
class HatchRenderScale:
    usage: str
    base_pattern_scale: float
    render_multiplier: float
    effective_unit_px: float


def resolve_hatch_render_scale(pattern: HatchPattern, *, usage: str, base_unit_px: float) -> HatchRenderScale:
    resolved_usage = str(usage or DEFAULT_HATCH_USAGE)
    base_pattern_scale = max(1e-9, float(pattern.scale or 1.0))
    render_multiplier = max(1e-9, float(HATCH_RENDER_MULTIPLIERS.get(resolved_usage, HATCH_RENDER_MULTIPLIERS[DEFAULT_HATCH_USAGE])))
    base_unit_px = max(1e-9, float(base_unit_px))
    effective_unit_px = (base_unit_px / base_pattern_scale) * render_multiplier
    return HatchRenderScale(
        usage=resolved_usage,
        base_pattern_scale=base_pattern_scale,
        render_multiplier=render_multiplier,
        effective_unit_px=effective_unit_px,
    )
