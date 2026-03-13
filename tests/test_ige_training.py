from src.zondeditor.calculations.ige_training import diff_layer_models, update_profile_from_examples


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
