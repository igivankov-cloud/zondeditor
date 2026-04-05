from src.zondeditor.processing.interpolation_precision import (
    infer_series_precision,
    normalize_interpolated_value,
)


def test_infer_precision_prefers_local_neighbors():
    assert infer_series_precision([2.1, 2.2], [1, 2, 3], field_name="qc") == 1


def test_normalize_integer_neighbors_to_integer():
    out = normalize_interpolated_value(
        27.6225,
        local_samples=[27, 28],
        series_samples=[25, 26, 27, 28],
        field_name="qc",
    )
    assert out == 28.0


def test_normalize_hundredths_neighbors():
    out = normalize_interpolated_value(
        0.53749,
        local_samples=[0.52, 0.56],
        series_samples=[0.31, 0.42, 0.68],
        field_name="qc",
    )
    assert out == 0.54


def test_normalize_tenths_neighbors():
    out = normalize_interpolated_value(
        3.149,
        local_samples=[3.1, 3.3],
        series_samples=[2.9, 3.0, 3.4],
        field_name="qc",
    )
    assert out == 3.1


def test_fs_field_fallback_is_integer():
    out = normalize_interpolated_value(
        5.27885,
        local_samples=[],
        series_samples=[],
        field_name="fs",
    )
    assert out == 5.0


def test_fs_series_integer_majority_forces_integer_precision():
    out = normalize_interpolated_value(
        27.6,
        local_samples=[],
        series_samples=[25, 27, 28, 31, 30.5],
        field_name="fs",
    )
    assert out == 28.0


def test_qc_keeps_fractional_precision_when_series_fractional():
    out = normalize_interpolated_value(
        3.149,
        local_samples=[],
        series_samples=[2.7, 2.8, 3.1, 3.4],
        field_name="qc",
    )
    assert out == 3.1
