from types import SimpleNamespace

from src.zondeditor.ui.editor import GeoCanvasEditor
import src.zondeditor.ui.editor as editor_module


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
    def __init__(self, *, bbox_all=(0, 0, 1000, 500), height=120, y0=0.0, rootx=0, rooty=0):
        self._bbox_all = bbox_all
        self._height = height
        self._y0 = y0
        self._rootx = rootx
        self._rooty = rooty
        self.y_moves = []
        self.y_scrolls = []
        self.draw_calls = []

    def bbox(self, _tag):
        return self._bbox_all

    def canvasy(self, value):
        return self._y0 + float(value)

    def winfo_height(self):
        return self._height

    def yview_moveto(self, frac):
        self.y_moves.append(frac)

    def yview_scroll(self, *args):
        self.y_scrolls.append(args)

    def winfo_rootx(self):
        return self._rootx

    def winfo_rooty(self):
        return self._rooty

    def create_rectangle(self, *args, **kwargs):
        self.draw_calls.append(("rectangle", args, kwargs))

    def create_line(self, *args, **kwargs):
        self.draw_calls.append(("line", args, kwargs))

    def create_text(self, *args, **kwargs):
        self.draw_calls.append(("text", args, kwargs))

    def delete(self, *args, **kwargs):
        self.draw_calls.append(("delete", args, kwargs))


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
    editor.show_graphs = False
    editor.show_geology_column = True
    editor.show_inclinometer = False
    editor.geo_kind = "K2"
    editor._scroll_w = 1000.0
    editor._content_size = lambda: (1000, 600, 72)
    editor._xview_proxy = lambda *args: editor.soundings_viewport.xview(*args)
    editor._total_body_height = lambda: 400
    editor._row_y_bounds = lambda row: (row * 22, row * 22 + 22)
    editor._viewport_sync_debug = False
    editor._viewport_sync_source_counts = {}
    editor._viewport_sync_wheel_seq = 0
    editor.compact_1m = False
    editor._debug_layers_overlay = False
    editor.expanded_meters = set()
    editor.display_sort_mode = "date"
    editor._hover = None
    editor._editing = None
    editor._marks_index = {}
    editor._inline_edit_active = False
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
    editor._layer_handle_hitbox = [{"kind": "boundary", "ti": 0, "boundary": 2, "bbox": (310, 80, 330, 100)}]
    editor._layer_label_hitbox = []
    editor._layer_plot_hitbox = []
    editor._table_col_width = lambda: 176
    editor._row_from_y = lambda y: 0
    editor._refresh_display_order = lambda: None
    editor.display_cols = [0]
    editor.w_depth = 64
    editor.w_val = 56

    hit = editor._hit_test(20, 90)

    assert hit == ("layer_boundary", 0, 2, None)


def test_card_at_world_picks_card_by_world_coordinates():
    editor = _make_editor()
    editor.display_cols = [0, 1]
    editor.tests = [object(), object()]
    editor._total_body_height = lambda: 400
    editor._is_graph_panel_visible = lambda: True
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.col_gap = 12
    editor.pad_x = 8
    editor.pad_y = 8
    editor.hdr_h = 64
    editor.soundings_viewport = SimpleNamespace(strip=None)
    editor._rebuild_sounding_cards()

    first = editor._card_at_world(20, 20)
    second = editor._card_at_world(360, 20)

    assert first is not None and first.test_index == 0
    assert second is not None and second.test_index == 1


def test_mousewheel_shift_routes_only_to_horizontal_handler():
    editor = _make_editor()
    calls = []
    editor._begin_scroll_debug_cycle = lambda source: calls.append(("begin", source))
    editor._on_mousewheel_x = lambda event: calls.append(("x", event.delta)) or "break"

    result = editor._on_mousewheel(SimpleNamespace(delta=120, state=0x0001))

    assert result == "break"
    assert calls == [("begin", "mousewheel_y"), ("x", 120)]


def test_independent_vertical_scroll_per_card_and_preserve_restore_active_y():
    editor = _make_editor()
    editor.display_cols = [0, 1]
    editor.tests = [object(), object()]
    editor._active_test_idx = 0
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.soundings_viewport = SimpleNamespace(strip=None, canvas=SimpleNamespace(canvasx=lambda v: float(v), winfo_width=lambda: 320), xview_fractions=lambda: (0.0, 1.0))
    editor._rebuild_sounding_cards()

    card0 = editor._card_for_test(0)
    card1 = editor._card_for_test(1)
    card0.body_yview_moveto(0.25)
    card1.body_yview_moveto(0.5)
    editor._active_test_idx = 1

    editor._rebuild_sounding_cards()

    assert round(editor._card_for_test(0).body_yview()[0], 2) == 0.25
    assert round(editor._card_for_test(1).body_yview()[0], 2) == 0.5
    assert round(editor._viewport_debug_snapshot()["active_card_body_yview"][0], 2) == 0.5


def test_editor_placement_and_hit_testing_after_local_card_scroll():
    editor = _make_editor()
    editor.display_cols = [0]
    editor.tests = [object()]
    editor._active_test_idx = 0
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.soundings_viewport = SimpleNamespace(strip=None, canvas=SimpleNamespace(canvasx=lambda v: 300.0 + float(v), winfo_width=lambda: 320), xview_fractions=lambda: (0.3, 0.62))
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.body_canvas = _DummyBodyCanvas(rootx=1000, rooty=2000)
    card.set_body_scroll_context(view_height=100.0, content_height=400.0)
    card.body_yview_moveto(0.25)
    editor._evt_widget = card.body_canvas
    editor._layer_depth_box_hitbox = []
    editor._layer_handle_hitbox = []
    editor._layer_label_hitbox = []
    editor._layer_plot_hitbox = []
    editor._refresh_display_order = lambda: None
    editor._row_from_y = lambda y: 0 if 100 <= y <= 122 else -1
    editor._row_y_bounds = lambda row: (100, 122)

    world = editor._event_body_world_xy(20, 10)
    root = editor._body_world_to_root(28, 70, ti=0)
    hit = editor._hit_test(20, 10)

    assert world == (28.0, 110.0)
    assert root == (1020, 1970)
    assert hit == ("cell", 0, 0, "depth")


def test_mousewheel_routes_vertical_to_card_and_shift_to_outer_viewport():
    editor = _make_editor()
    editor.display_cols = [0]
    editor.tests = [object()]
    editor._active_test_idx = 0
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.soundings_viewport = SimpleNamespace(strip=None, canvas=SimpleNamespace(canvasx=lambda v: float(v), winfo_width=lambda: 320), xview_fractions=lambda: (0.0, 1.0))
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.body_canvas = _DummyBodyCanvas()
    card.set_body_scroll_context(view_height=100.0, content_height=400.0)
    editor._evt_widget = card.body_canvas
    x_calls = []
    editor._on_mousewheel_x = lambda event: x_calls.append(event.delta) or "break"

    result_y = editor._on_mousewheel(SimpleNamespace(delta=-120, state=0))
    result_x = editor._on_mousewheel(SimpleNamespace(delta=120, state=0x0001))

    assert result_y == "break"
    assert round(card.body_yview()[0], 2) > 0.0
    assert result_x == "break"
    assert x_calls == [120]


def test_redraw_graphs_now_uses_card_body_canvas_not_shared_editor_canvas():
    editor = _make_editor()
    editor.display_cols = [0]
    editor.tests = [SimpleNamespace(qc=["10"], fs=["5"], depth=["0.00"], tid=1)]
    editor._active_test_idx = 0
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.show_graphs = True
    editor.show_geology_column = True
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.soundings_viewport = SimpleNamespace(strip=None, canvas=SimpleNamespace(canvasx=lambda v: float(v), winfo_width=lambda: 320), xview_fractions=lambda: (0.0, 1.0))
    editor._grid_units = [("row", 0)]
    editor._grid_row_maps = {0: {0: 0}}
    editor._row_y_bounds = lambda row: (0.0, 22.0)
    editor._calc_layer_params_for_all_tests = lambda: None
    editor._recompute_graph_scales = lambda: setattr(editor, "graph_qc_max_mpa", 30.0) or setattr(editor, "graph_fs_max_kpa", 500.0)
    editor._calc_qc_fs_from_del = lambda q, f: (float(q), float(f))
    editor._depth_to_canvas_y = lambda d: float(d) * 100.0
    editor._ensure_test_experience_column = lambda t: SimpleNamespace(column_depth_start=0.0, column_depth_end=1.0, intervals=[SimpleNamespace(from_depth=0.0, to_depth=1.0, ige_id="ИГЭ-1")])
    editor._column_interval_ige_id = lambda lyr: "ИГЭ-1"
    editor._ensure_ige_entry = lambda ige_id: {"soil_type": "sand"}
    editor._geology_layer_fill_color = lambda soil: "#eee"
    editor._draw_layer_hatch = lambda *args, **kwargs: None
    editor.cpt_calc_settings = {}
    editor._refresh_display_order = lambda: None
    editor._graph_rect_for_test = lambda ti: (226.0, 376.0, 0.0, 100.0)
    editor.canvas = SimpleNamespace(
        delete=lambda *args, **kwargs: None,
        create_rectangle=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("shared canvas should not draw")),
        create_line=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("shared canvas should not draw")),
        create_text=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("shared canvas should not draw")),
    )
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.body_canvas = _DummyBodyCanvas()
    font_backup = editor_module.tkfont.Font
    editor_module.tkfont.Font = lambda font=None: SimpleNamespace(measure=lambda text: len(text) * 4, metrics=lambda name: 8)
    try:
        editor._redraw_graphs_now()
    finally:
        editor_module.tkfont.Font = font_backup

    assert any(call[0] == "rectangle" for call in card.body_canvas.draw_calls)
    assert editor._layer_plot_hitbox
    assert editor._layer_handle_hitbox


def test_redraw_uses_card_hosted_header_and_body_targets_not_shared_canvases():
    editor = _make_editor()
    editor.tests = [SimpleNamespace(tid=1, dt="01.01.2026 10:00", export_on=True, locked=False, qc=["10"], fs=["5"], depth=["0.00"])]
    editor.display_cols = [0]
    editor.flags = {1: SimpleNamespace(invalid=False, force_cells=set(), interp_cells=set(), user_cells=set(), algo_cells=set())}
    editor._build_grid = lambda: setattr(editor, "_grid_base", [0.0]) or setattr(editor, "_grid", [0]) or setattr(editor, "_grid_row_maps", {0: {0: 0}}) or setattr(editor, "_grid_start_rows", {0: 0}) or setattr(editor, "_grid_units", [("row", 0)])
    editor._diagnostics_report = lambda: SimpleNamespace(by_test={1: SimpleNamespace(invalid=False, missing_rows=[])})
    editor._header_fill_for_test = lambda **kwargs: "#fff"
    editor._sync_view_ribbon_state = lambda: None
    editor._sync_layers_panel = lambda: None
    editor._update_scrollregion = lambda: None
    editor._is_graph_panel_visible = lambda: False
    editor._clear_graph_layers = lambda: None
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor._cell_bbox = lambda col, row, field: (200.0, 22.0, 256.0, 44.0)
    editor.canvas = SimpleNamespace(
        delete=lambda *args, **kwargs: None,
        create_rectangle=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("shared body canvas should not draw")),
        create_text=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("shared body canvas should not draw")),
    )
    editor.hcanvas = SimpleNamespace(
        delete=lambda *args, **kwargs: None,
        configure=lambda **kwargs: None,
        create_rectangle=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("shared header canvas should not draw")),
        create_text=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("shared header canvas should not draw")),
        create_line=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("shared header canvas should not draw")),
    )
    editor.soundings_viewport = SimpleNamespace(strip=None)
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.header_canvas = _DummyBodyCanvas()
    card.body_canvas = _DummyBodyCanvas()
    editor._refresh_display_order = lambda: None
    editor._rebuild_sounding_cards = lambda: {0: card}
    editor._sounding_cards = {0: card}

    editor._redraw()

    assert any(call[0] == "rectangle" for call in card.header_canvas.draw_calls)
    assert any(call[0] == "rectangle" for call in card.body_canvas.draw_calls)
