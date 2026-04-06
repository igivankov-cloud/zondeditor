from __future__ import annotations

from dataclasses import dataclass

from src.zondeditor.domain.models import TestData
from src.zondeditor.processing.calibration import Calibration, calc_qc_fs

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

MANDATORY_LAYERS: tuple[CadLayerSpec, ...] = (
    CadLayerSpec("ZE_CPT_QC_CURVE", color_aci=3, rgb=(22, 163, 74)),
    CadLayerSpec("ZE_CPT_FS_CURVE", color_aci=5, rgb=(37, 99, 235)),
    CadLayerSpec("ZE_CPT_DEPTH_AXIS", color_aci=7),
    CadLayerSpec("ZE_CPT_QC_SCALE", color_aci=3, rgb=(22, 163, 74)),
    CadLayerSpec("ZE_CPT_FS_SCALE", color_aci=5, rgb=(37, 99, 235)),
    CadLayerSpec("ZE_CPT_TITLES", color_aci=7),
    CadLayerSpec("ZE_CPT_FRAME", color_aci=8),
    CadLayerSpec("ZE_CPT_BASEPOINT", color_aci=1),
    CadLayerSpec("ZE_CPT_GRID", color_aci=9),
    CadLayerSpec("ZE_CPT_SERVICE", color_aci=8),
)


@dataclass(frozen=True)
class CadBuildResult:
    scene: CadScene
    qc_series: CurveSeries
    fs_series: CurveSeries
    qc_scale: CurveScaleSpec
    fs_scale: CurveScaleSpec
    depth_axis: DepthAxisSpec


def _parse_float(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip().replace(",", "."))
    except Exception:
        return None


def _build_scale_ticks(*, spec: CurveScaleSpec, y_top_mm: float, y_bottom_mm: float) -> list[CadLine]:
    out: list[CadLine] = []
    out.append(CadLine(spec.layer_scale, (spec.x_origin_mm, y_top_mm), (spec.x_origin_mm + spec.width_mm, y_top_mm)))
    major = spec.major_tick_step if spec.major_tick_step > 0 else (spec.max_value - spec.min_value)
    minor = spec.minor_tick_step if spec.minor_tick_step > 0 else major
    if major <= 0:
        return out
    val = spec.min_value
    while val <= spec.max_value + 1e-9:
        x_mm = spec.x_origin_mm + ((val - spec.min_value) / (spec.max_value - spec.min_value)) * spec.width_mm
        out.append(CadLine(spec.layer_scale, (x_mm, y_top_mm), (x_mm, y_top_mm - 2.5)))
        val += major
    if minor > 0 and minor < major:
        val = spec.min_value
        while val <= spec.max_value + 1e-9:
            x_mm = spec.x_origin_mm + ((val - spec.min_value) / (spec.max_value - spec.min_value)) * spec.width_mm
            out.append(CadLine(spec.layer_scale, (x_mm, y_top_mm), (x_mm, y_top_mm - 1.2)))
            val += minor
    _ = y_bottom_mm
    return out


def _depth_to_y_mm(depth_m: float, vertical_scale: int) -> float:
    return -depth_m * 1000.0 / float(vertical_scale)


def _value_to_x_mm(value: float, spec: CurveScaleSpec) -> float:
    value_clamped = max(spec.min_value, min(spec.max_value, value))
    span = spec.max_value - spec.min_value
    if span <= 0:
        return spec.x_origin_mm
    return spec.x_origin_mm + (value_clamped - spec.min_value) * spec.width_mm / span


def build_cpt_cad_scene(
    *,
    test: TestData,
    calibration: Calibration,
    options: ExportCadOptions,
    block_name: str,
    qc_max_mpa: float = 30.0,
    fs_max_kpa: float = 500.0,
) -> CadBuildResult:
    qc_scale = CurveScaleSpec(
        min_value=0.0,
        max_value=max(1.0, float(qc_max_mpa)),
        width_mm=65.0,
        major_tick_step=5.0,
        minor_tick_step=1.0,
        title="qc",
        unit="MPa",
        x_origin_mm=24.0,
        layer_scale="ZE_CPT_QC_SCALE",
        layer_curve="ZE_CPT_QC_CURVE",
    )
    fs_scale = CurveScaleSpec(
        min_value=0.0,
        max_value=max(10.0, float(fs_max_kpa)),
        width_mm=65.0,
        major_tick_step=100.0,
        minor_tick_step=20.0,
        title="fs",
        unit="kPa",
        x_origin_mm=98.0,
        layer_scale="ZE_CPT_FS_SCALE",
        layer_curve="ZE_CPT_FS_CURVE",
    )

    depth_values: list[float] = []
    qc_points: list[tuple[float, float]] = []
    fs_points: list[tuple[float, float]] = []

    depth_arr = list(getattr(test, "depth", []) or [])
    qc_arr = list(getattr(test, "qc", []) or [])
    fs_arr = list(getattr(test, "fs", []) or [])
    n = max(len(depth_arr), len(qc_arr), len(fs_arr))

    for i in range(n):
        depth = _parse_float(depth_arr[i]) if i < len(depth_arr) else None
        qc_raw = _parse_float(qc_arr[i]) if i < len(qc_arr) else None
        fs_raw = _parse_float(fs_arr[i]) if i < len(fs_arr) else None
        if depth is None or (qc_raw is None and fs_raw is None):
            continue
        qc_mpa, fs_kpa = calc_qc_fs(int(round(qc_raw or 0.0)), int(round(fs_raw or 0.0)), cal=calibration)
        y_mm = _depth_to_y_mm(float(depth), int(options.vertical_scale))
        depth_values.append(float(depth))
        qc_points.append((_value_to_x_mm(qc_mpa, qc_scale), y_mm))
        fs_points.append((_value_to_x_mm(fs_kpa, fs_scale), y_mm))

    if not depth_values:
        depth_values = [0.0]

    max_depth_m = max(depth_values)
    y_bottom_mm = _depth_to_y_mm(max_depth_m, int(options.vertical_scale))
    depth_axis = DepthAxisSpec(
        layer="ZE_CPT_DEPTH_AXIS",
        x_mm=0.0,
        max_depth_m=max_depth_m,
        major_step_m=1.0,
        minor_step_m=0.2,
        label_offset_mm=3.0,
    )

    lines: list[CadLine] = [
        CadLine("ZE_CPT_DEPTH_AXIS", (depth_axis.x_mm, 0.0), (depth_axis.x_mm, y_bottom_mm)),
    ]
    lines.extend(_build_scale_ticks(spec=qc_scale, y_top_mm=0.0, y_bottom_mm=y_bottom_mm))
    lines.extend(_build_scale_ticks(spec=fs_scale, y_top_mm=0.0, y_bottom_mm=y_bottom_mm))

    major = depth_axis.major_step_m
    minor = depth_axis.minor_step_m
    d = 0.0
    while d <= max_depth_m + 1e-9:
        y = _depth_to_y_mm(d, int(options.vertical_scale))
        lines.append(CadLine("ZE_CPT_DEPTH_AXIS", (-1.8, y), (1.8, y)))
        if options.include_grid:
            lines.append(CadLine("ZE_CPT_GRID", (qc_scale.x_origin_mm, y), (fs_scale.x_origin_mm + fs_scale.width_mm, y)))
        d += major
    d = 0.0
    while d <= max_depth_m + 1e-9:
        y = _depth_to_y_mm(d, int(options.vertical_scale))
        lines.append(CadLine("ZE_CPT_DEPTH_AXIS", (-1.0, y), (1.0, y)))
        d += minor

    frame_x0 = -8.0
    frame_x1 = fs_scale.x_origin_mm + fs_scale.width_mm + 8.0
    lines.extend(
        [
            CadLine("ZE_CPT_FRAME", (frame_x0, 6.0), (frame_x1, 6.0)),
            CadLine("ZE_CPT_FRAME", (frame_x1, 6.0), (frame_x1, y_bottom_mm - 6.0)),
            CadLine("ZE_CPT_FRAME", (frame_x1, y_bottom_mm - 6.0), (frame_x0, y_bottom_mm - 6.0)),
            CadLine("ZE_CPT_FRAME", (frame_x0, y_bottom_mm - 6.0), (frame_x0, 6.0)),
        ]
    )

    points = [CadPoint("ZE_CPT_BASEPOINT", (0.0, 0.0, 0.0))]
    lines.extend(
        [
            CadLine("ZE_CPT_BASEPOINT", (-1.5, 0.0), (1.5, 0.0)),
            CadLine("ZE_CPT_BASEPOINT", (0.0, -1.5), (0.0, 1.5)),
        ]
    )

    texts: list[TextLabel] = [
        TextLabel("ZE_CPT_TITLES", f"{qc_scale.title}, {qc_scale.unit}", qc_scale.x_origin_mm, 5.0, 2.5),
        TextLabel("ZE_CPT_TITLES", f"{fs_scale.title}, {fs_scale.unit}", fs_scale.x_origin_mm, 5.0, 2.5),
        TextLabel("ZE_CPT_TITLES", "Глубина, м", -7.0, 5.0, 2.5),
    ]

    d = 0.0
    while d <= max_depth_m + 1e-9:
        y = _depth_to_y_mm(d, int(options.vertical_scale))
        texts.append(TextLabel("ZE_CPT_TITLES", f"{d:.2f}", -7.0, y - 0.8, 2.0))
        d += major

    for spec in (qc_scale, fs_scale):
        val = spec.min_value
        while val <= spec.max_value + 1e-9:
            x = _value_to_x_mm(val, spec)
            texts.append(TextLabel("ZE_CPT_TITLES", f"{val:g}", x, -4.2, 1.8, align="CENTER"))
            val += spec.major_tick_step

    qc_series = CurveSeries(layer=qc_scale.layer_curve, points_mm=qc_points)
    fs_series = CurveSeries(layer=fs_scale.layer_curve, points_mm=fs_points)

    polylines = []
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
    return CadBuildResult(
        scene=scene,
        qc_series=qc_series,
        fs_series=fs_series,
        qc_scale=qc_scale,
        fs_scale=fs_scale,
        depth_axis=depth_axis,
    )
