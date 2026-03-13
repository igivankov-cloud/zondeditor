from src.zondeditor.calculations.ige_prebuild import build_preliminary_layers, MIN_AUTO_LAYER_THICKNESS_M, MAX_AUTO_LAYERS_PER_TEST


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
