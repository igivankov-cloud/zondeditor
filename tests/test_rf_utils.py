from src.zondeditor.calculations.rf_utils import calc_rf_pct, robust_rf_scale_max


def test_calc_rf_pct_basic_formula():
    # qc=10 MPa => 10000 kPa; fs=50 kPa => 0.5%
    rf = calc_rf_pct(50.0, 10.0)
    assert rf is not None
    assert abs(rf - 0.5) < 1e-9


def test_calc_rf_pct_handles_zero_or_invalid():
    assert calc_rf_pct(10.0, 0.0) is None
    assert calc_rf_pct(10.0, None) is None
    assert calc_rf_pct(None, 10.0) is None
    assert calc_rf_pct(-1.0, 10.0) is None


def test_robust_rf_scale_ignores_single_outlier():
    values = [0.7, 0.9, 1.1, 1.4, 1.8, 2.1, 232.2]
    vmax = robust_rf_scale_max(values, default_max=10.0, percentile=0.95, cap_max=15.0)
    assert 5.0 <= vmax <= 15.0
