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


def _samples_from_fixture(name: str, **opts):
    f = _load_fixture(name)
    snap = f["snapshot"]
    tests = _tests_from_snapshot(snap)
    return build_ige_samples(
        tests=tests,
        ige_registry=dict(snap["ige_registry"]),
        profile_id="DEFAULT_CURRENT",
        allow_fill_by_material=bool(opts.get("allow_fill_by_material", False)),
        use_legacy_sandy_loam_sp446=bool(opts.get("use_legacy_sandy_loam_sp446", False)),
        allow_normative_lt6=bool(opts.get("allow_normative_lt6", False)),
    )


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



def test_test_1_2_3_are_not_blocked_by_n_lt_6():
    s1 = _samples_from_fixture("test_1_basic_stable.json")
    assert all(x.sounding_count >= 6 for x in s1)
    assert all(x.status != "N_LT_6_BLOCKED" for x in s1)

    s2 = _samples_from_fixture("test_2_sandy_loam_warning.json")
    assert all(x.sounding_count >= 6 for x in s2)
    assert all(x.status != "N_LT_6_BLOCKED" for x in s2)

    s3 = _samples_from_fixture("test_3_fill_preliminary.json")
    assert all(x.sounding_count >= 6 for x in s3)
    assert all(x.status != "N_LT_6_BLOCKED" for x in s3)



def test_test_2_checks_sandy_loam_logic_without_n_lt_6_noise():
    blocked = _samples_from_fixture("test_2_sandy_loam_warning.json", use_legacy_sandy_loam_sp446=False)
    sandy = [x for x in blocked if x.ige_id == "ИГЭ-1"][0]
    assert sandy.status == "NOT_APPLICABLE"
    assert sandy.sounding_count >= 6

    allowed = _samples_from_fixture("test_2_sandy_loam_warning.json", use_legacy_sandy_loam_sp446=True)
    sandy_allowed = [x for x in allowed if x.ige_id == "ИГЭ-1"][0]
    assert sandy_allowed.status == "CALCULATED"
    assert any("старой редакции" in w.lower() for w in sandy_allowed.warnings)
    assert sandy_allowed.status != "N_LT_6_BLOCKED"



def test_test_3_checks_fill_preliminary_without_n_lt_6_noise():
    blocked = _samples_from_fixture("test_3_fill_preliminary.json", allow_fill_by_material=False)
    fill_blocked = [x for x in blocked if x.ige_id == "ИГЭ-1"][0]
    assert fill_blocked.status in {"LAB_ONLY", "NOT_APPLICABLE"}
    assert fill_blocked.sounding_count >= 6

    allowed = _samples_from_fixture("test_3_fill_preliminary.json", allow_fill_by_material=True)
    fill_allowed = [x for x in allowed if x.ige_id == "ИГЭ-1"][0]
    assert fill_allowed.status == "PRELIMINARY"
    assert fill_allowed.status != "N_LT_6_BLOCKED"



def test_test_4_is_explicit_n_lt_6_case_by_soundings_count():
    blocked = _samples_from_fixture("test_4_n_lt_6.json", allow_normative_lt6=False)
    s_b = blocked[0]
    assert s_b.sounding_count < 6
    assert s_b.n_lt_6_triggered is True
    assert s_b.n_lt_6_blocked is True
    assert s_b.status == "N_LT_6_BLOCKED"

    allowed = _samples_from_fixture("test_4_n_lt_6.json", allow_normative_lt6=True)
    s_a = allowed[0]
    assert s_a.sounding_count < 6
    assert s_a.n_lt_6_triggered is True
    assert s_a.n_lt_6_overridden is True
    assert s_a.status == "CALCULATED"
    assert any("число опытов" in w.lower() for w in s_a.warnings)



def test_debug_protocol_text_contains_n_and_n_points_labels():
    samples = _samples_from_fixture("test_4_n_lt_6.json", allow_normative_lt6=False)
    text = build_debug_protocol_text(
        project_name="Тест 4",
        profile_id="DEFAULT_CURRENT",
        samples=samples,
        calc_options={"allow_normative_lt6": False},
    )
    assert "Число опытов (N)" in text
    assert "Число точек выборки" in text
    assert "Правило N < 6 сработало" in text
    assert "Расчёт заблокирован по N < 6" in text
    assert "Rf_avg" in text
    assert "Комментарий по Rf" in text


def test_debug_protocol_contains_training_block():
    samples = _samples_from_fixture("test_1_basic_stable.json")
    text = build_debug_protocol_text(
        project_name="Тест training",
        profile_id="DEFAULT_CURRENT",
        samples=samples,
        calc_options={
            "interpretation_status": "completed",
            "approved_for_training": True,
            "training_info": {
                "method": "Пользовательский",
                "region": "ХМАО",
                "current_context_hash": "ctx1",
                "prebuild_context_hash": "ctx0",
                "context_matches": False,
                "training_eligible": False,
                "training_block_reason": "context_changed_after_prebuild",
                "used_trained_profile": True,
                "profile_state": "medium",
                "examples_count": 3,
                "profile_source": "обученный",
                "saved_training_example": True,
                "case_eligibility": {"eligible": False, "reasons": ["test reason"]},
                "examples_filter": {"total": 5, "valid": 2, "rejected": 3, "reason_counts": {"invalid_data_flags": 2}},
            }
        },
    )
    assert "Блок адаптации/обучения" in text
    assert "Метод интерпретации: Пользовательский" in text
    assert "Примеров у профиля: 3" in text
    assert "Статус интерпретации: completed" in text
    assert "Допуск в обучение: да" in text
    assert "Регион интерпретации: ХМАО" in text
    assert "Контекст совпадает с prebuild: нет" in text
    assert "Причина блокировки training: context_changed_after_prebuild" in text
    assert "Текущий кейс пригоден для обучения: нет" in text
    assert "Примеров валидных: 2" in text


def test_excluded_disabled_or_invalid_soundings_not_used_in_samples():
    f = _load_fixture("test_1_basic_stable.json")
    snap = f["snapshot"]
    tests = _tests_from_snapshot(snap)
    tests[0].export_on = False
    setattr(tests[1], "invalid", True)

    samples = build_ige_samples(
        tests=tests,
        ige_registry=dict(snap["ige_registry"]),
        profile_id="DEFAULT_CURRENT",
        allow_fill_by_material=False,
        use_legacy_sandy_loam_sp446=False,
        allow_normative_lt6=True,
    )

    assert samples
    for smp in samples:
        assert all(sid not in {"test_1", "test_2"} for sid in (smp.used_sounding_ids or []))
        ex = list(getattr(smp, "excluded_soundings", []) or [])
        ids = {x.get("sounding_id") for x in ex}
        assert {"test_1", "test_2"}.issubset(ids)
