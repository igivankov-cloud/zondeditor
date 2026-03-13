import json
from pathlib import Path

from src.zondeditor.calculations.protocol_builder import build_debug_protocol_text
from src.zondeditor.calculations.sample_builder import build_ige_samples
from src.zondeditor.domain.layers import layer_from_dict
from src.zondeditor.domain.models import TestData


def _load_fixture(name: str) -> dict:
    p = Path("fixtures/testdata") / name
    return json.loads(p.read_text(encoding="utf-8"))


def _tests_from_snapshot(snapshot: dict) -> list[TestData]:
    out = []
    for t in snapshot.get("tests", []):
        layers = [layer_from_dict(x) for x in (t.get("layers") or [])]
        td = TestData(
            tid=int(t["tid"]),
            dt=str(t.get("dt") or ""),
            depth=list(t.get("depth") or []),
            qc=list(t.get("qc") or []),
            fs=list(t.get("fs") or []),
            incl=t.get("incl"),
            marker=str(t.get("marker") or ""),
            header_pos=str(t.get("header_pos") or ""),
            orig_id=t.get("orig_id"),
            layers=layers,
        )
        td.export_on = bool(t.get("export_on", True))
        out.append(td)
    return out


def test_debug_fixtures_cover_required_cases():
    names = [
        "test_1_basic_stable.json",
        "test_2_sandy_loam_warning.json",
        "test_3_fill_preliminary.json",
        "test_4_n_lt_6.json",
    ]
    for n in names:
        f = _load_fixture(n)
        assert f.get("expected_notes")
        assert f.get("snapshot", {}).get("tests")
        assert f.get("snapshot", {}).get("ige_registry")


def test_debug_protocol_text_contains_sections_and_paths():
    f = _load_fixture("test_2_sandy_loam_warning.json")
    snap = f["snapshot"]
    tests = _tests_from_snapshot(snap)
    samples = build_ige_samples(
        tests=tests,
        ige_registry=dict(snap["ige_registry"]),
        profile_id="DEFAULT_CURRENT",
        allow_fill_by_material=False,
        use_legacy_sandy_loam_sp446=True,
        allow_normative_lt6=False,
    )

    text = build_debug_protocol_text(
        project_name=f.get("title", ""),
        profile_id="DEFAULT_CURRENT",
        samples=samples,
        calc_options={"use_legacy_sandy_loam_sp446": True},
    )
    assert "A. Паспорт расчёта" in text
    assert "Б. Выборка" in text
    assert "В. Статистика" in text
    assert "Г. Метод" in text
    assert "Д. Расчёт" in text
    assert "Е. Результат" in text
    assert "супесь по старой редакции" in text
