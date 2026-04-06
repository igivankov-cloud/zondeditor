from __future__ import annotations

from dataclasses import dataclass

from src.zondeditor.domain.models import TestData
from src.zondeditor.processing.calibration import Calibration, calc_qc_fs

from .logging import get_cad_logger
from .schema import (
    CadBlock,
    CadLayerSpec,
    CadLine,
    CadPoint,
    CadPolyline,
    CadScene,
    CurveScaleSpec,
    CurveSeries,
    DepthAxisSpec,
    ExportCadOptions,
    TextLabel,
)

_log = get_cad_logger()

MANDATORY_LAYERS: tuple[CadLayerSpec, ...] = (
    CadLayerSpec("ZE_CPT_QC_CURVE", color_aci=3, rgb=(22, 163, 74), lineweight=30),
    CadLayerSpec("ZE_CPT_FS_CURVE", color_aci=5, rgb=(37, 99, 235), lineweight=30),
    CadLayerSpec("ZE_CPT_QC_SCALE", color_aci=3, rgb=(22, 163, 74)),
    CadLayerSpec("ZE_CPT_FS_SCALE", color_aci=5, rgb=(37, 99, 235)),
    CadLayerSpec("ZE_CPT_TITLE", color_aci=7),
)


@dataclass(frozen=True)
class CadBuildResult:
    scene: CadScene
    qc_series: CurveSeries
    fs_series: CurveSeries
    qc_scale: CurveScaleSpec
    fs_scale: CurveScaleSpec
    depth_axis: DepthAxisSpec
    drawing_width_mm: float
    drawing_height_mm: float


def _parse_float(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip().replace(",", "."))
    except Exception:
        return None


def _depth_to_y_mm(depth_m: float, vertical_scale: int) -> float:
    return -depth_m * 1000.0 / float(vertical_scale)


def _value_to_x_mm(value: float, spec: CurveScaleSpec) -> float:
    span = spec.max_value - spec.min_value
    if span <= 0:
        return spec.x_origin_mm
    value_clamped = max(spec.min_value, min(spec.max_value, value))
    return spec.x_origin_mm + (value_clamped - spec.min_value) * spec.width_mm / span


def _build_scale_lines(*, spec: CurveScaleSpec, axis_y_mm: float) -> tuple[list[CadLine], list[TextLabel]]:
    lines: list[CadLine] = [
        CadLine(spec.layer_scale, (spec.x_origin_mm, axis_y_mm), (spec.x_origin_mm + spec.width_mm, axis_y_mm)),
    ]
    texts: list[TextLabel] = []

    if spec.major_tick_step <= 0:
        return lines, texts

    val = spec.min_value
    while val <= spec.max_value + 1e-9:
        x_mm = _value_to_x_mm(val, spec)
        lines.append(CadLine(spec.layer_scale, (x_mm, axis_y_mm), (x_mm, axis_y_mm - 2.2)))
        texts.append(TextLabel(spec.layer_scale, f"{int(round(val))}", x_mm, axis_y_mm - 3.8, 1.8, align="CENTER"))
        val += spec.major_tick_step

    return lines, texts


def build_cpt_cad_scene(
    *,
    test: TestData,
    calibration: Calibration,
    options: ExportCadOptions,
    block_name: str,
    qc_max_mpa: float | None = None,
    fs_max_kpa: float | None = None,
    title_text: str | None = None,
) -> CadBuildResult:
    _log.info(
        "build_cpt_cad_scene start test_id=%s vertical_scale=%s block=%s",
        int(getattr(test, "tid", 0) or 0),
        int(options.vertical_scale),
        block_name,
    )

    depth_arr = list(getattr(test, "depth", []) or [])
    qc_arr = list(getattr(test, "qc", []) or [])
    fs_arr = list(getattr(test, "fs", []) or [])
    n = max(len(depth_arr), len(qc_arr), len(fs_arr))

    samples: list[tuple[float, float, float]] = []
    for i in range(n):
        depth = _parse_float(depth_arr[i]) if i < len(depth_arr) else None
        qc_raw = _parse_float(qc_arr[i]) if i < len(qc_arr) else None
        fs_raw = _parse_float(fs_arr[i]) if i < len(fs_arr) else None
        if depth is None or (qc_raw is None and fs_raw is None):
            continue
        qc_mpa, fs_kpa = calc_qc_fs(int(round(qc_raw or 0.0)), int(round(fs_raw or 0.0)), cal=calibration)
        samples.append((float(depth), float(qc_mpa), float(fs_kpa)))

    if not samples:
        samples = [(0.0, 0.0, 0.0)]

    samples.sort(key=lambda item: item[0])
    max_depth_m = max(s[0] for s in samples)

    is_k4 = int(getattr(calibration, "scale_div", 250) or 250) >= 1000
    if is_k4:
        qc_range, fs_range = 50.0, 500.0
        qc_major, fs_major = 10.0, 100.0
    else:
        qc_range, fs_range = 30.0, 300.0
        qc_major, fs_major = 5.0, 50.0

    plot_x0 = 0.0
    plot_width = 55.0

    qc_scale = CurveScaleSpec(
        min_value=0.0,
        max_value=qc_range,
        width_mm=plot_width,
        major_tick_step=qc_major,
        minor_tick_step=0.0,
        title="qc",
        unit="MPa",
        x_origin_mm=plot_x0,
        layer_scale="ZE_CPT_QC_SCALE",
        layer_curve="ZE_CPT_QC_CURVE",
    )
    fs_scale = CurveScaleSpec(
        min_value=0.0,
        max_value=fs_range,
        width_mm=plot_width,
        major_tick_step=fs_major,
        minor_tick_step=0.0,
        title="fs",
        unit="kPa",
        x_origin_mm=plot_x0,
        layer_scale="ZE_CPT_FS_SCALE",
        layer_curve="ZE_CPT_FS_CURVE",
    )

    qc_points: list[tuple[float, float]] = []
    fs_points: list[tuple[float, float]] = []
    for depth, qc_mpa, fs_kpa in samples:
        y_mm = _depth_to_y_mm(depth, int(options.vertical_scale))
        qc_points.append((_value_to_x_mm(qc_mpa, qc_scale), y_mm))
        fs_points.append((_value_to_x_mm(fs_kpa, fs_scale), y_mm))

    title = title_text or f"Зондирование {int(getattr(test, 'tid', 0) or 0)}"

    # Header is moved up by +20 units compared to previous baseline around y=0..5
    qc_axis_y = 22.0
    fs_axis_y = 12.0
    title_y = 30.0

    lines: list[CadLine] = []
    texts: list[TextLabel] = [
        TextLabel("ZE_CPT_TITLE", title, plot_x0, title_y, 3.0, align="LEFT"),
        TextLabel(qc_scale.layer_scale, f"qc, {qc_scale.unit}", plot_x0, qc_axis_y + 1.8, 2.4, align="LEFT"),
        TextLabel(fs_scale.layer_scale, f"fs, {fs_scale.unit}", plot_x0, fs_axis_y + 1.8, 2.4, align="LEFT"),
    ]

    qc_scale_lines, qc_scale_texts = _build_scale_lines(spec=qc_scale, axis_y_mm=qc_axis_y)
    fs_scale_lines, fs_scale_texts = _build_scale_lines(spec=fs_scale, axis_y_mm=fs_axis_y)
    lines.extend(qc_scale_lines)
    lines.extend(fs_scale_lines)
    texts.extend(qc_scale_texts)
    texts.extend(fs_scale_texts)

    points = [CadPoint("ZE_CPT_TITLE", (0.0, 0.0, 0.0), color_aci=1)]

    polylines: list[CadPolyline] = []
    if len(qc_points) >= 2:
        polylines.append(CadPolyline(qc_scale.layer_curve, qc_points))
    if len(fs_points) >= 2:
        polylines.append(CadPolyline(fs_scale.layer_curve, fs_points))

    scene = CadScene(
        layers=list(MANDATORY_LAYERS),
        block=CadBlock(
            name=block_name,
            base_point=(0.0, 0.0, 0.0),
            lines=lines,
            polylines=polylines,
            points=points,
            texts=texts,
        ),
    )

    y_bottom = _depth_to_y_mm(max_depth_m, int(options.vertical_scale))
    _log.info(
        "build_cpt_cad_scene done test_id=%s points_qc=%s points_fs=%s qc_max=%.3f fs_max=%.3f",
        int(getattr(test, "tid", 0) or 0),
        len(qc_points),
        len(fs_points),
        qc_range,
        fs_range,
    )
    return CadBuildResult(
        scene=scene,
        qc_series=CurveSeries(layer=qc_scale.layer_curve, points_mm=qc_points),
        fs_series=CurveSeries(layer=fs_scale.layer_curve, points_mm=fs_points),
        qc_scale=qc_scale,
        fs_scale=fs_scale,
        depth_axis=DepthAxisSpec(layer="ZE_CPT_TITLE", x_mm=0.0, max_depth_m=max_depth_m, major_step_m=1.0, minor_step_m=0.2),
        drawing_width_mm=plot_width,
        drawing_height_mm=abs(y_bottom) + title_y,
    )
