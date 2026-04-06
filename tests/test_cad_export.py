from pathlib import Path

import builtins
import pytest

from src.zondeditor.domain.models import TestData as ZeTestData
from src.zondeditor.export.cad.builder import MANDATORY_LAYERS, build_cpt_cad_scene
from src.zondeditor.export.cad.dwg_bridge import convert_dxf_to_dwg
from src.zondeditor.export.cad.schema import ExportCadOptions
from src.zondeditor.processing.calibration import K2_DEFAULT, K4_DEFAULT


def _sample_test_data() -> ZeTestData:
    return ZeTestData(
        tid=1,
        dt="01.01.2026",
        depth=["0.0", "0.5", "1.0", "1.5"],
        qc=["10", "20", "30", "40"],
        fs=["5", "10", "15", "20"],
    )


def test_builder_contains_all_mandatory_layers_and_basepoint():
    result = build_cpt_cad_scene(
        test=_sample_test_data(),
        calibration=K2_DEFAULT,
        options=ExportCadOptions(vertical_scale=100),
        block_name="ZE_TEST",
    )

    names = {layer.name for layer in result.scene.layers}
    assert {layer.name for layer in MANDATORY_LAYERS}.issubset(names)
    assert names == {
        "ZE_CPT_QC_CURVE",
        "ZE_CPT_FS_CURVE",
        "ZE_CPT_QC_SCALE",
        "ZE_CPT_FS_SCALE",
        "ZE_CPT_TITLE",
    }
    assert any(p.layer == "ZE_CPT_TITLE" and p.position == (0.0, 0.0, 0.0) for p in result.scene.block.points)
    assert "ZE_CPT_FRAME" not in names and "ZE_CPT_DEPTH_AXIS" not in names and "ZE_CPT_GRID" not in names


def test_builder_respects_vertical_scale_formula():
    result_50 = build_cpt_cad_scene(
        test=_sample_test_data(),
        calibration=K2_DEFAULT,
        options=ExportCadOptions(vertical_scale=50),
        block_name="ZE_TEST_50",
    )
    result_200 = build_cpt_cad_scene(
        test=_sample_test_data(),
        calibration=K2_DEFAULT,
        options=ExportCadOptions(vertical_scale=200),
        block_name="ZE_TEST_200",
    )

    y50 = result_50.qc_series.points_mm[-1][1]
    y200 = result_200.qc_series.points_mm[-1][1]
    assert y50 == pytest.approx(-30.0)  # -1.5 * 1000 / 50
    assert y200 == pytest.approx(-7.5)  # -1.5 * 1000 / 200


def test_dwg_bridge_does_not_fail_when_converter_missing(tmp_path: Path):
    dxf_path = tmp_path / "graph.dxf"
    dxf_path.write_text("0\nEOF\n", encoding="utf-8")
    result = convert_dxf_to_dwg(dxf_path=dxf_path, dwg_path=tmp_path / "graph.dwg", converter_path="/missing/oda")

    assert result.requested is True
    assert result.success is False
    assert "not found" in result.message.lower()


def test_dxf_writer_outputs_layers_and_block_insert(tmp_path: Path):
    ezdxf = pytest.importorskip("ezdxf")
    from src.zondeditor.export.cad.dxf_writer import write_cad_scene_to_dxf

    result = build_cpt_cad_scene(
        test=_sample_test_data(),
        calibration=K2_DEFAULT,
        options=ExportCadOptions(vertical_scale=100),
        block_name="ZE_TEST_DXF",
    )
    out = tmp_path / "graph.dxf"
    write_cad_scene_to_dxf(result.scene, out)

    assert out.exists()
    doc = ezdxf.readfile(out)
    assert "ZE_CPT_QC_CURVE" in doc.layers
    assert "ZE_CPT_TITLE" in doc.layers
    msp = doc.modelspace()
    inserts = [e for e in msp if e.dxftype() == "INSERT"]
    assert inserts


def test_builder_has_fixed_k2_k4_scales_and_no_minor_ticks():
    k2 = build_cpt_cad_scene(
        test=_sample_test_data(),
        calibration=K2_DEFAULT,
        options=ExportCadOptions(vertical_scale=100),
        block_name="ZE_K2",
    )
    assert k2.qc_scale.max_value == 30.0
    assert k2.fs_scale.max_value == 300.0
    assert k2.qc_scale.major_tick_step == 5.0
    assert k2.fs_scale.major_tick_step == 50.0
    assert k2.qc_scale.minor_tick_step == 0.0
    assert k2.fs_scale.minor_tick_step == 0.0

    k4 = build_cpt_cad_scene(
        test=_sample_test_data(),
        calibration=K4_DEFAULT,
        options=ExportCadOptions(vertical_scale=100),
        block_name="ZE_K4",
    )
    assert k4.qc_scale.max_value == 50.0
    assert k4.fs_scale.max_value == 500.0
    assert k4.qc_scale.major_tick_step == 10.0
    assert k4.fs_scale.major_tick_step == 100.0


def test_dxf_writer_supports_multiple_blocks(tmp_path: Path):
    ezdxf = pytest.importorskip("ezdxf")
    from src.zondeditor.export.cad.dxf_writer import write_cad_scenes_to_dxf

    r1 = build_cpt_cad_scene(
        test=_sample_test_data(),
        calibration=K2_DEFAULT,
        options=ExportCadOptions(vertical_scale=100),
        block_name="ZE_TEST_1",
        title_text="Опыт 1",
    )
    r2 = build_cpt_cad_scene(
        test=ZeTestData(tid=2, dt="01.01.2026", depth=["0", "1"], qc=["10", "20"], fs=["20", "30"]),
        calibration=K2_DEFAULT,
        options=ExportCadOptions(vertical_scale=100),
        block_name="ZE_TEST_2",
        title_text="Опыт 2",
    )
    out = tmp_path / "multi.dxf"
    write_cad_scenes_to_dxf([r1.scene, r2.scene], out, x_step_mm=130.0)
    doc = ezdxf.readfile(out)
    inserts = [e for e in doc.modelspace() if e.dxftype() == "INSERT"]
    assert len(inserts) == 2


def test_dxf_writer_fallback_without_ezdxf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from src.zondeditor.export.cad.dxf_writer import write_cad_scene_to_dxf

    orig_import = builtins.__import__

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "ezdxf":
            raise ModuleNotFoundError("ezdxf")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _import)

    result = build_cpt_cad_scene(
        test=_sample_test_data(),
        calibration=K2_DEFAULT,
        options=ExportCadOptions(vertical_scale=100),
        block_name="ZE_TEST_FALLBACK",
        title_text="Опыт 6",
    )
    out = tmp_path / "graph_fallback.dxf"
    write_cad_scene_to_dxf(result.scene, out)

    text = out.read_text(encoding="utf-8")
    assert "SECTION" in text
    assert "ZE_CPT_QC_CURVE" in text
    assert "INSERT" in text
    assert "\\U+041E" in text  # Unicode escaped Cyrillic
