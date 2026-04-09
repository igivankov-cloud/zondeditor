from src.zondeditor.domain.models import TestData
from src.zondeditor.domain.experience_column import ColumnInterval, ExperienceColumn
from src.zondeditor.domain.hatching.registry import load_registered_hatch
from src.zondeditor.processing.calibration import Calibration
from src.zondeditor.export.protocol import build_protocol_documents, build_protocol_scene


def _test_data(tid: int = 1) -> TestData:
    return TestData(
        tid=tid,
        dt="09.07.25",
        depth=["0", "0.5", "1.0", "1.5", "2.0"],
        qc=["10", "20", "30", "40", "50"],
        fs=["5", "10", "15", "20", "25"],
    )


def test_protocol_scene_builds_with_dynamic_depth():
    pack = build_protocol_documents(tests=[_test_data()], ige_registry={"ИГЭ-1": {"notes": "Глина"}})
    cal = Calibration(scale_div=250, fcone_kn=30.0, fsleeve_kn=10.0, cone_area_cm2=10.0, sleeve_area_cm2=350.0)
    result = build_protocol_scene(doc=pack.documents[0], calibration=cal, block_name="PROTO1")
    assert result.height_mm > 0
    assert result.scene.block.name == "PROTO1"
    assert len(result.scene.block.polylines) >= 1


def test_protocol_build_uses_selected_order():
    t1 = _test_data(2)
    t2 = _test_data(5)
    pack = build_protocol_documents(tests=[t1, t2], ige_registry={})
    assert [d.test.tid for d in pack.documents] == [2, 5]


def test_protocol_scene_uses_registered_hatch_patterns_for_section_layers():
    pack = build_protocol_documents(
        tests=[_test_data()],
        ige_registry={"ИГЭ-1": {"soil_type": "глина", "notes": "Глина"}},
    )
    cal = Calibration(scale_div=250, fcone_kn=30.0, fsleeve_kn=10.0, cone_area_cm2=10.0, sleeve_area_cm2=350.0)
    result = build_protocol_scene(doc=pack.documents[0], calibration=cal, block_name="PROTO_HATCH")
    patterned = [
        h
        for h in result.scene.block.hatches
        if h.layer == "ZE_PROTO_CUT" and bool(h.pattern_name or h.pattern_definition)
    ]
    assert patterned
    assert all(len(h.boundary) >= 4 for h in patterned)
    assert all(len(h.pattern_definition) > 0 for h in patterned)
    assert all(str(h.pattern_name or "").startswith("ZE_") for h in patterned)


def test_protocol_scene_keeps_solid_hatches_for_masks_and_ruler():
    pack = build_protocol_documents(tests=[_test_data()], ige_registry={})
    cal = Calibration(scale_div=250, fcone_kn=30.0, fsleeve_kn=10.0, cone_area_cm2=10.0, sleeve_area_cm2=350.0)
    result = build_protocol_scene(doc=pack.documents[0], calibration=cal, block_name="PROTO_SOLID")
    solid_layers = {h.layer for h in result.scene.block.hatches if h.solid and not h.pattern_definition}
    assert "ZE_PROTO_MASK" in solid_layers
    assert "ZE_PROTO_RULER" in solid_layers


def test_protocol_suglinok_pattern_step_not_scaled_twice():
    pack = build_protocol_documents(
        tests=[_test_data()],
        ige_registry={"ИГЭ-1": {"soil_type": "суглинок", "notes": "Суглинок"}},
    )
    cal = Calibration(scale_div=250, fcone_kn=30.0, fsleeve_kn=10.0, cone_area_cm2=10.0, sleeve_area_cm2=350.0)
    result = build_protocol_scene(doc=pack.documents[0], calibration=cal, block_name="PROTO_SUG")
    patterned = [h for h in result.scene.block.hatches if h.layer == "ZE_PROTO_CUT" and h.pattern_definition]
    assert patterned
    first_row = patterned[0].pattern_definition[0]
    angle_deg, _base, offset, _dash_items = first_row
    assert angle_deg == 45.0
    # Suglinok JSON keeps dy around 5.65; export should not multiply by pattern.scale (14.0).
    assert offset[1] == 5.65


def test_protocol_build_infers_soil_type_from_description_when_registry_field_missing():
    pack = build_protocol_documents(
        tests=[_test_data()],
        ige_registry={"ИГЭ-1": {"notes": "ИГЭ-1 (суглинок)"}},
    )
    assert pack.documents
    assert pack.documents[0].layers
    assert pack.documents[0].layers[0].soil_type == "суглинок"


def test_protocol_build_resolves_soil_type_by_ige_number_when_id_formats_differ():
    t = _test_data()
    t.experience_column = ExperienceColumn(
        column_depth_start=0.0,
        column_depth_end=2.0,
        intervals=[ColumnInterval(from_depth=0.0, to_depth=2.0, ige_id="ИГЭ-3", ige_name="")],
    )
    pack = build_protocol_documents(
        tests=[t],
        ige_registry={"ИГ-3": {"soil_type": "песок", "label": "ИГ-3"}},
    )
    assert pack.documents
    assert pack.documents[0].layers
    assert pack.documents[0].layers[0].soil_type == "песок"


def test_registry_supports_argilit_alias():
    assert load_registered_hatch("аргилит") is not None


def test_protocol_section_pattern_hatches_use_black_color():
    pack = build_protocol_documents(
        tests=[_test_data()],
        ige_registry={"ИГЭ-1": {"soil_type": "глина", "notes": "Глина"}},
    )
    cal = Calibration(scale_div=250, fcone_kn=30.0, fsleeve_kn=10.0, cone_area_cm2=10.0, sleeve_area_cm2=350.0)
    result = build_protocol_scene(doc=pack.documents[0], calibration=cal, block_name="PROTO_BLACK_HATCH")
    patterned = [h for h in result.scene.block.hatches if h.layer == "ZE_PROTO_CUT" and h.pattern_definition]
    assert patterned
    assert all(h.color_aci == 7 for h in patterned)


def test_protocol_pesok_pattern_avoids_zero_length_dxf_dots():
    pack = build_protocol_documents(
        tests=[_test_data()],
        ige_registry={"ИГЭ-1": {"soil_type": "песок", "notes": "Песок"}},
    )
    cal = Calibration(scale_div=250, fcone_kn=30.0, fsleeve_kn=10.0, cone_area_cm2=10.0, sleeve_area_cm2=350.0)
    result = build_protocol_scene(doc=pack.documents[0], calibration=cal, block_name="PROTO_PESOK")
    patterned = [h for h in result.scene.block.hatches if h.layer == "ZE_PROTO_CUT" and h.pattern_definition]
    assert patterned
    for _angle, _base, _offset, dash_items in patterned[0].pattern_definition:
        if dash_items:
            assert all(v != 0.0 for v in dash_items)
