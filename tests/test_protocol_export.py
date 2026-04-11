import math

from src.zondeditor.domain.experience_column import ColumnInterval, ExperienceColumn
from src.zondeditor.domain.hatching.registry import SOIL_TYPE_TO_PAT_FILE, load_registered_hatch, load_registered_pat_pattern
from src.zondeditor.domain.models import TestData
from src.zondeditor.export.cad.dxf_writer import EMBEDDED_PAT_PATTERN_TYPE, _entity_polyline_lineweight, _offset_pattern_definition
from src.zondeditor.export.protocol import build_protocol_documents, build_protocol_scene
from src.zondeditor.export.protocol import exporters as protocol_exporters
from src.zondeditor.export.protocol.layout import DEFAULT_PROTOCOL_LAYOUT
from src.zondeditor.export.protocol.models import ProtocolDocument, ProtocolLayerRow
from src.zondeditor.processing.calibration import Calibration


def _test_data(tid: int = 1) -> TestData:
    return TestData(
        tid=tid,
        dt="09.07.25",
        depth=["0", "0.5", "1.0", "1.5", "2.0"],
        qc=["10", "20", "30", "40", "50"],
        fs=["5", "10", "15", "20", "25"],
    )


def _calibration() -> Calibration:
    return Calibration(scale_div=250, fcone_kn=30.0, fsleeve_kn=10.0, cone_area_cm2=10.0, sleeve_area_cm2=350.0)


def _patterned_section_hatches(result):
    return [
        hatch
        for hatch in result.scene.block.hatches
        if hatch.layer == "ZE_PROTO_CUT" and bool(hatch.pattern_name or hatch.pattern_definition)
    ]


def _solid_section_hatches(result):
    return [
        hatch
        for hatch in result.scene.block.hatches
        if hatch.layer == "ZE_PROTO_CUT" and hatch.solid and not hatch.pattern_definition and hatch.rgb is not None
    ]


def _pat_definition_as_dxf_rows(soil_type: str):
    pat = load_registered_pat_pattern(soil_type)
    assert pat is not None
    rows = []
    for angle_deg, base_point, offset, dash_items in pat.definition:
        angle_rad = math.radians(float(angle_deg))
        ex_x = math.cos(angle_rad)
        ex_y = math.sin(angle_rad)
        ey_x = -math.sin(angle_rad)
        ey_y = math.cos(angle_rad)
        rows.append(
            (
                float(angle_deg),
                (float(base_point[0]), float(base_point[1])),
                (
                    float(offset[0]) * ex_x + float(offset[1]) * ey_x,
                    float(offset[0]) * ex_y + float(offset[1]) * ey_y,
                ),
                [float(item) for item in dash_items],
            )
        )
    return rows


def _rounded_pattern_rows(rows, digits: int = 5):
    rounded = []
    for angle_deg, base_point, offset, dash_items in rows:
        rounded.append(
            (
                round(float(angle_deg), digits),
                (round(float(base_point[0]), digits), round(float(base_point[1]), digits)),
                (round(float(offset[0]), digits), round(float(offset[1]), digits)),
                [round(float(item), digits) for item in dash_items],
            )
        )
    return rounded


def test_protocol_scene_builds_with_dynamic_depth():
    pack = build_protocol_documents(tests=[_test_data()], ige_registry={"ИГЭ-1": {"notes": "Глина"}})
    result = build_protocol_scene(doc=pack.documents[0], calibration=_calibration(), block_name="PROTO1")
    assert result.height_mm > 0
    assert result.scene.block.name == "PROTO1"
    assert len(result.scene.block.polylines) >= 1


def test_protocol_build_uses_selected_order():
    t1 = _test_data(2)
    t2 = _test_data(5)
    pack = build_protocol_documents(tests=[t1, t2], ige_registry={})
    assert [doc.test.tid for doc in pack.documents] == [2, 5]


def test_protocol_scene_uses_registered_pat_patterns_for_section_layers():
    pack = build_protocol_documents(
        tests=[_test_data()],
        ige_registry={"ИГЭ-1": {"soil_type": "глина", "notes": "Глина"}},
    )
    result = build_protocol_scene(doc=pack.documents[0], calibration=_calibration(), block_name="PROTO_HATCH")
    patterned = _patterned_section_hatches(result)
    expected_name = load_registered_pat_pattern("глина").name
    assert patterned
    assert all(len(h.boundary) >= 4 for h in patterned)
    assert all(len(h.pattern_definition) > 0 for h in patterned)
    assert all(str(h.pattern_name or "") == expected_name for h in patterned)
    assert _rounded_pattern_rows(patterned[0].pattern_definition) == _rounded_pattern_rows(_pat_definition_as_dxf_rows("глина"))


def test_protocol_scene_keeps_solid_hatches_for_masks_and_ruler():
    pack = build_protocol_documents(tests=[_test_data()], ige_registry={})
    result = build_protocol_scene(doc=pack.documents[0], calibration=_calibration(), block_name="PROTO_SOLID")
    solid_layers = {h.layer for h in result.scene.block.hatches if h.solid and not h.pattern_definition}
    assert "ZE_PROTO_MASK" in solid_layers
    assert "ZE_PROTO_RULER" in solid_layers


def test_protocol_scene_keeps_circle_mask_above_interval_hatch():
    pack = build_protocol_documents(
        tests=[_test_data()],
        ige_registry={"ИГЭ-1": {"soil_type": "глина", "notes": "Глина"}},
    )
    result = build_protocol_scene(doc=pack.documents[0], calibration=_calibration(), block_name="PROTO_MASK_ORDER")
    hatch_layers = [h.layer for h in result.scene.block.hatches]
    assert "ZE_PROTO_CUT" in hatch_layers
    assert "ZE_PROTO_MASK" in hatch_layers
    assert hatch_layers.index("ZE_PROTO_CUT") < hatch_layers.index("ZE_PROTO_MASK")


def test_protocol_suglinok_pattern_uses_exact_pat_offset():
    suglinok_soil_type = next(soil for soil, pat_file in SOIL_TYPE_TO_PAT_FILE.items() if pat_file == "Suglinok.pat")
    doc = ProtocolDocument(
        test=_test_data(),
        title="PROTO SUG",
        date_text="09.07.2025",
        max_depth_m=2.0,
        layers=[
            ProtocolLayerRow(
                idx=1,
                from_depth_m=0.0,
                to_depth_m=2.0,
                ige_id="ИГЭ-1",
                description="Суглинок",
                soil_type=suglinok_soil_type,
            )
        ],
    )
    result = build_protocol_scene(doc=doc, calibration=_calibration(), block_name="PROTO_SUG")
    patterned = _patterned_section_hatches(result)
    assert patterned
    first_row = patterned[0].pattern_definition[0]
    angle_deg, base_point, offset, dash_items = first_row
    assert angle_deg == 45.0
    assert round(base_point[0], 5) == -2.12132
    assert round(base_point[1], 5) == 2.12132
    assert round(offset[0], 5) == 3.99515
    assert round(offset[1], 5) == -3.99515
    assert dash_items == []


def test_protocol_build_infers_soil_type_from_description_when_registry_field_missing():
    pack = build_protocol_documents(
        tests=[_test_data()],
        ige_registry={"ИГЭ-1": {"notes": "ИГЭ-1 (суглинок)"}},
    )
    assert pack.documents
    assert pack.documents[0].layers
    assert pack.documents[0].layers[0].soil_type == "суглинок"


def test_protocol_build_resolves_soil_type_by_ige_number_when_id_formats_differ():
    test = _test_data()
    test.experience_column = ExperienceColumn(
        column_depth_start=0.0,
        column_depth_end=2.0,
        intervals=[ColumnInterval(from_depth=0.0, to_depth=2.0, ige_id="ИГЭ-3", ige_name="")],
    )
    pack = build_protocol_documents(
        tests=[test],
        ige_registry={"ИГ-3": {"soil_type": "песок", "label": "ИГ-3"}},
    )
    assert pack.documents
    assert pack.documents[0].layers
    assert pack.documents[0].layers[0].soil_type == "песок"


def test_registry_supports_argilit_alias():
    assert load_registered_hatch("аргилит") is not None
    assert load_registered_pat_pattern("аргилит") is not None


def test_protocol_section_pattern_hatches_use_black_color():
    pack = build_protocol_documents(
        tests=[_test_data()],
        ige_registry={"ИГЭ-1": {"soil_type": "глина", "notes": "Глина"}},
    )
    result = build_protocol_scene(doc=pack.documents[0], calibration=_calibration(), block_name="PROTO_BLACK_HATCH")
    patterned = _patterned_section_hatches(result)
    assert patterned
    assert all(h.color_aci == 7 for h in patterned)


def test_protocol_section_color_fill_is_optional_and_uses_column_palette():
    clay_soil_type = next(soil for soil, pat_file in SOIL_TYPE_TO_PAT_FILE.items() if pat_file == "Glina.pat")
    doc = ProtocolDocument(
        test=_test_data(),
        title="PROTO COLOR",
        date_text="09.07.2025",
        max_depth_m=2.0,
        layers=[
            ProtocolLayerRow(
                idx=1,
                from_depth_m=0.0,
                to_depth_m=2.0,
                ige_id="ИГЭ-1",
                description="Глина",
                soil_type=clay_soil_type,
            )
        ],
    )
    plain = build_protocol_scene(doc=doc, calibration=_calibration(), block_name="PROTO_PLAIN", colorize_sections=False)
    colored = build_protocol_scene(doc=doc, calibration=_calibration(), block_name="PROTO_COLOR", colorize_sections=True)
    assert not _solid_section_hatches(plain)
    solid_fills = _solid_section_hatches(colored)
    assert solid_fills
    assert solid_fills[0].rgb == (168, 142, 122)
    patterned = _patterned_section_hatches(colored)
    assert patterned
    assert colored.scene.block.hatches.index(solid_fills[0]) < colored.scene.block.hatches.index(patterned[0])


def test_protocol_argillit_pattern_definition_matches_autocad_hatch_rows():
    argillit_soil_type = next(soil for soil, pat_file in SOIL_TYPE_TO_PAT_FILE.items() if pat_file == "Argillit.pat")
    doc = ProtocolDocument(
        test=_test_data(),
        title="PROTO ARGILLIT",
        date_text="09.07.2025",
        max_depth_m=2.0,
        layers=[
            ProtocolLayerRow(
                idx=1,
                from_depth_m=0.0,
                to_depth_m=2.0,
                ige_id="ИГЭ-1",
                description="Аргиллит",
                soil_type=argillit_soil_type,
            )
        ],
    )
    result = build_protocol_scene(doc=doc, calibration=_calibration(), block_name="PROTO_ARGILLIT", colorize_sections=False)
    patterned = _patterned_section_hatches(result)
    assert patterned
    assert _rounded_pattern_rows(patterned[0].pattern_definition) == _rounded_pattern_rows(_pat_definition_as_dxf_rows(argillit_soil_type))


def test_protocol_graviy_pattern_definition_matches_autocad_hatch_rows():
    graviy_soil_type = next(soil for soil, pat_file in SOIL_TYPE_TO_PAT_FILE.items() if pat_file == "graviy.pat")
    doc = ProtocolDocument(
        test=_test_data(),
        title="PROTO GRAVIY",
        date_text="09.07.2025",
        max_depth_m=2.0,
        layers=[
            ProtocolLayerRow(
                idx=1,
                from_depth_m=0.0,
                to_depth_m=2.0,
                ige_id="ИГЭ-1",
                description="Гравий",
                soil_type=graviy_soil_type,
            )
        ],
    )
    result = build_protocol_scene(doc=doc, calibration=_calibration(), block_name="PROTO_GRAVIY", colorize_sections=False)
    patterned = _patterned_section_hatches(result)
    assert patterned
    assert _rounded_pattern_rows(patterned[0].pattern_definition) == _rounded_pattern_rows(_pat_definition_as_dxf_rows(graviy_soil_type))


def test_protocol_uses_same_dxf_pattern_rows_across_intervals():
    graviy_soil_type = next(soil for soil, pat_file in SOIL_TYPE_TO_PAT_FILE.items() if pat_file == "graviy.pat")
    doc = ProtocolDocument(
        test=_test_data(),
        title="PROTO SHARED ORIGIN",
        date_text="09.07.2025",
        max_depth_m=4.0,
        layers=[
            ProtocolLayerRow(idx=1, from_depth_m=0.0, to_depth_m=2.0, ige_id="ИГЭ-1", description="Гравий", soil_type=graviy_soil_type),
            ProtocolLayerRow(idx=2, from_depth_m=2.0, to_depth_m=4.0, ige_id="ИГЭ-2", description="Гравий", soil_type=graviy_soil_type),
        ],
    )
    result = build_protocol_scene(doc=doc, calibration=_calibration(), block_name="PROTO_SHARED_ORIGIN")
    patterned = _patterned_section_hatches(result)
    assert len(patterned) == 2
    expected = _rounded_pattern_rows(_pat_definition_as_dxf_rows(graviy_soil_type))
    assert _rounded_pattern_rows(patterned[0].pattern_definition) == expected
    assert _rounded_pattern_rows(patterned[1].pattern_definition) == expected
    assert patterned[0].pattern_definition == patterned[1].pattern_definition


def test_protocol_embedded_pat_uses_custom_pattern_type():
    assert EMBEDDED_PAT_PATTERN_TYPE == 2


def test_embedded_pat_definition_is_shifted_with_scene_insertion():
    rows = [
        (45.0, (3.15, 2.7), (-4.499999978306722, 4.499999978306722), [1.272792, -5.091169]),
        (0.0, (4.05, 0.9), (4.5, 4.5), [0.9, -8.1]),
    ]
    shifted = _offset_pattern_definition(rows, dx=89.3, dy=-56.0)
    assert shifted[0] == (45.0, (92.45, -53.3), (-4.499999978306722, 4.499999978306722), [1.272792, -5.091169])
    assert shifted[1] == (0.0, (93.35, -55.1), (4.5, 4.5), [0.9, -8.1])


def test_protocol_qc_scale_labels_use_bylayer_dark_green():
    pack = build_protocol_documents(
        tests=[_test_data()],
        ige_registry={"ИГЭ-1": {"soil_type": "глина", "notes": "Глина"}},
    )
    result = build_protocol_scene(doc=pack.documents[0], calibration=_calibration(), block_name="PROTO_QC_TEXT")
    qc_tick_labels = [
        txt
        for txt in result.scene.block.texts
        if txt.layer == "ZE_PROTO_QC" and txt.text.isdigit()
    ]
    assert qc_tick_labels
    assert all(txt.color_aci is None for txt in qc_tick_labels)
    qc_layer = next(layer for layer in result.scene.layers if layer.name == "ZE_PROTO_QC")
    assert qc_layer.rgb == (22, 163, 74)


def test_protocol_curves_do_not_force_030mm_lineweight():
    pack = build_protocol_documents(tests=[_test_data()], ige_registry={})
    result = build_protocol_scene(doc=pack.documents[0], calibration=_calibration(), block_name="PROTO_CURVES")
    qc_layer = next(layer for layer in result.scene.layers if layer.name == "ZE_PROTO_QC")
    fs_layer = next(layer for layer in result.scene.layers if layer.name == "ZE_PROTO_FS")
    assert qc_layer.lineweight is None
    assert fs_layer.lineweight is None


def test_protocol_curve_entities_keep_030mm_lineweight_only_for_graph_curves():
    assert _entity_polyline_lineweight("ZE_PROTO_QC") == 30
    assert _entity_polyline_lineweight("ZE_PROTO_FS") == 30
    assert _entity_polyline_lineweight("ZE_PROTO_GRID") is None
    assert _entity_polyline_lineweight("ZE_PROTO_CUT") is None


def test_protocol_dxf_export_requests_exploded_entities():
    captured = {}

    def _fake_write(scenes, out_path, **kwargs):
        captured["scenes"] = scenes
        captured["out_path"] = out_path
        captured["kwargs"] = kwargs
        return out_path

    original = protocol_exporters.write_cad_scenes_to_dxf
    protocol_exporters.write_cad_scenes_to_dxf = _fake_write
    try:
        scene = build_protocol_scene(
            doc=build_protocol_documents(tests=[_test_data()], ige_registry={}).documents[0],
            calibration=_calibration(),
            block_name="PROTO_EXPORT",
        ).scene
        out = protocol_exporters.export_protocols_to_dxf(
            scenes=[scene],
            heights_mm=[100.0],
            out_path="dummy.dxf",
        )
    finally:
        protocol_exporters.write_cad_scenes_to_dxf = original

    assert out == "dummy.dxf"
    assert captured["kwargs"]["explode_blocks"] is True
    assert captured["kwargs"]["x_step_mm"] == 0.0
    assert captured["kwargs"]["require_ezdxf"] is True


def test_protocol_pesok_pattern_preserves_pat_dot_segments():
    pack = build_protocol_documents(
        tests=[_test_data()],
        ige_registry={"ИГЭ-1": {"soil_type": "песок", "notes": "Песок"}},
    )
    result = build_protocol_scene(doc=pack.documents[0], calibration=_calibration(), block_name="PROTO_PESOK")
    patterned = _patterned_section_hatches(result)
    assert patterned
    assert _rounded_pattern_rows(patterned[0].pattern_definition) == _rounded_pattern_rows(_pat_definition_as_dxf_rows("песок"))
    first_row = patterned[0].pattern_definition[0]
    _angle0, _base0, offset0, dash0 = first_row
    assert offset0 == (0.0, -6.0)
    assert dash0 == [0.0, -3.0]


def test_protocol_diagonal_offsets_match_autocad_reference_examples():
    graviy = _pat_definition_as_dxf_rows(next(soil for soil, pat_file in SOIL_TYPE_TO_PAT_FILE.items() if pat_file == "graviy.pat"))
    assert round(graviy[0][2][0], 6) == -4.5
    assert round(graviy[0][2][1], 6) == 4.5
    assert round(graviy[2][2][0], 6) == -4.5
    assert round(graviy[2][2][1], 6) == -4.5

    argillit = _pat_definition_as_dxf_rows(next(soil for soil, pat_file in SOIL_TYPE_TO_PAT_FILE.items() if pat_file == "Argillit.pat"))
    assert round(argillit[1][2][0], 6) == -5.999942
    assert round(argillit[1][2][1], 6) == -5.999942

    peschanik = _pat_definition_as_dxf_rows(next(soil for soil, pat_file in SOIL_TYPE_TO_PAT_FILE.items() if pat_file == "Peschanik.pat"))
    assert round(peschanik[2][2][0], 6) == -0.000002
    assert round(peschanik[2][2][1], 6) == 11.999996
    assert round(peschanik[3][2][0], 6) == -10.392302
    assert round(peschanik[3][2][1], 6) == 5.999996
