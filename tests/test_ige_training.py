from src.zondeditor.calculations.ige_training import (
    diff_layer_models,
    evaluate_training_case_eligibility,
    filter_valid_training_examples,
    update_profile_from_examples,
)


def test_diff_detects_boundaries_merge_split_and_type_change():
    auto = [
        {"top_m": 0.0, "bot_m": 1.0, "soil_type": "супесь"},
        {"top_m": 1.0, "bot_m": 2.0, "soil_type": "супесь"},
        {"top_m": 2.0, "bot_m": 3.0, "soil_type": "песок"},
    ]
    manual = [
        {"top_m": 0.0, "bot_m": 2.2, "soil_type": "супесь"},
        {"top_m": 2.2, "bot_m": 3.0, "soil_type": "суглинок"},
    ]
    d = diff_layer_models(auto, manual)
    kinds = {x["kind"] for x in d["actions"]}
    assert "interval_merge" in kinds
    assert any(k in kinds for k in {"boundary_shift", "boundary_removed"})
    assert "soil_type_changed" in kinds


def test_profile_update_avoids_overfit_on_single_example():
    base = {"min_layer_thickness_m": 0.8, "boundary_q_jump": 2.0}
    ex = [{"diff": {"auto_layers_count": 4, "manual_layers_count": 2, "actions": [{"kind": "interval_merge", "count": 2}]}}]
    r = update_profile_from_examples(base_profile=base, examples=ex)
    assert r.updated_profile["min_layer_thickness_m"] == 0.8
    assert r.updated_profile["training_confidence"] == "low"


def test_profile_update_changes_thresholds_with_multiple_examples():
    base = {"min_layer_thickness_m": 0.8, "boundary_q_jump": 2.0, "smoothing_window": 5, "merge_same_soil": False}
    examples = [
        {"diff": {"auto_layers_count": 5, "manual_layers_count": 3, "actions": [{"kind": "interval_merge", "count": 2}, {"kind": "boundary_shift", "delta_m": 0.4}]}},
        {"diff": {"auto_layers_count": 6, "manual_layers_count": 4, "actions": [{"kind": "interval_merge", "count": 2}, {"kind": "interval_split", "count": 1}, {"kind": "boundary_shift", "delta_m": 0.3}]}} ,
    ]
    r = update_profile_from_examples(base_profile=base, examples=examples)
    p = r.updated_profile
    assert p["min_layer_thickness_m"] > 0.8
    assert p["merge_same_soil"] is True
    assert p["boundary_q_jump"] < 2.0
    assert p["smoothing_window"] > 5


def test_training_case_not_eligible_when_not_completed_or_not_approved():
    r = evaluate_training_case_eligibility(
        interpretation_status="draft",
        approved_for_training=False,
        has_prebuild_snapshot=True,
        test_meta=[{"test_id": "t1", "is_real_field_data": True, "export_on": True}],
    )
    assert r.eligible is False
    assert any("не завершена" in x for x in r.reasons)
    assert any("Использовать для обучения" in x for x in r.reasons)


def test_training_case_not_eligible_for_synthetic_invalid_or_excluded_data():
    r = evaluate_training_case_eligibility(
        interpretation_status="completed",
        approved_for_training=True,
        has_prebuild_snapshot=True,
        test_meta=[
            {
                "test_id": "t1",
                "is_real_field_data": False,
                "is_synthetic": True,
                "is_copied": True,
                "is_invalid": True,
                "is_excluded": True,
                "export_on": False,
                "has_problem_points": True,
            }
        ],
    )
    assert r.eligible is False
    assert len(r.reasons) >= 5


def test_filter_valid_training_examples_uses_only_completed_approved_active_and_valid():
    examples = [
        {"example_id": "ok", "interpretation_status": "completed", "approved_for_training": True, "is_active": True, "quality": {"is_valid_for_training": True, "rejection_reasons": []}},
        {"example_id": "draft", "interpretation_status": "draft", "approved_for_training": True, "is_active": True, "quality": {"is_valid_for_training": True, "rejection_reasons": []}},
        {"example_id": "noapproved", "interpretation_status": "completed", "approved_for_training": False, "is_active": True, "quality": {"is_valid_for_training": True, "rejection_reasons": []}},
        {"example_id": "bad", "interpretation_status": "completed", "approved_for_training": True, "is_active": True, "quality": {"is_valid_for_training": False, "rejection_reasons": ["invalid_data_flags"]}},
        {"example_id": "old", "interpretation_status": "completed", "approved_for_training": True, "is_active": False, "quality": {"is_valid_for_training": True, "rejection_reasons": []}},
    ]
    pack = filter_valid_training_examples(examples)
    assert pack["valid"] == 1
    assert pack["rejected"] == 4
    assert pack["valid_examples"][0]["example_id"] == "ok"
    assert pack["reason_counts"]["inactive_example_version"] == 1
