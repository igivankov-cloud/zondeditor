from src.zondeditor.calculations.ige_prebuild import (
    MAX_AUTO_LAYERS_PER_TEST,
    MIN_AUTO_LAYER_THICKNESS_M,
    build_preliminary_layers,
    correlate_intervals_to_global_iges,
)


def test_prebuild_does_not_create_too_many_thin_layers():
    samples = []
    d = 0.0
    while d <= 10.0:
        # alternating spikes that previously could over-segment
        qc = 4.0 + (1.8 if int(d * 10) % 2 == 0 else -1.6)
        fs = 50.0 + (35.0 if int(d * 10) % 3 == 0 else -30.0)
        rf = 1.2 + (0.7 if int(d * 10) % 4 == 0 else -0.4)
        samples.append((d, qc, fs, rf))
        d += 0.2

    layers = build_preliminary_layers(samples)
    assert len(layers) <= MAX_AUTO_LAYERS_PER_TEST
    assert all((x.bot_m - x.top_m) >= MIN_AUTO_LAYER_THICKNESS_M for x in layers)


def test_correlate_similar_single_layer_across_tests_to_one_global_ige():
    local = {
        "t1": [{"z_from": 0.0, "z_to": 3.0, "preliminary_type": "суглинок", "qc_avg": 4.1, "rf_avg": 3.2}],
        "t2": [{"z_from": 0.2, "z_to": 3.1, "preliminary_type": "суглинок", "qc_avg": 4.0, "rf_avg": 3.0}],
        "t3": [{"z_from": 0.1, "z_to": 2.9, "preliminary_type": "суглинок", "qc_avg": 4.2, "rf_avg": 3.1}],
    }
    assigned, clusters = correlate_intervals_to_global_iges(local)
    assert len(clusters) == 1
    ids = {x["cluster_id"] for vals in assigned.values() for x in vals}
    assert len(ids) == 1


def test_correlate_two_stable_layers_to_two_global_iges_not_per_column():
    local = {
        "t1": [
            {"z_from": 0.0, "z_to": 2.0, "preliminary_type": "суглинок", "qc_avg": 3.8, "rf_avg": 3.0},
            {"z_from": 2.0, "z_to": 6.0, "preliminary_type": "песок", "qc_avg": 7.5, "rf_avg": 1.0},
        ],
        "t2": [
            {"z_from": 0.1, "z_to": 2.1, "preliminary_type": "суглинок", "qc_avg": 3.9, "rf_avg": 2.9},
            {"z_from": 2.1, "z_to": 6.1, "preliminary_type": "песок", "qc_avg": 7.2, "rf_avg": 1.1},
        ],
        "t3": [
            {"z_from": 0.0, "z_to": 1.9, "preliminary_type": "суглинок", "qc_avg": 4.0, "rf_avg": 3.2},
            {"z_from": 1.9, "z_to": 5.9, "preliminary_type": "песок", "qc_avg": 7.4, "rf_avg": 1.0},
        ],
    }
    assigned, clusters = correlate_intervals_to_global_iges(local)
    assert len(clusters) == 2
    for vals in assigned.values():
        assert len({x["cluster_id"] for x in vals}) == 2
