from pathlib import Path

from src.zondeditor.project.model import Project, ProjectSettings, SourceInfo
from src.zondeditor.project.store import load_project, save_project


def test_project_store_roundtrip_preserves_state_and_settings(tmp_path: Path):
    p = Project(
        object_name="OBJ-1",
        source=SourceInfo(kind="GEO", filename="sample.GEO", ext="geo"),
        settings=ProjectSettings(
            controller_scale_div="1000",
            cone_kn="50",
            sleeve_kn="10",
            cone_area_cm2="10",
            sleeve_area_cm2="350",
            step_m=0.05,
            extras={"cpt_calc_settings": {"method": "SP446"}},
        ),
        state={
            "geo_kind": "K4",
            "common_params": {
                "controller_scale_div": "1000",
                "cone_kn": "50",
                "sleeve_kn": "10",
                "cone_area_cm2": "10",
                "sleeve_area_cm2": "350",
            },
            "step_m": 0.05,
            "depth_start": 0.0,
            "show_graphs": False,
            "interpretation_status": "completed",
            "approved_for_training": True,
            "interpretation_revision": 3,
            "training_example_version": 2,
            "training_snapshot_hash": "abc123",
        },
        ops=[{"op": "noop"}],
    )

    out = tmp_path / "project.zproj"
    save_project(out, project=p, source_bytes=b"abc")
    loaded, source_bytes = load_project(out)

    assert loaded.object_name == "OBJ-1"
    assert loaded.source.ext == "geo"
    assert loaded.settings.controller_scale_div == "1000"
    assert loaded.settings.step_m == 0.05
    assert loaded.state["geo_kind"] == "K4"
    assert loaded.state["common_params"]["cone_kn"] == "50"
    assert loaded.state["step_m"] == 0.05
    assert loaded.state["interpretation_status"] == "completed"
    assert loaded.state["approved_for_training"] is True
    assert loaded.state["interpretation_revision"] == 3
    assert loaded.state["training_example_version"] == 2
    assert source_bytes == b"abc"
