from types import SimpleNamespace

from src.zondeditor.ui.sounding_card import SoundingCard, SoundingCardGeometry


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
    assert g.header_bounds_world == (120.0, 0.0, 296.0, 72.0)
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
    assert card.table_field_hit(220.0, 22.0, 44.0) == "depth"
    assert card.table_field_hit(280.0, 22.0, 44.0) == "qc"
    assert card.graph_hit(390.0, 100.0) is True
    assert card.cell_editor_rect(22.0, 44.0, "qc") == (265.0, 23.0, 319.0, 43.0)
    assert card.depth0_editor_rect(22.0, 44.0) == (201.0, 23.0, 263.0, 43.0)
    assert card.header_anchor_root(dx=10.0, dy=8.0) == (1210, 2008)
    assert card.popup_anchor_root(240.0, 50.0, section="body") == (3240, 4050)
