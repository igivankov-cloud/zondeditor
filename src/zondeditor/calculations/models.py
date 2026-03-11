from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IGEModel:
    ige_id: str
    display_label: str
    soil_code: str
    soil_family: str
    subtype: str | None = None
    is_alluvial: bool = False
    notes: str = ""
    calc_profile_id: str = "DEFAULT_CURRENT"
    calc_method: str | None = None
    calc_status: str | None = None
    manual_confirmation_required: bool = False
    calc_warning: str | None = None
    override_enabled: bool = False
    override_reason: str = ""


@dataclass
class IGECalcPoint:
    sounding_id: str
    depth_m: float
    qc_mpa: float
    fs_kpa: float | None
    segment_id: str | None = None


@dataclass
class IGECalcStats:
    n_points: int = 0
    qc_avg_mpa: float | None = None
    qc_min_mpa: float | None = None
    qc_max_mpa: float | None = None
    fs_avg_kpa: float | None = None
    v_qc: float | None = None
    avg_depth_m: float | None = None


@dataclass
class IGECalcResult:
    E_MPa: float | None = None
    phi_deg: float | None = None
    c_kPa: float | None = None


@dataclass
class IGECalcSample:
    ige_id: str
    profile_id: str
    method: str
    status: str
    points: list[IGECalcPoint]
    stats: IGECalcStats
    result: IGECalcResult
    warnings: list[str]
    excluded_count: int = 0
    exclusions: list[str] = field(default_factory=list)


@dataclass
class CalculationTabState:
    selected_profile_id: str = "DEFAULT_CURRENT"
    selected_method_mode: str = "AUTO"
    include_sandy_loam: bool = True
    allow_fill_by_material: bool = False
    show_excluded_points: bool = False
    last_run_at: str | None = None
    selected_ige_id: str | None = None
