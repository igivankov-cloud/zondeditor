from src.zondeditor.domain.cpt_params_ru import CptCalcSettings, METHOD_SP446, calculate_ige_cpt_results, qc_stats


class DummyLayer:
    def __init__(self, top_m, bot_m, ige_id):
        self.top_m = top_m
        self.bot_m = bot_m
        self.ige_id = ige_id


class DummyTest:
    def __init__(self):
        self.export_on = True
        self.depth = ["0.0", "0.1", "0.2", "0.3", "5.1", "5.2"]
        self.qc = ["1.0", "2.0", "0", "3.0", "6.0", "6.0"]
        self.layers = [DummyLayer(0.0, 0.3, "ИГЭ-1"), DummyLayer(5.0, 5.3, "ИГЭ-2")]


def test_qc_stats_excludes_zero():
    stats = qc_stats([1.0, 2.0, 0.0, 3.0])
    assert stats is not None
    assert stats.n == 3
    assert round(stats.qc_mean, 3) == 2.0


def test_lookup_pipeline_returns_phi_and_e_sp446_with_branches():
    tests = [DummyTest()]
    registry = {
        "ИГЭ-1": {"soil_type": "песок", "sand_class": "пылеватый", "alluvial": False, "saturated": None},
        "ИГЭ-2": {"soil_type": "песок", "sand_class": "мелкий", "alluvial": True, "saturated": None},
    }
    result = calculate_ige_cpt_results(tests=tests, ige_registry=registry, settings=CptCalcSettings(method=METHOD_SP446, groundwater_level=0.2))
    one = result.get("ИГЭ-1")
    two = result.get("ИГЭ-2")
    assert one is not None and two is not None
    assert one["status"] == "ok"
    assert one["saturated"] is False
    assert two["saturated"] is True
    assert two["lookup_branch"].find("глубина: 5м+") >= 0


def test_supes_returns_no_norm_status():
    tests = [DummyTest()]
    registry = {"ИГЭ-1": {"soil_type": "супесь"}}
    result = calculate_ige_cpt_results(tests=tests, ige_registry=registry, settings=CptCalcSettings(method=METHOD_SP446))
    one = result.get("ИГЭ-1")
    assert one is not None
    assert one["status"] == "no_norm"
    assert "требуется другой источник" in one["reason"]
