from src.zondeditor.domain.cpt_params_ru import CptCalcSettings, METHOD_SP446, calculate_ige_cpt_results, qc_stats


class DummyLayer:
    def __init__(self, top_m, bot_m, ige_id):
        self.top_m = top_m
        self.bot_m = bot_m
        self.ige_id = ige_id


class DummyTest:
    def __init__(self):
        self.export_on = True
        self.depth = ["0.0", "0.1", "0.2", "0.3"]
        self.qc = ["1.0", "2.0", "0", "3.0"]
        self.layers = [DummyLayer(0.0, 0.3, "ИГЭ-1")]


def test_qc_stats_excludes_zero():
    stats = qc_stats([1.0, 2.0, 0.0, 3.0])
    assert stats is not None
    assert stats.n == 3
    assert round(stats.qc_mean, 3) == 2.0


def test_lookup_pipeline_returns_phi_and_e():
    tests = [DummyTest()]
    registry = {"ИГЭ-1": {"soil_type": "песок"}}
    result = calculate_ige_cpt_results(tests=tests, ige_registry=registry, settings=CptCalcSettings(method=METHOD_SP446, alluvial_sands=False))
    one = result.get("ИГЭ-1")
    assert one is not None
    assert one["n"] == 3
    assert one["phi_norm"] > 0
    assert one["E_norm"] > 0
