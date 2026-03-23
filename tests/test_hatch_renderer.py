from src.zondeditor.domain.hatching import HATCH_USAGE_EDITOR_EXPANDED, load_registered_hatch
from src.zondeditor.ui.render.hatch_renderer import render_hatch_pattern


class _FakeCanvas:
    def __init__(self):
        self.items = []

    def create_line(self, *args, **kwargs):
        self.items.append(("line", args, kwargs))
        return len(self.items)

    def create_oval(self, *args, **kwargs):
        self.items.append(("oval", args, kwargs))
        return len(self.items)


def _render_count(*, card_index: int, trace: list[tuple[str, dict]] | None = None) -> int:
    pattern = load_registered_hatch("суглинок")
    assert pattern is not None
    canvas = _FakeCanvas()
    x0 = 184 + ((card_index - 1) * 338)
    x1 = x0 + 150
    scale_info = {
        "usage": HATCH_USAGE_EDITOR_EXPANDED,
        "layer_height_px": 400.0,
        "logical_rect": (x0, 0.0, x1, 400.0),
    }
    if trace is not None:
        scale_info["debug_hook"] = lambda event, **payload: trace.append((event, payload))
    render_hatch_pattern(canvas, (x0, 0.0, x1, 400.0), pattern, tags=("layers_overlay", f"layers_overlay_{card_index}"), scale_info=scale_info)
    return len(canvas.items)


def test_hatch_renderer_keeps_late_cards_drawn_at_large_absolute_x():
    early_count = _render_count(card_index=1)
    late_count = _render_count(card_index=13)

    assert early_count > 0
    assert late_count == early_count


def test_hatch_renderer_debug_hook_reports_drawn_primitives_for_late_card():
    trace: list[tuple[str, dict]] = []

    late_count = _render_count(card_index=13, trace=trace)

    assert late_count > 0
    line_events = [payload for event, payload in trace if event == "hatch_line_drawn"]
    assert line_events
    assert line_events[0]["primitives_count"] == late_count
