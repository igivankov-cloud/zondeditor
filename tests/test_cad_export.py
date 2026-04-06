from pathlib import Path

import builtins
import pytest

from src.zondeditor.domain.models import TestData as ZeTestData
from src.zondeditor.export.cad.builder import MANDATORY_LAYERS, build_cpt_cad_scene
from src.zondeditor.export.cad.dwg_bridge import convert_dxf_to_dwg
from src.zondeditor.export.cad.schema import ExportCadOptions
from src.zondeditor.processing.calibration import K2_DEFAULT


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
    assert any(p.layer == "ZE_CPT_BASEPOINT" and p.position == (0.0, 0.0, 0.0) for p in result.scene.block.points)


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
    assert "ZE_CPT_BASEPOINT" in doc.layers
    msp = doc.modelspace()
    inserts = [e for e in msp if e.dxftype() == "INSERT"]
    assert inserts


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
    )
    out = tmp_path / "graph_fallback.dxf"
    write_cad_scene_to_dxf(result.scene, out)

    text = out.read_text(encoding="utf-8")
    assert "SECTION" in text
    assert "ZE_CPT_QC_CURVE" in text
    assert "INSERT" in text
