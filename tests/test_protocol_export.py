from src.zondeditor.domain.models import TestData
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
