from src.zondeditor.processing.calibration import (
    K2_DEFAULT,
    Calibration,
    calc_qc_fs,
    calc_qc_fs_from_del,
    calibration_from_common_params,
)


def test_calibration_from_common_params_uses_defaults_and_bounds():
    cal = calibration_from_common_params(
        {
            "controller_scale_div": "0",
            "cone_kn": "",
            "sleeve_kn": "-1",
            "cone_area_cm2": "0",
            "sleeve_area_cm2": "",
        },
        geo_kind="K2",
    )
    assert cal.scale_div == K2_DEFAULT.scale_div
    assert cal.fcone_kn == K2_DEFAULT.fcone_kn
    assert cal.fsleeve_kn == K2_DEFAULT.fsleeve_kn
    assert cal.cone_area_cm2 == K2_DEFAULT.cone_area_cm2
    assert cal.sleeve_area_cm2 == K2_DEFAULT.sleeve_area_cm2


def test_calc_qc_fs_supports_custom_areas_via_calibration():
    cal = Calibration(scale_div=250, fcone_kn=30.0, fsleeve_kn=10.0, cone_area_cm2=15.0, sleeve_area_cm2=400.0)
    qc_mpa, fs_kpa = calc_qc_fs(250, 250, geo_kind="K2", cal=cal)
    assert round(qc_mpa, 3) == 20.0
    assert round(fs_kpa, 3) == 250.0


def test_calc_qc_fs_from_del_matches_reference_formula():
    qc_mpa, fs_kpa = calc_qc_fs_from_del(
        125,
        200,
        scale_div=250,
        fcone_kn=30.0,
        fsleeve_kn=10.0,
        cone_area_cm2=10.0,
        sleeve_area_cm2=350.0,
    )
    assert round(qc_mpa, 6) == round((125 / 250) * 30.0 * (10.0 / 10.0), 6)
    assert round(fs_kpa, 6) == round((200 / 250) * 10.0 * (10000.0 / 350.0), 6)
