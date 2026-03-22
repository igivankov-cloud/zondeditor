from types import SimpleNamespace

from src.zondeditor.ui.sounding_card import SoundingCard, SoundingCardGeometry


class _DummyCanvas:
    def __init__(self):
        self.calls = []
        self._config = {}
        self._y0 = 0.0

    def create_rectangle(self, *args, **kwargs):
        self.calls.append(("rectangle", args, kwargs))

    def create_line(self, *args, **kwargs):
        self.calls.append(("line", args, kwargs))

    def create_text(self, *args, **kwargs):
        self.calls.append(("text", args, kwargs))

    def delete(self, *args, **kwargs):
        self.calls.append(("delete", args, kwargs))

    def configure(self, **kwargs):
        self._config.update(kwargs)

    def cget(self, key):
        return self._config.get(key)

    def yview_moveto(self, frac):
        scrollregion = self._config.get("scrollregion", (0, 0, 0, 0))
        total = float(scrollregion[3] if len(scrollregion) >= 4 else 0.0)
        height = float(self._config.get("height", 0.0) or 0.0)
        max_y = max(0.0, total - height)
        self._y0 = min(max(float(frac) * max(total, 1.0), 0.0), max_y)
        self.calls.append(("yview_moveto", (frac,), {}))

    def canvasy(self, value):
        return self._y0 + float(value)


class _CountingCanvas(_DummyCanvas):
    def __init__(self):
        super().__init__()
        self.configure_calls = 0
        self.yview_calls = 0

    def configure(self, **kwargs):
        self.configure_calls += 1
        super().configure(**kwargs)

    def yview_moveto(self, frac):
        self.yview_calls += 1
        super().yview_moveto(frac)


class _DummyFont:
    def __init__(self, size):
        self.size = size

    def measure(self, text):
        return len(text) * self.size * 0.5

    def metrics(self, _name):
        return self.size + 2


def test_sounding_card_geometry_returns_local_and_world_bounds():
    g = SoundingCardGeometry(
        card_x0=120.0,
        card_y0=0.0,
        card_width=310.0,
        header_height=72.0,
        body_height=440.0,
        footer_height=24.0,
        table_width=176.0,
        graph_width=134.0,
        depth_width=64.0,
        value_width=56.0,
    )

    assert g.card_bounds_local == (0.0, 0.0, 310.0, 536.0)
    assert g.card_bounds_world == (120.0, 0.0, 430.0, 536.0)
    assert g.header_bounds_world == (120.0, 0.0, 430.0, 72.0)
    assert g.body_bounds_world == (120.0, 72.0, 430.0, 512.0)


def test_sounding_card_geometry_builds_cell_and_graph_boxes():
    g = SoundingCardGeometry(
        card_x0=50.0,
        card_y0=0.0,
        card_width=326.0,
        header_height=72.0,
        body_height=300.0,
        footer_height=0.0,
        table_width=176.0,
        graph_width=150.0,
        depth_width=64.0,
        value_width=56.0,
        inclinometer_width=56.0,
    )

    assert g.cell_bbox_world(22.0, 44.0, "depth") == (50.0, 22.0, 114.0, 44.0)
    assert g.cell_bbox_world(22.0, 44.0, "qc") == (114.0, 22.0, 170.0, 44.0)
    assert g.cell_bbox_world(22.0, 44.0, "fs") == (170.0, 22.0, 226.0, 44.0)
    assert g.graph_bbox_world(y0=0.0, y1=300.0) == (226.0, 0.0, 376.0, 300.0)


def test_sounding_card_geometry_exposes_anchor_and_handle_boxes():
    g = SoundingCardGeometry(
        card_x0=200.0,
        card_y0=0.0,
        card_width=310.0,
        header_height=72.0,
        body_height=400.0,
        footer_height=0.0,
        table_width=176.0,
        graph_width=134.0,
        depth_width=64.0,
        value_width=56.0,
    )

    assert g.header_anchor_world(dx=10.0, dy=8.0) == (210.0, 8.0)
    assert g.boundary_handle_world(y=120.0) == (302.0, 114.0, 314.0, 126.0)
    assert g.depth_box_world(y=120.0) == (256.0, 111.0, 296.0, 129.0)


def test_sounding_card_hit_testing_and_editor_rects():
    editor = SimpleNamespace(
        _header_world_to_root=lambda x, y: (int(x + 1000), int(y + 2000)),
        _body_world_to_root=lambda x, y: (int(x + 3000), int(y + 4000)),
    )
    g = SoundingCardGeometry(
        card_x0=200.0,
        card_y0=0.0,
        card_width=310.0,
        header_height=72.0,
        body_height=400.0,
        footer_height=20.0,
        table_width=176.0,
        graph_width=134.0,
        depth_width=64.0,
        value_width=56.0,
    )
    card = SoundingCard(None, editor=editor, test_index=7, geometry=g)

    assert card.contains_world(210.0, 10.0) is True
    assert card.section_at_world(210.0, 10.0) == "header"
    assert card.header_control_hit(208.0, 12.0) == "export"
    assert card.header_control_hit(362.0, 14.0) == "trash"
    assert card.header_control_hit(260.0, 14.0) == "header"
    assert card.header_control_hit(260.0, 52.0) is None
    assert card.table_field_hit(220.0, 22.0, 44.0) == "depth"
    assert card.table_field_hit(280.0, 22.0, 44.0) == "qc"
    assert card.graph_hit(390.0, 100.0) is True
    assert card.cell_editor_rect(22.0, 44.0, "qc") == (265.0, 23.0, 319.0, 43.0)
    assert card.depth0_editor_rect(22.0, 44.0) == (201.0, 23.0, 263.0, 43.0)
    assert card.header_anchor_root(dx=10.0, dy=8.0) == (1210, 2008)
    assert card.popup_anchor_root(240.0, 50.0, section="body") == (3240, 4050)


def test_sounding_card_render_header_and_body_cell_emit_card_local_bounds():
    editor = SimpleNamespace(
        _header_world_to_root=lambda x, y: (int(x), int(y)),
        _body_world_to_root=lambda x, y: (int(x), int(y)),
    )
    g = SoundingCardGeometry(
        card_x0=200.0,
        card_y0=0.0,
        card_width=310.0,
        header_height=72.0,
        body_height=400.0,
        footer_height=0.0,
        table_width=176.0,
        graph_width=134.0,
        depth_width=64.0,
        value_width=56.0,
    )
    card = SoundingCard(None, editor=editor, test_index=7, geometry=g)
    canvas = _DummyCanvas()

    hitboxes = card.render_header(
        canvas,
        title="Опыт 7",
        datetime_text="01.01.2026 10:00",
        header_fill="#fff",
        header_text="#111",
        header_icon="#444",
        export_on=True,
        lock_on=False,
        hover=None,
        icon_calendar="📅",
        icon_copy="⧉",
        icon_delete="🗑",
        icon_font=("Segoe UI Symbol", 12),
        hdr_h=64.0,
        show_inclinometer=False,
        show_graph_scale=True,
        qc_scale_max=30.0,
        fs_scale_max=120.0,
        qc_scale_unit="МПа",
        fs_scale_unit="кПа",
    )
    rect = card.render_body_cell(canvas, row_y0=22.0, row_y1=44.0, field="qc", text="12", fill="#fff", text_color="#000")

    assert hitboxes["header"] == (200.0, 0.0, 510.0, 72.0)
    assert hitboxes["experience_band"][2] == 376.0
    assert hitboxes["graph_band"][0] == 376.0
    assert hitboxes["graph_band"] == (376.0, 0.0, 510.0, 72.0)
    assert hitboxes["scale_band"] == hitboxes["graph_band"]
    assert hitboxes["edit"] == (299.0, 4.0, 321.0, 24.0)
    assert rect == (264.0, 22.0, 320.0, 44.0)
    assert any(call[0] == "rectangle" for call in canvas.calls)
    assert any(call[0] == "text" for call in canvas.calls)
    graph_texts = [call for call in canvas.calls if call[0] == "text" and call[1] and call[1][0] >= (200.0 + 176.0)]
    graph_boxes = [call for call in canvas.calls if call[0] == "rectangle" and call[1] and call[1][0] >= (200.0 + 176.0)]
    graph_lines = [call for call in canvas.calls if call[0] == "line" and call[1] and call[1][0] >= (200.0 + 176.0)]
    info_boxes = [call for call in canvas.calls if call[0] == "rectangle" and call[2].get("fill") == "#fff"]
    neutral_boxes = [call for call in canvas.calls if call[0] == "rectangle" and call[2].get("fill") == "#fbfbfb"]
    assert any("qc 0–30 МПа" in call[2].get("text", "") for call in graph_texts)
    assert any("fs 0–120 кПа" in call[2].get("text", "") for call in graph_texts)
    assert any(call[1][0] <= (hitboxes["scale_band"][0] + 6.0) and call[1][2] >= (hitboxes["scale_band"][2] - 6.0) for call in graph_boxes)
    assert any(call[1] == hitboxes["experience_band"] for call in info_boxes)
    assert any(call[1] == hitboxes["graph_band"] for call in neutral_boxes)
    assert hitboxes["lock"][0] < hitboxes["graph_band"][0]
    assert hitboxes["lock"][2] <= hitboxes["experience_band"][2]
    qc_label = next(call for call in graph_texts if "qc 0–30 МПа" in call[2].get("text", ""))
    fs_label = next(call for call in graph_texts if "fs 0–120 кПа" in call[2].get("text", ""))
    assert qc_label[2]["fill"] == "#2f9e44"
    assert fs_label[2]["fill"] == "#2563eb"
    assert qc_label[1][1] < fs_label[1][1]
    qc_scale_lines = [call for call in graph_lines if call[2].get("fill") == "#2f9e44"]
    fs_scale_lines = [call for call in graph_lines if call[2].get("fill") == "#2563eb"]
    assert qc_scale_lines and fs_scale_lines
    assert max(line[1][1] for line in qc_scale_lines) < min(line[1][1] for line in fs_scale_lines)


def test_sounding_card_make_hitbox_is_card_local_owner_api():
    editor = SimpleNamespace(
        _header_world_to_root=lambda x, y: (int(x), int(y)),
        _body_world_to_root=lambda x, y: (int(x), int(y)),
    )
    g = SoundingCardGeometry(
        card_x0=50.0,
        card_y0=0.0,
        card_width=326.0,
        header_height=72.0,
        body_height=300.0,
        footer_height=0.0,
        table_width=176.0,
        graph_width=150.0,
        depth_width=64.0,
        value_width=56.0,
    )
    card = SoundingCard(None, editor=editor, test_index=3, geometry=g)

    hit = card.make_hitbox(kind="boundary", bbox=(310.0, 80.0, 330.0, 100.0), boundary=2, extra={"tag": "h1"})

    assert hit == {"kind": "boundary", "ti": 3, "bbox": (310.0, 80.0, 330.0, 100.0), "boundary": 2, "tag": "h1"}


def test_sounding_card_render_graph_ige_and_overlays_are_self_owned():
    editor = SimpleNamespace(
        _header_world_to_root=lambda x, y: (int(x), int(y)),
        _body_world_to_root=lambda x, y: (int(x), int(y)),
    )
    g = SoundingCardGeometry(
        card_x0=50.0,
        card_y0=0.0,
        card_width=326.0,
        header_height=72.0,
        body_height=300.0,
        footer_height=0.0,
        table_width=176.0,
        graph_width=150.0,
        depth_width=64.0,
        value_width=56.0,
    )
    card = SoundingCard(None, editor=editor, test_index=3, geometry=g)
    canvas = _DummyCanvas()

    card.render_graph(
        canvas,
        rect=(226.0, 376.0, 0.0, 300.0),
        y_points=[20.0, 40.0, 60.0],
        qc_values=[1.0, 2.0, 3.0],
        fs_values=[10.0, 20.0, 30.0],
        qmax=5.0,
        fmax=50.0,
        qc_color="#0a0",
        fs_color="#00a",
        frame_fill="#fff",
        frame_outline="#ccc",
        groundwater_level=100.0,
    )
    plot_hits, label_hits = card.render_ige(
        canvas,
        intervals=[{"interval_index": 0, "ige_id": "ИГЭ-1", "soil_type": "sand", "top": 0.0, "bot": 1.0, "depth": 0.5, "x0": 226.0, "x1": 376.0, "y0": 0.0, "y1": 120.0}],
        fill_resolver=lambda soil: "#eee",
        hatch_drawer=lambda *args, **kwargs: None,
        label_font_factory=lambda size: _DummyFont(size),
        layer_ui_colors={"fill": "#eef3f8", "fill_active": "#e3ebf3", "outline": "#b7c4d1", "outline_active": "#97a8ba", "text": "#4d5c6b", "text_muted": "#9aa7b4", "line": "#aebbc8", "focus": "#7f94a9"},
    )
    handle_hits, depth_hits = card.render_overlays(
        canvas,
        overlay_specs=[
            {"kind": "line", "points": (226.0, 120.0, 376.0, 120.0), "fill": "#aaa", "dash": (3, 2)},
            {"kind": "handle", "bbox": (369.0, 115.0, 379.0, 125.0), "boundary": 1, "hit_kind": "boundary", "tag": "h1"},
            {"kind": "depth_box", "bbox": (324.0, 112.0, 364.0, 128.0), "boundary": 1, "hit_kind": "boundary_depth_edit", "text": "1.00"},
            {"kind": "plus", "bbox": (230.0, 114.0, 242.0, 126.0), "boundary": 1, "hit_kind": "plus", "tag": "p1"},
        ],
        layer_ui_colors={"fill": "#eef3f8", "fill_active": "#e3ebf3", "outline": "#b7c4d1", "outline_active": "#97a8ba", "text": "#4d5c6b", "text_muted": "#9aa7b4", "line": "#aebbc8", "focus": "#7f94a9"},
    )

    assert plot_hits[0]["kind"] == "interval"
    assert label_hits[0]["kind"] == "label"
    assert handle_hits[0]["kind"] == "boundary"
    assert depth_hits[0]["kind"] == "boundary_depth_edit"
    assert "graphs" in card.render_ownership_snapshot()["owned"]


def test_sounding_card_body_scroll_and_redraw_lifecycle_are_card_owned():
    editor = SimpleNamespace(
        _header_world_to_root=lambda x, y: (int(x), int(y)),
        _body_world_to_root=lambda x, y, ti=None: (int(x), int(y)),
    )
    g = SoundingCardGeometry(
        card_x0=50.0,
        card_y0=0.0,
        card_width=326.0,
        header_height=72.0,
        body_height=300.0,
        footer_height=0.0,
        table_width=176.0,
        graph_width=150.0,
        depth_width=64.0,
        value_width=56.0,
    )
    card = SoundingCard(None, editor=editor, test_index=3, geometry=g)
    calls = []

    card.set_body_scroll_context(view_height=100.0, content_height=400.0)
    card.body_yview_moveto(0.25)
    card.bind_redraw_callback("graph", lambda: calls.append("graph"))
    card.bind_redraw_callback("layers", lambda: calls.append("layers"))
    card.redraw_if_needed("graph", "layers")
    card.invalidate_graph()
    card.invalidate_layers()
    redrawn = card.redraw_if_needed("graph", "layers")
    snapshot = card.dev_selfcheck_snapshot()

    assert round(card.body_yview()[0], 2) == 0.25
    assert card.body_world_to_local(70.0, 130.0) == (20.0, 30.0)
    assert redrawn == ("graph", "layers")
    assert calls[-2:] == ["graph", "layers"]
    assert snapshot["body_yview"] == card.body_yview()
    assert "card_redraw_lifecycle" in card.render_ownership_snapshot()["owned"]


def test_sounding_card_scroll_moves_view_without_reconfiguring_canvas_each_step():
    editor = SimpleNamespace(
        _header_world_to_root=lambda x, y: (int(x), int(y)),
        _body_world_to_root=lambda x, y, ti=None: (int(x), int(y)),
    )
    g = SoundingCardGeometry(
        card_x0=50.0,
        card_y0=0.0,
        card_width=326.0,
        header_height=72.0,
        body_height=300.0,
        footer_height=0.0,
        table_width=176.0,
        graph_width=150.0,
        depth_width=64.0,
        value_width=56.0,
    )
    card = SoundingCard(None, editor=editor, test_index=3, geometry=g)
    canvas = _CountingCanvas()
    card.body_canvas = canvas

    card.set_body_scroll_context(view_height=100.0, content_height=400.0)
    configure_after_context = canvas.configure_calls
    card.body_yview_moveto(0.25)
    card.body_yview_scroll(1, "units")

    assert canvas.configure_calls == configure_after_context
    assert canvas.yview_calls >= 3


def test_sounding_card_body_canvas_is_render_target_for_graph_and_overlay_coords():
    editor = SimpleNamespace(
        _header_world_to_root=lambda x, y: (int(x), int(y)),
        _body_world_to_root=lambda x, y, ti=None: (int(x), int(y)),
    )
    g = SoundingCardGeometry(
        card_x0=50.0,
        card_y0=0.0,
        card_width=326.0,
        header_height=72.0,
        body_height=300.0,
        footer_height=0.0,
        table_width=176.0,
        graph_width=150.0,
        depth_width=64.0,
        value_width=56.0,
    )
    card = SoundingCard(None, editor=editor, test_index=5, geometry=g)
    card.body_canvas = _DummyCanvas()
    card.set_body_scroll_context(view_height=100.0, content_height=400.0)
    card.body_yview_moveto(0.25)

    card.render_graph(
        None,
        rect=(226.0, 100.0, 376.0, 200.0),
        y_points=[110.0, 130.0],
        qc_values=[1.0, 2.0],
        fs_values=[10.0, 20.0],
        qmax=5.0,
        fmax=50.0,
        qc_color="#0a0",
        fs_color="#00a",
        frame_fill="#fff",
        frame_outline="#ccc",
        groundwater_level=120.0,
    )
    handle_hits, _depth_hits = card.render_overlays(
        None,
        overlay_specs=[{"kind": "handle", "bbox": (300.0, 120.0, 310.0, 130.0), "boundary": 1, "hit_kind": "boundary", "tag": "h"}],
        layer_ui_colors={"fill": "#eef3f8", "fill_active": "#e3ebf3", "outline": "#b7c4d1", "outline_active": "#97a8ba", "text": "#4d5c6b", "text_muted": "#9aa7b4", "line": "#aebbc8", "focus": "#7f94a9"},
    )

    rect_call = next(call for call in card.body_canvas.calls if call[0] == "rectangle")
    assert rect_call[1] == (176.0, 0.0, 326.0, 100.0)
    assert handle_hits[0]["bbox"] == (299.0, 119.0, 311.0, 131.0)


def test_sounding_card_header_and_table_can_render_into_card_owned_targets():
    editor = SimpleNamespace(
        _header_world_to_root=lambda x, y: (int(x), int(y)),
        _body_world_to_root=lambda x, y, ti=None: (int(x), int(y)),
    )
    g = SoundingCardGeometry(
        card_x0=200.0,
        card_y0=0.0,
        card_width=310.0,
        header_height=72.0,
        body_height=300.0,
        footer_height=0.0,
        table_width=176.0,
        graph_width=134.0,
        depth_width=64.0,
        value_width=56.0,
    )
    card = SoundingCard(None, editor=editor, test_index=9, geometry=g)
    card.header_canvas = _DummyCanvas()
    card.body_canvas = _DummyCanvas()
    header_hits = card.render_header(
        None,
        title="Опыт 9",
        datetime_text="01.01.2026 10:00",
        header_fill="#fff",
        header_text="#111",
        header_icon="#444",
        export_on=True,
        lock_on=False,
        hover=None,
        icon_calendar="📅",
        icon_copy="⧉",
        icon_delete="🗑",
        icon_font=("Segoe UI Symbol", 12),
        hdr_h=64.0,
        show_inclinometer=False,
        show_graph_scale=True,
        qc_scale_max=30.0,
        fs_scale_max=120.0,
        qc_scale_unit="МПа",
        fs_scale_unit="кПа",
    )
    rect = card.render_body_cell(None, row_y0=22.0, row_y1=44.0, field="qc", text="12", fill="#fff", text_color="#000")

    assert header_hits["header"] == (0.0, 0.0, 310.0, 72.0)
    assert rect == (64.0, 22.0, 120.0, 44.0)


class _FakeFrame:
    def __init__(self, master=None):
        self.master = master


class _FakeTkCanvas:
    next_window_id = 1

    def __init__(self, master=None, **kwargs):
        self.master = master
        self.kwargs = dict(kwargs)
        self.configured = []
        self.destroyed = False
        self.windows = {}
        self.coords_calls = []

    def configure(self, **kwargs):
        self.configured.append(dict(kwargs))
        self.kwargs.update(kwargs)

    def create_window(self, coords, window=None, anchor=None):
        window_id = _FakeTkCanvas.next_window_id
        _FakeTkCanvas.next_window_id += 1
        self.windows[window_id] = {"coords": tuple(coords), "window": window, "anchor": anchor}
        return window_id

    def coords(self, window_id, x, y):
        self.coords_calls.append((window_id, x, y))
        self.windows[window_id]["coords"] = (x, y)

    def destroy(self):
        self.destroyed = True



def test_mount_targets_lazily_creates_canvases_with_correct_hosts(monkeypatch):
    import src.zondeditor.ui.sounding_card as sounding_card_module

    monkeypatch.setattr(sounding_card_module.ttk, 'Frame', _FakeFrame)
    monkeypatch.setattr(sounding_card_module.tk, 'Canvas', _FakeTkCanvas)

    editor = SimpleNamespace(
        _header_world_to_root=lambda x, y: (int(x), int(y)),
        _body_world_to_root=lambda x, y, ti=None: (int(x), int(y)),
    )
    g = SoundingCardGeometry(
        card_x0=50.0,
        card_y0=0.0,
        card_width=326.0,
        header_height=72.0,
        body_height=300.0,
        footer_height=0.0,
        table_width=176.0,
        graph_width=150.0,
        depth_width=64.0,
        value_width=56.0,
    )
    card = SoundingCard(object(), editor=editor, test_index=11, geometry=g)
    header_host = _FakeTkCanvas()
    body_host = _FakeTkCanvas()

    assert card.header_canvas is None
    assert card.body_canvas is None

    card.mount_targets(header_host=header_host, body_host=body_host, body_view_height=120.0)
    header_canvas = card.header_canvas
    body_canvas = card.body_canvas

    assert header_canvas is not None and header_canvas.master is header_host
    assert body_canvas is not None and body_canvas.master is body_host
    assert card._header_window_id in header_host.windows
    assert card._body_window_id in body_host.windows

    old_header_window_id = card._header_window_id
    old_body_window_id = card._body_window_id
    card.update_geometry(SoundingCardGeometry(
        card_x0=75.0,
        card_y0=0.0,
        card_width=330.0,
        header_height=72.0,
        body_height=300.0,
        footer_height=0.0,
        table_width=180.0,
        graph_width=150.0,
        depth_width=64.0,
        value_width=56.0,
    ))
    card.mount_targets(header_host=header_host, body_host=body_host, body_view_height=120.0)

    assert card._header_window_id == old_header_window_id
    assert card._body_window_id == old_body_window_id
    assert header_host.coords_calls[-1] == (old_header_window_id, 75.0, 0.0)
    assert body_host.coords_calls[-1] == (old_body_window_id, 75.0, 0.0)



def test_mount_targets_recreates_canvases_when_existing_master_is_wrong(monkeypatch):
    import src.zondeditor.ui.sounding_card as sounding_card_module

    monkeypatch.setattr(sounding_card_module.ttk, 'Frame', _FakeFrame)
    monkeypatch.setattr(sounding_card_module.tk, 'Canvas', _FakeTkCanvas)

    editor = SimpleNamespace(
        _header_world_to_root=lambda x, y: (int(x), int(y)),
        _body_world_to_root=lambda x, y, ti=None: (int(x), int(y)),
    )
    g = SoundingCardGeometry(
        card_x0=50.0,
        card_y0=0.0,
        card_width=326.0,
        header_height=72.0,
        body_height=300.0,
        footer_height=0.0,
        table_width=176.0,
        graph_width=150.0,
        depth_width=64.0,
        value_width=56.0,
    )
    card = SoundingCard(object(), editor=editor, test_index=12, geometry=g)
    wrong_header_parent = _FakeFrame()
    wrong_body_parent = _FakeFrame()
    wrong_header_canvas = _FakeTkCanvas(wrong_header_parent)
    wrong_body_canvas = _FakeTkCanvas(wrong_body_parent)
    card.header_canvas = wrong_header_canvas
    card.body_canvas = wrong_body_canvas

    header_host = _FakeTkCanvas()
    body_host = _FakeTkCanvas()
    card.mount_targets(header_host=header_host, body_host=body_host, body_view_height=120.0)

    assert wrong_header_canvas.destroyed is True
    assert wrong_body_canvas.destroyed is True
    assert card.header_canvas is not wrong_header_canvas and card.header_canvas.master is header_host
    assert card.body_canvas is not wrong_body_canvas and card.body_canvas.master is body_host



def test_body_scroll_syncs_canvas_view_and_local_y_pipeline():
    editor = SimpleNamespace(
        _header_world_to_root=lambda x, y: (int(x), int(y)),
        _body_world_to_root=lambda x, y, ti=None: (int(x), int(y)),
    )
    g = SoundingCardGeometry(
        card_x0=50.0,
        card_y0=0.0,
        card_width=326.0,
        header_height=72.0,
        body_height=300.0,
        footer_height=0.0,
        table_width=176.0,
        graph_width=150.0,
        depth_width=64.0,
        value_width=56.0,
    )
    card = SoundingCard(None, editor=editor, test_index=13, geometry=g)
    card.body_canvas = _DummyCanvas()
    card.set_body_scroll_context(view_height=100.0, content_height=400.0)
    card.body_yview_moveto(0.25)

    assert round(card.body_canvasy(0), 2) == 100.0
    assert card.body_world_to_local(70.0, 130.0) == (20.0, 30.0)
    assert card.body_local_to_world(20.0, 30.0) == (70.0, 130.0)
    assert card.dev_selfcheck_snapshot()["body_scrollregion"] == (0, 0, 326, 400)



def test_card_body_renderers_respect_visibility_flags():
    editor = SimpleNamespace(
        _header_world_to_root=lambda x, y: (int(x), int(y)),
        _body_world_to_root=lambda x, y, ti=None: (int(x), int(y)),
    )
    g = SoundingCardGeometry(
        card_x0=50.0,
        card_y0=0.0,
        card_width=326.0,
        header_height=72.0,
        body_height=300.0,
        footer_height=0.0,
        table_width=176.0,
        graph_width=150.0,
        depth_width=64.0,
        value_width=56.0,
    )
    card = SoundingCard(None, editor=editor, test_index=14, geometry=g)
    canvas = _DummyCanvas()

    assert card.render_graph(canvas, rect=(226.0, 0.0, 376.0, 100.0), y_points=[20.0], qc_values=[1.0], fs_values=[2.0], qmax=5.0, fmax=50.0, qc_color="#0a0", fs_color="#00a", frame_fill="#fff", frame_outline="#ccc", visible=False) == (226.0, 0.0, 376.0, 100.0)
    assert card.render_ige(canvas, intervals=[{"interval_index": 0, "ige_id": "ИГЭ-1", "soil_type": "sand", "top": 0.0, "bot": 1.0, "depth": 0.5, "x0": 226.0, "x1": 376.0, "y0": 0.0, "y1": 120.0}], fill_resolver=lambda soil: "#eee", hatch_drawer=lambda *args, **kwargs: None, label_font_factory=lambda size: _DummyFont(size), layer_ui_colors={"fill": "#eef3f8", "fill_active": "#e3ebf3", "outline": "#b7c4d1", "outline_active": "#97a8ba", "text": "#4d5c6b", "text_muted": "#9aa7b4", "line": "#aebbc8", "focus": "#7f94a9"}, visible=False) == ([], [])
    assert card.render_overlays(canvas, overlay_specs=[{"kind": "line", "points": (226.0, 120.0, 376.0, 120.0)}], layer_ui_colors={"fill": "#eef3f8", "fill_active": "#e3ebf3", "outline": "#b7c4d1", "outline_active": "#97a8ba", "text": "#4d5c6b", "text_muted": "#9aa7b4", "line": "#aebbc8", "focus": "#7f94a9"}, visible=False) == ([], [])
    assert canvas.calls == []
