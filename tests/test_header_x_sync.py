from types import SimpleNamespace

from src.zondeditor.ui import editor as editor_module
from src.zondeditor.ui.editor import GeoCanvasEditor


class _FakeCanvas:
    def __init__(self, *, width=120, height=80, content_width=600, content_height=200):
        self.width = width
        self.height = height
        self.content_width = content_width
        self.content_height = content_height
        self._xfrac = 0.0
        self._scrollregion = (0, 0, content_width, content_height)
        self._xscrollcommand = None
        self.last_set = None

    def configure(self, **kwargs):
        if "scrollregion" in kwargs:
            self._scrollregion = kwargs["scrollregion"]
            self.content_width = float(self._scrollregion[2])
            self.content_height = float(self._scrollregion[3])
        if "width" in kwargs:
            self.width = kwargs["width"]
        if "height" in kwargs:
            self.height = kwargs["height"]
        if "xscrollcommand" in kwargs:
            self._xscrollcommand = kwargs["xscrollcommand"]

    def xview(self, *args):
        if not args:
            span = min(1.0, self.width / max(1.0, self.content_width))
            return (self._xfrac, min(1.0, self._xfrac + span))
        mode = args[0]
        if mode == "moveto":
            frac = float(args[1])
        elif mode == "scroll":
            step = float(args[1])
            unit_px = 20.0 if str(args[2]) == "units" else float(self.width)
            frac = self._xfrac + (step * unit_px / max(1.0, self.content_width))
        else:
            raise AssertionError(f"unsupported xview args: {args}")
        max_frac = max(0.0, 1.0 - (self.width / max(1.0, self.content_width)))
        self._xfrac = min(max(frac, 0.0), max_frac)
        if self._xscrollcommand is not None:
            first, last = self.xview()
            self._xscrollcommand(first, last)

    def xview_moveto(self, frac):
        self.xview("moveto", frac)

    def canvasx(self, value):
        return float(value) + (self._xfrac * self.content_width)

    def winfo_width(self):
        return self.width

    def winfo_height(self):
        return self.height

    def bbox(self, _tag):
        return self._scrollregion

    def yview_moveto(self, _frac):
        return None


class _FakeScrollbar:
    def __init__(self):
        self.value = None
        self.states = []

    def set(self, first, last):
        self.value = (float(first), float(last))

    def state(self, state):
        self.states.append(tuple(state))


class _FakeFrame:
    def __init__(self):
        self.hidden = False

    def pack_forget(self):
        self.hidden = True


def _make_editor(*, header_content_width: float = 600) -> GeoCanvasEditor:
    editor = GeoCanvasEditor.__new__(GeoCanvasEditor)
    editor.canvas = _FakeCanvas()
    editor.hcanvas = _FakeCanvas(content_width=header_content_width)
    editor.hscroll = _FakeScrollbar()
    editor.vbar = _FakeScrollbar()
    editor.hscroll_frame = _FakeFrame()
    editor._debug_header_sync = lambda *args, **kwargs: None
    editor._end_edit_calls = []
    editor._end_edit = lambda commit=True: editor._end_edit_calls.append(commit)
    editor._sync_header_body_after_scroll = lambda: None
    editor._content_size = lambda: (600, 200, 64)
    editor._scroll_w = 600.0
    editor._shared_x_frac = 0.0
    editor._shared_x_lock = False
    editor._header_offset_px = 0.0
    editor._header_sync_wheel_seq = 0
    editor._header_sync_source_counts = {}
    editor._header_sync_pending = False
    editor._hscroll_hidden = False
    editor.col_gap = 12
    editor._column_block_width = lambda: 80
    editor._last_column_right_px = lambda: 560
    editor._xview_proxy = lambda *args: editor._apply_shared_xview(*args, close_editor=True)
    return editor


def test_horizontal_scrollbar_keeps_header_and_body_aligned():
    editor = _make_editor()

    editor._apply_shared_xview("moveto", 0.4, close_editor=True)

    assert editor.canvas.xview()[0] == editor.hcanvas.xview()[0]
    assert editor._shared_x_frac == editor.canvas.xview()[0]
    assert editor.hscroll.value == editor.canvas.xview()
    assert editor._end_edit_calls == [True]


def test_shift_wheel_path_keeps_header_and_body_aligned():
    editor = _make_editor()
    event = SimpleNamespace(delta=-120)
    editor._scroll_x_by_one_column = lambda direction: editor._apply_shared_xview("moveto", 0.25 + (0.05 * direction))

    result = editor._on_mousewheel_x(event)

    assert result == "break"
    assert editor.canvas.xview()[0] == editor.hcanvas.xview()[0]
    assert editor.canvas.xview()[0] == 0.3


def test_update_scrollregion_preserves_shared_x_without_drift():
    editor = _make_editor()
    editor._apply_shared_xview("moveto", 0.4)

    editor._update_scrollregion()

    assert editor.canvas.xview()[0] == editor.hcanvas.xview()[0]
    assert round(editor.canvas.xview()[0], 4) == 0.4


def test_ensure_visible_auto_scroll_uses_shared_x_path_without_desync(monkeypatch):
    editor = _make_editor()
    editor._cell_bbox = lambda col, row, field: (520, 0, 580, 24)
    monkeypatch.setattr(editor_module, "_canvas_view_bbox", lambda cnv: (cnv.canvasx(0), 0.0, cnv.canvasx(0) + cnv.winfo_width(), cnv.winfo_height()))

    editor._ensure_cell_visible(0, 0, "qc", pad=6)

    assert editor.canvas.xview()[0] == editor.hcanvas.xview()[0]
    assert editor.canvas.xview()[0] > 0.0


def test_repeated_scrollregion_refresh_does_not_accumulate_x_drift():
    editor = _make_editor()
    editor._apply_shared_xview("moveto", 0.35)

    for _ in range(5):
        editor._update_scrollregion()

    assert editor.canvas.xview()[0] == editor.hcanvas.xview()[0]
    assert round(editor.canvas.xview()[0], 4) == 0.35


def test_repeated_wheel_scrolling_to_far_right_keeps_zero_pixel_drift():
    editor = _make_editor(header_content_width=601)

    for _ in range(10):
        GeoCanvasEditor._scroll_x_by_one_column(editor, 1)

    assert round(editor.canvas.canvasx(0) - editor.hcanvas.canvasx(0), 6) == 0.0
    assert round(editor.canvas.xview()[0] - editor._shared_x_frac, 12) == 0.0


def test_final_clamped_right_edge_has_zero_pixel_drift():
    editor = _make_editor(header_content_width=601)

    editor._apply_shared_xview("moveto", 1.0)

    assert round(editor.canvas.canvasx(0) - editor.hcanvas.canvasx(0), 6) == 0.0
    assert editor.canvas.xview()[1] <= 1.0


def test_scroll_back_left_does_not_hide_right_edge_drift_fix():
    editor = _make_editor(header_content_width=601)

    for _ in range(10):
        GeoCanvasEditor._scroll_x_by_one_column(editor, 1)
    right_edge_delta = round(editor.canvas.canvasx(0) - editor.hcanvas.canvasx(0), 6)
    GeoCanvasEditor._scroll_x_by_one_column(editor, -1)

    assert right_edge_delta == 0.0
    assert round(editor.canvas.canvasx(0) - editor.hcanvas.canvasx(0), 6) == 0.0


def test_scrollbar_far_right_matches_zero_drift_alignment():
    editor = _make_editor(header_content_width=601)

    editor._xview_proxy("moveto", 1.0)

    assert round(editor.canvas.canvasx(0) - editor.hcanvas.canvasx(0), 6) == 0.0


def test_mid_range_positions_keep_existing_alignment_behavior():
    editor = _make_editor(header_content_width=601)

    editor._apply_shared_xview("moveto", 0.4)

    assert round(editor.canvas.canvasx(0) - editor.hcanvas.canvasx(0), 6) == 0.0
