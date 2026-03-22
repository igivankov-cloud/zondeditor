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
    def __init__(self, *, bbox_all=(0, 0, 1000, 500), height=120, y0=0.0, rootx=0, rooty=0, support_items=False):
        self._bbox_all = bbox_all
        self._height = height
        self._y0 = y0
        self._rootx = rootx
        self._rooty = rooty
        self.y_moves = []
        self.y_scrolls = []
        self.draw_calls = []
        self._config = {}
        self._support_items = support_items
        self._items = []
        self._next_item_id = 1
        self.bindings = {}
        self.raised_tags = []

    def bbox(self, _tag):
        return self._bbox_all

    def canvasy(self, value):
        return self._y0 + float(value)

    def winfo_height(self):
        return self._height

    def yview_moveto(self, frac):
        self.y_moves.append(frac)
        total = float((self._config.get("scrollregion") or (0, 0, 0, self._bbox_all[3]))[3])
        height = float(self._config.get("height", self._height) or self._height)
        max_y = max(0.0, total - height)
        self._y0 = min(max(float(frac) * max(total, 1.0), 0.0), max_y)

    def yview_scroll(self, *args):
        self.y_scrolls.append(args)

    def winfo_rootx(self):
        return self._rootx

    def winfo_rooty(self):
        return self._rooty

    def configure(self, **kwargs):
        self._config.update(kwargs)
        if "height" in kwargs:
            self._height = float(kwargs["height"])

    def cget(self, key):
        return self._config.get(key)

    def _add_item(self, item_type, *args, **kwargs):
        item_id = self._next_item_id
        self._next_item_id += 1
        self._items.append({"id": item_id, "type": item_type, "args": args, "kwargs": kwargs})
        self.draw_calls.append((item_type, args, kwargs))
        return item_id

    def create_rectangle(self, *args, **kwargs):
        if self._support_items:
            return self._add_item("rectangle", *args, **kwargs)
        self.draw_calls.append(("rectangle", args, kwargs))

    def create_line(self, *args, **kwargs):
        if self._support_items:
            return self._add_item("line", *args, **kwargs)
        self.draw_calls.append(("line", args, kwargs))

    def create_text(self, *args, **kwargs):
        if self._support_items:
            return self._add_item("text", *args, **kwargs)
        self.draw_calls.append(("text", args, kwargs))

    def create_window(self, *args, **kwargs):
        return self._add_item("window", *args, **kwargs)

    def find_all(self):
        return tuple(item["id"] for item in self._items)

    def type(self, item_id):
        for item in self._items:
            if item["id"] == item_id:
                return item["type"]
        raise KeyError(item_id)

    def bind(self, event, callback):
        self.bindings[event] = callback

    def tag_raise(self, tag, above_this=None):
        self.raised_tags.append((tag, above_this))

    def delete(self, *args, **kwargs):
        self.draw_calls.append(("delete", args, kwargs))
        if not self._support_items:
            return
        if args == ("all",):
            self._items.clear()
            return
        ids = {arg for arg in args if isinstance(arg, int)}
        self._items = [item for item in self._items if item["id"] not in ids]


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
    editor.col_gap = 4
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
    editor._debug_tail_edit = False
    editor._graph_redraw_after_id = None
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
    editor._boundary_depth_editor = None
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
    editor.col_gap = 4
    editor.pad_x = 8
    editor.pad_y = 8
    editor.hdr_h = 64
    editor.soundings_viewport = SimpleNamespace(strip=None)
    editor._rebuild_sounding_cards()

    first = editor._card_at_world(20, 20)
    second = editor._card_at_world(360, 20)

    assert first is not None and first.test_index == 0
    assert second is not None and second.test_index == 1


def test_consecutive_cards_use_tight_inter_card_gap():
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
    editor.soundings_viewport = SimpleNamespace(strip=None)
    editor._rebuild_sounding_cards()

    card0 = editor._card_for_test(0)
    card1 = editor._card_for_test(1)

    assert (card1.geometry.card_x0 - card0.geometry.card_bounds_world[2]) == 4.0


def test_mousewheel_shift_routes_only_to_horizontal_handler():
    editor = _make_editor()
    calls = []
    editor._begin_scroll_debug_cycle = lambda source: calls.append(("begin", source))
    editor._on_mousewheel_x = lambda event: calls.append(("x", event.delta)) or "break"

    result = editor._on_mousewheel(SimpleNamespace(delta=120, state=0x0001))

    assert result == "break"
    assert calls == [("begin", "mousewheel_y"), ("x", 120)]


def test_shared_vertical_scroll_is_preserved_across_cards_on_rebuild():
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
    editor._apply_shared_body_yview_fraction(0.25)
    editor._active_test_idx = 1

    editor._rebuild_sounding_cards()

    assert round(editor._card_for_test(0).body_yview()[0], 2) == 0.25
    assert round(editor._card_for_test(1).body_yview()[0], 2) == 0.25
    assert round(editor._viewport_debug_snapshot()["active_card_body_yview"][0], 2) == 0.25


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
    editor._recompute_graph_scales = lambda: setattr(editor, "graph_qc_max_mpa", 30.0) or setattr(editor, "graph_fs_max_kpa", 286.0) or setattr(editor, "graph_qc_max_source", "data") or setattr(editor, "graph_fs_max_source", "data") or setattr(editor, "graph_qc_max_display", 30.0) or setattr(editor, "graph_fs_max_display", 286.0)
    editor._calc_qc_fs_from_del = lambda q, f: (float(q), float(f))
    editor._depth_to_canvas_y = lambda d: float(d) * 100.0
    editor._ensure_test_experience_column = lambda t: SimpleNamespace(column_depth_start=0.0, column_depth_end=1.0, intervals=[SimpleNamespace(from_depth=0.0, to_depth=1.0, ige_id="ИГЭ-1")])
    editor._column_interval_ige_id = lambda lyr: "ИГЭ-1"
    editor._ensure_ige_entry = lambda ige_id: {"soil_type": "sand"}
    editor._geology_layer_fill_color = lambda soil: "#eee"
    editor._draw_layer_hatch = lambda *args, **kwargs: None
    editor.cpt_calc_settings = {}
    editor._refresh_display_order = lambda: None
    editor._graph_rect_for_test = lambda ti: (226.0, 0.0, 376.0, 100.0)
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
    assert editor._layer_label_hitbox
    assert editor._layer_handle_hitbox
    assert editor._layer_depth_box_hitbox


def test_redraw_graphs_now_keeps_hatch_visible_under_graph_frame():
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
    editor._row_y_bounds = lambda row: (0.0, 120.0)
    editor._calc_layer_params_for_all_tests = lambda: None
    editor._recompute_graph_scales = lambda: setattr(editor, "graph_qc_max_mpa", 30.0) or setattr(editor, "graph_fs_max_kpa", 286.0) or setattr(editor, "graph_qc_max_source", "data") or setattr(editor, "graph_fs_max_source", "data") or setattr(editor, "graph_qc_max_display", 30.0) or setattr(editor, "graph_fs_max_display", 286.0)
    editor._calc_qc_fs_from_del = lambda q, f: (float(q), float(f))
    editor._depth_to_canvas_y = lambda d: float(d) * 100.0
    editor._ensure_test_experience_column = lambda t: SimpleNamespace(column_depth_start=0.0, column_depth_end=1.0, intervals=[SimpleNamespace(from_depth=0.0, to_depth=1.0, ige_id="ИГЭ-1")])
    editor._column_interval_ige_id = lambda lyr: "ИГЭ-1"
    editor._ensure_ige_entry = lambda ige_id: {"soil_type": "суглинок"}
    editor._geology_layer_fill_color = lambda soil: "#eee"
    editor.cpt_calc_settings = {}
    editor._refresh_display_order = lambda: None
    editor._graph_rect_for_test = lambda ti: (226.0, 0.0, 376.0, 120.0)
    editor.canvas = SimpleNamespace(
        delete=lambda *args, **kwargs: None,
        create_rectangle=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("shared canvas should not draw")),
        create_line=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("shared canvas should not draw")),
        create_text=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("shared canvas should not draw")),
    )
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.body_canvas = _DummyBodyCanvas(support_items=True)
    font_backup = editor_module.tkfont.Font
    editor_module.tkfont.Font = lambda font=None: SimpleNamespace(measure=lambda text: len(text) * 4, metrics=lambda name: 8)
    try:
        editor._redraw_graphs_now()
    finally:
        editor_module.tkfont.Font = font_backup

    hatch_lines = [call for call in card.body_canvas.draw_calls if call[0] == "line" and "layers_overlay" in call[2].get("tags", ())]
    frame_rectangles = [call for call in card.body_canvas.draw_calls if call[0] == "rectangle" and call[2].get("tags") == ("graph_axes", "graph_axes_0")]

    assert hatch_lines
    assert frame_rectangles
    assert frame_rectangles[0][2]["fill"] == ""


def test_redraw_graphs_now_raises_ige_label_chip_above_graph_curves():
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
    editor._row_y_bounds = lambda row: (0.0, 120.0)
    editor._calc_layer_params_for_all_tests = lambda: None
    editor._recompute_graph_scales = lambda: setattr(editor, "graph_qc_max_mpa", 30.0) or setattr(editor, "graph_fs_max_kpa", 286.0) or setattr(editor, "graph_qc_max_source", "data") or setattr(editor, "graph_fs_max_source", "data") or setattr(editor, "graph_qc_max_display", 30.0) or setattr(editor, "graph_fs_max_display", 286.0)
    editor._calc_qc_fs_from_del = lambda q, f: (float(q), float(f))
    editor._depth_to_canvas_y = lambda d: float(d) * 100.0
    editor._ensure_test_experience_column = lambda t: SimpleNamespace(column_depth_start=0.0, column_depth_end=1.0, intervals=[SimpleNamespace(from_depth=0.0, to_depth=1.0, ige_id="ИГЭ-1")])
    editor._column_interval_ige_id = lambda lyr: "ИГЭ-1"
    editor._ensure_ige_entry = lambda ige_id: {"soil_type": "суглинок"}
    editor._geology_layer_fill_color = lambda soil: "#eee"
    editor.cpt_calc_settings = {}
    editor._refresh_display_order = lambda: None
    editor._graph_rect_for_test = lambda ti: (226.0, 0.0, 376.0, 120.0)
    editor.canvas = SimpleNamespace(delete=lambda *args, **kwargs: None)
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.body_canvas = _DummyBodyCanvas(support_items=True)
    font_backup = editor_module.tkfont.Font
    editor_module.tkfont.Font = lambda font=None: SimpleNamespace(measure=lambda text: len(text) * 4, metrics=lambda name: 8)
    try:
        editor._redraw_graphs_now()
    finally:
        editor_module.tkfont.Font = font_backup

    assert ("layers_label_chip_0", None) in card.body_canvas.raised_tags


def test_draw_layer_hatch_converts_world_logical_rect_to_card_local_canvas_coords():
    editor = _make_editor()
    editor.display_cols = [0]
    editor.tests = [SimpleNamespace(tid=1)]
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.soundings_viewport = SimpleNamespace(strip=None)
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.body_canvas = _DummyBodyCanvas(support_items=True, y0=400.0)
    editor._sounding_cards = {0: card}

    editor._draw_layer_hatch(
        176.0,
        220.0,
        326.0,
        360.0,
        "суглинок",
        tags=("layers_overlay", "layers_overlay_0"),
        logical_rect=(card.geometry.card_x0 + 176.0, 620.0, card.geometry.card_x0 + 326.0, 760.0),
        canvas=card.body_canvas,
    )

    hatch_lines = [call for call in card.body_canvas.draw_calls if call[0] == "line" and "layers_overlay" in call[2].get("tags", ())]

    assert hatch_lines


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
    editor._is_graph_panel_visible = lambda: True
    editor._clear_graph_layers = lambda: None
    editor._recompute_graph_scales = lambda: setattr(editor, "graph_qc_max_mpa", 30.0) or setattr(editor, "graph_fs_max_kpa", 286.0) or setattr(editor, "graph_qc_max_source", "data") or setattr(editor, "graph_fs_max_source", "data") or setattr(editor, "graph_qc_max_display", 30.0) or setattr(editor, "graph_fs_max_display", 286.0)
    editor._redraw_graphs_now = lambda: None
    editor.graph_qc_max_mpa = 0.0
    editor.graph_fs_max_kpa = 0.0
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
    header_texts = [str(call[2].get("text", "")) for call in card.header_canvas.draw_calls if call[0] == "text"]
    assert any("qc 0–30 МПа" in text for text in header_texts)
    assert any("fs 0–286 кПа" in text for text in header_texts)


def test_recompute_graph_scales_uses_data_before_fs_fallback_500():
    editor = _make_editor()
    editor.tests = [
        SimpleNamespace(qc=["5", "18.5", ""], fs=["40", "120", ""]),
        SimpleNamespace(qc=["7"], fs=["35"]),
    ]
    editor._current_calibration = lambda: (_ for _ in ()).throw(RuntimeError("no calibration"))

    editor._recompute_graph_scales()

    assert editor.graph_qc_max_mpa == 18.5
    assert editor.graph_fs_max_kpa == 120.0
    assert editor.graph_qc_max_source == "data"
    assert editor.graph_fs_max_source == "data"
    assert editor.graph_fs_max_display == 120.0


def test_canvas_delete_all_removes_card_window_items_on_host_canvas():
    host = _DummyBodyCanvas(support_items=True)
    primitive_id = host.create_rectangle(0, 0, 10, 10)
    window_id = host.create_window((20, 0), window=object(), anchor="nw")

    assert host.find_all() == (primitive_id, window_id)

    host.delete("all")

    assert host.find_all() == ()



def test_clear_host_canvas_primitives_preserves_card_window_items():
    editor = _make_editor()
    host = _DummyBodyCanvas(support_items=True)
    primitive_id = host.create_rectangle(0, 0, 10, 10)
    window_id = host.create_window((20, 0), window=object(), anchor="nw")
    card = SimpleNamespace(_body_host=host, _body_window_id=window_id, _header_host=None, _header_window_id=None)
    editor._sounding_cards = {0: card}

    editor._clear_host_canvas_primitives(host, label="body_host")

    assert host.find_all() == (window_id,)
    delete_calls = [call for call in host.draw_calls if call[0] == "delete"]
    assert delete_calls[-1][1] == (primitive_id,)



def test_redraw_preserves_host_window_items_and_clears_only_primitives():
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
    editor.canvas = _DummyBodyCanvas(support_items=True)
    editor.hcanvas = _DummyBodyCanvas(support_items=True)
    legacy_body_id = editor.canvas.create_rectangle(0, 0, 10, 10)
    legacy_header_id = editor.hcanvas.create_rectangle(0, 0, 10, 10)
    body_window_id = editor.canvas.create_window((20, 0), window=object(), anchor="nw")
    header_window_id = editor.hcanvas.create_window((20, 0), window=object(), anchor="nw")
    editor.soundings_viewport = SimpleNamespace(strip=None)
    editor._refresh_display_order = lambda: None
    editor._rebuild_sounding_cards = lambda: {0: card}
    card = editor._card_for_test(0)
    card.header_canvas = _DummyBodyCanvas()
    card.body_canvas = _DummyBodyCanvas()
    card._header_host = editor.hcanvas
    card._body_host = editor.canvas
    card._header_window_id = header_window_id
    card._body_window_id = body_window_id
    editor._sounding_cards = {0: card}

    editor._redraw()

    assert legacy_body_id not in editor.canvas.find_all()
    assert legacy_header_id not in editor.hcanvas.find_all()
    assert body_window_id in editor.canvas.find_all()
    assert header_window_id in editor.hcanvas.find_all()



def test_mousewheel_uses_hovered_body_canvas_not_active_card():
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
    card0.body_canvas = _DummyBodyCanvas()
    card1.body_canvas = _DummyBodyCanvas()
    card0.set_body_scroll_context(view_height=100.0, content_height=400.0)
    card1.set_body_scroll_context(view_height=100.0, content_height=400.0)

    result = editor._on_mousewheel(SimpleNamespace(delta=-120, state=0, widget=card1.body_canvas))

    assert result == "break"
    assert round(card0.body_yview()[0], 2) == round(card1.body_yview()[0], 2)
    assert round(card1.body_yview()[0], 2) > 0.0



def test_card_body_scrollregion_tracks_content_height_after_rebuild():
    editor = _make_editor()
    editor.display_cols = [0]
    editor.tests = [object()]
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.canvas = _DummyBodyCanvas(height=120)
    editor.hcanvas = SimpleNamespace()
    editor.soundings_viewport = SimpleNamespace(strip=None)
    editor._total_body_height = lambda: 400
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.body_canvas = _DummyBodyCanvas()
    card.set_body_scroll_context(view_height=120.0, content_height=400.0)

    assert card.dev_selfcheck_snapshot()["body_yview"] == (0.0, 0.3)



def test_redraw_graphs_now_does_not_crash_when_graphs_and_layers_are_disabled():
    editor = _make_editor()
    editor.display_cols = [0]
    editor.tests = [SimpleNamespace(qc=["10"], fs=["5"], depth=["0.00"], tid=1)]
    editor._active_test_idx = 0
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.show_graphs = False
    editor.show_geology_column = False
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
    editor._refresh_display_order = lambda: None
    editor._graph_rect_for_test = lambda ti: (226.0, 0.0, 376.0, 100.0)
    editor.canvas = SimpleNamespace(delete=lambda *args, **kwargs: None)
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.body_canvas = _DummyBodyCanvas()

    editor._redraw_graphs_now()

    assert editor._layer_plot_hitbox == []
    assert editor._layer_handle_hitbox == []
    assert editor._layer_depth_box_hitbox == []



def test_vertical_wheel_syncs_yview_across_all_cards():
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
    card0.body_canvas = _DummyBodyCanvas()
    card1.body_canvas = _DummyBodyCanvas()
    card0.set_body_scroll_context(view_height=100.0, content_height=400.0)
    card1.set_body_scroll_context(view_height=100.0, content_height=400.0)

    result = editor._on_mousewheel(SimpleNamespace(delta=-120, state=0, widget=card1.body_canvas))

    assert result == "break"
    assert round(card0.body_yview()[0], 2) == round(card1.body_yview()[0], 2)
    assert round(card1.body_yview()[0], 2) > 0.0



def test_body_alignment_stays_synced_after_shared_vertical_scroll():
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
    card0.body_canvas = _DummyBodyCanvas(rootx=1000, rooty=2000)
    card1.body_canvas = _DummyBodyCanvas(rootx=1400, rooty=2000)
    card0.set_body_scroll_context(view_height=100.0, content_height=400.0)
    card1.set_body_scroll_context(view_height=100.0, content_height=400.0)

    editor._apply_shared_body_yview_fraction(0.25)

    assert card0.body_world_to_local(70.0, 130.0)[1] == 30.0
    assert card1.body_world_to_local(card1.geometry.card_x0 + 20.0, 130.0)[1] == 30.0
    assert editor._body_world_to_root(card1.geometry.card_x0 + 20.0, 130.0, ti=1) == (1420, 2030)



def test_card_body_canvas_binds_drag_motion_and_release_for_layer_handles():
    editor = _make_editor()
    editor.display_cols = [0]
    editor.tests = [SimpleNamespace(tid=1)]
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.canvas = _DummyBodyCanvas(support_items=True)
    editor.hcanvas = _DummyBodyCanvas(support_items=True)
    editor.soundings_viewport = SimpleNamespace(strip=None)

    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.body_canvas = _DummyBodyCanvas(support_items=True)
    editor._bind_card_targets(card)

    assert "<B1-Motion>" in card.body_canvas.bindings
    assert "<ButtonRelease-1>" in card.body_canvas.bindings


def test_layer_drag_motion_uses_card_body_canvas_coordinates():
    editor = _make_editor()
    editor.display_cols = [0]
    editor.tests = [SimpleNamespace(tid=1, experience_column=SimpleNamespace(column_depth_end=2.0, intervals=[SimpleNamespace(from_depth=0.0), SimpleNamespace(from_depth=1.0)]))]
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.soundings_viewport = SimpleNamespace(strip=None)
    editor.canvas = _DummyBodyCanvas(y0=0.0)
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.body_canvas = _DummyBodyCanvas(y0=400.0)
    editor._sounding_cards = {0: card}
    editor._layer_drag = {"ti": 0, "boundary": 1, "mode": "boundary"}
    editor._is_test_locked = lambda ti: False
    captured = []
    editor._canvas_y_to_depth = lambda y: captured.append(float(y)) or 1.25
    editor._ensure_test_experience_column = lambda t: t.experience_column
    editor._set_status = lambda msg: None
    editor._redraw_graphs_now = lambda: None

    import src.zondeditor.ui.editor as editor_module
    move_backup = editor_module.move_experience_column_boundary
    editor_module.move_experience_column_boundary = lambda column, boundary, depth: column
    try:
        editor._on_layer_drag_motion(SimpleNamespace(widget=card.body_canvas, x=10, y=20))
    finally:
        editor_module.move_experience_column_boundary = move_backup

    assert captured == [420.0]


def test_layer_drag_release_refreshes_only_the_active_card():
    editor = _make_editor()
    editor.display_cols = [0, 1]
    editor.tests = [SimpleNamespace(tid=1), SimpleNamespace(tid=2)]
    editor._layer_drag = {"ti": 0, "boundary": 1, "mode": "boundary"}
    editor._layer_handle_hitbox = [{"ti": 0, "kind": "boundary"}, {"ti": 1, "kind": "boundary"}]
    editor._layer_depth_box_hitbox = [{"ti": 0, "kind": "boundary_depth_edit"}, {"ti": 1, "kind": "boundary_depth_edit"}]
    editor._layer_plot_hitbox = [{"ti": 0, "kind": "interval"}, {"ti": 1, "kind": "interval"}]
    editor._layer_label_hitbox = [{"ti": 0, "kind": "label"}, {"ti": 1, "kind": "label"}]
    refreshed = []
    calc_calls = []
    redraw_calls = []
    schedule_calls = []
    editor._calc_layer_params_for_test = lambda ti: calc_calls.append(int(ti))
    editor._refresh_card_graph_layers = lambda ti: refreshed.append(int(ti))
    editor._redraw = lambda: redraw_calls.append("all")
    editor.schedule_graph_redraw = lambda: schedule_calls.append("scheduled")

    editor._on_layer_drag_release(SimpleNamespace(widget=None))

    assert calc_calls == [0]
    assert refreshed == [0]
    assert redraw_calls == []
    assert schedule_calls == []
    assert editor._layer_drag is None


def test_add_unassigned_ige_from_ribbon_does_not_schedule_global_graph_redraw():
    editor = _make_editor()
    editor.ige_registry = {"ИГЭ-1": {"label": "ИГЭ-1", "ordinal": 1}}
    editor._push_undo = lambda: None
    editor._next_free_ige_ordinal = lambda: 2
    editor._next_free_ige_id = lambda: "ige-2-1"
    editor._ensure_ige_cpt_fields = lambda payload: dict(payload)
    synced = []
    focused = []
    scheduled = []
    editor._sync_layers_panel = lambda: synced.append("layers")
    editor.schedule_graph_redraw = lambda: scheduled.append("graphs")
    editor.ribbon_view = SimpleNamespace(focus_ige_row=lambda ige_id: focused.append(ige_id))

    editor._add_unassigned_ige_from_ribbon()

    assert "ige-2-1" in editor.ige_registry
    assert synced == ["layers"]
    assert focused == ["ige-2-1"]
    assert scheduled == []


def test_refresh_card_graph_layers_replaces_hitboxes_only_for_target_card():
    editor = _make_editor()
    editor.display_cols = [0, 1]
    editor.tests = [SimpleNamespace(tid=1), SimpleNamespace(tid=2)]
    editor._layer_handle_hitbox = [{"ti": 0, "kind": "boundary", "marker": "old0"}, {"ti": 1, "kind": "boundary", "marker": "keep1"}]
    editor._layer_depth_box_hitbox = [{"ti": 0, "kind": "boundary_depth_edit", "marker": "old0"}, {"ti": 1, "kind": "boundary_depth_edit", "marker": "keep1"}]
    editor._layer_plot_hitbox = [{"ti": 0, "kind": "interval", "marker": "old0"}, {"ti": 1, "kind": "interval", "marker": "keep1"}]
    editor._layer_label_hitbox = [{"ti": 0, "kind": "label", "marker": "old0"}, {"ti": 1, "kind": "label", "marker": "keep1"}]
    editor._clear_card_graph_layers = lambda ti: None
    editor._render_card_graph_layers = lambda ti: (
        editor._layer_handle_hitbox.append({"ti": ti, "kind": "boundary", "marker": "new0"}),
        editor._layer_depth_box_hitbox.append({"ti": ti, "kind": "boundary_depth_edit", "marker": "new0"}),
        editor._layer_plot_hitbox.append({"ti": ti, "kind": "interval", "marker": "new0"}),
        editor._layer_label_hitbox.append({"ti": ti, "kind": "label", "marker": "new0"}),
    )

    editor._refresh_card_graph_layers(0)

    assert [hit["marker"] for hit in editor._layer_handle_hitbox] == ["keep1", "new0"]
    assert [hit["marker"] for hit in editor._layer_depth_box_hitbox] == ["keep1", "new0"]
    assert [hit["marker"] for hit in editor._layer_plot_hitbox] == ["keep1", "new0"]
    assert [hit["marker"] for hit in editor._layer_label_hitbox] == ["keep1", "new0"]


def test_refresh_after_cell_edit_redraws_only_target_card_when_shared_scale_is_unchanged():
    editor = _make_editor()
    editor.show_graphs = True
    editor.tests = [SimpleNamespace(tid=1), SimpleNamespace(tid=2)]
    editor.graph_qc_max_mpa = 30.0
    editor.graph_fs_max_kpa = 500.0
    editor.graph_qc_max_source = "data"
    editor.graph_fs_max_source = "data"
    editor.graph_qc_max_display = 30.0
    editor.graph_fs_max_display = 500.0
    local_calls = []
    graph_calls = []
    redraw_calls = []
    editor._recompute_graph_scales = lambda: None
    editor._refresh_single_card = lambda ti, **kwargs: local_calls.append(int(ti))
    editor._refresh_card_graph_layers = lambda ti: graph_calls.append(int(ti))
    editor._redraw = lambda: redraw_calls.append("all")

    editor._refresh_after_cell_edit(1)

    assert local_calls == [1]
    assert graph_calls == [1]
    assert redraw_calls == []


def test_refresh_after_cell_edit_falls_back_to_global_redraw_when_shared_scale_changes():
    editor = _make_editor()
    editor.show_graphs = True
    editor.tests = [SimpleNamespace(tid=1), SimpleNamespace(tid=2)]
    editor.graph_qc_max_mpa = 30.0
    editor.graph_fs_max_kpa = 500.0
    editor.graph_qc_max_source = "data"
    editor.graph_fs_max_source = "data"
    editor.graph_qc_max_display = 30.0
    editor.graph_fs_max_display = 500.0
    local_calls = []
    graph_calls = []
    redraw_calls = []

    def _change_scales():
        editor.graph_qc_max_mpa = 35.0
        editor.graph_qc_max_display = 35.0

    editor._recompute_graph_scales = _change_scales
    editor._refresh_single_card = lambda ti, **kwargs: local_calls.append(int(ti))
    editor._refresh_card_graph_layers = lambda ti: graph_calls.append(int(ti))
    editor._redraw = lambda: redraw_calls.append("all")

    editor._refresh_after_cell_edit(0)

    assert local_calls == []
    assert graph_calls == []
    assert redraw_calls == ["all"]


def test_schedule_graph_redraw_is_suppressed_while_inline_editor_is_active():
    editor = _make_editor()
    editor.show_graphs = True
    editor._editing = (0, 0, "qc", object(), 0)
    after_calls = []
    editor.after = lambda delay, cb: after_calls.append((delay, cb)) or "after-id"

    editor.schedule_graph_redraw()

    assert after_calls == []
    assert editor._graph_redraw_after_id is None


def test_refresh_display_order_skips_rebuild_when_order_is_unchanged():
    editor = _make_editor()
    editor.tests = [SimpleNamespace(tid=2, dt=""), SimpleNamespace(tid=1, dt="")]
    editor.display_sort_mode = "tid"
    editor.display_cols = [1, 0]
    editor._sounding_cards = {1: object(), 0: object()}
    rebuild_calls = []
    editor._rebuild_sounding_cards = lambda: rebuild_calls.append("rebuild")

    editor._refresh_display_order()

    assert editor.display_cols == [1, 0]
    assert rebuild_calls == []


def test_begin_edit_cancels_pending_graph_redraw_before_placing_editor(monkeypatch):
    editor = _make_editor()
    editor.display_cols = [0]
    editor.tests = [SimpleNamespace(qc=["10"], fs=["5"], depth=["0.00"], tid=1, locked=False)]
    editor.flags = {1: SimpleNamespace(invalid=False, force_cells=set(), interp_cells=set(), user_cells=set(), algo_cells=set())}
    editor._active_test_idx = 0
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.soundings_viewport = SimpleNamespace(strip=None, canvas=SimpleNamespace(canvasx=lambda v: float(v), winfo_width=lambda: 320), xview_fractions=lambda: (0.0, 1.0))
    editor._grid_units = [("row", 0)]
    editor._grid_row_maps = {0: {0: 0}}
    editor._row_y_bounds = lambda row: (0.0, 22.0)
    editor._row_tops = [0.0, 22.0]
    editor._refresh_display_order = lambda: None
    editor._ensure_cell_visible = lambda *args, **kwargs: None
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.body_canvas = _DummyBodyCanvas(rootx=140, rooty=220)
    editor._sounding_cards = {0: card}
    cancelled = []
    editor._graph_redraw_after_id = "after-id"
    editor.after_cancel = lambda after_id: cancelled.append(after_id)

    class _FakeEntry:
        def __init__(self, parent, **kwargs):
            self.parent = parent
        def insert(self, *_args):
            pass
        def get(self):
            return "10"
        def configure(self, **_kwargs):
            pass
        def select_range(self, *_args):
            pass
        def place(self, **_kwargs):
            pass
        def focus_set(self):
            pass
        def bind(self, *_args, **_kwargs):
            pass
        def icursor(self, *_args):
            pass
        def after_idle(self, fn):
            fn()

    monkeypatch.setattr(editor_module.tk, "Entry", lambda parent, **kwargs: _FakeEntry(parent, **kwargs))
    editor.register = lambda fn: fn

    editor._begin_edit(0, 0, "qc", display_row=0)

    assert cancelled == ["after-id"]
    assert editor._graph_redraw_after_id is None


def test_redraw_graphs_now_is_suppressed_while_inline_editor_is_active():
    editor = _make_editor()
    editor.show_graphs = True
    editor.tests = [SimpleNamespace(tid=1)]
    editor._editing = (0, 0, "qc", object(), 0)
    calls = []
    editor._clear_graph_layers = lambda: calls.append("clear")
    editor._calc_layer_params_for_all_tests = lambda: calls.append("calc")
    editor._recompute_graph_scales = lambda: calls.append("scales")
    editor._refresh_display_order = lambda: calls.append("refresh")
    editor._render_card_graph_layers = lambda ti: calls.append(("render", ti))

    editor._redraw_graphs_now()

    assert calls == []


def test_layer_drag_motion_refreshes_only_target_card():
    editor = _make_editor()
    editor.tests = [SimpleNamespace(tid=1, locked=False, experience_column=SimpleNamespace(intervals=[SimpleNamespace(from_depth=0.0)], column_depth_end=1.0))]
    editor._layer_drag = {"ti": 0, "boundary": 0, "mode": "boundary"}
    editor._is_test_locked = lambda ti: False
    editor._card_for_widget = lambda widget: SimpleNamespace(body_canvas=widget, body_local_to_world=lambda x, y: (x, y))
    editor._canvas_y_to_depth = lambda y: 1.25
    editor._ensure_test_experience_column = lambda t: t.experience_column
    editor._calc_layer_params_for_test = lambda ti: calls.append(("calc", ti))
    editor._refresh_card_graph_layers = lambda ti: calls.append(("refresh", ti))
    editor._cancel_pending_graph_redraw = lambda: calls.append("cancel")
    editor._set_status = lambda text: calls.append(("status", text))
    event = SimpleNamespace(widget=_DummyBodyCanvas(), x=10, y=20)
    calls = []

    import src.zondeditor.ui.editor as editor_module_local
    original_move = editor_module_local.move_experience_column_boundary
    try:
        editor_module_local.move_experience_column_boundary = lambda column, boundary, depth: SimpleNamespace(
            intervals=[SimpleNamespace(from_depth=depth)],
            column_depth_end=depth + 1.0,
        )
        editor._on_layer_drag_motion(event)
    finally:
        editor_module_local.move_experience_column_boundary = original_move

    assert "cancel" in calls
    assert ("calc", 0) in calls
    assert ("refresh", 0) in calls


def test_center_toplevel_withdraws_before_showing_centered_window():
    editor = _make_editor()
    editor.winfo_rootx = lambda: 100
    editor.winfo_rooty = lambda: 200
    editor.winfo_width = lambda: 500
    editor.winfo_height = lambda: 400
    editor.update_idletasks = lambda: None
    calls = []

    class _DummyWin:
        def withdraw(self):
            calls.append("withdraw")
        def update_idletasks(self):
            calls.append("update")
        def winfo_reqwidth(self):
            return 120
        def winfo_reqheight(self):
            return 80
        def geometry(self, value):
            calls.append(("geometry", value))
        def deiconify(self):
            calls.append("deiconify")

    editor._center_toplevel(_DummyWin(), parent=editor)

    assert calls[0] == "withdraw"
    assert calls[-1] == "deiconify"


def test_center_child_withdraws_before_showing_centered_window():
    editor = _make_editor()
    editor.winfo_rootx = lambda: 100
    editor.winfo_rooty = lambda: 200
    editor.winfo_width = lambda: 500
    editor.winfo_height = lambda: 400
    calls = []

    class _DummyWin:
        def withdraw(self):
            calls.append("withdraw")
        def update_idletasks(self):
            calls.append("update")
        def winfo_reqwidth(self):
            return 120
        def winfo_reqheight(self):
            return 80
        def geometry(self, value):
            calls.append(("geometry", value))
        def deiconify(self):
            calls.append("deiconify")

    editor._center_child(_DummyWin())

    assert calls[0] == "withdraw"
    assert calls[-1] == "deiconify"


def test_compact_toggle_redraw_clears_stale_body_rows_from_card_canvas():
    editor = _make_editor()
    editor.tests = [SimpleNamespace(tid=1, dt="01.01.2026 10:00", export_on=True, locked=False, qc=["10", "11", "12"], fs=["5", "6", "7"], depth=["0.00", "0.10", "0.20"])]
    editor.display_cols = [0]
    editor.flags = {1: SimpleNamespace(invalid=False, force_cells=set(), interp_cells=set(), user_cells=set(), algo_cells=set())}
    editor._sync_view_ribbon_state = lambda: None
    editor._sync_layers_panel = lambda: None
    editor._update_scrollregion = lambda: None
    editor._diagnostics_report = lambda: SimpleNamespace(by_test={1: SimpleNamespace(invalid=False, missing_rows=[])})
    editor._header_fill_for_test = lambda **kwargs: "#fff"
    editor._is_graph_panel_visible = lambda: False
    editor._clear_graph_layers = lambda: None
    editor._refresh_display_order = lambda: None
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.canvas = _DummyBodyCanvas(support_items=True)
    editor.hcanvas = _DummyBodyCanvas(support_items=True)
    editor.soundings_viewport = SimpleNamespace(strip=None)

    state = {"collapsed": False}
    def build_grid():
        if state["collapsed"]:
            editor._grid_base = [0.0]
            editor._grid = [0]
            editor._grid_units = [("row", 0)]
            editor._grid_row_maps = {0: {0: 0}}
            editor._grid_start_rows = {0: 0}
        else:
            editor._grid_base = [0.0, 0.1, 0.2]
            editor._grid = [0, 1, 2]
            editor._grid_units = [("row", 0), ("row", 1), ("row", 2)]
            editor._grid_row_maps = {0: {0: 0, 1: 1, 2: 2}}
            editor._grid_start_rows = {0: 0}
    editor._build_grid = build_grid
    editor._row_y_bounds = lambda row: (row * 22.0, row * 22.0 + 22.0)
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.header_canvas = _DummyBodyCanvas(support_items=True)
    card.body_canvas = _DummyBodyCanvas(support_items=True)
    editor._rebuild_sounding_cards = lambda: {0: card}
    editor._sounding_cards = {0: card}

    build_grid()
    editor._redraw()
    expanded_items = list(card.body_canvas._items)
    assert any(item["args"][1] >= 44.0 for item in expanded_items if item["type"] == "rectangle")

    state["collapsed"] = True
    build_grid()
    editor._redraw()
    collapsed_items = list(card.body_canvas._items)

    assert not any(item["type"] == "rectangle" and len(item["args"]) >= 4 and item["args"][1] >= 44.0 for item in collapsed_items)
    assert editor.canvas.find_all() == ()



def test_expand_collapse_expand_keeps_card_body_canvas_clean():
    editor = _make_editor()
    editor.tests = [SimpleNamespace(tid=1, dt="01.01.2026 10:00", export_on=True, locked=False, qc=["10", "11", "12"], fs=["5", "6", "7"], depth=["0.00", "0.10", "0.20"])]
    editor.display_cols = [0]
    editor.flags = {1: SimpleNamespace(invalid=False, force_cells=set(), interp_cells=set(), user_cells=set(), algo_cells=set())}
    editor._sync_view_ribbon_state = lambda: None
    editor._sync_layers_panel = lambda: None
    editor._update_scrollregion = lambda: None
    editor._diagnostics_report = lambda: SimpleNamespace(by_test={1: SimpleNamespace(invalid=False, missing_rows=[])})
    editor._header_fill_for_test = lambda **kwargs: "#fff"
    editor._is_graph_panel_visible = lambda: False
    editor._clear_graph_layers = lambda: None
    editor._refresh_display_order = lambda: None
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.canvas = _DummyBodyCanvas(support_items=True)
    editor.hcanvas = _DummyBodyCanvas(support_items=True)
    editor.soundings_viewport = SimpleNamespace(strip=None)

    rows = {"count": 3}
    def build_grid():
        editor._grid_base = [0.1 * i for i in range(rows["count"])]
        editor._grid = list(range(rows["count"]))
        editor._grid_units = [("row", i) for i in range(rows["count"])]
        editor._grid_row_maps = {0: {i: i for i in range(rows["count"])}}
        editor._grid_start_rows = {0: 0}
    editor._build_grid = build_grid
    editor._row_y_bounds = lambda row: (row * 22.0, row * 22.0 + 22.0)
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.header_canvas = _DummyBodyCanvas(support_items=True)
    card.body_canvas = _DummyBodyCanvas(support_items=True)
    editor._rebuild_sounding_cards = lambda: {0: card}
    editor._sounding_cards = {0: card}

    for count in (3, 1, 3):
        rows["count"] = count
        build_grid()
        editor._redraw()

    final_rectangles = [item for item in card.body_canvas._items if item["type"] == "rectangle"]
    assert len(final_rectangles) == 9
    assert editor.canvas.find_all() == ()



def test_redraw_graphs_now_renders_each_card_in_its_own_local_graph_column():
    editor = _make_editor()
    editor.display_cols = [0, 1]
    editor.tests = [
        SimpleNamespace(qc=["10", "20"], fs=["5", "15"], depth=["0.00", "0.10"], tid=1),
        SimpleNamespace(qc=["12", "24"], fs=["6", "18"], depth=["0.00", "0.10"], tid=2),
    ]
    editor._active_test_idx = 0
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.show_graphs = True
    editor.show_geology_column = False
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.soundings_viewport = SimpleNamespace(strip=None, canvas=SimpleNamespace(canvasx=lambda v: float(v), winfo_width=lambda: 640), xview_fractions=lambda: (0.0, 1.0))
    editor._grid_units = [("row", 0), ("row", 1)]
    editor._grid_row_maps = {0: {0: 0, 1: 1}, 1: {0: 0, 1: 1}}
    editor._row_y_bounds = lambda row: (row * 22.0, row * 22.0 + 22.0)
    editor._calc_layer_params_for_all_tests = lambda: None
    editor._recompute_graph_scales = lambda: setattr(editor, "graph_qc_max_mpa", 30.0) or setattr(editor, "graph_fs_max_kpa", 500.0)
    editor._calc_qc_fs_from_del = lambda q, f: (float(q), float(f))
    editor._clear_graph_layers = lambda: None
    editor._refresh_display_order = lambda: None
    editor._rebuild_sounding_cards()
    card0 = editor._card_for_test(0)
    card1 = editor._card_for_test(1)
    card0.body_canvas = _DummyBodyCanvas(support_items=True)
    card1.body_canvas = _DummyBodyCanvas(support_items=True)
    card0.set_body_scroll_context(view_height=100.0, content_height=200.0)
    card1.set_body_scroll_context(view_height=100.0, content_height=200.0)

    editor._redraw_graphs_now()

    rect0 = next(item for item in card0.body_canvas._items if item["type"] == "rectangle")
    rect1 = next(item for item in card1.body_canvas._items if item["type"] == "rectangle")
    assert rect0["args"][:3] == (176.0, 0.0, 326.0)
    assert rect1["args"][:3] == (176.0, 0.0, 326.0)
    assert rect0["args"][3] == 400.0
    assert rect1["args"][3] == 400.0
    assert sum(1 for item in card0.body_canvas._items if item["type"] == "line") >= 2
    assert sum(1 for item in card1.body_canvas._items if item["type"] == "line") >= 2



def test_click_on_body_cell_triggers_begin_edit_and_survives_global_click_guard(monkeypatch):
    editor = _make_editor()
    editor.display_cols = [0]
    editor.tests = [SimpleNamespace(qc=["10"], fs=["5"], depth=["0.00"], tid=1, locked=False)]
    editor.flags = {1: SimpleNamespace(invalid=False, force_cells=set(), interp_cells=set(), user_cells=set(), algo_cells=set())}
    editor._active_test_idx = 0
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.soundings_viewport = SimpleNamespace(strip=None, canvas=SimpleNamespace(canvasx=lambda v: float(v), winfo_width=lambda: 320), xview_fractions=lambda: (0.0, 1.0))
    editor._grid_units = [("row", 0)]
    editor._grid_row_maps = {0: {0: 0}}
    editor._row_y_bounds = lambda row: (0.0, 22.0)
    editor._row_tops = [0.0, 22.0]
    editor._refresh_display_order = lambda: None
    editor._sync_layers_panel = lambda: None
    editor.schedule_graph_redraw = lambda: None
    editor._layer_depth_box_hitbox = []
    editor._layer_handle_hitbox = []
    editor._layer_label_hitbox = []
    editor._layer_plot_hitbox = []
    editor._layer_ige_picker = None
    editor._layer_ige_picker_meta = None
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.body_canvas = _DummyBodyCanvas()
    editor._sounding_cards = {0: card}
    calls = []
    editor._begin_edit = lambda ti, data_row, field, display_row=None: calls.append((ti, data_row, field, display_row))

    editor._on_left_click(SimpleNamespace(widget=card.body_canvas, x=80, y=10))
    editor._editing = (0, 0, "qc", object())
    editor._on_global_click(SimpleNamespace(widget=card.body_canvas))

    assert calls == [(0, 0, "qc", 0)]
    assert editor._editing is not None



def test_begin_edit_editor_rect_stays_inside_card_body_after_shared_scroll(monkeypatch):
    editor = _make_editor()
    editor.display_cols = [0, 1]
    editor.tests = [SimpleNamespace(qc=["10"], fs=["5"], depth=["0.00"], tid=1, locked=False), SimpleNamespace(qc=["11"], fs=["6"], depth=["0.00"], tid=2, locked=False)]
    editor.flags = {1: SimpleNamespace(invalid=False, force_cells=set(), interp_cells=set(), user_cells=set(), algo_cells=set()), 2: SimpleNamespace(invalid=False, force_cells=set(), interp_cells=set(), user_cells=set(), algo_cells=set())}
    editor._active_test_idx = 1
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.soundings_viewport = SimpleNamespace(strip=None, canvas=SimpleNamespace(canvasx=lambda v: float(v), winfo_width=lambda: 640), xview_fractions=lambda: (0.0, 1.0))
    editor._grid_units = [("row", 0)]
    editor._grid_row_maps = {0: {0: 0}, 1: {0: 0}}
    editor._row_y_bounds = lambda row: (100.0, 122.0)
    editor._row_tops = [100.0, 122.0]
    editor._refresh_display_order = lambda: None
    editor._sync_layers_panel = lambda: None
    editor._ensure_cell_visible = lambda *args, **kwargs: None
    editor._debug_tail_edit = False
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(1)
    card.body_canvas = _DummyBodyCanvas(rootx=1400, rooty=2000)
    editor._sounding_cards = {0: editor._card_for_test(0), 1: card}
    editor._apply_shared_body_yview_fraction(0.25)

    class _FakeEntry:
        def __init__(self, parent, **kwargs):
            self.parent = parent
            self.placed = None
        def insert(self, *_args):
            pass
        def get(self):
            return "11"
        def configure(self, **_kwargs):
            pass
        def select_range(self, *_args):
            pass
        def place(self, **kwargs):
            self.placed = kwargs
        def focus_set(self):
            pass
        def bind(self, *_args, **_kwargs):
            pass
        def icursor(self, *_args):
            pass
        def selection_range(self, *_args):
            pass
        def after_idle(self, fn):
            fn()

    entries = []
    monkeypatch.setattr(editor_module.tk, 'Entry', lambda parent, **kwargs: entries.append(_FakeEntry(parent, **kwargs)) or entries[-1])
    editor.register = lambda fn: fn

    editor._begin_edit(1, 0, 'qc', display_row=0)

    placed = entries[-1].placed
    assert placed is not None
    assert 0 <= placed['x'] <= card.geometry.card_width
    assert 0 <= placed['y'] <= 22.0



def test_bind_card_targets_rebinds_double_click_for_body_canvas():
    editor = _make_editor()
    editor.display_cols = [0]
    editor.tests = [object()]
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.soundings_viewport = SimpleNamespace(strip=None)
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.body_canvas = _DummyBodyCanvas()
    card.header_canvas = _DummyBodyCanvas()

    editor._bind_card_targets(card)

    assert '<Button-1>' in card.body_canvas.bindings
    assert '<Double-1>' in card.body_canvas.bindings


def test_bind_card_targets_keeps_header_bindings_alive_after_rebuild():
    editor = _make_editor()
    editor.display_cols = [0]
    editor.tests = [object()]
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.soundings_viewport = SimpleNamespace(strip=None)
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.body_canvas = _DummyBodyCanvas()
    card.header_canvas = _DummyBodyCanvas()

    editor._bind_card_targets(card)

    assert '<Button-1>' in card.header_canvas.bindings
    assert '<Motion>' in card.header_canvas.bindings
    assert '<MouseWheel>' in card.header_canvas.bindings


def test_hit_test_resolves_header_controls_on_card_header_canvas():
    editor = _make_editor()
    editor.display_cols = [0]
    editor.tests = [SimpleNamespace(tid=1, dt="01.01.2026 10:00", export_on=True, locked=False, qc=["10"], fs=["5"], depth=["0.00"])]
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.soundings_viewport = SimpleNamespace(strip=None, canvas=SimpleNamespace(canvasx=lambda v: float(v), winfo_width=lambda: 320), xview_fractions=lambda: (0.0, 1.0))
    editor._refresh_display_order = lambda: None
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.header_canvas = _DummyBodyCanvas()
    editor._sounding_cards = {0: card}
    editor._evt_widget = card.header_canvas

    assert editor._hit_test(10, 12) == ("export", 0, None, None)
    assert editor._hit_test(card.geometry.table_width - 14, 14) == ("trash", 0, None, None)
    assert editor._hit_test(220, 52) is None


def test_global_click_guard_does_not_close_editing_for_header_canvas():
    editor = _make_editor()
    editor.display_cols = [0]
    editor.tests = [object()]
    editor._table_col_width = lambda: 176
    editor._column_block_width = lambda: 326
    editor._is_graph_panel_visible = lambda: True
    editor.graph_w = 150
    editor.w_depth = 64
    editor.w_val = 56
    editor.soundings_viewport = SimpleNamespace(strip=None)
    editor._rebuild_sounding_cards()
    card = editor._card_for_test(0)
    card.header_canvas = _DummyBodyCanvas()
    editor._sounding_cards = {0: card}
    editor._editing = (0, 0, "qc", object())

    editor._on_global_click(SimpleNamespace(widget=card.header_canvas))

    assert editor._editing is not None
