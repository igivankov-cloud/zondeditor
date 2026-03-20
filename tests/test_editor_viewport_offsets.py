from types import SimpleNamespace

from src.zondeditor.ui.editor import GeoCanvasEditor


class _DummyViewportCanvas:
    def __init__(self, *, width=300, x0=0.0, fractions=(0.0, 1.0)):
        self._width = width
        self._x0 = x0
        self._fractions = fractions

    def canvasx(self, value):
        return self._x0 + float(value)

    def winfo_width(self):
        return self._width


class _DummyViewport:
    def __init__(self, *, width=300, x0=0.0, fractions=(0.0, 1.0)):
        self.canvas = _DummyViewportCanvas(width=width, x0=x0, fractions=fractions)
        self._fractions = fractions
        self.content_sizes = []
        self.moves = []

    def xview_fractions(self):
        return self._fractions

    def set_content_size(self, *, width, body_height, header_height):
        self.content_sizes.append((width, body_height, header_height))

    def xview(self, *args):
        self.moves.append(args)


class _DummyBodyCanvas:
    def __init__(self, *, bbox_all=(0, 0, 1000, 500), height=120, y0=0.0):
        self._bbox_all = bbox_all
        self._height = height
        self._y0 = y0
        self.y_moves = []

    def bbox(self, _tag):
        return self._bbox_all

    def canvasy(self, value):
        return self._y0 + float(value)

    def winfo_height(self):
        return self._height

    def yview_moveto(self, frac):
        self.y_moves.append(frac)

    def yview_scroll(self, *args):
        pass


class _DummyScrollbar:
    def __init__(self):
        self.values = []
        self.states = []

    def set(self, first, last):
        self.values.append((first, last))

    def state(self, values):
        self.states.append(tuple(values))


def _make_editor():
    editor = GeoCanvasEditor.__new__(GeoCanvasEditor)
    editor.soundings_viewport = _DummyViewport()
    editor.canvas = _DummyBodyCanvas()
    editor.hcanvas = SimpleNamespace()
    editor.hscroll = _DummyScrollbar()
    editor.hscroll_frame = SimpleNamespace(pack=lambda **_: None, pack_forget=lambda: None)
    editor.vbar = _DummyScrollbar()
    editor._hscroll_hidden = True
    editor._end_edit = lambda commit=True: None
    editor._sync_header_body_after_scroll = lambda: None
    editor._dev_log_viewport_state = lambda source: None
    editor.status = SimpleNamespace(pack_forget=lambda: None, pack=lambda **_: None)
    editor.footer = object()
    editor.pad_x = 8
    editor.pad_y = 8
    editor.col_gap = 12
    editor.hdr_h = 64
    editor._scroll_w = 1000.0
    editor._content_size = lambda: (1000, 600, 72)
    editor._xview_proxy = lambda *args: editor.soundings_viewport.xview(*args)
    return editor


def test_update_scrollregion_preserves_pixel_position_after_rebuild():
    editor = _make_editor()
    editor.soundings_viewport = _DummyViewport(width=320, x0=400.0, fractions=(0.4, 0.72))
    editor._content_size = lambda: (2000, 700, 72)

    editor._update_scrollregion()

    assert editor.soundings_viewport.content_sizes[-1] == (2000, 700, 72)
    assert editor.soundings_viewport.moves[-1] == ("moveto", 0.2)


def test_update_scrollregion_resets_x_when_content_fits():
    editor = _make_editor()
    editor.soundings_viewport = _DummyViewport(width=1200, x0=250.0, fractions=(0.25, 1.0))
    editor._content_size = lambda: (800, 400, 72)

    editor._update_scrollregion()

    assert ("moveto", 0) in editor.soundings_viewport.moves


def test_ensure_cell_visible_uses_viewport_x_offset():
    editor = _make_editor()
    editor.soundings_viewport = _DummyViewport(width=250, x0=300.0, fractions=(0.3, 0.55))
    editor.canvas = _DummyBodyCanvas(bbox_all=(0, 0, 1000, 500), height=100, y0=0.0)
    editor._cell_bbox = lambda col, row, field: (620, 20, 680, 42)

    editor._ensure_cell_visible(0, 0, "qc", pad=10)

    assert editor.soundings_viewport.moves[-1] == ("moveto", 0.44)


def test_hit_test_layer_handle_accounts_for_nonzero_viewport_x():
    editor = _make_editor()
    editor.tests = [object()]
    editor._evt_widget = editor.canvas
    editor.soundings_viewport = _DummyViewport(width=250, x0=300.0, fractions=(0.3, 0.55))
    editor._layer_depth_box_hitbox = []
    editor._layer_handle_hitbox = [{"kind": "boundary", "ti": 0, "boundary": 2, "bbox": (340, 40, 360, 60)}]
    editor._layer_label_hitbox = []
    editor._layer_plot_hitbox = []
    editor._table_col_width = lambda: 176
    editor._row_from_y = lambda y: 0
    editor._refresh_display_order = lambda: None
    editor.display_cols = [0]
    editor.w_depth = 64
    editor.w_val = 56

    hit = editor._hit_test(50, 50)

    assert hit == ("layer_boundary", 0, 2, None)


def test_mousewheel_shift_routes_only_to_horizontal_handler():
    editor = _make_editor()
    calls = []
    editor._begin_scroll_debug_cycle = lambda source: calls.append(("begin", source))
    editor._on_mousewheel_x = lambda event: calls.append(("x", event.delta)) or "break"

    result = editor._on_mousewheel(SimpleNamespace(delta=120, state=0x0001))

    assert result == "break"
    assert calls == [("begin", "mousewheel_y"), ("x", 120)]
