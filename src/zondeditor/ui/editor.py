# src/zondeditor/ui/editor.py
# Auto-generated from tools/_ui_extract/GeoCanvasEditor.py (Step19)
# === FILE MAP BEGIN ===
# FILE MAP (обновляй при правках; указывай строки Lx–Ly)
# - _extract_base_ige_num/_used_base_ige_ordinals: L1120–L1139 — поиск базовых имён ИГЭ-N для выбора следующего свободного номера.
# - _next_free_ige_ordinal/_next_free_ige_id: L1141–L1340 — генерация ближайшего свободного базового имени ИГЭ.
# - _add_unassigned_ige_from_ribbon: L1371–L1383 — добавление нового ИГЭ с пустым типом грунта.
# - _rename_ige_from_ribbon: L1635–L1670 — переименование ИГЭ с проверкой уникальности и обновлением ссылок в слоях.
# - hatching integration: _draw_layer_hatch/_draw_layers_overlay_for_test — применение встроенной библиотеки hatch-паттернов.
# === FILE MAP END ===

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont

# stdlib
import random
import re
import bisect
import os
import sys
import math
import copy
import csv
import json
import time
import datetime
import datetime as _dt
import zipfile
import shutil
import tempfile
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path

# project modules already extracted:
from src.zondeditor.processing.fixes import fix_tests_by_algorithm
from src.zondeditor.processing.diagnostics import evaluate_diagnostics, ProtocolEntry
from src.zondeditor.processing.calibration import (
    calc_qc_fs_from_del,
    calibration_from_common_params,
)
try:
    from src.zondeditor.export.excel_export import export_excel as export_excel_file
except Exception:
    export_excel_file = None
from src.zondeditor.export.credo_zip import export_credo_zip
from src.zondeditor.export.cpt_protocol_docx import export_cpt_protocol_docx
from src.zondeditor.export.geo_export import bundle_geo_filename, export_bundle_geo, prepare_geo_tests
from src.zondeditor.export.gxl_export import export_gxl_generated
from src.zondeditor.export.selection import select_export_tests
from src.zondeditor.io.geo_reader import load_geo, parse_geo_bytes, GeoParseError
from src.zondeditor.io.gxl_reader import load_gxl, parse_gxl_file, GxlParseError
from src.zondeditor.io.geo_writer import save_geo_as, save_k2_geo_from_template, build_k2_geo_from_template
from src.zondeditor.domain.models import TestData, GeoBlockInfo, TestFlags
from src.zondeditor.calculations.ige_policy import build_ige_display_label, get_ige_profile
from src.zondeditor.domain.layer_store import LayerStore
from src.zondeditor.domain.experience_column import (
    ColumnInterval,
    ExperienceColumn,
    build_column_from_layers,
    append_bottom,
    column_interval_to_dict,
    column_from_dict,
    column_to_dict,
    insert_between,
    move_column_boundary as move_experience_column_boundary,
    normalize_column,
    resize_column_end as resize_experience_column_end,
    remove_column_interval,
    split_column_interval,
)
from src.zondeditor.domain.layers import (
    SoilType,
    CalcMode,
    Layer,
    INSERT_LAYER_THICKNESS_M,
    SOIL_STYLE,
    build_default_layers,
    calc_mode_for_soil,
    layer_from_dict,
    layer_to_dict,
    move_layer_boundary,
    normalize_layers,
    validate_layers,
    MIN_LAYERS_PER_TEST,
    MAX_LAYERS_PER_TEST,
    SOIL_TYPE_TO_COLUMN_FILL,
)

from src.zondeditor.ui.consts import *
from src.zondeditor.ui.helpers import _apply_win11_style, _setup_shared_logger, _validate_nonneg_float_key, _check_license_or_exit, _parse_depth_float, _try_parse_dt, _pick_icon_font, _validate_tid_key, _validate_depth_0_4_key, _format_date_ru, _format_time_ru, _canvas_view_bbox, _validate_hh_key, _validate_mm_key, _parse_cell_int, _max_zero_run, _noise_around, _interp_with_noise, _resource_path, _open_logs_folder
from src.zondeditor.domain.hatching import HATCH_USAGE_EDITOR_EXPANDED, load_registered_hatch
from src.zondeditor.ui.render.hatch_renderer import render_hatch_pattern
from src.zondeditor.ui.widgets import ToolTip, CalendarDialog
from src.zondeditor.ui.ribbon import RibbonView
from src.zondeditor.project import Project, ProjectSettings, SourceInfo, load_project, save_project
from src.zondeditor.project.ops import op_algo_fix_applied, op_cell_set, op_cells_marked, op_meta_change
from src.zondeditor.domain.cpt_params_ru import (
    CptCalcSettings,
    METHOD_SP11,
    METHOD_SP446,
    calculate_ige_cpt_results,
)
from src.zondeditor.calculations.models import CalculationTabState
from src.zondeditor.calculations.normative_profiles import load_normative_profiles
from src.zondeditor.calculations.sample_builder import build_ige_samples
from src.zondeditor.calculations.protocol_builder import build_protocol

_rebuild_geo_from_template = build_k2_geo_from_template

LAYER_UI_COLORS = {
    "fill": "#eef3f8",
    "fill_active": "#e3ebf3",
    "outline": "#b7c4d1",
    "outline_active": "#97a8ba",
    "text": "#4d5c6b",
    "text_muted": "#9aa7b4",
    "line": "#aebbc8",
    "focus": "#7f94a9",
}


# --- Cell edit validators (auto-restored) ---
import re as _re__cell

def _validate_int_0_300_key(p: str) -> bool:
    """Tk validatecommand: allow empty while typing; otherwise int in [0, 300]."""
    if p is None:
        return True
    p = str(p)
    if p == "":
        return True
    if not p.isdigit():
        return False
    try:
        v = int(p)
    except Exception:
        return False
    return 0 <= v <= 300


def _sanitize_int_0_300(s: str) -> str:
    """Normalize entry value to a safe int string in [0, 300]. Empty -> ''."""
    if s is None:
        return ""
    s = str(s).strip()
    if s == "":
        return ""
    if not s.isdigit():
        m = _re__cell.search(r"(\d+)", s)
        if not m:
            return ""
        s = m.group(1)
    try:
        v = int(s)
    except Exception:
        return ""
    if v < 0:
        v = 0
    if v > 300:
        v = 300
    return str(v)
class GeoCanvasEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        _apply_win11_style(self)
        self.title(APP_TITLE)
        try:
            self.iconbitmap(_resource_path('SZ_icon_adaptive.ico'))
        except Exception:
            pass
        # Центрируем главное окно на экране

        W0, H0 = 1480, 880

        try:

            sw = self.winfo_screenwidth()

            sh = self.winfo_screenheight()

            x = max((sw - W0) // 2, 0)

            y = max((sh - H0) // 2, 0)

            self.geometry(f"{W0}x{H0}+{x}+{y}")

        except Exception:

            self.geometry("1480x880")


        # --- offline machine-bound license + shared logs ---
        from tkinter import messagebox
        _check_license_or_exit(messagebox)
        self.usage_logger = _setup_shared_logger()
        self._install_dialog_defaults()
        self.bind_all("<F12>", lambda e: _open_logs_folder())

        self.geo_path: Path | None = None
        self.is_gxl = False
        self.geo_kind = 'K2'
        self.original_bytes: bytes | None = None

        # template block infos from original GEO (needed to rebuild GEO correctly after deletions)
        self._geo_template_blocks_info = []  # legacy: blocks info (do not mutate on edits)
        self._geo_template_blocks_info_full = []  # immutable template blocks info from original GEO
        self.meta_rows: list[dict] = []
        self.tests: list[TestData] = []
        self.flags: dict[int, TestFlags] = {}
        self.depth_start: float | None = None
        self.step_m: float | None = None
        self._depth_confirmed = False
        self._step_confirmed = False

        # Для GEO: индивидуальная начальная глубина по каждому опыту (tid -> h0)
        # Если не задано — используется self.depth_start.
        self.depth0_by_tid = {}
        self.step_by_tid = {}  # tid -> step_m (float), задел под индивидуальный шаг
        self.gwl_by_tid = {}  # tid -> {"enabled": bool, "value": float|None}

        self.undo_stack: list[dict] = []
        self.redo_stack: list[dict] = []

        self._dirty = False

        # Algorithm preview mode (autocheck on open): use pale colors, no data modification
        self._algo_preview_mode = False
        self.object_code = ""
        self.object_name = ""
        self.project_name = "Новый проект"
        self.project_type = "type2_electric"
        self.project_mode_params: dict[str, str] = {}
        self._suspend_type1_param_validation = False
        self._skip_next_type1_error_popup = False
        self._validation_error_popup_active = False
        self._ui_ready_for_mode_validation = False
        self.project_path: Path | None = None
        self.project_ops: list[dict] = []
        self._marks_index: dict[tuple[int, float, str], dict] = {}
        self._marks_ops_count = 0
        self._marks_built_count = 0
        self._marks_applied_count = 0
        self._marks_color_counts: dict[str, int] = {"green": 0, "purple": 0, "blue": 0, "orange": 0}
        self.use_ribbon_ui = True
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._install_tk_root_guard()

        self.display_cols: list[int] = []  # indices of self.tests in left-to-right order

        self.row_h_default = 22
        # В режиме «Свернуть 1 м» строка-агрегат должна быть визуально выше
        # (по запросу пользователей ~1 см на типичном DPI).
        self.row_h_compact_1m = 38
        self.row_h = self.row_h_default
        self.hdr_h = 64
        self.col_gap = 12
        self.w_depth = 64
        self.w_val = 56
        self.pad_x = 8
        self.pad_y = 8
        self.show_graphs = False
        self.show_geology_column = True
        self.show_inclinometer = True
        self.show_layer_colors = False
        self.show_layer_hatching = True
        self.compact_1m = False
        self.display_sort_mode = "date"
        self.expanded_meters: set[int] = set()
        self._graph_redraw_after_id = None
        self._header_offset_px = 0.0
        self._shared_x_frac = 0.0
        self._shared_x_lock = False
        self._xsync_after_id = None
        self._rebuild_redraw_after_id = None
        self._header_stabilize_after_id = None
        self._header_sync_pending = False
        self._header_sync_mode = str(os.getenv("ZOND_HEADER_SYNC_MODE", "legacy") or "legacy").strip().lower()
        self._header_sync_debug = str(os.getenv("ZOND_DEBUG_HEADER_SYNC", "") or "").strip().lower() in {"1", "true", "yes", "on"}
        self._header_sync_wheel_seq = 0
        self._header_sync_source_counts: dict[str, int] = {}
        self._debug_hatch = str(os.getenv("ZOND_DEBUG_HATCH", "") or "").strip().lower() in {"1", "true", "yes", "on"}
        self._active_test_idx: int | None = None
        self.graph_qc_max_mpa: float = 30.0
        self.graph_fs_max_kpa: float = 500.0
        self.layer_edit_mode = True
        self._layer_drag = None  # {"ti": int, "boundary": int}
        self._layer_handle_hitbox = []
        self._layer_depth_box_hitbox = []
        self._layer_plot_hitbox = []
        self._layer_label_hitbox = []
        self._layer_ige_picker = None
        self._layer_ige_picker_meta = None
        self._ige_picker_debug = bool(os.environ.get("ZONDEDITOR_DEBUG_IGE_PICKER") == "1")
        self._boundary_depth_editor = None
        self._editor_just_opened = False
        self._inline_edit_active = False
        self.ige_registry: dict[str, dict[str, object]] = {
            "ИГЭ-1": {"soil_type": SoilType.LOAM.value, "calc_mode": calc_mode_for_soil(SoilType.LOAM).value, "style": dict(SOIL_STYLE.get(SoilType.LOAM, {})), "label": "ИГЭ-1", "ordinal": 1},
            "ИГЭ-2": {"soil_type": SoilType.SAND.value, "calc_mode": calc_mode_for_soil(SoilType.SAND).value, "style": dict(SOIL_STYLE.get(SoilType.SAND, {})), "label": "ИГЭ-2", "ordinal": 2},
            "ИГЭ-3": {"soil_type": SoilType.CLAY.value, "calc_mode": calc_mode_for_soil(SoilType.CLAY).value, "style": dict(SOIL_STYLE.get(SoilType.CLAY, {})), "label": "ИГЭ-3", "ordinal": 3},
        }
        self.layer_store = LayerStore()
        self._debug_layers_overlay = bool(os.environ.get("ZONDEDITOR_DEBUG_LAYERS") == "1")
        self._debug_tail_edit = bool(os.environ.get("ZONDEDITOR_DEBUG_TAIL_EDIT") == "1")
        self._debug_tail_rows = int(os.environ.get("ZONDEDITOR_DEBUG_TAIL_ROWS", "10") or 10)
        self.cpt_calc_settings = {"method": METHOD_SP446, "alluvial_sands": True, "groundwater_level": None}
        self.calc_tab_state = CalculationTabState()
        self.calc_rows = []
        self.calc_samples = []
        self.calc_protocol = None
        self.normative_profiles = load_normative_profiles()

        try:
            self.graph_w = int(self.winfo_fpixels("4c"))
        except Exception:
            self.graph_w = 150
        if self.graph_w <= 0:
            self.graph_w = 150

        self._editing = None  # (test_idx,row,field, entry)
        self._editing_meta = None
        self._ctx_menu = None
        self._ctx_target = None  # (ti,row) for delete
        self._rc_preview = None  # (ti,row) transient red row highlight for context menu

        self._build_ui()
        self._update_window_title()
        # realtime footer status
        self._footer_force_live = True
        try:
            self.after(400, self._footer_live_tick)
        except Exception:
            pass

    def _install_dialog_defaults(self):
        """Ensure dialogs are parented to the main window to avoid extra implicit tk roots."""
        def _wrap(module, name: str):
            fn = getattr(module, name, None)
            if not callable(fn):
                return
            def _wrapped(*args, **kwargs):
                kwargs.setdefault("parent", self)
                return fn(*args, **kwargs)
            setattr(module, name, _wrapped)

        for _name in ("showinfo", "showwarning", "showerror", "askyesno", "askyesnocancel", "askokcancel", "askretrycancel", "askquestion"):
            _wrap(messagebox, _name)
        for _name in ("askopenfilename", "askopenfilenames", "asksaveasfilename", "askdirectory"):
            _wrap(filedialog, _name)

    def _install_tk_root_guard(self):
        if os.environ.get("ZONDEDITOR_DEV_GUARD") != "1":
            return
        tk_mod = tk
        if getattr(tk_mod, "_zondeditor_tk_guard", False):
            return
        original_tk = tk_mod.Tk
        main_root = self

        def _guarded_tk(*args, **kwargs):
            if getattr(main_root, "_allow_secondary_tk", False):
                return original_tk(*args, **kwargs)
            stack = "".join(traceback.format_stack(limit=20))
            msg = "[ZondEditor guard] Попытка создать второй tk.Tk(). Используйте Toplevel(parent)."
            print(msg, file=sys.stderr)
            print(stack, file=sys.stderr)
            raise RuntimeError(msg)

        tk_mod.Tk = _guarded_tk
        tk_mod._zondeditor_tk_guard = True

    # ---------------- history ----------------

    def _compute_depth_grid(self):
        """Build a common depth grid to align all tests visually.

        Returns: (grid_floats, step_m, row_maps, start_rows)
          - row_maps[ti]: dict(grid_row_index -> data_index_in_test)
          - start_rows[ti]: first grid row where the test has data (depth[0])
        """
        if not getattr(self, "tests", None):
            return [], None, {}, {}

        include_column_axis = bool(getattr(self, "show_geology_column", True))

        depth_lists = {}
        min_d = None
        max_d = None
        diffs = []
        for ti, t in enumerate(self.tests):
            dvals = []
            for ds in (getattr(t, "depth", []) or []):
                dv = _parse_depth_float(ds)
                if dv is None:
                    continue
                dvals.append(float(dv))
            if not dvals:
                continue
            depth_lists[ti] = dvals
            min_d = dvals[0] if (min_d is None or dvals[0] < min_d) else min_d
            max_d = dvals[-1] if (max_d is None or dvals[-1] > max_d) else max_d
            for a, b in zip(dvals, dvals[1:]):
                dd = b - a
                if dd > 1e-6:
                    diffs.append(dd)
            if include_column_axis:
                try:
                    col_top, col_bot = self._experience_column_depth_range(t)
                    min_d = col_top if (min_d is None or col_top < min_d) else min_d
                    max_d = col_bot if (max_d is None or col_bot > max_d) else max_d
                except Exception:
                    pass

        if include_column_axis and (min_d is None or max_d is None):
            for t in (self.tests or []):
                try:
                    col_top, col_bot = self._experience_column_depth_range(t)
                except Exception:
                    continue
                min_d = col_top if (min_d is None or col_top < min_d) else min_d
                max_d = col_bot if (max_d is None or col_bot > max_d) else max_d

        if min_d is None or max_d is None:
            return [], None, {}, {}

        step = None
        if diffs:
            step = min(diffs)
            for cand in (0.05, 0.1):
                if abs(step - cand) < 0.005:
                    step = cand
                    break
            step = round(step, 4)
        if step is None or step <= 0:
            step = float(getattr(self, "step_m", 0.05) or 0.05)

        grid = []
        x = round(float(min_d), 2)
        lim = float(max_d) + 1e-6
        i = 0
        while x <= lim and i < 20000:
            grid.append(round(x, 2))
            x = round(x + step, 4)
            i += 1

        row_maps = {}
        start_rows = {}
        grid_index = {round(v, 2): idx for idx, v in enumerate(grid)}
        for ti, dvals in depth_lists.items():
            mp = {}
            for di, dv in enumerate(dvals):
                key = round(dv, 2)
                gi = grid_index.get(key)
                if gi is not None:
                    mp[gi] = di
            row_maps[ti] = mp
            if mp:
                start_rows[ti] = min(mp.keys())

        return grid, step, row_maps, start_rows

    def _experience_column_depth_range(self, t) -> tuple[float, float]:
        column = self._ensure_test_experience_column(t)
        return float(column.column_depth_start), float(column.column_depth_end)

    def _build_grid(self):
        """Backward-compatible grid cache builder used by legacy callbacks."""
        if not getattr(self, "tests", None):
            self._grid = []
            self._grid_step = None
            self._grid_row_maps = {}
            self._grid_start_rows = {}
            self._grid_units = []
            self._grid_meter_rows = {}
            self._grid_base = []
            self._grid_base_row_maps = {}
            return

        if str(getattr(self, "project_type", "") or "") in {"type1_mech", "direct_qcfs"}:
            self._ensure_mechanical_depth_template_rows()

        grid, grid_step, row_maps, start_rows = self._compute_depth_grid()
        if not grid:
            max_rows = max((len(getattr(t, "qc", []) or []) for t in self.tests), default=0)
            grid = [None] * max_rows
            row_maps = {ti: {r: r for r in range(len(getattr(self.tests[ti], "qc", []) or []))} for ti in range(len(self.tests))}
            start_rows = {ti: 0 for ti in range(len(self.tests))}

        view_rows = []
        meter_rows: dict[int, int] = {}
        if bool(getattr(self, "compact_1m", False)) and grid:
            gmin = min((g for g in grid if g is not None), default=None)
            gmax = max((g for g in grid if g is not None), default=None)
            if gmin is not None and gmax is not None:
                meter_start = int(math.floor(float(gmin)))
                meter_end = int(math.ceil(float(gmax)))
                for m in range(meter_start, meter_end):
                    g_rows = [ri for ri, dv in enumerate(grid) if dv is not None and (m <= float(dv) < (m + 1))]
                    if not g_rows:
                        continue
                    if m in getattr(self, "expanded_meters", set()):
                        for gi in g_rows:
                            view_rows.append(("row", gi))
                    else:
                        disp_r = len(view_rows)
                        view_rows.append(("meter", m))
                        meter_rows[disp_r] = m

        if not view_rows:
            view_rows = [("row", r) for r in range(len(grid))]

        disp_maps = {}
        disp_start_rows = {}
        for ti in range(len(self.tests)):
            base = row_maps.get(ti, {}) or {}
            dmap = {}
            for disp_r, unit in enumerate(view_rows):
                if unit[0] == "row":
                    dmap[disp_r] = base.get(unit[1])
            disp_maps[ti] = dmap
            disp_start_rows[ti] = next((dr for dr, di in dmap.items() if di is not None), 0)

        self._grid = [None] * len(view_rows)
        self._grid_step = grid_step
        self._grid_row_maps = disp_maps
        self._grid_start_rows = disp_start_rows
        self._grid_units = view_rows
        self._grid_meter_rows = meter_rows
        self._grid_base = grid
        self._grid_base_row_maps = row_maps
        self._rebuild_row_geometry()

    def _ensure_mechanical_depth_template_rows(self):
        tests = list(getattr(self, "tests", []) or [])
        if not tests:
            return
        t0 = tests[0]
        depth = list(getattr(t0, "depth", []) or [])
        if len(depth) > 1:
            return
        depth = [f"{(i * 0.2):.2f}" for i in range(26)]
        n = len(depth)
        qc = list(getattr(t0, "qc", []) or [])
        fs = list(getattr(t0, "fs", []) or [])
        if len(qc) < n:
            qc += [""] * (n - len(qc))
        if len(fs) < n:
            fs += [""] * (n - len(fs))
        t0.depth = depth
        t0.qc = qc[:n]
        t0.fs = fs[:n]
        self.depth0_by_tid[int(getattr(t0, "tid", 1) or 1)] = 0.0
        self.step_by_tid[int(getattr(t0, "tid", 1) or 1)] = 0.2

    def _row_height_for(self, row: int) -> int:
        units = getattr(self, "_grid_units", []) or []
        if 0 <= int(row) < len(units):
            unit = units[int(row)]
            if bool(getattr(self, "compact_1m", False)) and unit[0] == "meter":
                return int(self.row_h_compact_1m)
        return int(self.row_h_default)

    def _rebuild_row_geometry(self):
        units = getattr(self, "_grid_units", []) or []
        tops = [0]
        y = 0
        for r in range(len(units)):
            y += self._row_height_for(r)
            tops.append(y)
        self._row_tops = tops

    def _row_y_bounds(self, row: int) -> tuple[float, float]:
        tops = getattr(self, "_row_tops", None)
        if not tops:
            self._rebuild_row_geometry()
            tops = getattr(self, "_row_tops", [0])
        row = int(max(0, row))
        if row >= len(tops) - 1:
            y0 = float(tops[-1])
            return y0, y0 + float(self.row_h_default)
        return float(tops[row]), float(tops[row + 1])

    def _total_body_height(self) -> int:
        tops = getattr(self, "_row_tops", None)
        if not tops:
            self._rebuild_row_geometry()
            tops = getattr(self, "_row_tops", [0])
        return int(tops[-1] if tops else 0)

    def _row_from_y(self, y: float) -> int:
        tops = getattr(self, "_row_tops", None)
        if not tops:
            self._rebuild_row_geometry()
            tops = getattr(self, "_row_tops", [0])
        if y < 0:
            return -1
        idx = bisect.bisect_right(tops, float(y)) - 1
        if idx < 0:
            return -1
        if idx >= len(tops) - 1:
            return len(tops) - 2
        return idx

    def _snapshot(self) -> dict:
        """Снимок состояния для Undo/Redo: данные + раскраска."""
        tests_snap: list[dict] = []
        for t in self.tests:
            tests_snap.append({
                "tid": t.tid,
                "dt": t.dt,
                "depth": list(t.depth),
                "qc": list(t.qc),
                "fs": list(t.fs),
                "incl": (None if getattr(t, "incl", None) is None else list(getattr(t, "incl", []) or [])),
                "marker": t.marker,
                "header_pos": t.header_pos,
                "orig_id": t.orig_id,
                "layers": [layer_to_dict(x) for x in (getattr(t, "layers", []) or [])],
                "experience_column": (
                    column_to_dict(getattr(t, "experience_column", None))
                    if getattr(t, "experience_column", None) is not None
                    else None
                ),
                "export_on": bool(getattr(t, "export_on", True)),
                "locked": bool(getattr(t, "locked", False)),
                "block": None if t.block is None else {
                    "order_index": t.block.order_index,
                    "header_start": t.block.header_start,
                    "header_end": t.block.header_end,
                    "id_pos": t.block.id_pos,
                    "dt_pos": t.block.dt_pos,
                    "data_start": t.block.data_start,
                    "data_end": t.block.data_end,
                    "marker_byte": t.block.marker_byte,
                    "data_len": getattr(t.block, "data_len", max(0, t.block.data_end - t.block.data_start)),
                    "bytes_per_row": getattr(t.block, "bytes_per_row", 2),
                    "layout": getattr(t.block, "layout", "K2_QC_FS"),
                },
            })
        flags_snap: dict[int, dict] = {}
        try:
            for tid, fl in (self.flags or {}).items():
                flags_snap[int(tid)] = {
                    "invalid": bool(getattr(fl, "invalid", False)),
                    "interp": sorted(list(getattr(fl, "interp_cells", set()))),
                    "force": sorted(list(getattr(fl, "force_cells", set()))),
                    "user": sorted(list(getattr(fl, "user_cells", set()))),
                    "algo": sorted(list(getattr(fl, "algo_cells", set()))),
                }
        except Exception:
            flags_snap = {}
        return {
            "tests": tests_snap,
            "flags": flags_snap,
            "step_m": float(getattr(self, "step_m", 0.05) or 0.05),
            "depth_start": float(getattr(self, "depth_start", 0.0) or 0.0),
            "geo_kind": str(getattr(self, "geo_kind", "K2") or "K2"),
            "common_params": dict(getattr(self, "_common_params", self._default_common_params(getattr(self, "geo_kind", "K2"))) or {}),
            "depth0_by_tid": dict(getattr(self, "depth0_by_tid", {}) or {}),
            "step_by_tid": dict(getattr(self, "step_by_tid", {}) or {}),
            "gwl_by_tid": copy.deepcopy(dict(getattr(self, "gwl_by_tid", {}) or {})),
            "compact_1m": bool(getattr(self, "compact_1m", False)),
            "show_graphs": bool(getattr(self, "show_graphs", False)),
            "show_geology_column": bool(getattr(self, "show_geology_column", True)),
            "show_inclinometer": bool(getattr(self, "show_inclinometer", True)),
            "show_layer_colors": bool(getattr(self, "show_layer_colors", False)),
            "show_layer_hatching": bool(getattr(self, "show_layer_hatching", True)),
            "display_sort_mode": str(getattr(self, "display_sort_mode", "date") or "date"),
            "expanded_meters": sorted(int(x) for x in (getattr(self, "expanded_meters", set()) or set())),
            "layer_edit_mode": bool(getattr(self, "layer_edit_mode", False)),
            "project_ops": copy.deepcopy(list(getattr(self, "project_ops", []) or [])),
            "ige_registry": copy.deepcopy(dict(getattr(self, "ige_registry", {}) or {})),
            "cpt_calc_settings": copy.deepcopy(dict(getattr(self, "cpt_calc_settings", {}) or {})),
            "calc_tab_state": copy.deepcopy(getattr(self, "calc_tab_state", CalculationTabState()).__dict__),
        }

    def _restore(self, snap: dict):
        self.tests = []
        self._credo_force_export = False  # after user acknowledged issues/fix, export proceeds without re-check
        self.flags = {}
        # восстановить выбранный шаг сетки (м), иначе после Undo возможны «пропуски»
        try:
            self.step_m = float(snap.get("step_m", getattr(self, "step_m", 0.05) or 0.05) or 0.05)
        except Exception:
            pass
        try:
            self.depth_start = float(snap.get("depth_start", getattr(self, "depth_start", 0.0) or 0.0) or 0.0)
        except Exception:
            pass
        try:
            self.geo_kind = str(snap.get("geo_kind", getattr(self, "geo_kind", "K2")) or "K2").upper()
        except Exception:
            self.geo_kind = str(getattr(self, "geo_kind", "K2") or "K2").upper()
        if self.geo_kind not in ("K2", "K4"):
            self.geo_kind = "K2"
        try:
            self._set_common_params(dict(snap.get("common_params") or {}), self.geo_kind)
        except Exception:
            self._set_common_params({}, self.geo_kind)

        # restore per-test start depths (tid -> h0)
        try:
            self.depth0_by_tid = dict((snap.get("depth0_by_tid") or {}))
        except Exception:
            self.depth0_by_tid = {}
        try:
            self.step_by_tid = dict((snap.get("step_by_tid") or {}))
        except Exception:
            self.step_by_tid = {}
        try:
            self.gwl_by_tid = copy.deepcopy(dict((snap.get("gwl_by_tid") or {})) or {})
        except Exception:
            self.gwl_by_tid = {}

        try:
            self.compact_1m = bool(snap.get("compact_1m", getattr(self, "compact_1m", False)))
        except Exception:
            self.compact_1m = bool(getattr(self, "compact_1m", False))
        try:
            self.show_graphs = bool(snap.get("show_graphs", getattr(self, "show_graphs", False)))
        except Exception:
            self.show_graphs = bool(getattr(self, "show_graphs", False))
        try:
            self.show_geology_column = bool(snap.get("show_geology_column", getattr(self, "show_geology_column", True)))
        except Exception:
            self.show_geology_column = bool(getattr(self, "show_geology_column", True))
        try:
            self.show_inclinometer = bool(snap.get("show_inclinometer", getattr(self, "show_inclinometer", True)))
        except Exception:
            self.show_inclinometer = bool(getattr(self, "show_inclinometer", True))
        try:
            self.show_layer_colors = bool(snap.get("show_layer_colors", getattr(self, "show_layer_colors", False)))
        except Exception:
            self.show_layer_colors = bool(getattr(self, "show_layer_colors", False))
        try:
            self.show_layer_hatching = bool(snap.get("show_layer_hatching", getattr(self, "show_layer_hatching", True)))
        except Exception:
            self.show_layer_hatching = bool(getattr(self, "show_layer_hatching", True))
        try:
            self.display_sort_mode = str(snap.get("display_sort_mode", getattr(self, "display_sort_mode", "date")) or "date").lower()
        except Exception:
            self.display_sort_mode = "date"
        if self.display_sort_mode not in ("date", "tid"):
            self.display_sort_mode = "date"
        self.row_h = int(self.row_h_compact_1m if self.compact_1m else self.row_h_default)
        try:
            self.expanded_meters = set(int(x) for x in (snap.get("expanded_meters") or []))
            self.layer_edit_mode = True
        except Exception:
            self.expanded_meters = set()
        try:
            if getattr(self, "_compact_1m_var", None) is not None:
                self._compact_1m_var.set(bool(self.compact_1m))
        except Exception:
            pass
        try:
            if getattr(self, "ribbon_view", None):
                self.ribbon_view.set_compact_1m(bool(self.compact_1m))
                self.ribbon_view.set_show_graphs(bool(self.show_graphs))
                self.ribbon_view.set_show_geology_column(bool(self.show_geology_column))
                self.ribbon_view.set_show_inclinometer(bool(self.show_inclinometer), enabled=(str(getattr(self, "geo_kind", "K2") or "K2").upper() == "K4"))
                self.ribbon_view.set_show_layer_colors(bool(self.show_layer_colors))
                self.ribbon_view.set_show_layer_hatching(bool(self.show_layer_hatching))
                self.ribbon_view.set_display_sort_mode(str(self.display_sort_mode))
                self.ribbon_view.set_common_params(self._current_common_params(), geo_kind=str(getattr(self, "geo_kind", "K2")))
                self.ribbon_view.set_layer_edit_mode(True)
                self.ribbon_view.calc_cpt_method_var.set(str(getattr(self, "calc_tab_state", CalculationTabState()).cpt_method or "СП 446.1325800.2019 (с Изм. № 1), приложение Ж"))
                self.ribbon_view.calc_transition_method_var.set(str(getattr(self, "calc_tab_state", CalculationTabState()).transition_method or "СП 22.13330.2016 (с Изм. № 1–5), п. 5.3.17"))
                self.ribbon_view.calc_allow_normative_lt6_var.set(bool(getattr(self, "calc_tab_state", CalculationTabState()).allow_normative_lt6))
                self.ribbon_view.calc_legacy_sandy_loam_var.set(bool(getattr(self, "calc_tab_state", CalculationTabState()).use_legacy_sandy_loam_sp446))
                self.ribbon_view.calc_fill_preliminary_var.set(bool(getattr(self, "calc_tab_state", CalculationTabState()).allow_fill_preliminary))
        except Exception:
            pass

        try:
            self.project_ops = copy.deepcopy(list(snap.get("project_ops", []) or []))
        except Exception:
            self.project_ops = []
        try:
            self.ige_registry = copy.deepcopy(dict(snap.get("ige_registry", {}) or {}))
        except Exception:
            self.ige_registry = {}
        try:
            self.cpt_calc_settings = copy.deepcopy(dict(snap.get("cpt_calc_settings", {}) or {})) or {"method": METHOD_SP446, "alluvial_sands": True, "groundwater_level": None}
        except Exception:
            self.cpt_calc_settings = {"method": METHOD_SP446, "alluvial_sands": True, "groundwater_level": None}
        cts = dict(snap.get("calc_tab_state") or {})
        _base_cts = CalculationTabState().__dict__
        _safe_cts = {k: v for k, v in cts.items() if k in _base_cts}
        self.calc_tab_state = CalculationTabState(**{**_base_cts, **_safe_cts})
        self._ensure_default_iges()

        for d in snap.get("tests", []):
            blk = None
            if d.get("block") is not None:
                b = d["block"]
                blk = GeoBlockInfo(
                    order_index=b["order_index"],
                    header_start=b["header_start"],
                    header_end=b["header_end"],
                    id_pos=b["id_pos"],
                    dt_pos=b["dt_pos"],
                    data_start=b["data_start"],
                    data_end=b["data_end"],
                    marker_byte=b["marker_byte"],
                    data_len=int(b.get("data_len", max(0, b["data_end"] - b["data_start"]))),
                    bytes_per_row=int(b.get("bytes_per_row", 2) or 2),
                    layout=str(b.get("layout", "K2_QC_FS") or "K2_QC_FS"),
                )
            t = TestData(
                tid=int(d["tid"]),
                dt=d["dt"],
                depth=list(d["depth"]),
                qc=list(d["qc"]),
                fs=list(d["fs"]),
                incl=(None if d.get("incl") is None else list(d.get("incl") or [])),
                marker=d.get("marker",""),
                header_pos=d.get("header_pos",""),
                orig_id=d.get("orig_id", None),
                block=blk,
                layers=[layer_from_dict(x) for x in (d.get("layers") or [])],
                experience_column=(column_from_dict(d["experience_column"]) if isinstance(d.get("experience_column"), dict) else None),
            )
            self.tests.append(t)
            try:
                t.export_on = bool(d.get('export_on', True))
            except Exception:
                pass
            try:
                t.locked = bool(d.get('locked', False))
            except Exception:
                t.locked = False
            # создать флаги для восстановленного зондирования
            try:
                self.flags[t.tid] = TestFlags(False, set(), set(), set(), set())
            except Exception:
                pass
        fsnap = snap.get("flags", {}) or {}
        for t in self.tests:
            s = fsnap.get(int(t.tid))
            if not s:
                continue
            fl = self.flags.get(t.tid)
            if not fl:
                continue
            try:
                fl.invalid = bool(s.get("invalid", False))
                fl.interp_cells = set(tuple(x) for x in s.get("interp", []))
                fl.force_cells = set(tuple(x) for x in s.get("force", []))
                fl.user_cells = set(tuple(x) for x in s.get("user", []))
                fl.algo_cells = set(tuple(x) for x in s.get("algo", []))
            except Exception:
                pass

        self._normalize_all_ige_references()
        self._ensure_layers_defaults_for_all_tests()
        self._active_test_idx = 0 if self.tests else None
        self._sync_layers_panel()
        self._end_edit(commit=False)

        # После успешной корректировки — синяя строка в подвале
        try:
            self._footer_force_live = False
            self.footer_cmd.config(foreground="#0b5ed7")
            self.footer_cmd.config(text="Статическое зондирование откорректировано.")
        except Exception:
            pass

    def _debug_log(self, msg: str):
        if bool(getattr(self, "_debug_layers_overlay", False)):
            try:
                print(f"[DEBUG] {msg}", file=sys.stderr)
            except Exception:
                pass

    def _hatch_debug_log(self, event: str, **payload):
        if not bool(getattr(self, "_debug_hatch", False)):
            return
        try:
            extras = " ".join(f"{k}={payload[k]!r}" for k in sorted(payload))
            print(f"[HATCH] {event} {extras}".rstrip(), file=sys.stderr)
        except Exception:
            pass

    def _tail_debug_log(self, prefix: str, msg: str, *, ti: int | None = None):
        if not bool(getattr(self, "_debug_tail_edit", False)):
            return
        if ti is not None:
            active = getattr(self, "_active_test_idx", None)
            if active is not None and int(active) != int(ti):
                return
        try:
            print(f"[{prefix}] {msg}", file=sys.stderr)
        except Exception:
            pass

    def _is_tail_display_row(self, display_row: int, *, window: int | None = None) -> bool:
        try:
            units = getattr(self, "_grid_units", []) or []
            if not units:
                return False
            w = int(window if window is not None else getattr(self, "_debug_tail_rows", 10) or 10)
            w = max(1, w)
            return int(display_row) >= max(0, len(units) - w)
        except Exception:
            return False

    def _push_undo(self):
        if not self.tests:
            self._sync_layers_panel()
            self._update_scrollregion()
            return
        self.undo_stack.append(self._snapshot())
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self._dirty = True

    def _refresh_after_undo_redo(self) -> None:
        """Bring UI to a fully consistent state after undo/redo."""
        self._rebuild_marks_index()
        self._recompute_statuses_after_data_load(preview_mode=False)

    def undo(self):
        # Если сейчас редактируется ячейка — завершаем редактирование и только потом делаем UNDO
        if getattr(self, '_editing', None):
            try:
                if len(self._editing) >= 4:
                    ti, row, field, e = self._editing[0], self._editing[1], self._editing[2], self._editing[3]
                else:
                    ti, row, field, e = self._editing
                if field == 'depth':
                    self._end_edit_depth0(ti, e, commit=True)
                else:
                    self._end_edit(commit=True)
            except Exception:
                pass
        self._debug_log(f"Undo pressed: undo={len(self.undo_stack)} redo={len(self.redo_stack)}")
        if not self.undo_stack:
            return
        self.redo_stack.append(self._snapshot())
        snap = self.undo_stack.pop()
        self._restore(snap)
        # не затираем статус текстом Undo
        self._footer_force_live = True
        try:
            self._refresh_after_undo_redo()
        except Exception:
            pass
        # После Undo — вернуть красную строку (или серую, если проблем нет)
        try:
            self._set_footer_from_scan()
        except Exception:
            pass


    def redo(self):
        # Если сейчас редактируется ячейка — завершаем редактирование и только потом делаем REDO
        if getattr(self, '_editing', None):
            try:
                if len(self._editing) >= 4:
                    ti, row, field, e = self._editing[0], self._editing[1], self._editing[2], self._editing[3]
                else:
                    ti, row, field, e = self._editing
                if field == 'depth':
                    self._end_edit_depth0(ti, e, commit=True)
                else:
                    self._end_edit(commit=True)
            except Exception:
                pass
        self._debug_log(f"Redo pressed: undo={len(self.undo_stack)} redo={len(self.redo_stack)}")
        if not self.redo_stack:
            return
        self.undo_stack.append(self._snapshot())
        snap = self.redo_stack.pop()
        self._restore(snap)
        # не затираем статус текстом Redo
        self._footer_force_live = True
        try:
            self._refresh_after_undo_redo()
        except Exception:
            pass
        # После Redo — показать актуальную строку по текущему состоянию
        try:
            self._set_footer_from_scan()
        except Exception:
            pass

    def _toggle_show_graphs(self, value: bool | None = None):
        if value is None:
            value = bool(getattr(self, "show_graphs", False))
        self.show_graphs = bool(value)
        try:
            if getattr(self, "_show_graphs_var", None) is not None and bool(self._show_graphs_var.get()) != self.show_graphs:
                self._show_graphs_var.set(self.show_graphs)
        except Exception:
            pass
        try:
            if getattr(self, "ribbon_view", None):
                self.ribbon_view.set_show_graphs(self.show_graphs)
        except Exception:
            pass
        self._build_grid()
        self._redraw()
        self.schedule_graph_redraw()

    def _toggle_show_graphs_from_ui(self):
        self._toggle_show_graphs(bool(getattr(self, "_show_graphs_var", None).get() if getattr(self, "_show_graphs_var", None) is not None else False))

    def _toggle_show_geology_column(self, value: bool | None = None):
        if value is None:
            value = bool(getattr(self, "show_geology_column", True))
        self.show_geology_column = bool(value)
        try:
            if getattr(self, "ribbon_view", None):
                self.ribbon_view.set_show_geology_column(self.show_geology_column)
        except Exception:
            pass
        self._build_grid()
        self._redraw()
        self.schedule_graph_redraw()

    def _toggle_show_layer_colors(self, value: bool | None = None):
        if value is None:
            value = bool(getattr(self, "show_layer_colors", False))
        self.show_layer_colors = bool(value)
        try:
            if getattr(self, "ribbon_view", None):
                self.ribbon_view.set_show_layer_colors(self.show_layer_colors)
        except Exception:
            pass
        self._redraw()
        self.schedule_graph_redraw()

    def _toggle_show_layer_hatching(self, value: bool | None = None):
        if value is None:
            value = bool(getattr(self, "show_layer_hatching", True))
        self.show_layer_hatching = bool(value)
        try:
            if getattr(self, "ribbon_view", None):
                self.ribbon_view.set_show_layer_hatching(self.show_layer_hatching)
        except Exception:
            pass
        self._redraw()
        self.schedule_graph_redraw()

    def _sync_view_ribbon_state(self):
        try:
            rv = getattr(self, "ribbon_view", None)
            if rv is None:
                return
            is_k4 = str(getattr(self, "geo_kind", "K2") or "K2").upper() == "K4"
            if not is_k4:
                self.show_inclinometer = False
            rv.set_show_inclinometer(bool(getattr(self, "show_inclinometer", True)) if is_k4 else False, enabled=is_k4)
        except Exception:
            pass

    def _toggle_show_inclinometer(self, value: bool | None = None):
        is_k4 = str(getattr(self, "geo_kind", "K2") or "K2").upper() == "K4"
        if not is_k4:
            self.show_inclinometer = False
            try:
                if getattr(self, "ribbon_view", None):
                    self.ribbon_view.set_show_inclinometer(False, enabled=False)
            except Exception:
                pass
            return
        if value is None:
            value = bool(getattr(self, "show_inclinometer", True))
        self.show_inclinometer = bool(value)
        try:
            if getattr(self, "ribbon_view", None):
                self.ribbon_view.set_show_inclinometer(self.show_inclinometer, enabled=True)
        except Exception:
            pass
        self._build_grid()
        self._redraw()
        self.schedule_graph_redraw()

    def _set_display_sort_mode(self, mode: str | None):
        mode_norm = str(mode or "date").strip().lower()
        mode_norm = "tid" if mode_norm == "tid" else "date"
        if str(getattr(self, "display_sort_mode", "date")) == mode_norm:
            return
        self.display_sort_mode = mode_norm
        try:
            if getattr(self, "ribbon_view", None):
                self.ribbon_view.set_display_sort_mode(self.display_sort_mode)
        except Exception:
            pass
        self._build_grid()
        self._redraw()
        self.schedule_graph_redraw()

    def _schedule_rebuild_redraw(self):
        prev = getattr(self, "_rebuild_redraw_after_id", None)
        if prev is not None:
            try:
                self.after_cancel(prev)
            except Exception:
                pass
        self._rebuild_redraw_after_id = self.after(60, self._rebuild_redraw_now)

    def _rebuild_redraw_now(self):
        self._rebuild_redraw_after_id = None
        self._build_grid()
        self._redraw()
        self.schedule_graph_redraw()

    def _toggle_compact_1m(self, value: bool | None = None, *, push_undo: bool = True):
        if value is None:
            value = not bool(getattr(self, "compact_1m", False))
        value = bool(value)
        if bool(getattr(self, "compact_1m", False)) == value:
            return
        if push_undo:
            self._push_undo()
        self.compact_1m = value
        # При сворачивании 1 м делаем строку выше, чтобы блоки не были «слишком тонкими».
        self.row_h = int(self.row_h_compact_1m if self.compact_1m else self.row_h_default)
        try:
            if getattr(self, "_compact_1m_var", None) is not None and bool(self._compact_1m_var.get()) != self.compact_1m:
                self._compact_1m_var.set(self.compact_1m)
        except Exception:
            pass
        try:
            if getattr(self, "ribbon_view", None):
                self.ribbon_view.set_compact_1m(self.compact_1m)
        except Exception:
            pass
        # Избегаем визуального «разрыва» между шапкой и данными после смены режима.
        try:
            self.canvas.yview_moveto(0.0)
        except Exception:
            pass
        self._schedule_rebuild_redraw()

    def _toggle_meter_expanded(self, meter_n: int, *, push_undo: bool = True):
        meter_n = int(meter_n)
        if push_undo:
            self._push_undo()
        if meter_n in self.expanded_meters:
            self.expanded_meters.discard(meter_n)
        else:
            self.expanded_meters.add(meter_n)
        self._schedule_rebuild_redraw()

    def _meter_for_display_row(self, display_row: int) -> int | None:
        if not bool(getattr(self, "compact_1m", False)):
            return None
        try:
            units = getattr(self, "_grid_units", []) or []
            if int(display_row) < 0 or int(display_row) >= len(units):
                return None
            unit = units[int(display_row)]
            if not unit:
                return None
            if unit[0] == "meter":
                return int(unit[1])
            if unit[0] == "row":
                base_i = int(unit[1])
                base = getattr(self, "_grid_base", []) or []
                if 0 <= base_i < len(base) and base[base_i] is not None:
                    return int(math.floor(float(base[base_i])))
        except Exception:
            return None
        return None

    def _expanded_meter_for_depth_cell(self, ti: int, display_row: int) -> int | None:
        meter_n = self._meter_for_display_row(int(display_row))
        if meter_n is None:
            return None
        return meter_n if meter_n in (getattr(self, "expanded_meters", set()) or set()) else None

    def _toggle_compact_1m_from_ui(self):
        self._toggle_compact_1m(bool(getattr(self, "_compact_1m_var", None).get() if getattr(self, "_compact_1m_var", None) is not None else False))

    def _toggle_layer_edit_mode(self, value: bool | None = None):
        self.layer_edit_mode = True
        try:
            if getattr(self, "ribbon_view", None):
                self.ribbon_view.set_layer_edit_mode(self.layer_edit_mode)
        except Exception:
            pass
        self.schedule_graph_redraw()

    def _cell_input_max(self) -> int:
        return 1000 if str(getattr(self, "geo_kind", "K2") or "K2").upper() == "K4" else 300

    def _validate_cell_int_key(self, p: str) -> bool:
        if p is None:
            return True
        txt = str(p)
        if txt == "":
            return True
        if not txt.isdigit():
            return False
        try:
            v = int(txt)
        except Exception:
            return False
        return 0 <= v <= int(self._cell_input_max())

    def _sanitize_cell_int(self, s: str) -> str:
        if s is None:
            return ""
        txt = str(s).strip()
        if txt == "":
            return ""
        if not txt.isdigit():
            m = _re__cell.search(r"(\d+)", txt)
            if not m:
                return ""
            txt = m.group(1)
        try:
            v = int(txt)
        except Exception:
            return ""
        if v < 0:
            v = 0
        vmax = int(self._cell_input_max())
        if v > vmax:
            v = vmax
        return str(v)

    def _ige_id_to_num(self, ige_id: str) -> int:
        m = re.search(r"(\d+)", str(ige_id or ""))
        return max(1, int(m.group(1))) if m else 1

    def _ige_default_label(self, ordinal: int) -> str:
        return f"ИГЭ-{max(1, int(ordinal or 1))}"

    def _resolve_existing_ige_id(self, raw_ref: str | None) -> str | None:
        raw = str(raw_ref or "").strip()
        if not raw:
            return None
        if raw in (self.ige_registry or {}):
            return raw
        for ige_id, ent in (self.ige_registry or {}).items():
            for candidate in (
                ent.get("stable_ige_id"),
                ent.get("label"),
                ent.get("display_label"),
                ige_id,
            ):
                if str(candidate or "").strip() == raw:
                    return str(ige_id)
        raw_ord = self._extract_base_ige_num(raw)
        if raw_ord is not None:
            matches = []
            for ige_id, ent in (self.ige_registry or {}).items():
                try:
                    ord_num = int(ent.get("ordinal", self._ige_id_to_num(ige_id)) or self._ige_id_to_num(ige_id))
                except Exception:
                    ord_num = self._ige_id_to_num(ige_id)
                if int(ord_num) == int(raw_ord):
                    matches.append(str(ige_id))
            if len(matches) == 1:
                return matches[0]
        return None

    def _build_ige_display_label(self, ige_id: str, ent: dict[str, object] | None = None) -> str:
        resolved = self._resolve_existing_ige_id(ige_id) or str(ige_id or "").strip() or "ИГЭ-1"
        payload = dict(ent or (self.ige_registry or {}).get(resolved) or {})
        return build_ige_display_label(
            resolved,
            label=str(payload.get("label") or resolved),
            soil_name=str(payload.get("soil_type") or ""),
            soil_code=str(payload.get("soil_code") or ""),
            params=payload,
        )

    def _sync_ige_display_label(self, ige_id: str, ent: dict[str, object] | None = None) -> str:
        resolved = self._resolve_existing_ige_id(ige_id) or str(ige_id or "").strip() or "ИГЭ-1"
        payload = ent if ent is not None else self._ensure_ige_entry(resolved)
        display = self._build_ige_display_label(resolved, payload)
        payload["display_label"] = str(display)
        return str(display)

    def _ige_display_label(self, ige_ref: str | None) -> str:
        resolved = self._resolve_existing_ige_id(ige_ref)
        if resolved is None:
            return str(ige_ref or "").strip() or "ИГЭ-1"
        ent = self._ensure_ige_entry(resolved)
        return self._sync_ige_display_label(resolved, ent)

    def _ensure_ige_identity(self, ige_id: str, ent: dict[str, object]) -> dict[str, object]:
        key = str(ige_id or "").strip() or "ИГЭ-1"
        ord_raw = ent.get("ordinal", None)
        try:
            ord_num = int(ord_raw)
        except Exception:
            ord_num = self._ige_id_to_num(key)
        if ord_num < 1:
            ord_num = 1
        ent["ordinal"] = int(ord_num)
        lbl = str(ent.get("label", "") or "").strip()
        if not lbl:
            lbl = self._ige_default_label(ord_num)
        ent["label"] = lbl
        ent["stable_ige_id"] = key
        ent["display_label"] = str(ent.get("display_label") or lbl)
        return ent

    def _ige_sort_key(self, ige_id: str) -> tuple[int, str]:
        ent = self._ensure_ige_entry(str(ige_id or ""))
        try:
            ord_num = int(ent.get("ordinal", self._ige_id_to_num(ige_id)) or self._ige_id_to_num(ige_id))
        except Exception:
            ord_num = self._ige_id_to_num(ige_id)
        return max(1, ord_num), str(ige_id or "")

    def _extract_base_ige_num(self, raw_name: str) -> int | None:
        name = str(raw_name or "").strip()
        m = re.fullmatch(r"ИГЭ-(\d+)", name)
        if not m:
            return None
        try:
            n = int(m.group(1))
        except Exception:
            return None
        return n if n > 0 else None

    def _used_base_ige_ordinals(self) -> set[int]:
        used: set[int] = set()
        for ige_id in (self.ige_registry or {}).keys():
            ent = self._ensure_ige_entry(str(ige_id or ""))
            for candidate in (str(ent.get("label", "") or "").strip(), str(ige_id or "").strip()):
                num = self._extract_base_ige_num(candidate)
                if num is not None:
                    used.add(int(num))
        return used

    def _next_free_ige_ordinal(self) -> int:
        used = self._used_base_ige_ordinals()
        n = 1
        while n in used:
            n += 1
        return n

    def _layer_ige_id(self, lyr: Layer) -> str:
        ige_id = str(getattr(lyr, "ige_id", "") or "").strip()
        resolved = self._resolve_existing_ige_id(ige_id)
        if resolved:
            ige_id = resolved
            lyr.ige_id = resolved
        if not ige_id:
            ige_id = f"ИГЭ-{int(getattr(lyr, 'ige_num', 1) or 1)}"
            lyr.ige_id = ige_id
        lyr.ige_num = self._ige_id_to_num(ige_id)
        return ige_id

    def _ensure_ige_entry(self, ige_id: str, *, fallback_soil: str | None = None, fallback_mode: str | None = None) -> dict[str, object]:
        key = str(ige_id or "").strip() or "ИГЭ-1"
        resolved = self._resolve_existing_ige_id(key)
        if resolved:
            key = resolved
        ent = self.ige_registry.get(key)
        if ent is None:
            soil_raw = str(fallback_soil or "").strip()
            if soil_raw in (x.value for x in SoilType):
                soil = SoilType(soil_raw)
                mode_raw = calc_mode_for_soil(soil).value
                ent = {"soil_type": soil.value, "calc_mode": mode_raw, "style": dict(SOIL_STYLE.get(soil, {}))}
            else:
                mode_raw = str(fallback_mode or CalcMode.LIMITED.value)
                if mode_raw not in (CalcMode.VALID.value, CalcMode.LIMITED.value):
                    mode_raw = CalcMode.LIMITED.value
                ent = {"soil_type": None, "calc_mode": mode_raw, "style": {}}
            self.ige_registry[key] = ent
        if "lab_phys" not in ent:
            ent["lab_phys"] = {}
        if "cpt_result" not in ent:
            ent["cpt_result"] = None
        self._ensure_ige_identity(key, ent)
        self._ensure_ige_cpt_fields(ent)
        self._sync_ige_display_label(key, ent)
        return ent

    def _ensure_ige_cpt_fields(self, ent: dict[str, object]) -> dict[str, object]:
        ent.setdefault("sand_class", "")
        ent.setdefault("alluvial", True)
        if "saturated" not in ent:
            ent["saturated"] = None
        ent.setdefault("IL", "")
        ent.setdefault("consistency", "")
        ent.setdefault("note", "")
        ent.setdefault("source_flags", {"CPT": True, "LAB": False, "Stamp": False})
        ent.setdefault("sand_kind", "")
        ent.setdefault("sand_water_saturation", "")
        ent.setdefault("density_state", "")
        ent.setdefault("sand_is_alluvial", False)
        ent.setdefault("sandy_loam_kind", "")
        ent.setdefault("notes", "")
        ent.setdefault("fill_subtype", "")
        ent.setdefault("stable_ige_id", "")
        ent.setdefault("display_label", "")
        ent.setdefault("soil_family", "")
        ent.setdefault("is_alluvial", False)
        ent.setdefault("manual_notes", "")
        ent.setdefault("calc_method", "")
        ent.setdefault("calc_status", "")
        ent.setdefault("calc_warning", "")
        ent.setdefault("use_for_auto_calc", False)
        ent.setdefault("requires_manual_confirmation", False)
        return ent

    def _auto_recalculate_cpt(self):
        settings = dict(getattr(self, "cpt_calc_settings", {}) or {})
        calc = CptCalcSettings(
            method=str(settings.get("method") or METHOD_SP446),
            alluvial_sands=bool(settings.get("alluvial_sands", True)),
            groundwater_level=settings.get("groundwater_level"),
        )
        results = calculate_ige_cpt_results(tests=list(self.tests or []), ige_registry=self.ige_registry, settings=calc)
        for ige_id in sorted(self.ige_registry.keys(), key=self._ige_id_to_num):
            self._ensure_ige_entry(ige_id)["cpt_result"] = results.get(ige_id)
        self._sync_layers_panel()

    def _edit_selected_ige_cpt_params(self):
        if not getattr(self, "ribbon_view", None):
            return
        ige_id = str(self.ribbon_view.layer_ige_var.get() or "ИГЭ-1").strip() or "ИГЭ-1"
        ent = self._ensure_ige_cpt_fields(self._ensure_ige_entry(ige_id))
        dlg = tk.Toplevel(self)
        dlg.title(f"Параметры CPT для {ige_id}")
        dlg.transient(self)
        dlg.grab_set()
        frm = ttk.Frame(dlg, padding=10)
        frm.pack(fill="both", expand=True)

        sand_class = tk.StringVar(value=str(ent.get("sand_class") or ""))
        sat_var = tk.BooleanVar(value=bool(ent.get("saturated", False)))
        il_var = tk.StringVar(value=str(ent.get("IL") or ""))
        cons_var = tk.StringVar(value=str(ent.get("consistency") or ""))
        note_var = tk.StringVar(value=str(ent.get("note") or ""))
        sf = dict(ent.get("source_flags") or {})
        src_cpt = tk.BooleanVar(value=bool(sf.get("CPT", True)))
        src_lab = tk.BooleanVar(value=bool(sf.get("LAB", False)))
        src_stamp = tk.BooleanVar(value=bool(sf.get("Stamp", False)))

        sand_class_lbl = ttk.Label(frm, text="sand_class:")
        sand_class_lbl.grid(row=0, column=0, sticky="w")
        sand_class_cb = ttk.Combobox(frm, state="readonly", textvariable=sand_class, width=28, values=["", "крупный", "средней крупности", "мелкий", "пылеватый"])
        sand_class_cb.grid(row=0, column=1, sticky="w")
        sat_chk = ttk.Checkbutton(frm, text="saturated: водонасыщенный", variable=sat_var)
        sat_chk.grid(row=1, column=1, sticky="w")
        il_lbl = ttk.Label(frm, text="IL:")
        il_lbl.grid(row=4, column=0, sticky="w")
        il_ent = ttk.Entry(frm, textvariable=il_var, width=12)
        il_ent.grid(row=4, column=1, sticky="w")
        cons_lbl = ttk.Label(frm, text="консистенция:")
        cons_lbl.grid(row=5, column=0, sticky="w")
        cons_cb = ttk.Combobox(frm, textvariable=cons_var, width=28, values=["", "твердая", "полутвердая", "тугопластичная", "твердый", "полутвердый", "тугопластичный", "пластичная", "текучая"], state="readonly")
        cons_cb.grid(row=5, column=1, sticky="w")
        ttk.Label(frm, text="note:").grid(row=6, column=0, sticky="w")
        ttk.Entry(frm, textvariable=note_var, width=42).grid(row=6, column=1, sticky="w")
        ttk.Label(frm, text="source flags:").grid(row=7, column=0, sticky="w")
        src_frm = ttk.Frame(frm)
        src_frm.grid(row=7, column=1, sticky="w")
        ttk.Checkbutton(src_frm, text="CPT", variable=src_cpt).pack(side="left")
        ttk.Checkbutton(src_frm, text="LAB", variable=src_lab).pack(side="left")
        ttk.Checkbutton(src_frm, text="Stamp", variable=src_stamp).pack(side="left")

        def _soil_group_for_dialog() -> str:
            soil = str(ent.get("soil_type") or "").lower()
            if "пес" in soil:
                return "sand"
            if "супес" in soil or "суглин" in soil or "глин" in soil:
                return "clay"
            return "other"

        def _update_consistency_state(*_args):
            txt = str(il_var.get() or "").strip().replace(",", ".")
            if not txt:
                cons_cb.configure(state="readonly")
                return
            try:
                ilv = float(txt)
            except Exception:
                cons_cb.configure(state="readonly")
                return
            soil = str(ent.get("soil_type") or "").lower()
            if "супес" in soil:
                auto_cons = "твердая" if ilv < 0 else ("пластичная" if ilv <= 1.0 else "текучая")
            elif "глин" in soil and "суглин" not in soil:
                auto_cons = "твердая" if ilv < 0 else ("полутвердая" if ilv <= 0.25 else "тугопластичная")
            else:
                auto_cons = "твердый" if ilv < 0 else ("полутвердый" if ilv <= 0.25 else "тугопластичный")
            cons_var.set(auto_cons)
            cons_cb.configure(state="disabled")

        def _update_visibility(*_args):
            mode = _soil_group_for_dialog()
            sand_on = mode == "sand"
            clay_on = mode == "clay"
            other_on = mode == "other"
            for w in (sand_class_lbl, sand_class_cb, sat_chk):
                if sand_on:
                    w.grid()
                else:
                    w.grid_remove()
            for w in (il_lbl, il_ent, cons_lbl, cons_cb):
                if clay_on:
                    w.grid()
                else:
                    w.grid_remove()
            if other_on:
                src_frm.grid()
            _update_consistency_state()

        il_var.trace_add("write", _update_consistency_state)
        _update_visibility()

        def _save():
            self._push_undo()
            ent["sand_class"] = str(sand_class.get() or "")
            ent["alluvial"] = True
            ent["saturated"] = bool(sat_var.get())
            ent["IL"] = str(il_var.get() or "")
            ent["consistency"] = str(cons_var.get() or "")
            ent["note"] = str(note_var.get() or "")
            ent["source_flags"] = {"CPT": bool(src_cpt.get()), "LAB": bool(src_lab.get()), "Stamp": bool(src_stamp.get())}
            self._auto_recalculate_cpt()
            dlg.destroy()

        btns = ttk.Frame(frm)
        btns.grid(row=8, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(btns, text="Отмена", command=dlg.destroy).pack(side="right")
        ttk.Button(btns, text="Сохранить", command=_save).pack(side="right", padx=(0, 8))
        self.wait_window(dlg)

    def _next_free_ige_id(self) -> str:
        n = self._next_free_ige_ordinal()
        candidate = self._ige_default_label(n)
        if candidate not in (self.ige_registry or {}):
            return candidate
        i = 1
        while f"ige-{n}-{i}" in (self.ige_registry or {}):
            i += 1
        return f"ige-{n}-{i}"

    def _find_unassigned_ige_id(self) -> str | None:
        candidates: list[str] = []
        for ige_id in (self.ige_registry or {}).keys():
            ent = self._ensure_ige_entry(str(ige_id or ""))
            if ent.get("soil_type") is None:
                candidates.append(str(ige_id))
        if not candidates:
            return None
        return sorted(candidates, key=self._ige_sort_key)[0]

    def _ensure_default_iges(self):
        if self.ige_registry:
            return
        has_layer_ige = False
        for t in (self.tests or []):
            for lyr in (getattr(t, "layers", []) or []):
                if str(getattr(lyr, "ige_id", "") or "").strip():
                    has_layer_ige = True
                    break
            if has_layer_ige:
                break
        if has_layer_ige:
            return
        self.ige_registry = {
            "ИГЭ-1": {"soil_type": SoilType.LOAM.value, "calc_mode": calc_mode_for_soil(SoilType.LOAM).value, "style": dict(SOIL_STYLE.get(SoilType.LOAM, {})), "label": "ИГЭ-1", "ordinal": 1},
            "ИГЭ-2": {"soil_type": SoilType.SAND.value, "calc_mode": calc_mode_for_soil(SoilType.SAND).value, "style": dict(SOIL_STYLE.get(SoilType.SAND, {})), "label": "ИГЭ-2", "ordinal": 2},
            "ИГЭ-3": {"soil_type": SoilType.CLAY.value, "calc_mode": calc_mode_for_soil(SoilType.CLAY).value, "style": dict(SOIL_STYLE.get(SoilType.CLAY, {})), "label": "ИГЭ-3", "ordinal": 3},
        }

    def _add_unassigned_ige_from_ribbon(self):
        if len(self.ige_registry or {}) >= MAX_LAYERS_PER_TEST:
            self._set_status("Достигнут лимит 12 ИГЭ")
            return
        self._push_undo()
        new_ord = self._next_free_ige_ordinal()
        new_ige_id = self._next_free_ige_id()
        self.ige_registry[new_ige_id] = self._ensure_ige_cpt_fields({"soil_type": None, "calc_mode": CalcMode.LIMITED.value, "style": {}, "label": self._ige_default_label(new_ord), "ordinal": int(new_ord)})
        self._sync_layers_panel()
        self.schedule_graph_redraw()
        if getattr(self, "ribbon_view", None):
            self.ribbon_view.focus_ige_row(new_ige_id)

    def _apply_ige_to_layer(self, lyr: Layer):
        ige_id = self._layer_ige_id(lyr)
        ent = self._ensure_ige_entry(ige_id, fallback_soil=getattr(lyr, "soil_type", SoilType.SANDY_LOAM).value, fallback_mode=getattr(lyr, "calc_mode", CalcMode.VALID).value)
        soil_raw = str(ent.get("soil_type") or "").strip()
        if soil_raw in (x.value for x in SoilType):
            soil = SoilType(soil_raw)
            mode = calc_mode_for_soil(soil)
            style = dict(SOIL_STYLE.get(soil, {}))
            style.update(dict(ent.get("style") or {}))
            ent["calc_mode"] = mode.value
            ent["soil_type"] = soil.value
            ent["style"] = dict(style)
        else:
            soil = SoilType.SANDY_LOAM
            mode = CalcMode.LIMITED
            style = {}
            ent["soil_type"] = None
            ent["calc_mode"] = mode.value
            ent["style"] = {}
        lyr.soil_type = soil
        lyr.calc_mode = mode
        lyr.style = style

    def _select_ige_for_ribbon(self, ige_id: str):
        if not getattr(self, "ribbon_view", None):
            return
        ent = self._ensure_ige_entry(str(ige_id or "ИГЭ-1"))
        self.ribbon_view.layer_ige_var.set(str(ige_id or "ИГЭ-1"))
        self.ribbon_view.layer_soil_var.set(str(ent.get("soil_type") or ""))
        self.ribbon_view.layer_mode_var.set(str(ent.get("calc_mode") or ""))

    def _on_calc_profile_changed(self, profile_id: str):
        return

    def _on_calc_mode_changed(self, mode: str):
        return

    def _on_calc_option_changed(self, option: str, value):
        key = str(option or "").strip()
        if not key:
            return
        if key == "cpt_method":
            self.calc_tab_state.cpt_method = str(value or "СП 446.1325800.2019 (с Изм. № 1), приложение Ж")
        elif key == "transition_method":
            self.calc_tab_state.transition_method = str(value or "СП 22.13330.2016 (с Изм. № 1–5), п. 5.3.17")
        elif key == "allow_normative_lt6":
            self.calc_tab_state.allow_normative_lt6 = bool(value)
        elif key == "use_legacy_sandy_loam_sp446":
            self.calc_tab_state.use_legacy_sandy_loam_sp446 = bool(value)
        elif key == "allow_fill_preliminary":
            self.calc_tab_state.allow_fill_preliminary = bool(value)

    def _rebuild_calc_samples(self):
        samples = build_ige_samples(
            tests=list(self.tests or []),
            ige_registry=self.ige_registry,
            profile_id="DEFAULT_CURRENT",
            allow_fill_by_material=bool(self.calc_tab_state.allow_fill_preliminary),
            use_legacy_sandy_loam_sp446=bool(self.calc_tab_state.use_legacy_sandy_loam_sp446),
            allow_normative_lt6=bool(self.calc_tab_state.allow_normative_lt6),
        )
        self.calc_samples = samples
        rows = []
        for smp in samples:
            rows.append({
                "ige_id": smp.ige_id,
                "soil_type": str((self.ige_registry.get(smp.ige_id, {}) or {}).get("soil_type", "")),
                "fill_subtype": str((self.ige_registry.get(smp.ige_id, {}) or {}).get("fill_subtype", "")),
                "method": smp.method,
                "status": smp.status,
                "warning": "; ".join(smp.warnings),
                "intervals": [],
                "n_points": smp.stats.n_points,
                "qc_avg": smp.stats.qc_avg_mpa,
                "qc_min": smp.stats.qc_min_mpa,
                "qc_max": smp.stats.qc_max_mpa,
                "V_qc": smp.stats.v_qc,
                "avg_depth": smp.stats.avg_depth_m,
                "fs_avg": smp.stats.fs_avg_kpa,
                "E": smp.result.E_MPa,
                "phi": smp.result.phi_deg,
                "c": smp.result.c_kPa,
            })
        self.calc_rows = rows
        try:
            self.calc_tab_state.last_run_at = _dt.datetime.now().replace(microsecond=0).isoformat()
            self.calc_tab_state.last_trace = [
                {
                    "ige_id": smp.ige_id,
                    "method": smp.method,
                    "status": smp.status,
                    "used_soundings": list(smp.used_sounding_ids or []),
                    "depth_interval": smp.depth_interval,
                    "n_points": smp.stats.n_points,
                    "excluded_count": smp.excluded_count,
                    "warnings": list(smp.warnings or []),
                    "errors": list(smp.errors or []),
                    "missing_fields": list(smp.missing_fields or []),
                }
                for smp in list(samples or [])
            ]
        except Exception:
            pass
        self._sync_calc_table()

    def _run_calc_pipeline(self):
        self._rebuild_calc_samples()
        self._set_status(f"Расчёт: подготовлено ИГЭ {len(self.calc_rows or [])}")

    def _sync_calc_table(self):
        trees = self._calc_trees()
        if not trees:
            return
        rows_to_insert = []
        for row in list(self.calc_rows or []):
            intervals = row.get("intervals") or []
            interval_txt = ""
            if intervals:
                a = min(float(x[1]) for x in intervals)
                b = max(float(x[2]) for x in intervals)
                interval_txt = f"{a:.2f}-{b:.2f}"
            rows_to_insert.append((
                row.get("ige_id", ""),
                row.get("soil_type", ""),
                row.get("fill_subtype", ""),
                row.get("method", ""),
                row.get("status", ""),
                row.get("n_points", 0),
                "" if row.get("qc_avg") is None else f"{float(row['qc_avg']):.3f}",
                "" if row.get("V_qc") is None else f"{float(row['V_qc']):.3f}",
                interval_txt,
                "" if row.get("E") is None else row.get("E"),
                "" if row.get("phi") is None else row.get("phi"),
                "" if row.get("c") is None else row.get("c"),
                row.get("warning", ""),
            ))
        for tree in trees:
            for iid in tree.get_children():
                tree.delete(iid)
            for values in rows_to_insert:
                tree.insert("", "end", values=values)

    def _show_calc_sample_dialog(self):
        if not (self.calc_samples or {}):
            self._rebuild_calc_samples()
        lines = []
        for smp in list(self.calc_samples or []):
            lines.append(f"{smp.ige_id}: n={len(smp.points)}, qc={','.join(f'{p.qc_mpa:.2f}' for p in smp.points[:12])}")
        messagebox.showinfo("Выборки ИГЭ", "\n".join(lines) if lines else "Нет выборок")

    def _show_calc_excluded_dialog(self):
        if not (self.calc_samples or {}):
            self._rebuild_calc_samples()
        lines = []
        for smp in list(self.calc_samples or []):
            if smp.excluded_count:
                reasons = ", ".join(list(smp.exclusions or []))
                lines.append(f"{smp.ige_id}: исключено {smp.excluded_count}" + (f" ({reasons})" if reasons else ""))
        messagebox.showinfo("Исключённые точки", "\n".join(lines) if lines else "Нет исключённых точек")

    def _make_calc_protocol(self):
        if not (self.calc_rows or []):
            self._rebuild_calc_samples()
        self.calc_protocol = build_protocol(
            project_name=str(getattr(self, "object_name", "") or ""),
            profile_id="DEFAULT_CURRENT",
            samples=list(self.calc_samples or []),
        )
        self._set_status("Протокол расчёта сформирован")

    def redraw_all(self):
        self._sync_layers_panel()
        self._redraw()
        self.schedule_graph_redraw()

    def _active_layers_test_index(self) -> int | None:
        if getattr(self, "_active_test_idx", None) is not None:
            return int(self._active_test_idx)
        if getattr(self, "expanded_cols", None):
            return int(self.expanded_cols[0])
        if getattr(self, "display_cols", None):
            return int(self.display_cols[0])
        if getattr(self, "tests", None):
            return 0
        return None

    def _can_add_layer(self, ti: int) -> bool:
        if ti is None or ti < 0 or ti >= len(self.tests):
            return False
        layers = self._ensure_test_layers(self.tests[int(ti)])
        return len(layers) < MAX_LAYERS_PER_TEST

    def _can_delete_layer(self, ti: int) -> bool:
        if ti is None or ti < 0 or ti >= len(self.tests):
            return False
        layers = self._ensure_test_layers(self.tests[int(ti)])
        return len(layers) > MIN_LAYERS_PER_TEST

    def _add_layer_from_ribbon(self):
        ti = self._active_layers_test_index()
        if ti is None:
            return
        if not self._can_add_layer(int(ti)):
            self._set_status("Достигнут лимит 12 слоёв")
            return
        if not self._can_insert_layer_from_bottom(int(ti)):
            self._set_status("Недостаточно мощности для добавления слоя")
            return
        self._push_undo()
        self._insert_layer_from_bottom(int(ti))

    def _delete_layer_by_ige(self, ige_id: str):
        target = str(ige_id or "").strip()
        keys = sorted((self.ige_registry or {}).keys(), key=self._ige_sort_key)
        if target not in keys:
            return
        if len(keys) <= MIN_LAYERS_PER_TEST:
            self._set_status("Нельзя удалить единственный ИГЭ")
            return
        fallback = next((k for k in keys if k != target), keys[0])
        self._push_undo()
        self.ige_registry.pop(target, None)
        for t in (self.tests or []):
            for lyr in self._ensure_test_layers(t):
                if str(getattr(lyr, "ige_id", "") or "").strip() == target:
                    lyr.ige_id = fallback
                    self._apply_ige_to_layer(lyr)
        self._sync_layers_panel()
        self.schedule_graph_redraw()

    def _set_layer_soil_from_ribbon(self, ige_id: str, soil_raw: str):
        ige = str(ige_id or "").strip()
        if not ige:
            return
        soil_text = str(soil_raw or "").strip()
        try:
            soil = SoilType(soil_text)
        except Exception:
            return
        self._push_undo()
        ent = self._ensure_ige_entry(ige)
        ent.update({"soil_type": soil.value, "calc_mode": calc_mode_for_soil(soil).value, "style": dict(SOIL_STYLE.get(soil, {}))})
        self._sync_ige_display_label(ige, ent)
        if soil != SoilType.SAND:
            ent["sand_is_alluvial"] = False
        if soil != SoilType.FILL:
            ent["fill_subtype"] = ""
        for t in (self.tests or []):
            for lyr in self._ensure_test_layers(t):
                if str(getattr(lyr, "ige_id", "") or "").strip() == ige:
                    self._apply_ige_to_layer(lyr)
        self._sync_layers_panel()
        self.schedule_graph_redraw()

    def _rename_ige_from_ribbon(self, old_id: str, new_label: str):
        old_key = self._resolve_existing_ige_id(old_id) or str(old_id or "").strip()
        if not old_key or old_key not in (self.ige_registry or {}):
            return
        ent = self._ensure_ige_entry(old_key)
        lbl = str(new_label or "").strip()
        if not lbl:
            try:
                lbl = self._ige_default_label(int(ent.get("ordinal", self._ige_id_to_num(old_key)) or self._ige_id_to_num(old_key)))
            except Exception:
                lbl = old_key
        if lbl == old_key:
            if str(ent.get("label", old_key) or old_key).strip() != lbl:
                self._push_undo()
                ent["label"] = str(lbl)
                self._sync_ige_display_label(old_key, ent)
                self._sync_layers_panel()
                self.schedule_graph_redraw()
            return
        if self._resolve_existing_ige_id(lbl) not in (None, old_key):
            messagebox.showwarning("Переименование ИГЭ", f"ИГЭ с именем «{lbl}» уже существует.")
            return

        self._push_undo()
        ent["label"] = str(lbl)
        self._sync_ige_display_label(old_key, ent)
        self._normalize_all_ige_references()

        if getattr(self, "ribbon_view", None):
            try:
                self.ribbon_view.layer_ige_var.set(str(old_key))
            except Exception:
                pass
        self._sync_layers_panel()
        self.schedule_graph_redraw()

    def _change_layer_field_from_ribbon(self, ige_id: str, field_name: str, value):
        target = str(ige_id or "").strip()
        field = str(field_name or "").strip()
        if not target or not field:
            return
        ent = self._ensure_ige_entry(target)
        self._push_undo()
        ent[field] = value
        self._sync_ige_display_label(target, ent)
        self._sync_layers_panel()

    def _sync_layers_panel(self):
        self._ensure_default_iges()
        if not getattr(self, "ribbon_view", None):
            return
        keys = sorted((self.ige_registry or {}).keys(), key=self._ige_sort_key)
        rows = []
        for ige_id in keys:
            ent = self._ensure_ige_cpt_fields(self._ensure_ige_entry(ige_id))
            rows.append(
                {
                    "ige_id": str(ige_id),
                    "label": str(self._ige_display_label(ige_id) or ige_id),
                    "visual_order": int(ent.get("ordinal", self._ige_id_to_num(ige_id)) or self._ige_id_to_num(ige_id)),
                    "soil": str(ent.get("soil_type") or ""),
                    "sand_kind": str(ent.get("sand_kind") or ""),
                    "sand_water_saturation": str(ent.get("sand_water_saturation") or ""),
                    "density_state": str(ent.get("density_state") or ""),
                    "sand_is_alluvial": bool(ent.get("sand_is_alluvial", False)),
                    "sandy_loam_kind": str(ent.get("sandy_loam_kind") or ""),
                    "consistency": str(ent.get("consistency") or ""),
                    "fill_subtype": str(ent.get("fill_subtype") or ""),
                    "IL": ent.get("IL", ""),
                    "notes": str(ent.get("notes") or ""),
                }
            )
        self.ribbon_view.set_layers(rows, [x.value for x in SoilType], can_add=(len(keys) < MAX_LAYERS_PER_TEST), can_delete=(len(keys) > MIN_LAYERS_PER_TEST))
        self._sync_calc_table()
        if rows:
            self.ribbon_view.layer_ige_var.set(str(rows[0].get("ige_id") or "ИГЭ-1"))
            self.ribbon_view.layer_soil_var.set(str(rows[0].get("soil") or ""))
            self.ribbon_view.layer_mode_var.set("")

    def _recalc_layers_for_test(self, ti: int, *, push_undo: bool = True) -> bool:
        if ti is None or ti < 0 or ti >= len(self.tests):
            return False
        if push_undo:
            self._push_undo()
        t = self.tests[ti]
        top, bot = self._test_depth_range(t)
        t.layers = build_default_layers(top, bot)
        self._calc_layer_params_for_test(int(ti))
        return True

    def _recalc_layers_active(self):
        ti = self._active_layers_test_index()
        if ti is None:
            return
        if self._recalc_layers_for_test(int(ti), push_undo=True):
            self._sync_layers_panel()
            self._redraw()
            self.schedule_graph_redraw()

    def _recalc_layers_enabled(self):
        targets = [i for i, t in enumerate(self.tests or []) if bool(getattr(t, "export_on", True))]
        if not targets:
            return
        self._push_undo()
        changed = False
        for ti in targets:
            changed = self._recalc_layers_for_test(int(ti), push_undo=False) or changed
        if changed:
            self._sync_layers_panel()
            self._redraw()
            self.schedule_graph_redraw()

    def _edit_ige_from_ribbon(self, ige_raw: str, soil_raw: str, mode_raw: str = ""):
        ige_id = str(ige_raw or "").strip() or "ИГЭ-1"
        self._push_undo()
        base = self._ensure_ige_cpt_fields(self._ensure_ige_entry(ige_id))
        try:
            soil = SoilType(str(soil_raw))
        except Exception:
            self.ige_registry[ige_id] = dict(base)
            self.ige_registry[ige_id].update({"soil_type": None, "calc_mode": CalcMode.LIMITED.value, "style": {}})
            self._sync_ige_display_label(ige_id, self.ige_registry[ige_id])
            for t in (self.tests or []):
                for lyr in self._ensure_test_layers(t):
                    if self._layer_ige_id(lyr) == ige_id:
                        self._apply_ige_to_layer(lyr)
            self._auto_recalculate_cpt()
            self.redraw_all()
            return
        mode = calc_mode_for_soil(soil).value
        base.update({"soil_type": soil.value, "calc_mode": mode, "style": dict(SOIL_STYLE.get(soil, {}))})
        self.ige_registry[ige_id] = base
        self._sync_ige_display_label(ige_id, self.ige_registry[ige_id])
        for t in (self.tests or []):
            for lyr in self._ensure_test_layers(t):
                if self._layer_ige_id(lyr) == ige_id:
                    self._apply_ige_to_layer(lyr)
        self._auto_recalculate_cpt()
        self.redraw_all()

    def _build_ui(self):
        self.ribbon_view = None
        # ========= LEGACY TOP BAR =========
        ribbon = ttk.Frame(self, padding=(10,8))
        if not getattr(self, "use_ribbon_ui", False):
            ribbon.pack(side="top", fill="x")

        # Win11-ish ttk styles
        s = ttk.Style()
        try:
            s.configure("Ribbon.TButton", padding=(14,10))
            s.configure("RibbonAccent.TButton", padding=(14,10))
        except Exception:
            pass

        left = ttk.Frame(ribbon)
        left.pack(side="left", padx=10, pady=8)
        mid = ttk.Frame(ribbon)
        mid.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=8)

        # Текущий файл (перенесено в левую часть ленты)
        self.file_var = tk.StringVar(master=self, value="(не выбран)")
        f_lbl = ttk.Label(mid, textvariable=self.file_var)
        f_lbl.pack(side="left", padx=(0, 10))
        ToolTip(f_lbl, "Текущий файл")
        def make_btn(parent, text, tip, cmd, style="Ribbon.TButton", w=4):
            b = ttk.Button(parent, text=text, command=cmd, style=style, width=w)
            ToolTip(b, tip)
            return b

        # File + history
        make_btn(left, "📂", "Загрузить GEO/GE0 или GXL", self.pick_file_and_load).grid(row=0, column=0, padx=4)
        make_btn(left, "📦", "Экспорт-архив (GEO+GXL+XLSX+CSV CREDO)", self.export_bundle, ).grid(row=0, column=1, padx=4)
        make_btn(left, "↶", "Назад (Undo)", self.undo, ).grid(row=0, column=2, padx=(16, 4))
        make_btn(left, "↷", "Вперёд (Redo)", self.redo, ).grid(row=0, column=3, padx=4)

        # Project map (FILE MAP)
        right = ttk.Frame(ribbon)
        right.pack(side="right", padx=10, pady=8)
        make_btn(right, "Карта", "Показать карту проекта (FILE MAP)", self.show_file_map, w=6).pack(side="right", padx=4)


        # Inputs (скрыты: параметры спрашиваем только при необходимости при открытии GEO)
        self.depth_var = tk.StringVar(master=self, value="")
        self.step_choice = tk.StringVar(master=self, value="")

        self._depth_label = ttk.Label(left, text="Глубина начала, м:")
        self._depth_label.grid(row=0, column=4, padx=(20, 4))
        self._depth_entry = ttk.Entry(left, textvariable=self.depth_var, width=12)
        self._depth_entry.grid(row=0, column=5, padx=4)
        ToolTip(self._depth_entry, "Изменить начальную глубину зондирования")
        ToolTip(self._depth_label, "Изменить начальную глубину зондирования")

        self._step_label = ttk.Label(left, text="Шаг зондирования, см:")
        self._step_label.grid(row=0, column=6, padx=(12, 4))
        self._step_box = ttk.Frame(left)
        self._step_box.grid(row=0, column=7, padx=4)
        self.rb5 = ttk.Radiobutton(self._step_box, text="5", variable=self.step_choice, value="5")
        self.rb10 = ttk.Radiobutton(self._step_box, text="10", variable=self.step_choice, value="10")
        self.rb5.pack(side="left")
        self.rb10.pack(side="left", padx=(8, 0))
        try:
            self.rb5.deselect(); self.rb10.deselect(); self.step_choice.set("")
        except Exception:
            pass
        ToolTip(self._step_box, "Шаг по глубине (см): 5 или 10")

        # Скрываем эти элементы — теперь они появляются только в окне ввода, если данных нет в GEO.
        try:
            self._depth_label.grid_remove()
            self._depth_entry.grid_remove()
            self._step_label.grid_remove()
            self._step_box.grid_remove()
        except Exception:
            pass


        # Action buttons (moved from bottom)
        btns = ttk.Frame(ribbon)
        btns.pack(side="left", padx=16, pady=8)
        self.btn_show = make_btn(btns, "👁", "Показать зондирования (читать GEO)", self.load_and_render, style="RibbonAccent.TButton")
        self.btn_show.grid(row=0, column=0, padx=4)
        try:
            self.btn_show.grid_remove()
        except Exception:
            pass
        make_btn(btns, "🛠", "Корректировка", self.fix_by_algorithm, ).grid(row=0, column=1, padx=4)
        make_btn(btns, "10→5", "Конвертировать шаг 10 см → 5 см", self.convert_10_to_5, w=5).grid(row=0, column=2, padx=4)  
        
        make_btn(btns, "⚙", "Параметры зондирований", self.open_geo_params_dialog, w=3).grid(row=0, column=3, padx=4)
        self._show_graphs_var = tk.BooleanVar(master=self, value=bool(getattr(self, "show_graphs", False)))
        graphs_chk = ttk.Checkbutton(btns, text="Графики", variable=self._show_graphs_var, command=self._toggle_show_graphs_from_ui)
        graphs_chk.grid(row=0, column=4, padx=6)
        ToolTip(graphs_chk, "Показывать графики")
        self._compact_1m_var = tk.BooleanVar(master=self, value=bool(getattr(self, "compact_1m", False)))
        compact_chk = ttk.Checkbutton(btns, text="Свернуть 1 м", variable=self._compact_1m_var, command=self._toggle_compact_1m_from_ui)
        compact_chk.grid(row=0, column=5, padx=6)
        ToolTip(compact_chk, "Свернуть таблицу/графики в интервалы 1 м")
        make_btn(btns, "➕", "Добавить зондирование", self.add_test).grid(row=0, column=6, padx=4)

        # Right: calc params
        right = ttk.Frame(ribbon)
        right.pack(side="right", padx=10, pady=6)

        params = ttk.LabelFrame(right, text="Параметры пересчёта", padding=(10,6))
        params.pack(side="right")

        self.scale_var = tk.StringVar(master=self, value="250")
        self.fcone_var = tk.StringVar(master=self, value="30")
        self.fsleeve_var = tk.StringVar(master=self, value="10")
        self.acon_var = tk.StringVar(master=self, value="10")
        self.asl_var = tk.StringVar(master=self, value="350")
        self.controller_type_var = tk.StringVar(master=self, value="")
        self.probe_type_var = tk.StringVar(master=self, value="")
        self._common_params = self._default_common_params("K2")
        self._apply_common_params_to_ui(self._common_params)

        def p_row(r, c, label, var, tip):
            ttk.Label(params, text=label).grid(row=r, column=c, sticky="w", padx=(8, 4), pady=2)
            ent = ttk.Entry(params, textvariable=var, width=10, validate="key", validatecommand=(self.register(_validate_nonneg_float_key), "%P"))
            ent.grid(row=r, column=c+1, sticky="w", padx=(0, 10), pady=2)
            ToolTip(ent, tip)
            def _sanitize(_ev=None, _v=var):
                s=_v.get().strip()
                if s=='':
                    return
                try:
                    v=float(s.replace(',', '.'))
                except Exception:
                    _v.set('0')
                    return
                if v<0:
                    v=0.0
                if abs(v-round(v))<1e-9:
                    _v.set(str(int(round(v))))
                else:
                    _v.set(str(v).replace('.', ','))
            ent.bind('<FocusOut>', _sanitize)

        p_row(0, 0, "Шкала:", self.scale_var, "Максимум делений прибора (обычно 250)")
        p_row(0, 2, "Aкон (см²):", self.acon_var, "Площадь лба конуса, см²")
        p_row(1, 0, "Fкон (кН):", self.fcone_var, "Макс. усилие по лбу конуса, кН")
        p_row(1, 2, "Aмуф (см²):", self.asl_var, "Площадь боковой поверхности муфты, см²")
        p_row(2, 0, "Fмуф (кН):", self.fsleeve_var, "Макс. усилие по муфте, кН")
        if getattr(self, "use_ribbon_ui", False):
            commands = {
                "undo": self.undo,
                "redo": self.redo,
                "new_project": self.new_project_file,
                "open_project": self.open_project_file,
                "save_project": self.save_project_file,
                "save_project_as": lambda: self.save_project_file(save_as=True),
                "object_name_changed": self._on_object_name_changed,
                "open_geo": lambda: self.pick_file_and_load(forced_ext=".geo"),
                "open_gxl": lambda: self.pick_file_and_load(forced_ext=".gxl"),
                "export_geo": self.save_geo,
                "export_gxl": self.save_gxl,
                "export_excel": self.export_excel,
                "export_credo": self.export_credo_zip,
                "export_archive": self.export_bundle,
                "export_dxf": self.export_dxf,
                "export_cpt_protocol": self.export_cpt_protocol,
                "geo_params": self.open_geo_params_dialog,
                "common_params_changed": self._on_common_params_changed,
                "fix_algo": self.fix_by_algorithm,
                "reduce_step": self.convert_10_to_5,
                "toggle_graphs": self._toggle_show_graphs,
                "toggle_geology_column": self._toggle_show_geology_column,
                "toggle_inclinometer": self._toggle_show_inclinometer,
                "toggle_layer_colors": self._toggle_show_layer_colors,
                "toggle_layer_hatching": self._toggle_show_layer_hatching,
                "toggle_compact_1m": self._toggle_compact_1m,
                "set_display_sort_mode": self._set_display_sort_mode,
                "toggle_layer_edit": self._toggle_layer_edit_mode,
                "edit_ige": self._edit_ige_from_ribbon,
                "select_ige": self._select_ige_for_ribbon,
                "add_ige": self._add_unassigned_ige_from_ribbon,
                "delete_ige": self._delete_layer_by_ige,
                "change_ige_field": self._change_layer_field_from_ribbon,
                "rename_ige": self._rename_ige_from_ribbon,
                "set_layer_soil": self._set_layer_soil_from_ribbon,
                "calc_cpt": self.calculate_cpt_params,
                "edit_ige_cpt": self._edit_selected_ige_cpt_params,
                "apply_calc": lambda: self._redraw(),
                "k2k4_30": lambda: messagebox.showinfo("К2→К4", "Режим 30 МПа будет добавлен в следующем шаге."),
                "k2k4_50": lambda: messagebox.showinfo("К2→К4", "Режим 50 МПа будет добавлен в следующем шаге."),
                "calc_profile_changed": self._on_calc_profile_changed,
                "calc_mode_changed": self._on_calc_mode_changed,
                "calc_option_changed": self._on_calc_option_changed,
                "calc_run": self._run_calc_pipeline,
                "calc_rebuild_samples": self._rebuild_calc_samples,
                "calc_show_sample": self._show_calc_sample_dialog,
                "calc_show_excluded": self._show_calc_excluded_dialog,
                "calc_make_protocol": self._make_calc_protocol,
                "ribbon_tab_changed": self._on_ribbon_tab_changed,
            }
            self.ribbon_view = RibbonView(self, commands=commands, icon_font=_pick_icon_font(11))
            self.ribbon_view.pack(side="top", fill="x")
            self.ribbon_view.set_object_name(self.object_name)
            self.ribbon_view.set_project_type(str(getattr(self, "project_type", "type2_electric")), mode_params=dict(getattr(self, "project_mode_params", {}) or {}))
            self.ribbon_view.set_common_params(self._current_common_params(), geo_kind=str(getattr(self, "geo_kind", "K2")))
            self.ribbon_view.set_show_graphs(bool(getattr(self, "show_graphs", False)))
            self.ribbon_view.set_show_geology_column(bool(getattr(self, "show_geology_column", True)))
            self.ribbon_view.set_show_inclinometer(bool(getattr(self, "show_inclinometer", True)), enabled=(str(getattr(self, "geo_kind", "K2") or "K2").upper() == "K4"))
            self.ribbon_view.set_show_layer_colors(bool(getattr(self, "show_layer_colors", False)))
            self.ribbon_view.set_show_layer_hatching(bool(getattr(self, "show_layer_hatching", True)))
            self.ribbon_view.set_compact_1m(bool(getattr(self, "compact_1m", False)))
            self.ribbon_view.set_display_sort_mode(str(getattr(self, "display_sort_mode", "date")))
            self.ribbon_view.set_layer_edit_mode(True)
            try:
                self.ribbon_view.calc_cpt_method_var.set(str(getattr(self, "calc_tab_state", CalculationTabState()).cpt_method or "СП 446.1325800.2019 (с Изм. № 1), приложение Ж"))
                self.ribbon_view.calc_transition_method_var.set(str(getattr(self, "calc_tab_state", CalculationTabState()).transition_method or "СП 22.13330.2016 (с Изм. № 1–5), п. 5.3.17"))
                self.ribbon_view.calc_allow_normative_lt6_var.set(bool(getattr(self, "calc_tab_state", CalculationTabState()).allow_normative_lt6))
                self.ribbon_view.calc_legacy_sandy_loam_var.set(bool(getattr(self, "calc_tab_state", CalculationTabState()).use_legacy_sandy_loam_sp446))
                self.ribbon_view.calc_fill_preliminary_var.set(bool(getattr(self, "calc_tab_state", CalculationTabState()).allow_fill_preliminary))
            except Exception:
                pass
            ribbon.pack_forget()
            self.after_idle(self._sync_workspace_visibility)
        self._ui_ready_for_mode_validation = True
        # ========= Main canvas (fixed header) =========
        mid = ttk.Frame(self)
        mid.pack(side="top", fill="both", expand=True)

        self.main_workspace = mid
        self.mid = mid  # host for table + hscroll (between table and footer)

        self.calc_workspace = ttk.Frame(self)
        self._build_calc_workspace(self.calc_workspace)
        self.calc_workspace.pack(side="top", fill="both", expand=True)
        self.calc_workspace.pack_forget()

        # Верхняя фиксированная шапка
        self.header_row = ttk.Frame(mid)
        self.header_row.pack(side="top", fill="x")
        self.collapsed_header_spacer = tk.Frame(self.header_row, width=0, bg="white", highlightthickness=0, bd=0)
        self.collapsed_header_spacer.pack(side="left", fill="y")
        self.hcanvas = tk.Canvas(self.header_row, background="white", highlightthickness=0, height=120)
        self.hcanvas.pack(side="left", fill="x", expand=True)
        self.hcanvas_vbar_spacer = ttk.Frame(self.header_row, width=0)
        self.hcanvas_vbar_spacer.pack(side="right", fill="y")

        # Нижняя область с данными (скролл)
        body = ttk.Frame(mid)
        body.pack(side="top", fill="both", expand=True)

        self.vbar = ttk.Scrollbar(body, orient="vertical")
        self.vbar.pack(side="right", fill="y")

        self.collapsed_dock = tk.Canvas(body, background="white", highlightthickness=0, width=0)
        self.collapsed_dock.pack(side="left", fill="y")

        self.canvas = tk.Canvas(
            body, background="white", highlightthickness=0,
            yscrollcommand=self.vbar.set
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        try:
            self.vbar.bind("<Configure>", lambda _e: self._sync_header_vbar_gutter())
        except Exception:
            pass
        try:
            self.after_idle(self._sync_header_vbar_gutter)
        except Exception:
            pass

        def _xview_proxy(*args):
            # ЕДИНАЯ ТОЧКА ЗАПИСИ X — shared helper для body + header.
            self._apply_shared_xview(*args, close_editor=True)

        def _on_xscroll_command(first, last):
            # first/last: доли [0..1] видимой области body canvas.
            try:
                self._shared_x_frac = float(first)
            except Exception:
                pass
            try:
                if hasattr(self, "hscroll"):
                    self.hscroll.set(first, last)
            except Exception:
                pass
            self._debug_header_sync("xscroll_command")

        # назначаем xscrollcommand сразу, а сам hscroll свяжем позже, когда создадим в footer
        self.canvas.configure(xscrollcommand=_on_xscroll_command)
        # Важно: xscrollcommand назначаем ТОЛЬКО на основной canvas.
        # Иначе на самом правом краю могут появляться расхождения фракций и «уезд» шапки.
        # Шапку двигаем синхронно через _xview_proxy / _on_xscroll_command.
        self._xview_proxy = _xview_proxy
        self._on_xscroll_command = _on_xscroll_command

        def _yview_proxy(*args):
            self._end_edit(commit=True)
            try:
                self.canvas.yview(*args)
            except Exception:
                pass
            self._sync_header_body_after_scroll()
        self.vbar.config(command=_yview_proxy)
        # configure/redraw
        self.canvas.bind("<Configure>", lambda _e: self._update_scrollregion())
        self.hcanvas.bind("<Configure>", lambda _e: (self._sync_header_vbar_gutter(), self.hcanvas.configure(width=self.canvas.winfo_width()), self._update_scrollregion()))

        # scrolling and events: таблица
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self._on_mousewheel_linux(-1))
        self.canvas.bind("<Button-5>", lambda e: self._on_mousewheel_linux(1))
        self.canvas.bind("<Double-1>", lambda _e: "break")  # disable dblclick edit
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Control-Button-1>", self._on_right_click)
        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<B1-Motion>", self._on_layer_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_layer_drag_release)
        # глобальный клик вне canvases закрывает редактирование
        self.bind_all("<Button-1>", self._on_global_click, add="+")
        # Навигация стрелками по активным ячейкам (qc/fs)
        for _k in ("<Up>", "<Down>", "<Left>", "<Right>"):
            self.bind(_k, self._on_arrow_key)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", lambda _e: self._set_hover(None))
        self.collapsed_dock.bind("<Button-1>", self._on_left_click)
        self.collapsed_dock.bind("<Motion>", self._on_motion)
        self.collapsed_dock.bind("<Leave>", lambda _e: self._set_hover(None))
        self.collapsed_dock.bind("<MouseWheel>", self._on_collapsed_dock_wheel)
        self.collapsed_dock.bind("<Button-4>", lambda _e: self._on_collapsed_dock_wheel_linux(-1))
        self.collapsed_dock.bind("<Button-5>", lambda _e: self._on_collapsed_dock_wheel_linux(1))

        # события шапки (клики по иконкам/галочке)
        self.hcanvas.bind("<Button-1>", self._on_left_click)
        # супер-фишка: колесо мыши по шапке листает горизонтально
        self.hcanvas.bind("<MouseWheel>", self._on_mousewheel_x)
        self.hcanvas.bind("<Button-4>", lambda e: self._on_mousewheel_linux_x(-1))
        self.hcanvas.bind("<Button-5>", lambda e: self._on_mousewheel_linux_x(1))
        self.hcanvas.bind("<Motion>", self._on_motion)
        self.hcanvas.bind("<Leave>", lambda _e: self._set_hover(None))
        self._ctx_menu = tk.Menu(self, tearoff=0)
        self._ctx_menu.add_command(label="Удалить выше (вкл.)", command=self._ctx_delete_above)
        self._ctx_menu.add_command(label="Удалить ниже (вкл.)", command=self._ctx_delete_below)

        # ========= Footer: команды + легенда цветов =========
        self.footer = ttk.Frame(self, padding=(12, 4))
        self.footer.pack(side="bottom", fill="x")

        # ===== Горизонтальная прокрутка (классический Win/Win11 Scrollbar) =====
        # Требование (по скрину): полоска должна быть ВЫШЕ строки статуса (например: «Добавлена новая зондирование...»),
        # но НИЖЕ таблицы и ВЫШЕ нижнего подвала (легенда/индикаторы).
        #
        # Схема по pack (снизу вверх):
        #   footer (легенда)          — самый низ
        #   status (текстовый статус) — над footer
        #   hscroll_frame             — над status, у нижней кромки таблицы
        #
        # Синхронизация X:
        #   - Scrollbar двигает одновременно canvas (тело) и hcanvas (шапку) через единый прокси self._xview_proxy
        #   - xscrollcommand навешан на оба canvas
        self.hscroll_frame = ttk.Frame(self.mid, padding=(12, 0, 12, 0))
        self.hscroll = ttk.Scrollbar(self.hscroll_frame, orient="horizontal")
        self.hscroll.pack(fill="x")
        try:
            self.hscroll.configure(command=self._xview_proxy)
        except Exception:
            pass
        # супер-фишка: колесо мыши по горизонтальному скроллу листает горизонтально
        try:
            self.hscroll.bind("<MouseWheel>", self._on_mousewheel_x)
            self.hscroll.bind("<Button-4>", lambda e: self._on_mousewheel_linux_x(-1))
            self.hscroll.bind("<Button-5>", lambda e: self._on_mousewheel_linux_x(1))
        except Exception:
            pass
        # по умолчанию скрыт — показываем только когда ширина контента больше видимой области
        self._hscroll_hidden = True

        self.footer_cmd = ttk.Label(
            self.footer,
            text="",
            foreground="#666666",
            cursor="arrow",
        )
        self.footer_cmd.pack(side="left")
        self.footer_cmd.bind("<Button-1>", self._on_footer_click)

        leg = ttk.Frame(self.footer)
        leg.pack(side="right")

        def _leg_item(parent, color: str, text: str):
            box = tk.Label(parent, width=2, height=1, bg=color, relief="solid", bd=1)
            box.pack(side="left", padx=(8, 4), pady=2)
            ttk.Label(parent, text=text).pack(side="left")

        # ЛЕГЕНДА (строго по промту)
        _leg_item(leg, GUI_PURPLE, "исправлено")
        _leg_item(leg, GUI_YELLOW, "отсутствуют значения")
        _leg_item(leg, GUI_GREEN, "откорректировано")
        _leg_item(leg, GUI_RED, "некорректный опыт")

        self.status = ttk.Label(self, text="Готов.", padding=(12, 6))

        # статусная строка — над подвалом
        self.status.pack(side="bottom", fill="x", before=self.footer)

        # горизонтальная полоса прокрутки — СРАЗУ после таблицы (над статусом)
        # по умолчанию скрыта; при показе перепаковываем статус НИЖЕ полосы

        # hscroll живёт ВНУТРИ mid (между таблицей и нижними статус/подвал)
        self.hscroll_frame.pack(side="bottom", fill="x")
        self.hscroll_frame.pack_forget()
    def _on_ribbon_tab_changed(self, tab_title: str = ""):
        self._sync_workspace_visibility(tab_title)

    def _sync_workspace_visibility(self, tab_title: str = ""):
        rv = getattr(self, "ribbon_view", None)
        if not tab_title and rv is not None:
            try:
                tab_title = rv.current_tab_title()
            except Exception:
                tab_title = ""
        is_calc_tab = str(tab_title or "").strip() == "Расчёт"

        workspace = getattr(self, "main_workspace", None)
        if workspace is not None:
            if is_calc_tab:
                if workspace.winfo_manager():
                    workspace.pack_forget()
            else:
                if not workspace.winfo_manager():
                    workspace.pack(side="top", fill="both", expand=True)

        calc_workspace = getattr(self, "calc_workspace", None)
        if calc_workspace is not None:
            if is_calc_tab:
                if not calc_workspace.winfo_manager():
                    calc_workspace.pack(side="top", fill="both", expand=True)
            else:
                if calc_workspace.winfo_manager():
                    calc_workspace.pack_forget()

        footer = getattr(self, "footer", None)
        if footer is not None:
            if is_calc_tab:
                if footer.winfo_manager():
                    footer.pack_forget()
            else:
                if not footer.winfo_manager():
                    footer.pack(side="bottom", fill="x")

        status = getattr(self, "status", None)
        if status is not None:
            if is_calc_tab:
                if status.winfo_manager():
                    status.pack_forget()
            else:
                if not status.winfo_manager():
                    if footer is not None and footer.winfo_manager():
                        status.pack(side="bottom", fill="x", before=footer)
                    else:
                        status.pack(side="bottom", fill="x")

    def _build_calc_workspace(self, parent):
        top = ttk.Frame(parent, padding=(12, 8, 12, 4))
        top.pack(side="top", fill="x")
        ttk.Button(top, text="Рассчитать", command=self._run_calc_pipeline).pack(side="left", padx=(0, 6))
        ttk.Button(top, text="Пересобрать выборки", command=self._rebuild_calc_samples).pack(side="left", padx=6)
        ttk.Button(top, text="Показать выборку ИГЭ", command=self._show_calc_sample_dialog).pack(side="left", padx=6)
        ttk.Button(top, text="Показать исключённые точки", command=self._show_calc_excluded_dialog).pack(side="left", padx=6)

        table_host = ttk.Frame(parent, padding=(12, 0, 12, 8))
        table_host.pack(side="top", fill="both", expand=True)
        cols = ("ige", "soil", "subtype", "method", "status", "n", "qc_avg", "V", "interval", "E", "phi", "c", "warning")
        self.calc_tree_main = ttk.Treeview(table_host, columns=cols, show="headings")
        heads = {
            "ige": "ИГЭ", "soil": "тип", "subtype": "subtype", "method": "метод", "status": "статус", "n": "n",
            "qc_avg": "qc_avg", "V": "V", "interval": "интервал", "E": "E", "phi": "φ", "c": "c", "warning": "предупреждение"
        }
        for c in cols:
            self.calc_tree_main.heading(c, text=heads[c])
            self.calc_tree_main.column(c, width=90, anchor="center", stretch=False)
        self.calc_tree_main.column("warning", width=240, anchor="w", stretch=False)

        xscroll = ttk.Scrollbar(table_host, orient="horizontal", command=self.calc_tree_main.xview)
        yscroll = ttk.Scrollbar(table_host, orient="vertical", command=self.calc_tree_main.yview)
        self.calc_tree_main.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
        self.calc_tree_main.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_host.columnconfigure(0, weight=1)
        table_host.rowconfigure(0, weight=1)

    def _calc_trees(self):
        trees = []
        main_tree = getattr(self, "calc_tree_main", None)
        if main_tree is not None:
            trees.append(main_tree)
        rv = getattr(self, "ribbon_view", None)
        rv_tree = getattr(rv, "calc_tree", None) if rv is not None else None
        if rv_tree is not None:
            trees.append(rv_tree)
        return trees

    def _update_window_title(self):
        pname = str(getattr(self, "project_name", "") or "").strip() or "Новый проект"
        ptype = self._project_type_caption(str(getattr(self, "project_type", "") or "type2_electric"))
        self.title(f"ZondEditor — {pname} — {ptype}")

    @staticmethod
    def _project_type_caption(project_type: str) -> str:
        t = str(project_type or "").strip()
        if t == "type1_mech":
            return "Тип 1"
        if t == "direct_qcfs":
            return "Прямой ввод qc/fs"
        return "Тип 2"

    def _apply_visual_mode_for_project_type(self):
        ptype = str(getattr(self, "project_type", "") or "")
        if ptype in {"type1_mech", "direct_qcfs"}:
            self.show_graphs = False
            self.show_geology_column = False
            self.show_layer_colors = False
            self.show_layer_hatching = False
            self.show_inclinometer = False
        rv = getattr(self, "ribbon_view", None)
        if rv is not None:
            rv.set_show_graphs(bool(getattr(self, "show_graphs", False)))
            rv.set_show_geology_column(bool(getattr(self, "show_geology_column", True)))
            rv.set_show_layer_colors(bool(getattr(self, "show_layer_colors", False)))
            rv.set_show_layer_hatching(bool(getattr(self, "show_layer_hatching", True)))
            rv.set_show_inclinometer(bool(getattr(self, "show_inclinometer", True)), enabled=(str(getattr(self, "geo_kind", "K2") or "K2").upper() == "K4"))

    def _confirm_discard_if_dirty(self) -> bool:
        if not getattr(self, "_dirty", False):
            return True
        ans = messagebox.askyesnocancel("Несохраненные изменения", "Сохранить изменения проекта?")
        if ans is None:
            return False
        if ans:
            ok = self.save_project_file()
            return bool(ok)
        return True

    def pick_file_and_load(self, forced_ext: str | None = None):
        if not self._confirm_discard_if_dirty():
            return
        if forced_ext == ".geo":
            title = "Открыть GEO/GE0"
            fts = [("GEO/GE0", "*.geo *.ge0 *.GEO *.GE0"), ("Все файлы", "*.*")]
        elif forced_ext == ".gxl":
            title = "Открыть GXL"
            fts = [("GXL", "*.gxl *.GXL"), ("Все файлы", "*.*")]
        else:
            title = "Выберите файл GEO/GE0 или GXL"
            fts = [
                ("GeoExplorer GEO / GXL", "*.geo *.ge0 *.GEO *.GE0 *.gxl *.GXL"),
                ("Все файлы", "*.*"),
            ]
        path = filedialog.askopenfilename(title=title, filetypes=fts)
        if not path:
            return
        self.geo_path = Path(path)
        self.file_var.set(str(self.geo_path))
        self.is_gxl = (self.geo_path.suffix.lower() == ".gxl")
        self.loaded_path = str(self.geo_path)
        self.project_path = None
        self.project_name = str(self.geo_path.stem or "Новый проект")
        self.project_type = "type2_electric"
        self.load_and_render()
        try:
            _log_event(self.usage_logger, "OPEN", file=str(self.geo_path))
        except Exception:
            pass
        self._ensure_object_code()
        if getattr(self, "ribbon_view", None):
            self.ribbon_view.set_project_type(self.project_type, mode_params=dict(getattr(self, "project_mode_params", {}) or {}))
        self._update_window_title()

    def _current_start_depth_for_test(self, t) -> float:
        """Текущая начальная глубина опыта из модели (единый источник)."""
        tid = int(getattr(t, "tid", 0) or 0)
        try:
            if getattr(self, "depth0_by_tid", None) and tid in self.depth0_by_tid:
                return float(self.depth0_by_tid[tid])
        except Exception:
            pass
        try:
            d0 = _parse_depth_float((getattr(t, "depth", []) or [""])[0])
            if d0 is not None:
                return float(d0)
        except Exception:
            pass
        return float(getattr(self, "depth_start", 0.0) or 0.0)

    def _set_start_depth_for_test(self, t, depth0: float):
        """Обновляет модель начальной глубины для опыта."""
        tid = int(getattr(t, "tid", 0) or 0)
        try:
            self.depth0_by_tid[int(tid)] = float(depth0)
        except Exception:
            pass

    def _current_step_for_test(self, t) -> float:
        """Текущий шаг опыта из модели (задел под индивидуальный шаг)."""
        tid = int(getattr(t, "tid", 0) or 0)
        try:
            if getattr(self, "step_by_tid", None) and tid in self.step_by_tid:
                return float(self.step_by_tid[tid])
        except Exception:
            pass
        try:
            if getattr(t, "depth", None) and len(t.depth) >= 2:
                d0 = _parse_depth_float(t.depth[0])
                d1 = _parse_depth_float(t.depth[1])
                if d0 is not None and d1 is not None:
                    dv = float(d1 - d0)
                    if dv > 0:
                        return dv
        except Exception:
            pass
        return float(getattr(self, "step_m", 0.1) or 0.1)

    def _set_step_for_test(self, t, step_m: float):
        """Обновляет шаг опыта в модели (tid -> step_m)."""
        tid = int(getattr(t, "tid", 0) or 0)
        try:
            step_f = float(step_m)
            if step_f > 0:
                self.step_by_tid[int(tid)] = step_f
        except Exception:
            pass

    def _default_common_params(self, geo_kind: str | None = None) -> dict[str, str]:
        g = str(geo_kind or getattr(self, "geo_kind", "K2") or "K2").upper()
        if g == "K4":
            return {
                "controller_type": "ТЕСТ-К4М",
                "controller_scale_div": "1000",
                "probe_type": "",
                "cone_kn": "50",
                "sleeve_kn": "10",
                "cone_area_cm2": "10",
                "sleeve_area_cm2": "350",
            }
        return {
            "controller_type": "ТЕСТ-К2М",
            "controller_scale_div": "250",
            "probe_type": "",
            "cone_kn": "30",
            "sleeve_kn": "10",
            "cone_area_cm2": "10",
            "sleeve_area_cm2": "350",
        }

    def _parse_probe_type_values(self, probe_type: str) -> dict[str, str]:
        """Parse probe type like A3/50/20/10/350 [№115]."""
        s = str(probe_type or "").strip()
        s = re.sub(r"\s*\[[^\]]*\]\s*$", "", s)
        m = re.search(r"([A-Za-zА-Яа-я]\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\b", s)
        if not m:
            return {}
        return {
            "probe_type": f"{m.group(1)}/{m.group(2)}/{m.group(3)}/{m.group(4)}/{m.group(5)}",
            "cone_kn": m.group(2),
            "sleeve_kn": m.group(3),
            "cone_area_cm2": m.group(4),
            "sleeve_area_cm2": m.group(5),
        }

    def _apply_common_params_to_ui(self, params: dict[str, str] | None):
        p = dict(params or {})
        if hasattr(self, "controller_type_var"):
            self.controller_type_var.set(str(p.get("controller_type", "") or ""))
        if hasattr(self, "probe_type_var"):
            self.probe_type_var.set(str(p.get("probe_type", "") or ""))
        if hasattr(self, "scale_var"):
            self.scale_var.set(str(p.get("controller_scale_div", "") or ""))
        if hasattr(self, "fcone_var"):
            self.fcone_var.set(str(p.get("cone_kn", "") or ""))
        if hasattr(self, "fsleeve_var"):
            self.fsleeve_var.set(str(p.get("sleeve_kn", "") or ""))
        if hasattr(self, "acon_var"):
            self.acon_var.set(str(p.get("cone_area_cm2", "") or ""))
        if hasattr(self, "asl_var"):
            self.asl_var.set(str(p.get("sleeve_area_cm2", "") or ""))

    def _set_common_params(self, params: dict[str, str] | None, geo_kind: str | None = None):
        merged = self._default_common_params(geo_kind)
        for k, v in dict(params or {}).items():
            if k in merged and str(v or "").strip() != "":
                merged[k] = str(v).strip()
        self._common_params = merged
        self._apply_common_params_to_ui(merged)

    def _extract_sounding_params_from_geo_bytes(self, data: bytes, geo_kind: str) -> dict[str, str]:
        params = self._default_common_params(geo_kind)
        if str(geo_kind).upper() == "K4":
            params["controller_type"] = "ТЕСТ-К4М"
            probe_candidates: list[dict[str, str]] = []
            parsed_scale = ""
            for enc in ("cp1251", "cp866", "latin1"):
                try:
                    txt = data.decode(enc, errors="ignore")
                except Exception:
                    continue
                if not parsed_scale:
                    sm = re.search(r"(?:шкала|scale)\D{0,8}(\d{2,5})", txt, flags=re.IGNORECASE)
                    if sm:
                        parsed_scale = sm.group(1)
                for mm in re.finditer(r"[A-Za-zА-Яа-я]\d+\s*/\s*\d+\s*/\s*\d+\s*/\s*\d+\s*/\s*\d+(?:\s*\[[^\]]+\])?", txt):
                    parsed = self._parse_probe_type_values(mm.group(0).strip())
                    if parsed:
                        probe_candidates.append(parsed)
            if parsed_scale:
                params["controller_scale_div"] = parsed_scale
            else:
                params["controller_scale_div"] = "1000"
            if probe_candidates:
                def _score(c: dict[str, str]) -> tuple[int, int]:
                    try:
                        sa = int(float(str(c.get("sleeve_area_cm2", "0")).replace(",", ".")))
                    except Exception:
                        sa = 0
                    is_valid = 1 if 100 <= sa <= 500 else 0
                    # Для K4/K4M типовая площадь муфты 350 см²: среди валидных
                    # выбираем ближайшее значение, чтобы не хватать мусорные 80/803.
                    return (is_valid, -abs(sa - 350))
                params.update(max(probe_candidates, key=_score))
            else:
                try:
                    starts = __import__("src.zondeditor.io.k4_reader", fromlist=["_k4_find_starts"])._k4_find_starts(data)
                    if starts:
                        p = int(starts[0])
                        cone = int(data[p + 15])
                        sleeve = int(data[p + 16])
                        cone_area = int(data[p + 18])
                        device_no = int(data[p + 14])
                        # В реальных K4 файлах (например ...J1 и ...O1) поле p+19/p+20
                        # даёт 0x0323=803, но это НЕ площадь муфты. Поэтому в fallback
                        # берём площадь муфты из K4M-дефолта (350) и не используем 803.
                        if 1 <= cone <= 500:
                            params["cone_kn"] = str(cone)
                        if 1 <= sleeve <= 500:
                            params["sleeve_kn"] = str(sleeve)
                        if 1 <= cone_area <= 200:
                            params["cone_area_cm2"] = str(cone_area)
                        params["sleeve_area_cm2"] = str(self._default_common_params("K4").get("sleeve_area_cm2", "350"))
                        params["probe_type"] = f"A3/{params['cone_kn']}/{params['sleeve_kn']}/{params['cone_area_cm2']}/{params['sleeve_area_cm2']} [№{device_no}]"
                        params.update(self._parse_probe_type_values(params["probe_type"]))
                except Exception:
                    pass
        return params

    def _apply_sounding_params(self, params: dict[str, str] | None):
        self._set_common_params(params, getattr(self, "geo_kind", "K2"))

    def open_sounding_params_dialog(self):
        """Минимальные параметры зондирования: контроллер/зонд/нагрузки/площади."""
        dlg = tk.Toplevel(self)
        dlg.title("Параметры зондирований")
        dlg.transient(self)
        dlg.grab_set()
        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill="both", expand=True)

        vars_map = {
            "controller_type": tk.StringVar(master=self, value=(self.controller_type_var.get().strip() if hasattr(self, "controller_type_var") else "")),
            "controller_scale_div": tk.StringVar(master=self, value=(self.scale_var.get().strip() if hasattr(self, "scale_var") else "250")),
            "probe_type": tk.StringVar(master=self, value=(self.probe_type_var.get().strip() if hasattr(self, "probe_type_var") else "")),
            "cone_kn": tk.StringVar(master=self, value=(self.fcone_var.get().strip() if hasattr(self, "fcone_var") else "30")),
            "sleeve_kn": tk.StringVar(master=self, value=(self.fsleeve_var.get().strip() if hasattr(self, "fsleeve_var") else "10")),
            "cone_area_cm2": tk.StringVar(master=self, value=(self.acon_var.get().strip() if hasattr(self, "acon_var") else "10")),
            "sleeve_area_cm2": tk.StringVar(master=self, value=(self.asl_var.get().strip() if hasattr(self, "asl_var") else "350")),
        }
        labels = [
            ("Тип контроллера", "controller_type"),
            ("Шкала прибора", "controller_scale_div"),
            ("Тип зонда", "probe_type"),
            ("КН лоб", "cone_kn"),
            ("КН бок", "sleeve_kn"),
            ("Площадь конуса, см²", "cone_area_cm2"),
            ("Площадь муфты, см²", "sleeve_area_cm2"),
        ]
        entries = {}
        for i, (lbl, key) in enumerate(labels):
            ttk.Label(frm, text=lbl).grid(row=i, column=0, sticky="w", padx=(0, 8), pady=2)
            e = ttk.Entry(frm, textvariable=vars_map[key], width=28)
            e.grid(row=i, column=1, sticky="ew", pady=2)
            entries[key] = e
        frm.columnconfigure(1, weight=1)

        if str(getattr(self, "geo_kind", "K2") or "K2").upper() == "K4":
            try:
                entries["controller_scale_div"].configure(state="disabled")
            except Exception:
                pass

        def _on_probe_change(*_):
            parsed = self._parse_probe_type_values(vars_map["probe_type"].get())
            if not parsed:
                return
            vars_map["cone_kn"].set(parsed["cone_kn"])
            vars_map["sleeve_kn"].set(parsed["sleeve_kn"])
            vars_map["cone_area_cm2"].set(parsed["cone_area_cm2"])
            vars_map["sleeve_area_cm2"].set(parsed["sleeve_area_cm2"])

        vars_map["probe_type"].trace_add("write", _on_probe_change)

        btns = ttk.Frame(frm)
        btns.grid(row=len(labels), column=0, columnspan=2, sticky="e", pady=(10, 0))

        def on_ok():
            p = {
                "controller_type": vars_map["controller_type"].get().strip(),
                "controller_scale_div": vars_map["controller_scale_div"].get().strip(),
                "probe_type": vars_map["probe_type"].get().strip(),
                "cone_kn": vars_map["cone_kn"].get().strip(),
                "sleeve_kn": vars_map["sleeve_kn"].get().strip(),
                "cone_area_cm2": vars_map["cone_area_cm2"].get().strip(),
                "sleeve_area_cm2": vars_map["sleeve_area_cm2"].get().strip(),
            }
            self._set_common_params(p, getattr(self, "geo_kind", "K2"))
            try:
                if getattr(self, "ribbon_view", None):
                    self.ribbon_view.set_common_params(self._current_common_params(), geo_kind=str(getattr(self, "geo_kind", "K2")))
                self._redraw()
                self.schedule_graph_redraw()
            except Exception:
                pass
            dlg.destroy()

        ttk.Button(btns, text="Отмена", command=dlg.destroy).pack(side="right")
        ttk.Button(btns, text="OK", command=on_ok).pack(side="right", padx=(0, 8))
        try:
            dlg.bind("<Escape>", lambda _e: dlg.destroy())
            dlg.bind("<Return>", lambda _e: on_ok())
            self._center_child(dlg)
        except Exception:
            pass
        self.wait_window(dlg)

    def _current_common_params(self) -> dict[str, str]:
        return dict(getattr(self, "_common_params", self._default_common_params(getattr(self, "geo_kind", "K2"))))

    def _on_common_params_changed(self, params: dict[str, str] | None = None):
        p = dict(params or {})
        ptype = str(p.pop("project_type", "") or "").strip()
        if ptype:
            self.project_type = ptype
        mode_keys = {k: v for k, v in p.items() if str(k).startswith("mode_")}
        if bool(getattr(self, "_ui_ready_for_mode_validation", False)) and (not bool(getattr(self, "_suspend_type1_param_validation", False))) and mode_keys:
            ptype_cur = str(getattr(self, "project_type", "") or "")
            if ptype_cur == "type1_mech":
                if not self._apply_type1_params(mode_keys):
                    return
            elif ptype_cur == "type2_electric":
                if not self._apply_type2_params(mode_keys):
                    return
            elif ptype_cur == "direct_qcfs":
                if not self._apply_direct_params(mode_keys):
                    return
        if mode_keys:
            self.project_mode_params.update({k: str(v or "").strip() for k, v in mode_keys.items()})
            for k in list(mode_keys):
                p.pop(k, None)
        if str(getattr(self, "geo_kind", "K2") or "K2").upper() == "K4" and "controller_scale_div" in p and str(p.get("controller_scale_div", "")).strip() == "":
            p.pop("controller_scale_div", None)
        self._set_common_params(p, getattr(self, "geo_kind", "K2"))
        self._update_window_title()
        try:
            self.schedule_graph_redraw()
        except Exception:
            pass

    def _show_validation_error_once(self, message: str):
        if bool(getattr(self, "_validation_error_popup_active", False)):
            return
        self._validation_error_popup_active = True
        try:
            messagebox.showerror("Ошибка", str(message or "Некорректные параметры."))
        finally:
            self._validation_error_popup_active = False

    def _sync_mode_step_from_loaded_tests(self):
        if str(getattr(self, "project_type", "") or "") != "type2_electric":
            return
        try:
            step_val = float(getattr(self, "step_m", 0.05) or 0.05)
        except Exception:
            step_val = 0.05
        self.project_mode_params["mode_step_depth"] = f"{step_val:.2f}".rstrip("0").rstrip(".")
        rv = getattr(self, "ribbon_view", None)
        if rv is not None:
            rv.set_project_type("type2_electric", mode_params=dict(getattr(self, "project_mode_params", {}) or {}))

    def _apply_type1_params(self, mode_keys: dict[str, str]) -> bool:
        old_step = str(getattr(self, "project_mode_params", {}).get("mode_step_depth", "0.20") or "0.20")
        old_lob = str(getattr(self, "project_mode_params", {}).get("mode_lob_coeff", "1.00") or "1.00")
        old_tot = str(getattr(self, "project_mode_params", {}).get("mode_total_coeff", "1.00") or "1.00")
        new_step = str(mode_keys.get("mode_step_depth", old_step) or old_step).replace(",", ".").strip()
        new_lob = str(mode_keys.get("mode_lob_coeff", old_lob) or old_lob).replace(",", ".").strip()
        new_tot = str(mode_keys.get("mode_total_coeff", old_tot) or old_tot).replace(",", ".").strip()

        try:
            step_val = round(float(new_step), 3)
        except Exception:
            self._show_validation_error_once("Недопустимый шаг зондирования. Разрешены только значения: 0.1, 0.2, 0.3, 0.4, 0.5 м.")
            self._sync_type1_params_to_ribbon()
            return False
        if step_val not in {0.1, 0.2, 0.3, 0.4, 0.5}:
            self._show_validation_error_once("Недопустимый шаг зондирования. Разрешены только значения: 0.1, 0.2, 0.3, 0.4, 0.5 м.")
            self._sync_type1_params_to_ribbon()
            return False

        def _parse_coeff(txt: str) -> float | None:
            try:
                v = float(txt)
            except Exception:
                return None
            return v

        lob_val = _parse_coeff(new_lob)
        tot_val = _parse_coeff(new_tot)
        if lob_val is None or tot_val is None or not (0.01 <= lob_val <= 5.00) or not (0.01 <= tot_val <= 5.00):
            self._show_validation_error_once("Тарировочный коэффициент должен быть в диапазоне от 0.01 до 5.00.")
            self._sync_type1_params_to_ribbon()
            return False

        if round(step_val, 3) != round(float(old_step), 3):
            self._rebuild_type1_depth_grid(step_val)

        self.project_mode_params["mode_step_depth"] = f"{step_val:.2f}".rstrip("0").rstrip(".")
        self.project_mode_params["mode_lob_coeff"] = f"{lob_val:.2f}".rstrip("0").rstrip(".")
        self.project_mode_params["mode_total_coeff"] = f"{tot_val:.2f}".rstrip("0").rstrip(".")
        self._skip_next_type1_error_popup = False
        self._redraw()
        self.schedule_graph_redraw()
        return True

    def _sync_type1_params_to_ribbon(self):
        rv = getattr(self, "ribbon_view", None)
        if rv is None:
            return
        self._suspend_type1_param_validation = True
        try:
            rv.set_project_type("type1_mech", mode_params=dict(getattr(self, "project_mode_params", {}) or {}))
        finally:
            self._suspend_type1_param_validation = False

    def _apply_direct_params(self, mode_keys: dict[str, str]) -> bool:
        old_step = str(getattr(self, "project_mode_params", {}).get("mode_step_depth", "0.20") or "0.20")
        new_step = str(mode_keys.get("mode_step_depth", old_step) or old_step).replace(",", ".").strip()
        try:
            step_val = round(float(new_step), 3)
        except Exception:
            self._show_validation_error_once("Недопустимый шаг зондирования. Разрешены только значения: 0.1, 0.2, 0.3, 0.4, 0.5 м.")
            self._sync_direct_params_to_ribbon()
            return False
        if step_val not in {0.1, 0.2, 0.3, 0.4, 0.5}:
            self._show_validation_error_once("Недопустимый шаг зондирования. Разрешены только значения: 0.1, 0.2, 0.3, 0.4, 0.5 м.")
            self._sync_direct_params_to_ribbon()
            return False
        if round(step_val, 3) != round(float(old_step), 3):
            self._rebuild_type1_depth_grid(step_val)
        self.project_mode_params["mode_step_depth"] = f"{step_val:.2f}".rstrip("0").rstrip(".")
        self._skip_next_type1_error_popup = False
        self._redraw()
        self.schedule_graph_redraw()
        return True

    def _apply_type2_params(self, mode_keys: dict[str, str]) -> bool:
        old_step = str(getattr(self, "project_mode_params", {}).get("mode_step_depth", "0.05") or "0.05")
        new_step = str(mode_keys.get("mode_step_depth", old_step) or old_step).replace(",", ".").strip()
        try:
            step_val = round(float(new_step), 3)
        except Exception:
            self._show_validation_error_once("Недопустимый шаг зондирования. Для Типа 2 разрешены только значения: 0.05 и 0.10 м.")
            self._sync_type2_params_to_ribbon()
            return False
        if step_val not in {0.05, 0.1}:
            self._show_validation_error_once("Недопустимый шаг зондирования. Для Типа 2 разрешены только значения: 0.05 и 0.10 м.")
            self._sync_type2_params_to_ribbon()
            return False
        is_k4 = str(getattr(self, "geo_kind", "K2") or "K2").upper() == "K4"
        try:
            old_step_val = round(float(old_step), 3)
        except Exception:
            old_step_val = 0.05
        if is_k4 and old_step_val <= 0.05 and step_val > 0.05:
            self._show_validation_error_once("Для K4 запрещено увеличивать шаг с 0.05 до 0.10. Разрешено только 0.10 → 0.05.")
            self._sync_type2_params_to_ribbon()
            return False
        if round(step_val, 3) != round(float(old_step), 3):
            if is_k4 and old_step_val >= 0.1 and step_val == 0.05:
                self.convert_10_to_5()
                self.step_by_tid = {int(getattr(t, "tid", 0) or 0): 0.05 for t in (getattr(self, "tests", []) or [])}
            else:
                self._rebuild_type1_depth_grid(step_val)
        self.project_mode_params["mode_step_depth"] = f"{step_val:.2f}".rstrip("0").rstrip(".")
        self._skip_next_type1_error_popup = False
        self._redraw()
        self.schedule_graph_redraw()
        return True

    def _sync_type2_params_to_ribbon(self):
        rv = getattr(self, "ribbon_view", None)
        if rv is None:
            return
        self._suspend_type1_param_validation = True
        try:
            rv.set_project_type("type2_electric", mode_params=dict(getattr(self, "project_mode_params", {}) or {}))
        finally:
            self._suspend_type1_param_validation = False

    def _sync_direct_params_to_ribbon(self):
        rv = getattr(self, "ribbon_view", None)
        if rv is None:
            return
        self._suspend_type1_param_validation = True
        try:
            rv.set_project_type("direct_qcfs", mode_params=dict(getattr(self, "project_mode_params", {}) or {}))
        finally:
            self._suspend_type1_param_validation = False

    def _rebuild_type1_depth_grid(self, step_val: float):
        start_rows = max(1, int(round(5.0 / float(step_val)))) + 1
        existing_rows = 0
        for t in (getattr(self, "tests", []) or []):
            existing_rows = max(existing_rows, len(getattr(t, "depth", []) or []), len(getattr(t, "qc", []) or []), len(getattr(t, "fs", []) or []))
        rows = max(start_rows, existing_rows)
        depth = [f"{(i * float(step_val)):.2f}" for i in range(rows)]
        for t in (getattr(self, "tests", []) or []):
            t.depth = list(depth)
            t.qc = list(getattr(t, "qc", []) or []) + [""] * max(0, rows - len(getattr(t, "qc", []) or []))
            t.fs = list(getattr(t, "fs", []) or []) + [""] * max(0, rows - len(getattr(t, "fs", []) or []))
            tid = int(getattr(t, "tid", 0) or 0)
            self.depth0_by_tid[tid] = 0.0
            self.step_by_tid[tid] = float(step_val)
        self.step_m = float(step_val)

    def open_geo_params_dialog(self):
        """Открыть окно параметров GEO для текущего файла."""
        if not getattr(self, "tests", None):
            return

        # Перед открытием окна принудительно коммитим активное редактирование
        # (особенно первой глубины), чтобы читать только актуальную модель.
        try:
            if getattr(self, "_editing", None):
                try:
                    if len(self._editing) >= 4:
                        ti, row, field, e = self._editing[0], self._editing[1], self._editing[2], self._editing[3]
                    else:
                        ti, row, field, e = self._editing
                except Exception:
                    ti, row, field, e = None, None, None, None
                if field == "depth" and ti is not None and e is not None:
                    self._end_edit_depth0(int(ti), e, commit=True)
                elif field is not None:
                    self._end_edit(commit=True)
        except Exception:
            pass

        # Снимок для Undo делаем только если пользователь нажмёт OK
        snap = None
        try:
            snap = self._snapshot()
        except Exception:
            snap = None

        ok = False
        try:
            ok = self._prompt_geo_build_params(self.tests, need_depth=True, need_step=True)
        except Exception as e:
            try:
                self._log(f"[geo_params] error: {e}")
            except Exception:
                pass
            ok = False

        if ok:
            try:
                if snap is not None:
                    self.undo_stack.append(snap)
                    if len(self.undo_stack) > 50:
                        self.undo_stack.pop(0)
                    self.redo_stack.clear()
                    self._dirty = True
            except Exception:
                pass
            try:
                self._redraw()
            except Exception:
                pass


    def _parse_depth_step(self):
        if not self.geo_path or not self.geo_path.exists():
            messagebox.showerror("Ошибка", "Сначала выберите файл .GEO/.GE0")
            return None

        dtxt = self.depth_var.get().strip()
        if not dtxt:
            messagebox.showwarning("Внимание", "Укажи начальную глубину (м).")
            return None
        try:
            depth_start = float(dtxt.replace(",", "."))
        except Exception:
            messagebox.showerror("Ошибка", "Некорректная начальная глубина. Пример: 1.5")
            return None

        stxt = self.step_choice.get().strip()
        if not stxt:
            messagebox.showwarning("Внимание", "Выбери шаг (5 или 10 см).")
            return None
        step_cm = int(stxt)
        if step_cm not in (5, 10):
            messagebox.showerror("Ошибка", "Шаг должен быть 5 или 10 см.")
            return None

        step_m = step_cm / 100.0
        return depth_start, step_m


    def _update_status_loaded(self, prefix: str):
        """Обновляет строку статуса подвала (1-я строка): количество опытов + параметры.
        Формат: 'Загружено опытов N шт. параметры: шкала делений 250, Fкон 30кН, Fмуф 10кН, шаг 10см'
        """
        try:
            cp = self._current_common_params()
            scale = str(cp.get("controller_scale_div", "") or "").strip()
            fcone = str(cp.get("cone_kn", "") or "").strip()
            fsleeve = str(cp.get("sleeve_kn", "") or "").strip()
            step = self.step_cm_var.get().strip() if hasattr(self, "step_cm_var") else ""

            parts = []
            if scale:
                parts.append(f"шкала делений {scale}")
            if fcone:
                parts.append(f"Fкон {fcone}кН")
            if fsleeve:
                parts.append(f"Fмуф {fsleeve}кН")
            if step:
                parts.append(f"шаг {step}см")

            tail = (" параметры: " + ", ".join(parts)) if parts else ""
            # status (1-я строка) всегда чёрная — не красим её предупреждениями
            self.status.config(text=prefix + tail)
        except Exception:
            self.status.config(text=prefix)


    def _set_status_loaded(self, prefix: str):
        # alias for legacy calls
        return self._update_status_loaded(prefix)

    def _set_status(self, message: str):
        """Обновить текст основной (верхней) строки статуса."""
        try:
            self.status.config(text=message)
        except Exception:
            pass

    def _normalize_test_lengths(self, t):
        """
        Нормализует длины массивов внутри ОДНОГО опыта:
        - строки с пустой depth считаются удалёнными и выкидываются целиком
        - qc/fs при пустом значении -> "0"
        Гарантия: len(depth)==len(qc)==len(fs) для каждого опыта отдельно.
        """
        depth = list(getattr(t, "depth", []) or [])
        qc    = list(getattr(t, "qc", []) or [])
        fs    = list(getattr(t, "fs", []) or [])

        n = max(len(depth), len(qc), len(fs))
        new_d, new_qc, new_fs = [], [], []

        for i in range(n):
            d = depth[i] if i < len(depth) else ""
            d = (d or "").strip()
            if not d:
                continue  # удалённая/пустая строка

            q = qc[i] if i < len(qc) else "0"
            f = fs[i] if i < len(fs) else "0"

            q = "0" if (q is None or str(q).strip() == "") else str(q)
            f = "0" if (f is None or str(f).strip() == "") else str(f)

            new_d.append(str(d))
            new_qc.append(q)
            new_fs.append(f)

        t.depth = new_d
        t.qc = new_qc
        t.fs = new_fs
        return t


    def _apply_gxl_calibration_from_meta(self, meta_rows: list[dict]):
        """Если в meta_rows есть шкала/тарировки — подставить в поля пересчёта."""
        if not meta_rows:
            return
        kv = {}
        for row in meta_rows:
            try:
                k = str(row.get("key", "")).strip().lower()
                v = str(row.get("value", "")).strip()
                if k:
                    kv[k] = v
            except Exception:
                pass

        upd = {}
        if kv.get("scale"):
            upd["controller_scale_div"] = kv["scale"]
        if kv.get("scaleostria"):
            upd["cone_kn"] = kv["scaleostria"]
        if kv.get("scalemufta"):
            upd["sleeve_kn"] = kv["scalemufta"]
        if upd:
            self._set_common_params(upd, getattr(self, "geo_kind", "K2"))

    def _current_calibration(self):
        return calibration_from_common_params(
            self._current_common_params(),
            geo_kind=str(getattr(self, "geo_kind", "K2") or "K2"),
        )

    def _calc_qc_fs_from_del(self, qc_del: int, fs_del: int) -> tuple[float, float]:
        """Пересчёт делений в qc/fs через единый контур processing.calibration."""
        if str(getattr(self, "project_type", "") or "") == "type1_mech":
            mode = dict(getattr(self, "project_mode_params", {}) or {})
            try:
                k_lob = float(str(mode.get("mode_lob_coeff", "1.0") or "1.0").replace(",", "."))
            except Exception:
                k_lob = 1.0
            try:
                k_tot = float(str(mode.get("mode_total_coeff", "1.0") or "1.0").replace(",", "."))
            except Exception:
                k_tot = 1.0
            qc_raw = float(qc_del or 0)
            qt_raw = float(fs_del or 0)  # в механике второй столбец = Qt (общ)
            qc_val = qc_raw * k_lob
            qt_val = qt_raw * k_tot
            qs_val = max(0.0, qt_val - qc_val)  # Qs = Qt - Qc
            return qc_val, qs_val
        if str(getattr(self, "project_type", "") or "") == "direct_qcfs":
            return float(qc_del or 0), float(fs_del or 0)
        cal = self._current_calibration()
        return calc_qc_fs_from_del(
            qc_del,
            fs_del,
            scale_div=cal.scale_div,
            fcone_kn=cal.fcone_kn,
            fsleeve_kn=cal.fsleeve_kn,
            cone_area_cm2=cal.cone_area_cm2,
            sleeve_area_cm2=cal.sleeve_area_cm2,
        )

    def _prompt_missing_geo_params(self, *, need_depth: bool, need_step: bool) -> bool:
        """Спросить у пользователя недостающие параметры для GEO: h0 (0..4 м) и/или шаг (5/10 см)."""
        dlg = tk.Toplevel(self)
        dlg.title("Параметры зондирования")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)

        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill="both", expand=True)

        try:
            frm.columnconfigure(1, weight=1)
            frm.columnconfigure(2, weight=1)
            frm.columnconfigure(3, weight=1)
            frm.columnconfigure(4, weight=1)
        except Exception:
            pass

        row = 0
        info = ttk.Label(frm, text="В файле GEO отсутствуют (или нулевые) параметры глубины/шага.\nЗаполни недостающие значения.", justify="left")
        info.grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1

        depth_var = tk.StringVar(master=self, value="")
        step_var = tk.StringVar(master=self, value="10")

        if need_depth:
            ttk.Label(frm, text="Начальная глубина h0, м (0..4):").grid(row=row, column=0, sticky="w", pady=(10, 4))
            ent = ttk.Entry(frm, textvariable=depth_var, width=10)
            ent.grid(row=row, column=1, sticky="w", pady=(10, 4))
            row += 1
        else:
            ttk.Label(frm, text=f"Начальная глубина h0, м: {float(getattr(self, 'depth_start', 0.0) or 0.0):g}").grid(row=row, column=0, columnspan=3, sticky="w", pady=(10, 4))
            row += 1

        if need_step:
            ttk.Label(frm, text="Шаг зондирования, см:").grid(row=row, column=0, sticky="w", pady=(6, 4))
            rbfrm = ttk.Frame(frm)
            rbfrm.grid(row=row, column=1, sticky="w", pady=(6, 4))
            ttk.Radiobutton(rbfrm, text="5", value="5", variable=step_var).pack(side="left")
            ttk.Radiobutton(rbfrm, text="10", value="10", variable=step_var).pack(side="left", padx=(10, 0))
            row += 1
        else:
            step_cm = 10 if float(getattr(self, "step_m", 0.10) or 0.10) >= 0.075 else 5
            ttk.Label(frm, text=f"Шаг, см: задан ранее ({step_cm})").grid(row=row, column=0, columnspan=3, sticky="w", pady=(6, 4))
            row += 1

        msg_var = tk.StringVar(master=self, value="")
        ttk.Label(frm, textvariable=msg_var, foreground="#b00020").grid(row=row, column=0, columnspan=3, sticky="w", pady=(6, 0))
        row += 1

        btns = ttk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=3, sticky="e", pady=(12, 0))

        result = {"ok": False}

        def on_ok():
            if need_depth:
                try:
                    h0 = float(depth_var.get().strip().replace(",", "."))
                except Exception:
                    msg_var.set("Некорректная глубина. Пример: 1.2")
                    return
                if not (0.0 <= h0 <= 4.0):
                    msg_var.set("h0 должна быть в диапазоне 0..4 м.")
                    return
                self.depth_start = h0
                self._depth_confirmed = True
                try:
                    self.depth_var.set(f"{h0:g}")
                except Exception:
                    pass

            if need_step:
                st = step_var.get().strip()
                if st not in ("5", "10"):
                    msg_var.set("Выберите шаг 5 или 10 см.")
                    return
                self.step_m = 0.05 if st == "5" else 0.10
                self._step_confirmed = True
                try:
                    self.step_choice.set(st)
                except Exception:
                    pass

            result["ok"] = True
            dlg.destroy()

        def on_cancel():
            dlg.destroy()

        ttk.Button(btns, text="Отмена", command=on_cancel).pack(side="right")
        ttk.Button(btns, text="OK", command=on_ok).pack(side="right", padx=(0, 10))

        try:
            # Enter = OK, Esc = Cancel; focus first field when possible
            if need_depth and 'ent' in locals():
                ent.focus_set()
                ent.bind('<Return>', lambda e: on_ok())
            dlg.bind('<Return>', lambda e: on_ok())
            dlg.bind('<Escape>', lambda e: on_cancel())
        except Exception:
            pass

        self.wait_window(dlg)
        return bool(result["ok"])


    def _prompt_geo_build_params(self, tests_list, *, need_depth: bool, need_step: bool) -> bool:
        """Окно после открытия GEO:
        - по центру рабочей области
        - шаг 10/5 см (по умолчанию 10)
        - общая начальная глубина + кнопка 'Применить ко всем'
        - список опытов: h0 + дата/время + кнопка календаря
        - Enter перескакивает по ячейкам h0
        - кнопка 'Применить ко всем' копирует общую глубину и выбранный шаг во все СЗ
        """
        dlg = tk.Toplevel(self)
        dlg.title("Параметры зондирований")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)

        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill="both", expand=True)

        ntests = len(tests_list or [])
        ttk.Label(frm, text=f"В файле GEO {ntests} опытов статического зондирования.", font=("Segoe UI", 10, "bold"))\
            .grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 8))

        # --- переменные ---
        # шаг (по умолчанию 10 см)
        _sm = float(getattr(self, "step_m", 0.10) or 0.10)
        _default_step = "5" if abs(_sm - 0.05) < 1e-6 else "10"
        step_var = tk.StringVar(master=self, value=_default_step)
        # общая начальная глубина — из текущей модели по загруженным опытам
        try:
            _vals = [float(self._current_start_depth_for_test(t)) for t in (tests_list or [])]
            common_depth0 = float(min(_vals)) if _vals else float(getattr(self, "depth_start", 0.0) or 0.0)
        except Exception:
            common_depth0 = float(getattr(self, "depth_start", 0.0) or 0.0)
        common_var = tk.StringVar(master=self, value=f"{common_depth0:g}")
        # сообщение об ошибке
        msg_var = tk.StringVar(master=self, value="")
        # msg_lbl будет создан ниже, перед кнопками

        r = 1

        # --- шаг ---
        if need_step:
            ttk.Label(frm, text="Шаг, см:").grid(row=r, column=0, sticky="w", padx=(0, 8), pady=2)
            rb_frame = ttk.Frame(frm)
            rb_frame.grid(row=r, column=1, sticky="w", pady=2)
            ttk.Radiobutton(rb_frame, text="10", value="10", variable=step_var).pack(side="left", padx=(0, 10))
            ttk.Radiobutton(rb_frame, text="5", value="5", variable=step_var).pack(side="left")
            r += 1

        # --- общая глубина + apply all ---
        ttk.Label(frm, text="Начальная глубина, м:").grid(row=r, column=0, sticky="w", padx=(0, 8), pady=2)
        common_ent = ttk.Entry(
            frm,
            textvariable=common_var,
            width=10,
            validate="key",
            validatecommand=(dlg.register(_validate_depth_0_4_key), "%P"),
        )
        common_ent.grid(row=r, column=1, sticky="w", pady=2)

        def _on_common_focus_in(_ev=None):
            try:
                v = common_var.get()
                if isinstance(v, str) and v.strip().startswith("("):
                    common_var.set("")
                    common_ent.after(1, lambda: common_ent.select_range(0, "end"))
            except Exception:
                pass

        common_ent.bind("<FocusIn>", _on_common_focus_in)

        apply_all_btn = ttk.Button(frm, text="Применить ко всем")
        apply_all_btn.grid(row=r, column=2, columnspan=3, sticky="w", padx=(12, 0), pady=2)
        r += 1

        ttk.Separator(frm).grid(row=r, column=0, columnspan=5, sticky="ew", pady=(8, 8))
        r += 1

        # --- таблица опытов ---
        table_wrap = ttk.Frame(frm)
        table_wrap.grid(row=r, column=0, columnspan=5, sticky="nsew")
        r += 1

        MAX_VISIBLE = 14
        use_scroll = ntests > MAX_VISIBLE

        if use_scroll:
            canvas = tk.Canvas(table_wrap, height=MAX_VISIBLE * 26, highlightthickness=0)
            ysb = ttk.Scrollbar(table_wrap, orient="vertical", command=canvas.yview)
            inner = ttk.Frame(canvas)
            inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=inner, anchor="nw")
            canvas.configure(yscrollcommand=ysb.set)
            canvas.pack(side="left", fill="both", expand=True)
            ysb.pack(side="right", fill="y")
            table = inner
        else:
            table = table_wrap

        ttk.Label(table, text="Опыт", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Label(table, text="Нач. глубина, м", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w")
        ttk.Label(table, text="Шаг, см", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Label(table, text="Дата/время", font=("Segoe UI", 9, "bold")).grid(row=0, column=3, sticky="w", padx=(12, 0))
        ttk.Label(table, text="УГВ", font=("Segoe UI", 9, "bold")).grid(row=0, column=4, sticky="w", padx=(12, 0))

        row_vars = []   # (t, tid, h0_var, ent, step_var_row, step_ent, dt_var, dt_lbl, gwl_on_var, gwl_var, gwl_ent)
        source_step_by_tid: dict[int, float] = {}
        k4_mode = str(getattr(self, "geo_kind", "K2") or "K2").upper() == "K4"

        def _parse_depth_str(s: str):
            try:
                ss = (s or "").strip().replace(",", ".")
                if ss == "":
                    return None
                return float(ss)
            except Exception:
                return None

        def _current_step_m():
            st = step_var.get().strip()
            return 0.05 if st == "5" else 0.10

        def _norm_dt(val):
            # из файла может прийти datetime, date или строка
            if isinstance(val, _dt.datetime):
                return val
            if isinstance(val, _dt.date):
                return _dt.datetime(val.year, val.month, val.day, 0, 0)
            try:
                if val is None:
                    return None
                return _try_parse_dt(str(val))
            except Exception:
                return None

        def _fmt_dt(dt_obj: _dt.datetime | None) -> str:
            if not dt_obj:
                return "--.--.---- --:--"
            return dt_obj.strftime("%d.%m.%Y %H:%M")

        # дефолт для общих/индивидуальных
        for i, t in enumerate(tests_list or [], start=1):
            tid = int(getattr(t, "tid", 0) or 0)

            ttk.Label(table, text=f"СЗ-{tid}").grid(row=i, column=0, sticky="w", padx=(0, 10), pady=2)

            try:
                init_v = float(self._current_start_depth_for_test(t))
            except Exception:
                init_v = common_depth0

            h0_var = tk.StringVar(master=self, value=f"{init_v:g}")
            ent = ttk.Entry(
                table,
                textvariable=h0_var,
                width=10,
                validate="key",
                validatecommand=(dlg.register(_validate_depth_0_4_key), "%P"),
            )
            ent.grid(row=i, column=1, sticky="w", pady=2)
            try:
                ent._geo_param_entry = True
            except Exception:
                pass

            step_row_m = float(self._current_step_for_test(t))
            source_step_by_tid[int(tid)] = float(step_row_m)
            step_row_cm = int(round(step_row_m * 100.0))
            if step_row_cm <= 0:
                step_row_cm = 10
            step_var_row = tk.StringVar(master=self, value=str(step_row_cm))
            step_ent = ttk.Entry(table, textvariable=step_var_row, width=4)
            step_ent.grid(row=i, column=2, sticky="w", padx=(12, 0), pady=2)

            # дата/время (парсим из файла)
            dt0 = _norm_dt(getattr(t, "dt", None))
            dt_var = tk.StringVar(master=self, value=_fmt_dt(dt0))

            dt_lbl = ttk.Label(table, textvariable=dt_var, foreground="#666666", cursor="hand2")
            dt_lbl.grid(row=i, column=3, sticky="w", padx=(12, 0), pady=2)

            gwl_state = dict((getattr(self, "gwl_by_tid", {}) or {}).get(int(tid), {}) or {})
            gwl_enabled = bool(gwl_state.get("enabled", False))
            gwl_val = gwl_state.get("value", "")
            gwl_on_var = tk.BooleanVar(master=self, value=gwl_enabled)
            gwl_var = tk.StringVar(master=self, value=("" if gwl_val in (None, "") else f"{float(gwl_val):g}"))
            gwl_box = ttk.Frame(table)
            gwl_box.grid(row=i, column=4, sticky="w", padx=(12, 0), pady=2)
            gwl_chk = ttk.Checkbutton(gwl_box, variable=gwl_on_var)
            gwl_chk.pack(side="left", padx=(0, 4))
            gwl_ent = ttk.Entry(gwl_box, textvariable=gwl_var, width=6)
            gwl_ent.pack(side="left")

            def _sync_gwl_state(_ev=None, _on=gwl_on_var, _ent=gwl_ent):
                try:
                    _ent.configure(state=("normal" if bool(_on.get()) else "disabled"))
                except Exception:
                    pass
            gwl_chk.configure(command=_sync_gwl_state)
            _sync_gwl_state()

            row_vars.append((t, tid, h0_var, ent, step_var_row, step_ent, dt_var, dt_lbl, gwl_on_var, gwl_var, gwl_ent))

        def _apply_common_to_all_rows(_ev=None):
            cd = _parse_depth_str(common_var.get())
            if cd is None:
                msg_var.set("Введите корректную общую начальную глубину (например 1.2).")
                return
            if not (0.0 <= cd <= 4.0):
                msg_var.set("Начальная глубина должна быть в диапазоне 0..4 м.")
                return
            step_cm_txt = (step_var.get() or "").strip()
            if step_cm_txt not in ("5", "10"):
                msg_var.set("Выберите шаг 5 или 10 см.")
                return
            for (_t, _tid, h0_var, _ent, step_var_row, _step_ent, _dt_var, _dt_lbl, *_rest) in row_vars:
                h0_var.set(f"{cd:g}")
                step_var_row.set(step_cm_txt)
            msg_var.set("")

        def _sync_master_step_to_rows(*_args):
            step_cm_txt = (step_var.get() or "").strip()
            if step_cm_txt not in ("5", "10"):
                return
            if k4_mode and step_cm_txt == "10":
                for _tid, _src_step in source_step_by_tid.items():
                    if abs(float(_src_step) - 0.05) < 1e-6:
                        msg_var.set("Для K4 нельзя увеличивать шаг с 0.05 до 0.10. Разрешено только 0.10 → 0.05.")
                        try:
                            step_var.set("5")
                        except Exception:
                            pass
                        step_cm_txt = "5"
                        break
            for (_t, _tid, _h0_var, _ent, step_var_row, _step_ent, _dt_var, _dt_lbl, *_rest) in row_vars:
                step_var_row.set(step_cm_txt)

        try:
            apply_all_btn.configure(command=_apply_common_to_all_rows)
        except Exception:
            pass
        try:
            step_var.trace_add("write", _sync_master_step_to_rows)
        except Exception:
            pass

        def _open_dt_calendar(row_tuple):
            t, tid, h0_var, ent, _step_var_row, _step_ent, dt_var, dt_lbl, *_rest = row_tuple
            # подсветка строки на время редактирования
            old = dt_var.get()
            dt_var.set(f"[{old}]")

            cur_dt = _norm_dt(getattr(t, "dt", None))
            cur_date = (cur_dt.date() if cur_dt else _dt.date.today())
            if cur_date > _dt.date.today():
                cur_date = _dt.date.today()

            cd = CalendarDialog(dlg, initial=cur_date, title="Выбор даты")
            self._center_child(cd)
            dlg.wait_window(cd)

            # вернуть подсветку/обновить
            sel = cd.selected
            if sel:
                # сохраняем время из файла, меняем только дату
                if cur_dt:
                    new_dt = _dt.datetime(sel.year, sel.month, sel.day, cur_dt.hour, cur_dt.minute, cur_dt.second)
                else:
                    new_dt = _dt.datetime(sel.year, sel.month, sel.day, 0, 0, 0)
                t.dt = new_dt.strftime("%Y-%m-%d %H:%M:%S")
                dt_var.set(_fmt_dt(new_dt))
            else:
                dt_var.set(old)

        # клик по дате открывает календарь
        for row in row_vars:
            row[7].bind("<Button-1>", lambda e, r=row: _open_dt_calendar(r))
        recompute_busy = False
        def _recompute_common_depth_marker():
            nonlocal recompute_busy
            if recompute_busy:
                return
            recompute_busy = True
            try:
                msg_var.set("")
                vals = []
                for (_t, tid, h0_var, _ent, _step_var_row, _step_ent, _dt_var, _dt_lbl, *_rest) in row_vars:
                    dv = _parse_depth_str(h0_var.get())
                    if dv is None:
                        try:
                            dv = float((getattr(self, "depth0_by_tid", {}) or {}).get(int(tid), self._current_start_depth_for_test(_t)))
                        except Exception:
                            dv = float(self._current_start_depth_for_test(_t))
                    vals.append(float(dv))
                uniq_h0 = sorted({round(float(v), 6) for v in vals})
                cur_txt = (common_var.get() or '').strip()
                cur_can_override = (cur_txt == '' or cur_txt.startswith('('))
                if len(uniq_h0) > 1:
                    if cur_can_override and cur_txt != "(разные)":
                        common_var.set("(разные)")
                elif len(uniq_h0) == 1:
                    v0 = float(uniq_h0[0])
                    if cur_can_override and cur_txt != f"{v0:g}":
                        common_var.set(f"{v0:g}")
            finally:
                recompute_busy = False

        def _make_row_trace(h0_var):
            def _on_row_change(*_):
                _recompute_common_depth_marker()
            h0_var.trace_add("write", _on_row_change)

        for (t, tid, h0_var, ent, step_var_row, step_ent, dt_var, dt_lbl, *_rest) in row_vars:
            _make_row_trace(h0_var)
            ent.bind("<FocusIn>", lambda e, ee=ent: ee.selection_range(0, "end"), add="+")

        # (кнопки календаря убраны: редактирование по клику на дате)

        # Enter = переход к следующей ячейке h0
        def _focus_next(current_index: int):
            nxt = current_index + 1
            if nxt >= len(row_vars):
                on_ok()
                return "break"
            try:
                row_vars[nxt][3].focus_set()
                row_vars[nxt][3].selection_range(0, "end")
            except Exception:
                pass
            return "break"

        for idx, (t, tid, h0_var, ent, step_var_row, step_ent, dt_var, dt_lbl, *_rest) in enumerate(row_vars):
            ent.bind("<Return>", lambda e, k=idx: _focus_next(k))

        # применить начальные состояния
        _recompute_common_depth_marker()
        _sync_master_step_to_rows()

        # --- сообщение об ошибке + кнопки ---
        msg_lbl = ttk.Label(frm, textvariable=msg_var, foreground="#b00020")
        msg_lbl.grid(row=r, column=0, columnspan=5, sticky="w", pady=(8, 0))
        r += 1

        btns = ttk.Frame(frm)
        btns.grid(row=r, column=0, columnspan=5, sticky="e", pady=(12, 0))

        result = {"ok": False}

        def on_ok():
            # шаг
            if need_step:
                st = step_var.get().strip()
                if st not in ("5", "10"):
                    msg_var.set("Выберите шаг 5 или 10 см.")
                    return

            # общая глубина (в шапке может быть число или '(разные)')
            common_txt = (common_var.get() or "").strip()
            cd = _parse_depth_str(common_txt)
            if cd is not None and not (0.0 <= cd <= 4.0):
                msg_var.set("Начальная глубина должна быть в диапазоне 0..4 м.")
                return

            # сохранить общие
            self._depth_confirmed = True

            if need_step:
                self.step_m = 0.05 if step_var.get().strip() == "5" else 0.10
                self._step_confirmed = True

            # индивидуальные h0 — обновляем из текущей модели, не затирая чужие значения дефолтами
            prev_depth0 = dict(getattr(self, "depth0_by_tid", {}) or {})
            new_depth0 = {}
            for (t, tid, h0_var, ent, step_var_row, step_ent, dt_var, dt_lbl, *_rest) in row_vars:
                dv = _parse_depth_str(h0_var.get())
                if dv is None:
                    try:
                        dv = float(prev_depth0.get(int(tid), self._current_start_depth_for_test(t)))
                    except Exception:
                        dv = float(self._current_start_depth_for_test(t))
                if not (0.0 <= dv <= 4.0):
                    msg_var.set(f"СЗ-{tid}: начальная глубина должна быть 0..4 м.")
                    return
                new_depth0[int(tid)] = float(dv)
            self.depth0_by_tid = new_depth0

            # индивидуальный шаг по опытам (см -> м), задел под разный шаг
            try:
                new_step_by_tid = dict(getattr(self, "step_by_tid", {}) or {})
                for (t, tid, _h0_var, _ent, step_var_row, _step_ent, _dt_var, _dt_lbl, *_rest) in row_vars:
                    raw_step = str(step_var_row.get() or "").strip().replace(",", ".")
                    if raw_step == "":
                        step_m_row = float(getattr(self, "step_m", 0.1) or 0.1)
                    else:
                        try:
                            step_cm_row = float(raw_step)
                        except Exception:
                            msg_var.set(f"СЗ-{tid}: шаг должен быть числом (см).")
                            return
                        if step_cm_row <= 0:
                            msg_var.set(f"СЗ-{tid}: шаг должен быть больше 0.")
                            return
                        step_m_row = float(step_cm_row) / 100.0
                    if k4_mode and abs(float(source_step_by_tid.get(int(tid), step_m_row)) - 0.05) < 1e-6 and float(step_m_row) > 0.05:
                        msg_var.set(f"СЗ-{tid}: для K4 нельзя менять шаг 0.05 → 0.10.")
                        return
                    new_step_by_tid[int(tid)] = float(step_m_row)
                    self._set_step_for_test(t, step_m_row)
                self.step_by_tid = new_step_by_tid
            except Exception:
                pass

            # depth_start = минимум по текущим индивидуальным глубинам
            try:
                if self.depth0_by_tid:
                    self.depth_start = float(min(self.depth0_by_tid.values()))
                elif cd is not None:
                    self.depth_start = float(cd)
            except Exception:
                pass

            # обновить построение глубин здесь же (без перезагрузки)
            try:
                step = float(self.step_m or 0.10)
                for (t, tid, h0_var, ent, step_var_row, step_ent, dt_var, dt_lbl, *_rest) in row_vars:
                    d0 = float(self.depth0_by_tid.get(int(tid), float(self.depth_start or 0.0)))
                    step_t = float((getattr(self, "step_by_tid", {}) or {}).get(int(tid), step))
                    if getattr(t, "qc", None) is not None:
                        t.depth = [f"{(d0 + i * step_t):g}" for i in range(len(t.qc))]
                    try:
                        for _ti, _tt in enumerate(self.tests):
                            if int(getattr(_tt, "tid", 0) or 0) == int(tid):
                                self._sync_layers_to_test_depth_range(int(_ti))
                                break
                    except Exception:
                        pass
            except Exception:
                pass

            # обновим поля панели, если есть
            try:
                self.depth_var.set(f"{cd:g}")
            except Exception:
                pass
            try:
                if need_step:
                    self.step_choice.set(step_var.get().strip())
            except Exception:
                pass

            # УГВ по опытам (задел для будущего отображения в колонках/ползунке)
            try:
                new_gwl = dict(getattr(self, "gwl_by_tid", {}) or {})
                for (_t, tid, _h0_var, _ent, _step_var_row, _step_ent, _dt_var, _dt_lbl, gwl_on_var, gwl_var, _gwl_ent) in row_vars:
                    enabled = bool(gwl_on_var.get())
                    raw = str(gwl_var.get() or "").strip().replace(",", ".")
                    gval = None
                    if enabled and raw != "":
                        try:
                            gval = float(raw)
                        except Exception:
                            msg_var.set(f"СЗ-{tid}: УГВ должен быть числом (например 2.5).")
                            return
                    new_gwl[int(tid)] = {"enabled": enabled, "value": gval}
                self.gwl_by_tid = new_gwl
            except Exception:
                pass

            result["ok"] = True
            dlg.destroy()

        def on_cancel():
            dlg.destroy()

        ttk.Button(btns, text="Отмена", command=on_cancel).pack(side="right")
        ttk.Button(btns, text="OK", command=on_ok).pack(side="right", padx=(0, 10))

        try:
            dlg.bind("<Escape>", lambda e: on_cancel())
            # Enter = OK, но если курсор в ячейках начальной глубины — оставляем их логику (переход по Enter)
            def _on_dlg_return(e):
                w = None
                try:
                    w = dlg.focus_get()
                except Exception:
                    w = None
                if getattr(w, "_geo_param_entry", False):
                    return
                on_ok()
                return "break"
            dlg.bind("<Return>", _on_dlg_return)

            common_ent.focus_set()
            common_ent.selection_range(0, "end")
        except Exception:
            pass

        try:
            dlg.update_idletasks()
            self._center_child(dlg)
        except Exception:
            pass

        self.wait_window(dlg)
        return bool(result["ok"])
    def _set_geo_inputs_enabled(self, enabled: bool):
        # H0 and step controls are required only for GEO/GE0, not for GXL.
        state = "normal" if enabled else "disabled"
        for attr in ("h0_entry", "rb5", "rb10"):
            w = getattr(self, attr, None)
            if w is not None:
                try:
                    w.config(state=state)
                except Exception:
                    pass
        for attr in ("h0_label", "step_label"):
            w = getattr(self, attr, None)
            if w is not None:
                try:
                    w.config(fg="#333333" if enabled else "#888888")
                except Exception:
                    pass

    def _depth_at(self, idx: int) -> float:
        return round(float(self.depth_start) + idx * float(self.step_m), 4)

    def _apply_open_file_view_defaults(self):
        """Defaults for opened files: expanded view, graphs/geology columns off."""
        self.show_graphs = False
        self.show_geology_column = False
        self.show_layer_colors = False
        self.show_layer_hatching = True
        self.compact_1m = False
        self.expanded_meters = set()
        self.row_h = int(self.row_h_default)
        try:
            if getattr(self, "_show_graphs_var", None) is not None:
                self._show_graphs_var.set(False)
        except Exception:
            pass
        try:
            if getattr(self, "ribbon_view", None):
                self.ribbon_view.set_show_graphs(False)
                self.ribbon_view.set_show_geology_column(False)
                self.ribbon_view.set_show_layer_colors(False)
                self.ribbon_view.set_show_layer_hatching(bool(getattr(self, "show_layer_hatching", True)))
                self.ribbon_view.set_compact_1m(False)
        except Exception:
            pass

    def load_and_render(self):

            if not self.geo_path:

                messagebox.showwarning("Нет файла", "Сначала выбери файл.")

                return


            if getattr(self, "is_gxl", False) or self.geo_path.suffix.lower() == ".gxl":

                try:

                    series_list = load_gxl(self.geo_path)
                    tests_list = [TestData(
                        tid=s.test_id, dt=s.dt,
                        depth=[f"{r.depth_m:g}" for r in s.rows],
                        qc=[str(int(r.qc_raw)) for r in s.rows],
                        fs=[str(int(r.fs_raw)) for r in s.rows],
                        incl=[str(int(r.u_raw)) for r in s.rows] if any(int(r.u_raw) != 0 for r in s.rows) else None,
                        marker=getattr(s, "marker", ""),
                        header_pos=getattr(s, "header_pos", ""),
                        orig_id=getattr(s, "orig_id", None),
                        block=getattr(s, "block", None),
                    ) for s in series_list]
                    meta_rows = []
                    self.loaded_path = str(self.geo_path)
                    self.is_gxl = True
                    self.geo_kind = "K4" if any(getattr(t, "incl", None) for t in tests_list) else "K2"
                    self._set_common_params({}, self.geo_kind)
                    self._geo_template_blocks_info = []
                    self._geo_template_blocks_info_full = []
                    self.original_bytes = None

                except GxlParseError as e:

                    messagebox.showerror("Неподдерживаемый GXL", str(e))

                    return

                except Exception as e:

                    messagebox.showerror("Ошибка чтения GXL", str(e))

                    return


                self.meta_rows = meta_rows

                self.flags.clear()

                self.tests.clear()


                if tests_list:

                    self.depth_start = _parse_depth_float(tests_list[0].depth[0]) or 0.0

                    if len(tests_list[0].depth) >= 2:

                        d0 = _parse_depth_float(tests_list[0].depth[0])

                        d1 = _parse_depth_float(tests_list[0].depth[1])

                        self.step_m = (d1 - d0) if (d0 is not None and d1 is not None) else 0.05

                    else:

                        self.step_m = 0.05

                else:

                    self.depth_start = 0.0

                    self.step_m = 0.05


                for t in tests_list:

                    self.tests.append(t)

                    self.flags[t.tid] = TestFlags(False, set(), set(), set(), set())


                self._end_edit(commit=False)
                self._apply_open_file_view_defaults()

                self._ensure_layers_defaults_for_all_tests()
                self._active_test_idx = 0 if self.tests else None
                self._sync_layers_panel()
                self._redraw()

                self.undo_stack.clear()

                self.redo_stack.clear()

                self._apply_gxl_calibration_from_meta(meta_rows)
                self._set_common_params(self._current_common_params(), self.geo_kind)
                self._sync_mode_step_from_loaded_tests()
                if getattr(self, "ribbon_view", None):
                    self.ribbon_view.set_common_params(self._current_common_params(), geo_kind=str(self.geo_kind))
                self._update_status_loaded(prefix=f"GXL: загружено опытов {len(self.tests)}")

                self._auto_scan_after_load()

                return
            # GEO/GE0: читаем и разбираем без требований к параметрам
            try:
                data = self.geo_path.read_bytes()
                self.loaded_path = str(self.geo_path)
                self.is_gxl = False
                self.original_bytes = data
                series_list = load_geo(self.geo_path)
                tests_list = [TestData(
                    tid=s.test_id, dt=s.dt,
                    depth=[f"{r.depth_m:g}" for r in s.rows],
                    qc=[str(int(r.qc_raw)) for r in s.rows],
                    fs=[str(int(r.fs_raw)) for r in s.rows],
                    incl=[str(int(r.u_raw)) for r in s.rows] if any(int(r.u_raw) != 0 for r in s.rows) else None,
                    marker=getattr(s, "marker", ""),
                    header_pos=getattr(s, "header_pos", ""),
                    orig_id=getattr(s, "orig_id", None),
                    block=getattr(s, "block", None),
                ) for s in series_list]
                _tests2, meta_rows, self.geo_kind = parse_geo_bytes(data)
                self._set_common_params({}, self.geo_kind)
                try:
                    self._apply_sounding_params(self._extract_sounding_params_from_geo_bytes(data, self.geo_kind))
                    if getattr(self, "ribbon_view", None):
                        self.ribbon_view.set_common_params(self._current_common_params(), geo_kind=str(self.geo_kind))
                except Exception:
                    pass
                # store template blocks (do not depend on current edited/deleted tests)
                self._geo_template_blocks_info = [t.block for t in tests_list if getattr(t, 'block', None)]
                self._geo_template_blocks_info_full = list(self._geo_template_blocks_info)

            except GeoParseError as e:
                messagebox.showerror("Неподдерживаемый GEO/GE0", str(e))
                return

            except Exception as e:
                messagebox.showerror("Ошибка чтения", str(e))
                return


            # GEO/GE0: параметры глубины/шага
            # K2: в GEO/GE0 обычно нет надёжных параметров — считаем неизвестными и спрашиваем у пользователя.
            # K4: start/step уже зашиты в шапке опыта (marker) и depths уже посчитаны парсером.
            if getattr(self, "geo_kind", "K2") == "K4" and tests_list:
                # Попробуем восстановить шаг/начальную глубину для внутренних нужд UI (без диалогов)
                try:
                    d0 = _parse_depth_float(tests_list[0].depth[0]) or 0.0
                    d1 = _parse_depth_float(tests_list[0].depth[1]) if len(tests_list[0].depth) > 1 else None
                    self.depth_start = float(d0)
                    self.step_m = float(d1 - d0) if (d1 is not None and d0 is not None) else 0.05
                except Exception:
                    self.depth_start = 0.0
                    self.step_m = 0.05
                self._depth_confirmed = True
                self._step_confirmed = True
            else:
                self.depth_start = 0.0
                self.step_m = None
                self._depth_confirmed = False
                self._step_confirmed = False

            # Параметры глубины/шага в K2 GEO могут отсутствовать.
            # Если глубина отсутствует или равна 0 — просим указать в диапазоне 0..4 м.
            need_depth = (getattr(self, "depth_start", None) is None) or ((not getattr(self, "_depth_confirmed", False)) and (float(getattr(self, "depth_start", 0.0) or 0.0) == 0.0))
            # Если шаг отсутствует — предлагаем 5 или 10 см.
            need_step = (getattr(self, "step_m", None) is None) or (not getattr(self, "_step_confirmed", False))

            # K4: start/step уже зашиты в самом файле (marker), и глубины мы уже посчитали в parse_k4_geo_strict().
            # Поэтому диалог "Параметры GEO" не показываем.
            if getattr(self, "geo_kind", "K2") == "K4":
                need_depth = False
                need_step = False
                self._depth_confirmed = True
                self._step_confirmed = True

            if need_depth or need_step:
                ok = self._prompt_geo_build_params(tests_list, need_depth=need_depth, need_step=need_step)
                if not ok:
                    return

            self.meta_rows = meta_rows
            self.flags.clear()
            self.tests.clear()

            step = float(self.step_m or 0.05)
            for t in tests_list:
                # K4: depth уже рассчитана парсером (start/step из шапки опыта).
                if getattr(self, "geo_kind", "K2") != "K4":
                    tid = int(getattr(t, "tid", 0) or 0)
                    d0 = float(self.depth0_by_tid.get(tid, float(self.depth_start or 0.0)))
                    t.depth = [f"{(d0 + i * step):g}" for i in range(len(t.qc))]
                # K4: сохраним начальную глубину и дату/время для окна «Параметры GEO»
                try:
                    if getattr(self, "geo_kind", "K2") == "K4" and getattr(t, "depth", None):
                        self.depth0_by_tid[int(t.tid)] = float(_parse_depth_float(t.depth[0]) or 0.0)
                        if getattr(t, "dt", None):
                            self.dt_by_tid[int(t.tid)] = str(t.dt)
                except Exception:
                    pass
                self.tests.append(t)
                self.flags[t.tid] = TestFlags(False, set(), set(), set(), set())

            self._end_edit(commit=False)
            self._apply_open_file_view_defaults()
            self._ensure_layers_defaults_for_all_tests()
            self._active_test_idx = 0 if self.tests else None
            self._sync_layers_panel()
            self._redraw()
            self.undo_stack.clear()
            self.redo_stack.clear()

            self._sync_mode_step_from_loaded_tests()
            self._update_status_loaded(prefix=f"GEO: загружено опытов {len(self.tests)}")

            self._auto_scan_after_load()
            return


            try:

                data = self.geo_path.read_bytes()

                self.original_bytes = data

                tests_list, meta_rows = parse_geo_with_blocks(data, TestData, GeoBlockInfo)
                # store template blocks (do not depend on current edited/deleted tests)
                self._geo_template_blocks_info = [t.block for t in tests_list if getattr(t, 'block', None)]
                self._geo_template_blocks_info_full = list(self._geo_template_blocks_info)


            except Exception as e:

                messagebox.showerror("Ошибка чтения", str(e))

                return


            self.meta_rows = meta_rows

            self.flags.clear()

            self.tests.clear()


            step = float(self.step_m or 0.05)
            for t in tests_list:
                tid = int(getattr(t, "tid", 0) or 0)
                d0 = float(self.depth0_by_tid.get(tid, float(self.depth_start or 0.0)))
                t.depth = [f"{(d0 + i * step):g}" for i in range(len(t.qc))]

                self.tests.append(t)

                self.flags[t.tid] = TestFlags(False, set(), set(), set(), set())


            self._end_edit(commit=False)

            self._redraw()

            self.undo_stack.clear()

            self.redo_stack.clear()

            self._update_status_loaded(f"Загружено опытов {len(self.tests)} шт.")


    def _scan_by_algorithm(self, preview_mode: bool = True):
        """Скан-проверка: подсветить, но не менять значения (qc/fs).
        Возвращает сводку (dict) и обновляет self.flags для подсветки.
        """
        summary = {
            "tests_total": 0,
            "tests_invalid": 0,
            "cells_interp": 0,
            "cells_missing": 0,
        }
        if not self.tests:
            return summary

        self._algo_preview_mode = bool(preview_mode)
        summary["tests_total"] = len([t for t in self.tests if bool(getattr(t, "export_on", True))])

        for t in self.tests:
            tid = t.tid
            prev = self.flags.get(tid) or TestFlags(False, set(), set(), set(), set())
            user_cells = set(getattr(prev, "user_cells", set()) or set())
            interp_cells = set(getattr(prev, "interp_cells", set()) or set())
            force_cells = set(getattr(prev, "force_cells", set()) or set())

            if not bool(getattr(t, "export_on", True)):
                self.flags[tid] = TestFlags(False, interp_cells, force_cells, user_cells, set())
                continue

            qc = [(_parse_cell_int(v) or 0) for v in t.qc]
            fs = [(_parse_cell_int(v) or 0) for v in t.fs]

            try:
                for i0 in range(min(len(qc), len(fs))):
                    if qc[i0] == 0 and (i0, "qc") not in user_cells:
                        summary["cells_missing"] += 1
                    if fs[i0] == 0 and (i0, "fs") not in user_cells:
                        summary["cells_missing"] += 1
            except Exception:
                pass

            invalid = (_max_zero_run(qc) > 5) or (_max_zero_run(fs) > 5)
            if invalid:
                self.flags[tid] = TestFlags(True, interp_cells, force_cells, user_cells, set())
                summary["tests_invalid"] += 1
                continue

            def mark_short_zero_runs(arr, kind):
                n = len(arr)
                i = 0
                while i < n:
                    if arr[i] != 0:
                        i += 1
                        continue
                    j = i
                    while j < n and arr[j] == 0:
                        j += 1
                    gap = j - i
                    if 1 <= gap <= 5:
                        for k in range(gap):
                            cell = (i + k, kind)
                            if cell not in user_cells and cell not in interp_cells:
                                interp_cells.add(cell)
                                summary["cells_interp"] += 1
                    i = j

            mark_short_zero_runs(qc, "qc")
            mark_short_zero_runs(fs, "fs")

            prev_algo_cells = set(getattr(prev, 'algo_cells', set()) or set())
            self.flags[tid] = TestFlags(False, interp_cells, force_cells, user_cells, prev_algo_cells)

        self._redraw()
        try:
            report = self._diagnostics_report()
            summary["tests_total"] = int(report.tests_total)
            summary["tests_invalid"] = int(report.tests_invalid)
            summary["cells_missing"] = int(report.cells_missing)
            summary["cells_interp"] = int(report.cells_interp)
        except Exception:
            pass
        return summary

    def _set_footer_from_scan(self):
        """Поставить НИЖНЮЮ строку (footer_cmd) по текущей автопроверке.
        Важно: всегда перезаписывает цвет (красный/серый), чтобы не оставалось синего после отката.
        """
        try:
            self._scan_by_algorithm()
            self._update_footer_realtime()
        except Exception:
            pass

    def _diagnostics_report(self):
        return evaluate_diagnostics(
            list(getattr(self, "tests", []) or []),
            getattr(self, "flags", {}) or {},
        )

    @staticmethod
    def _footer_text_from_report(report) -> str:
        parts = []
        if int(getattr(report, "tests_invalid", 0) or 0):
            parts.append(f"Некорректный опыт {int(report.tests_invalid)}")
        if int(getattr(report, "cells_missing", 0) or 0):
            parts.append(f"отсутствуют значения {int(report.cells_missing)}")
        return ", ".join(parts)

    def _compute_footer_realtime(self):
        """Пересчитать нижнюю строку (в реальном времени) из единого диагностического отчёта."""
        try:
            report = self._diagnostics_report()
            return {"inv": int(report.tests_invalid), "miss": int(report.cells_missing)}
        except Exception:
            return {"inv": 0, "miss": 0}

    def _header_fill_for_test(self, *, invalid: bool, has_missing: bool, export_on: bool) -> str:
        if invalid:
            return GUI_RED if export_on else "#f4b6b0"  # muted red
        if has_missing:
            return GUI_ORANGE if export_on else "#ffd8aa"  # muted orange
        return GUI_HDR if export_on else "#f2f2f2"

    def _collect_error_protocol_items(self) -> list[dict]:
        items: list[dict] = []
        tests_by_tid = {int(getattr(t, "tid", 0) or 0): t for t in (getattr(self, "tests", []) or [])}

        def _depth_text(t: Any, row: int) -> str:
            d = self._safe_depth_m(t, row)
            if d is None:
                return "-"
            return f"{float(d):.2f} м"

        report = self._diagnostics_report()
        for entry in report.protocol_entries:
            if not isinstance(entry, ProtocolEntry):
                continue
            t = tests_by_tid.get(int(entry.test_id))
            if t is None:
                continue
            if entry.type == "invalid_zero_run":
                d0 = _depth_text(t, int(entry.row))
                d1 = _depth_text(t, int(entry.row_end))
                text = f"Опыт {entry.test_id} — некорректный: нули более 5 раз подряд, интервал {d0}–{d1}"
            elif entry.type == "missing_qc":
                text = f"Опыт {entry.test_id}, глубина {_depth_text(t, int(entry.row))} — отсутствует значение qc"
            elif entry.type == "missing_fs":
                text = f"Опыт {entry.test_id}, глубина {_depth_text(t, int(entry.row))} — отсутствует значение fs"
            else:
                text = f"Опыт {entry.test_id} — опыт помечен как некорректный по дополнительной диагностике"
            items.append({
                "test_id": int(entry.test_id),
                "row": int(entry.row),
                "type": str(entry.type),
                "text": text,
            })

        items.sort(key=lambda x: (int(x.get("test_id", 0) or 0), int(x.get("row", 0) or 0), str(x.get("type") or "")))
        return items

    def _show_error_protocol_dialog(self):
        items = self._collect_error_protocol_items()
        if not items:
            messagebox.showinfo("Протокол ошибок", "Ошибок не найдено.")
            return

        dlg = tk.Toplevel(self)
        dlg.title("Протокол ошибок зондирования")
        dlg.transient(self)
        dlg.grab_set()
        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=f"Найдено записей: {len(items)}", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))
        box = tk.Text(frm, width=110, height=min(24, max(10, len(items) + 2)), wrap="word")
        box.pack(fill="both", expand=True)
        box.insert("1.0", "\n".join(f"• {it.get('text','')}" for it in items))
        box.config(state="disabled")
        ttk.Button(frm, text="Закрыть", command=dlg.destroy).pack(anchor="e", pady=(8, 0))

    def _on_footer_click(self, _event=None):
        try:
            self._show_error_protocol_dialog()
        except Exception:
            pass

    def _update_footer_realtime(self):
        """Обновить нижнюю строку (красная/серая) по текущему состоянию."""
        try:
            report = self._diagnostics_report()
            msg = self._footer_text_from_report(report)
            if not msg:
                try:
                    self.footer_cmd.config(foreground="#0b5ed7")
                except Exception:
                    pass
                self.footer_cmd.config(text="Статическое зондирование откорректировано.")
                try:
                    self.footer_cmd.config(cursor="arrow")
                except Exception:
                    pass
                return
            try:
                self.footer_cmd.config(foreground="#8B0000")
            except Exception:
                pass
            self.footer_cmd.config(text=msg)
            try:
                self.footer_cmd.config(cursor="hand2")
            except Exception:
                pass
        except Exception:
            pass

    def _footer_live_tick(self):
        """Таймер: держит нижнюю строку актуальной при удалениях/ручных правках."""
        try:
            if getattr(self, "_footer_force_live", True):
                self._update_footer_realtime()
        except Exception:
            pass
        try:
            self.after(350, self._footer_live_tick)
        except Exception:
            pass

    def _auto_scan_after_load(self):
        """Автопроверка при открытии: подсветить (бледно), без изменений, без всплывающих окон.
        Пишет сводку в подвал (status).
        """
        try:
            info = self._scan_by_algorithm()
            bad = (info.get("tests_invalid", 0) + info.get("cells_interp", 0) + info.get("cells_missing", 0))
            if bad <= 0:
                self._algo_preview_mode = False
                self._redraw()
                self.footer_cmd.config(text="")
                try:
                    self.footer_cmd.config(cursor="arrow")
                except Exception:
                    pass
                return

            self._algo_preview_mode = True
            self._redraw()

            report = self._diagnostics_report()
            msg = self._footer_text_from_report(report)
            self.footer_cmd.config(text=msg)
            try:
                self.footer_cmd.config(cursor=("hand2" if msg else "arrow"))
            except Exception:
                pass
            try:
                self.footer_cmd.config(foreground=("#8B0000" if msg else "#666666"))
            except Exception:
                pass
        except Exception:
            self._algo_preview_mode = False

    def add_test(self):
        """
        Добавление нового зондирования через диалог:
        - Номер (по порядку)
        - Дата/время (по умолчанию: сегодня, +10 минут, секунды случайные; в поле секунды не показываем)
        - Начальная глубина (по умолчанию: наиболее частое стартовое значение среди опытов)
        - Конечная глубина (по умолчанию: последнее значение глубины последнего опыта)
        OK / Enter — подтвердить, Esc — отмена.
        """
        if self.depth_start is None or self.step_m is None:
            messagebox.showwarning("Внимание", "Сначала загрузите зондирования (чтобы была задана глубина/шаг).")
            return
        if not self.tests:
            messagebox.showwarning("Внимание", "Сначала нажмите «Показать зондирования».")
            return

        def _f(v):
            try:
                return float(str(v).replace(",", ".").strip())
            except Exception:
                return None

        def _mode_start_depth():
            # Берём первое валидное значение глубины из каждого опыта и выбираем самое частое
            counts = {}
            for t in self.tests:
                d = None
                for x in (getattr(t, "depth", []) or []):
                    if str(x).strip() == "":
                        continue
                    d = _f(x)
                    if d is not None:
                        break
                if d is None:
                    # fallback на depth0_by_tid, если есть
                    d = _f(self.depth0_by_tid.get(getattr(t, "tid", None), None)) if getattr(self, "depth0_by_tid", None) else None
                if d is None:
                    continue
                # округлим до миллиметра, чтобы не плодить почти-одинаковые ключи
                k = round(d, 3)
                counts[k] = counts.get(k, 0) + 1
            if not counts:
                return float(self.depth_start or 0.0)
            # max по частоте, при равенстве — минимальная глубина
            best = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            return float(best)

        def _last_end_depth():
            # Последнее валидное значение глубины из последнего опыта
            t = self.tests[-1]
            arr = getattr(t, "depth", []) or []
            for x in reversed(arr):
                if str(x).strip() == "":
                    continue
                d = _f(x)
                if d is not None:
                    return float(d)
            # fallback: старт + шаг * (len-1)
            step = float(self.step_m or 0.05)
            d0 = _mode_start_depth()
            n = max(1, len(getattr(t, "depth", []) or []))
            return float(d0 + step * (n - 1))

        # defaults
        new_id = (max((t.tid for t in self.tests), default=0) + 1)
        d0_default = _mode_start_depth()
        d1_default = _last_end_depth()
        if d1_default < d0_default:
            d1_default = d0_default

        now_dt = _dt.datetime.now().replace(microsecond=0)
        dt_default_dt = (now_dt + _dt.timedelta(minutes=10)).replace(second=random.randint(0, 59))
        dt_default_str = dt_default_dt.strftime("%Y-%m-%d %H:%M")  # в поле без секунд

        # ---- dialog ----
        dlg = tk.Toplevel(self)
        dlg.title("Добавить зондирование")
        dlg.transient(self)
        dlg.grab_set()

        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill="both", expand=True)

        def _row(r, label, var):
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", pady=4)
            e = ttk.Entry(frm, textvariable=var, width=24)
            e.grid(row=r, column=1, sticky="we", pady=4)
            return e

        frm.columnconfigure(1, weight=1)

        
        v_id = tk.StringVar(master=self, value=str(new_id))

        # Раздельно: дата (с календарём) + время (HH:MM). Секунды НЕ показываем, но сохраняем (случайные).
        v_date = tk.StringVar(master=self, value=dt_default_dt.strftime("%Y-%m-%d"))
        v_time = tk.StringVar(master=self, value=dt_default_dt.strftime("%H:%M"))

        v_d0 = tk.StringVar(master=self, value=f"{d0_default:g}")
        v_d1 = tk.StringVar(master=self, value=f"{d1_default:g}")

        e_id = _row(0, "Номер:", v_id)


        def _open_calendar(_evt=None):
            # Используем уже реализованный CalendarDialog (с подсветкой выбранной даты и запретом будущих дат)
            try:
                s = (v_date.get() or "").strip()
                cur_date = None
                for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
                    try:
                        cur_date = _dt.datetime.strptime(s, fmt).date()
                        break
                    except Exception:
                        pass
                if cur_date is None:
                    cur_date = _dt.date.today()
                if cur_date > _dt.date.today():
                    cur_date = _dt.date.today()

                cd = CalendarDialog(dlg, initial=cur_date, title="Выбор даты")
                self._center_child(cd)
                dlg.wait_window(cd)
                sel = getattr(cd, "selected", None)
                if sel:
                    v_date.set(sel.strftime("%Y-%m-%d"))
            except Exception:
                pass

        # --- Date row with calendar ---
        ttk.Label(frm, text="Дата:").grid(row=1, column=0, sticky="w", pady=4)
        date_row = ttk.Frame(frm)
        date_row.grid(row=1, column=1, sticky="we", pady=4)
        date_row.columnconfigure(0, weight=1)
        e_date = ttk.Entry(date_row, textvariable=v_date, width=14)
        e_date.grid(row=0, column=0, sticky="we")
        btn_cal = ttk.Button(date_row, text="📅", width=3)
        btn_cal.grid(row=0, column=1, padx=(6, 0))
        btn_cal.config(command=_open_calendar)

        ttk.Label(frm, text="Время (HH:MM):").grid(row=2, column=0, sticky="w", pady=4)
        e_time = ttk.Entry(frm, textvariable=v_time, width=10)
        e_time.grid(row=2, column=1, sticky="w", pady=4)

        e_d0 = _row(3, "Начальная глубина, м:", v_d0)
        e_d1 = _row(4, "Конечная глубина, м:", v_d1)

        btns = ttk.Frame(frm)
        btns.grid(row=5, column=0, columnspan=2, sticky="e", pady=(10, 0))

        result = {"ok": False}

        def _parse_date_time(date_s: str, time_s: str):
            date_s = (date_s or '').strip()
            time_s = (time_s or '').strip()
            # допускаем ввод даты как YYYY-MM-DD или DD.MM.YYYY
            d = None
            for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d.%m.%y'):
                try:
                    d = _dt.datetime.strptime(date_s, fmt).date()
                    break
                except Exception:
                    pass
            if d is None:
                return None
            # время HH:MM
            t = None
            for fmt in ('%H:%M',):
                try:
                    t = _dt.datetime.strptime(time_s, fmt).time()
                    break
                except Exception:
                    pass
            if t is None:
                return None
            return _dt.datetime.combine(d, t)

        def _ok(_evt=None):
            tid = None
            try:
                tid = int(v_id.get().strip())
            except Exception:
                messagebox.showwarning("Ошибка", "Номер должен быть целым числом.", parent=dlg)
                return
            if tid <= 0:
                messagebox.showwarning("Ошибка", "Номер должен быть > 0.", parent=dlg)
                return

            # запрет коллизий по tid
            existing_ids = {t.tid for t in self.tests}
            if tid in existing_ids:
                messagebox.showwarning("Ошибка", f"Зондирование №{tid} уже существует.", parent=dlg)
                return

            d0 = _f(v_d0.get())
            d1 = _f(v_d1.get())
            if d0 is None or d1 is None:
                messagebox.showwarning("Ошибка", "Глубины должны быть числами.", parent=dlg)
                return
            if d1 < d0:
                d0, d1 = d1, d0  # автоматически поменяем местами

            dt_user = _parse_date_time(v_date.get(), v_time.get())
            if dt_user is None:
                messagebox.showwarning("Ошибка", "Введите дату и время. Дата: YYYY-MM-DD (или DD.MM.YYYY), время: HH:MM.", parent=dlg)
                return
            # секунды всегда генерируем случайно (в поле не показываем)
            dt_user = dt_user.replace(second=random.randint(0, 59), microsecond=0)

            result.update(ok=True, tid=tid, d0=float(d0), d1=float(d1), dt=dt_user)
            dlg.destroy()

        def _cancel(_evt=None):
            dlg.destroy()


        ttk.Button(btns, text="Отмена", command=_cancel).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text="OK", command=_ok).pack(side="right")

        dlg.bind("<Return>", _ok)
        dlg.bind("<Escape>", _cancel)

        dlg.update_idletasks()
        try:
            self._center_child(dlg)
        except Exception:
            pass

        dlg.minsize(dlg.winfo_width(), dlg.winfo_height())
        e_id.focus_set()
        e_id.selection_range(0, "end")

        self.wait_window(dlg)
        if not result.get("ok"):
            return

        # ---- apply ----
        self._push_undo()

        tid = int(result["tid"])
        d0 = float(result["d0"])
        d1 = float(result["d1"])
        dt_val = result["dt"]

        # сохраняем стартовую глубину для опыта
        self.depth0_by_tid[int(tid)] = d0

        step = float(self.step_m or 0.05)
        n = int(round((d1 - d0) / step)) + 1
        n = max(1, n)

        depth = [f"{(d0 + i * step):g}" for i in range(n)]
        qc = ["0"] * n
        fs = ["0"] * n

        now = dt_val.strftime("%Y-%m-%d %H:%M:%S")

        # вставляем по времени (у тебя везде логика: показывать по времени)
        new_test = TestData(tid=tid, dt=now, depth=depth, qc=qc, fs=fs, orig_id=None, block=None)

        def _parse_dt_any(s):
            try:
                return _dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
            except Exception:
                try:
                    return _dt.datetime.strptime(s, "%Y-%m-%d %H:%M")
                except Exception:
                    return None

        insert_at = len(self.tests)
        new_dt_cmp = _parse_dt_any(now) or _dt.datetime.max
        for i, t in enumerate(self.tests):
            td = _parse_dt_any(getattr(t, "dt", "") or "")
            if td is None:
                continue
            if td > new_dt_cmp:
                insert_at = i
                break

        self.tests.insert(insert_at, new_test)
        self.flags[tid] = TestFlags(False, set(), set(), set(), set())

        self._end_edit(commit=False)
        self._active_test_idx = insert_at
        self._redraw()
        self.schedule_graph_redraw()

        # Механика автопрокрутки как при копировании:
        # если добавленное зондирование не помещается — прокручиваем по X к нему,
        # при этом используем _xview_proxy, чтобы шапка и тело оставались синхронны.
        try:
            self.update_idletasks()
        except Exception:
            pass

        def _scroll_to_new():
            try:
                self._ensure_cell_visible(insert_at, 0, 'depth', pad=12)
            except Exception:
                try:
                    self._xview_proxy("moveto", 1.0)
                except Exception:
                    pass

        try:
            self.after_idle(_scroll_to_new)
        except Exception:
            _scroll_to_new()
        self.status.config(text=f"Добавлена новая зондирование {tid}. (В GEO-сохранение не попадёт — только Excel)")

        try:
            self._set_footer_from_scan()
        except Exception:
            pass

    # ---------------- conversion 10cm -> 5cm ----------------
    def convert_10_to_5(self):
        # 10см -> 5см: вставляем промежуточную строку ТОЛЬКО между двумя валидными соседними строками.
        # Пустые/удаленные строки не трогаем и не заполняем.
        if not self.tests:
            messagebox.showwarning("Нет данных", "Сначала загрузи и покажи зондирования.")
            return
        self._push_undo()
        resample_cells: list[dict] = []

        for t in self.tests:
            old_flags = self.flags.get(t.tid) or TestFlags(False, set(), set(), set(), set())

            n = min(len(t.depth), len(t.qc), len(t.fs))
            if n < 2:
                continue

            def blank(i):
                return (str(t.depth[i]).strip()=="" and str(t.qc[i]).strip()=="" and str(t.fs[i]).strip()=="")

            def valid(i):
                if blank(i):
                    return False
                d = _parse_depth_float(t.depth[i])
                if d is None:
                    return False
                q = _parse_cell_int(t.qc[i])
                f = _parse_cell_int(t.fs[i])
                return (q is not None or f is not None)

            new_depth, new_qc, new_fs = [], [], []
            map_old_to_new: dict[int,int] = {}
            created_rows: list[int] = []

            i = 0
            while i < n:
                map_old_to_new[i] = len(new_depth)
                new_depth.append(t.depth[i])
                new_qc.append(t.qc[i])
                new_fs.append(t.fs[i])

                if i+1 < n and valid(i) and valid(i+1):
                    d0 = _parse_depth_float(t.depth[i])
                    d1 = _parse_depth_float(t.depth[i+1])
                    if d0 is not None and d1 is not None and 0.09 <= (d1-d0) <= 0.11:
                        dm = d0 + 0.05
                        q0 = _parse_cell_int(t.qc[i]) or 0
                        q1 = _parse_cell_int(t.qc[i+1]) or 0
                        f0 = _parse_cell_int(t.fs[i]) or 0
                        f1 = _parse_cell_int(t.fs[i+1]) or 0
                        qm = int(round((q0+q1)/2))
                        fm = int(round((f0+f1)/2))

                        created_rows.append(len(new_depth))
                        new_depth.append(f"{dm:.2f}")
                        new_qc.append(str(qm))
                        new_fs.append(str(fm))
                i += 1

            t.depth, t.qc, t.fs = new_depth, new_qc, new_fs

            # перенос подсветки (не теряем фиолетовый и др. цвета)
            new_interp: set[tuple[int,str]] = set()
            new_force: set[tuple[int,str]] = set()
            new_user: set[tuple[int,str]] = set()
            new_algo: set[tuple[int,str]] = set()
            for (r, fld) in (old_flags.interp_cells or set()):
                if r in map_old_to_new:
                    new_interp.add((map_old_to_new[r], fld))
            for (r, fld) in (old_flags.force_cells or set()):
                if r in map_old_to_new:
                    new_force.add((map_old_to_new[r], fld))
            for (r, fld) in (old_flags.user_cells or set()):
                if r in map_old_to_new:
                    new_user.add((map_old_to_new[r], fld))
            for (r, fld) in (old_flags.algo_cells or set()):
                if r in map_old_to_new:
                    new_algo.add((map_old_to_new[r], fld))
            # новые созданные строки (вставки при 10→5) помечаем как откорректированные (зелёным)
            for rr in created_rows:
                new_algo.add((rr, "qc"))
                new_algo.add((rr, "fs"))
                depth_m = self._safe_depth_m(t, rr)
                if depth_m is not None:
                    resample_cells.append({"testId": int(getattr(t, "tid", 0) or 0), "depthM": depth_m, "field": "qc", "before": "", "after": str((t.qc or [""])[rr]).strip()})
                    resample_cells.append({"testId": int(getattr(t, "tid", 0) or 0), "depthM": depth_m, "field": "fs", "before": "", "after": str((t.fs or [""])[rr]).strip()})

            # если после 10→5 появился критерий некорректности (>5 нулей подряд) — считаем опыт некорректным (красным)
            try:
                qv = [(_parse_cell_int(v) or 0) for v in (t.qc or [])]
                fv = [(_parse_cell_int(v) or 0) for v in (t.fs or [])]
                invalid_now = bool(old_flags.invalid) or (_max_zero_run(qv) > 5) or (_max_zero_run(fv) > 5)
            except Exception:
                invalid_now = bool(old_flags.invalid)

            self.flags[t.tid] = TestFlags(bool(invalid_now), new_interp, new_force, new_user, new_algo)

        # после конвертации считаем шаг 5 см
        try:
            self.step_m = 0.05
            self.step_choice.set("5")
        except Exception:
            pass

        try:
            if resample_cells:
                self.project_ops.append(op_cells_marked(reason="step_reduce", color="green", cells=resample_cells))
                self._rebuild_marks_index()
        except Exception:
            pass

        self._redraw()
        self.schedule_graph_redraw()
        self.status.config(text="Конвертация 10→5 выполнена. Новые строки помечены зелёным.")

    # ---------------- drawing helpers ----------------
    def _table_col_width(self) -> int:
        show_incl = bool(getattr(self, "show_inclinometer", True)) and (str(getattr(self, "geo_kind", "K2") or "K2").upper() == "K4")
        return self.w_depth + self.w_val*2 + (self.w_val if show_incl else 0)

    def _is_graph_panel_visible(self) -> bool:
        return bool(getattr(self, "show_graphs", False) or getattr(self, "show_geology_column", True))

    def _column_block_width(self) -> int:
        graph_w = int(getattr(self, "graph_w", 150) or 150) if self._is_graph_panel_visible() else 0
        return self._table_col_width() + graph_w

    def _collapsed_header_width(self) -> int:
        # Компактная ширина для header-only карточки (чекбокс + title/datetime + иконки).
        return max(170, min(220, int(self._table_col_width())))

    def _collapsed_header_row_height(self) -> int:
        return 44

    def _is_test_collapsed(self, ti: int) -> bool:
        if ti is None or ti < 0 or ti >= len(getattr(self, "tests", []) or []):
            return False
        return not bool(getattr(self.tests[int(ti)], "export_on", True))

    def _split_display_columns(self):
        ordered = list((vars(self).get("display_cols", []) or []))
        collapsed = [ti for ti in ordered if self._is_test_collapsed(int(ti))]
        expanded = [ti for ti in ordered if not self._is_test_collapsed(int(ti))]
        self.collapsed_cols = collapsed
        self.expanded_cols = expanded

    def _collapsed_dock_width(self) -> int:
        if not (vars(self).get("collapsed_cols", []) or []):
            return 0
        return int(self._collapsed_header_width() + 10)

    def _rebuild_column_layout(self):
        cols = list(getattr(self, "expanded_cols", []) or [])
        x_positions: list[int] = []
        widths: list[int] = []
        x = int(self.pad_x)
        for col, _ti in enumerate(cols):
            w = int(self._column_block_width())
            x_positions.append(int(x))
            widths.append(int(w))
            x += int(w) + int(self.col_gap)
        self._expanded_col_x0 = x_positions
        self._expanded_col_widths = widths

    def _expanded_col_index(self, ti: int) -> int | None:
        cols = getattr(self, "expanded_cols", []) or []
        try:
            return int(cols.index(int(ti)))
        except Exception:
            return None

    def _header_action_buttons_enabled(self, ti: int) -> bool:
        # Для collapsed/locked опыта отключаем кнопки даты/копии/удаления.
        return (not self._is_test_collapsed(int(ti))) and (not self._is_test_locked(int(ti)))

    def _collapsed_header_bbox(self, row: int):
        x0 = 4
        x1 = int(x0 + self._collapsed_header_width())
        y0 = int(4 + row * self._collapsed_header_row_height())
        y1 = int(y0 + self._collapsed_header_row_height() - 4)
        return x0, y0, x1, y1

    def _column_x0(self, col: int) -> int:
        try:
            x_positions = getattr(self, "_expanded_col_x0", []) or []
            if 0 <= int(col) < len(x_positions):
                return int(x_positions[int(col)])
        except Exception:
            pass
        return self.pad_x + col * (self._column_block_width() + self.col_gap)

    def _last_column_right_px(self) -> float:
        """Правая граница последнего блока в пикселях (с учетом графиков)."""
        try:
            n_cols = len(getattr(self, "expanded_cols", []) or [])
        except Exception:
            n_cols = 0
        if n_cols <= 0:
            return float((getattr(self, "pad_x", 0) or 0))
        try:
            widths = list(getattr(self, "_expanded_col_widths", []) or [])
            x_positions = list(getattr(self, "_expanded_col_x0", []) or [])
            if len(widths) == n_cols and len(x_positions) == n_cols:
                return float(x_positions[-1] + widths[-1])
        except Exception:
            pass
        # fallback: равные ширины (legacy)
        col_w = float(self._column_block_width())
        gap = float(self.col_gap)
        pad = float(self.pad_x)
        return float(pad + (col_w + gap) * max(0, n_cols - 1) + col_w)

    def _graph_rect_for_test(self, ti: int, r: int | None = None):
        try:
            col = int((getattr(self, "expanded_cols", []) or []).index(ti))
        except Exception:
            return None
        if not self._is_graph_panel_visible():
            return None
        x0 = self._column_x0(col) + self._table_col_width()
        x1 = x0 + int(getattr(self, "graph_w", 150) or 150)
        if r is None:
            return x0, x1, 0, self._total_body_height()
        y0, y1 = self._row_y_bounds(r)
        return x0, x1, y0, y1

    def _content_size(self):
        # Размеры контента для scrollregion.
        # Важно: таблица (цифры) теперь в отдельном canvas и скроллится по Y без шапки.
        max_rows = 0
        try:
            if getattr(self, "_grid", None):
                max_rows = len(self._grid)
            else:
                max_rows = max((len(t.qc) for t in self.tests), default=0)
        except Exception:
            max_rows = max((len(t.qc) for t in self.tests), default=0)

        try:
            n_cols = len(getattr(self, "expanded_cols", []) or [])
        except Exception:
            n_cols = len(getattr(self, "tests", []) or [])
        n_cols = max(0, int(n_cols))
        try:
            widths = list(getattr(self, "_expanded_col_widths", []) or [])
            if len(widths) != n_cols:
                widths = [int(self._column_block_width())] * n_cols
        except Exception:
            widths = [int(self._column_block_width())] * n_cols
        self._last_col_w = int(widths[-1]) if widths else int(self._column_block_width())
        total_w = self.pad_x * 2 + sum(widths) + (self.col_gap * max(0, n_cols - 1))
        body_h = self._total_body_height() if max_rows > 0 else 0
        header_h = int(self.pad_y + self.hdr_h)  # фиксированная область
        return total_w, body_h, header_h

    def _shared_x_offset_px(self) -> float:
        try:
            return float(self.canvas.canvasx(0))
        except Exception:
            try:
                w_total = float(getattr(self, "_scroll_w", 0.0) or 0.0)
            except Exception:
                w_total = 0.0
            try:
                frac = float(getattr(self, "_shared_x_frac", 0.0) or 0.0)
            except Exception:
                frac = 0.0
            return max(0.0, frac) * max(0.0, w_total)

    def _sync_header_vbar_gutter(self) -> int:
        spacer = getattr(self, "hcanvas_vbar_spacer", None)
        if spacer is None:
            return 0
        vbar = getattr(self, "vbar", None)
        width = 0
        try:
            width = int(vbar.winfo_width() or 0) if vbar is not None else 0
        except Exception:
            width = 0
        if width <= 0:
            try:
                width = int(vbar.winfo_reqwidth() or 0) if vbar is not None else 0
            except Exception:
                width = 0
        width = max(0, int(width))
        try:
            spacer.configure(width=width)
        except Exception:
            pass
        return width

    def _apply_shared_xview(self, *args, close_editor: bool = False):
        """Единая точка записи X для body/header canvas в старой архитектуре."""
        if close_editor:
            self._end_edit(commit=True)
        if getattr(self, "_shared_x_lock", False):
            return
        self._shared_x_lock = True
        try:
            try:
                self.canvas.xview(*args)
            except Exception:
                return
            try:
                first, last = self.canvas.xview()
                first = float(first)
                last = float(last)
            except Exception:
                first, last = 0.0, 1.0
            first = 0.0 if first < 0.0 else (1.0 if first > 1.0 else first)
            self._shared_x_frac = first
            body_left_px = self._shared_x_offset_px()
            requested_first = first
            if args:
                try:
                    if str(args[0]) == "moveto" and len(args) > 1:
                        requested_first = float(args[1])
                except Exception:
                    requested_first = first
            try:
                self.hcanvas.configure(width=self.canvas.winfo_width())
            except Exception:
                pass
            vbar_w = self._sync_header_vbar_gutter()
            try:
                self.hcanvas.xview_moveto(first)
            except Exception:
                pass
            try:
                body_region_w = float((self.canvas.bbox("all") or (0, 0, float(getattr(self, "_scroll_w", 0.0) or 0.0), 0))[2])
            except Exception:
                body_region_w = float(getattr(self, "_scroll_w", 0.0) or 0.0)
            try:
                header_region_w = float((self.hcanvas.bbox("all") or (0, 0, body_region_w, 0))[2])
            except Exception:
                header_region_w = body_region_w
            try:
                body_vw = float(self.canvas.winfo_width() or 1.0)
            except Exception:
                body_vw = 1.0
            try:
                header_vw = float(self.hcanvas.winfo_width() or body_vw)
            except Exception:
                header_vw = body_vw
            body_max_px = max(0.0, body_region_w - max(1.0, body_vw))
            right_edge = bool((last >= (1.0 - 1e-9)) or (body_left_px >= (body_max_px - 1e-6)))
            if right_edge and header_region_w > 1.0:
                header_snap_frac = body_left_px / header_region_w
                header_snap_frac = 0.0 if header_snap_frac < 0.0 else (1.0 if header_snap_frac > 1.0 else header_snap_frac)
                try:
                    self.hcanvas.xview_moveto(header_snap_frac)
                except Exception:
                    pass
            try:
                if hasattr(self, "hscroll"):
                    self.hscroll.set(first, last)
            except Exception:
                pass
            try:
                self._header_offset_px = float(self.hcanvas.canvasx(0))
            except Exception:
                self._header_offset_px = body_left_px
            try:
                header_left_px = float(self.hcanvas.canvasx(0))
            except Exception:
                header_left_px = float(self._header_offset_px or 0.0)
            delta_px = float(header_left_px - body_left_px)
            clamp_applied = abs(requested_first - first) > 1e-9
            self._debug_header_sync(
                "apply_shared_xview",
                request=args,
                requested=f"{requested_first:.9f}",
                clamped=f"{first:.9f}",
                body_px=f"{body_left_px:.3f}",
                header_px=f"{header_left_px:.3f}",
                delta_px=f"{delta_px:.3f}",
                body_sr_w=f"{body_region_w:.3f}",
                header_sr_w=f"{header_region_w:.3f}",
                body_vw=f"{body_vw:.3f}",
                header_vw=f"{header_vw:.3f}",
                body_max_left=f"{body_max_px:.3f}",
                header_max_left=f"{max(0.0, header_region_w - max(1.0, header_vw)):.3f}",
                vbar_w=f"{float(vbar_w):.3f}",
                clamp=int(bool(clamp_applied)),
                right_edge=int(bool(right_edge)),
            )
        finally:
            self._shared_x_lock = False

    def _update_scrollregion(self):
        # сохраняем пиксельный сдвиг по X, чтобы после изменения ширины scrollregion
        # (например, после добавления зондирования) шапка и тело не расходились.
        try:
            old_w = float(getattr(self, "_scroll_w", 0) or 0)
        except Exception:
            old_w = 0.0
        try:
            old_frac = float(self.canvas.xview()[0])
        except Exception:
            old_frac = 0.0
        if old_w <= 0:
            old_w = 1.0
        old_px = old_frac * old_w

        w, body_h, header_h = self._content_size()
        w_total = max(1, int(w))

        try:
            vw = int(self.canvas.winfo_width() or 1)
        except Exception:
            vw = 1
        need_h = (w_total > max(vw, 1))

        # scroll по Y только для таблицы
        self.canvas.configure(scrollregion=(0, 0, w_total, body_h))
        try:
            view_h = int(self.canvas.winfo_height() or 1)
        except Exception:
            view_h = 1
        need_v = body_h > max(1, view_h)
        if not need_v:
            try:
                self.canvas.yview_moveto(0.0)
            except Exception:
                pass
            try:
                self.vbar.state(["disabled"])
            except Exception:
                pass
        else:
            try:
                self.vbar.state(["!disabled"])
            except Exception:
                pass
        try:
            self._sync_header_vbar_gutter()
        except Exception:
            pass
        # Шапка: отдельный canvas, X синхронизируем с body через xview_moveto.
        try:
            self.hcanvas.configure(scrollregion=(0, 0, w_total, header_h))
            self.hcanvas.configure(height=header_h)
            self.hcanvas.configure(width=self.canvas.winfo_width())
        except Exception:
            pass
        dock_w = int(self._collapsed_dock_width())
        try:
            spacer = vars(self).get("collapsed_header_spacer")
            if spacer is not None:
                if dock_w > 0:
                    spacer.configure(width=dock_w)
                    if not bool(spacer.winfo_ismapped()):
                        spacer.pack(side="left", fill="y", before=self.hcanvas)
                else:
                    spacer.configure(width=0)
                    if bool(spacer.winfo_ismapped()):
                        spacer.pack_forget()
        except Exception:
            pass
        try:
            dock = vars(self).get("collapsed_dock")
            if dock is not None:
                if dock_w > 0:
                    dock.configure(width=dock_w)
                    if not bool(dock.winfo_ismapped()):
                        dock.pack(side="left", fill="y", before=self.canvas)
                else:
                    dock.configure(width=0)
                    if bool(dock.winfo_ismapped()):
                        dock.pack_forget()
        except Exception:
            pass


        # восстановить X-сдвиг в пикселях
        try:
            self._scroll_w = float(w_total)
        except Exception:
            self._scroll_w = float(w_total)
        try:
            new_frac = 0.0 if (w_total <= 1) else (old_px / float(w_total))
            if new_frac < 0.0:
                new_frac = 0.0
            if new_frac > 1.0:
                new_frac = 1.0
            self._apply_shared_xview("moveto", new_frac)
        except Exception:
            pass

        # Горизонтальная прокрутка: показываем только если колонки не помещаются в видимую область
        if not need_h:
            try:
                self._apply_shared_xview("moveto", 0.0)
            except Exception:
                pass
            # скрыть скроллбар
            try:
                if not getattr(self, "_hscroll_hidden", True):
                    self.hscroll_frame.pack_forget()
            except Exception:
                pass
            self._hscroll_hidden = True
            try:
                # ttk.Scrollbar.set ожидает (first, last)
                self.hscroll.set(0.0, 1.0)
            except Exception:
                pass
        else:
            # показать горизонтальную полосу сразу после таблицы (над статусом)
            if getattr(self, "_hscroll_hidden", True):
                try:
                    self.hscroll_frame.pack(side="bottom", fill="x")
                except Exception:
                    try:
                        self.hscroll_frame.pack(side="bottom", fill="x")
                    except Exception:
                        pass
                # статус должен быть НИЖЕ полосы — перепаковываем
                try:
                    self.status.pack_forget()
                    self.status.pack(side="bottom", fill="x", before=self.footer)
                except Exception:
                    pass
                self._hscroll_hidden = False

        self._sync_header_body_after_scroll()

    def _sorted_display_indices(self) -> list[int]:
        """Return display indices for tests using current sort mode."""

        def _tid_key(tid):
            try:
                return int(str(tid).strip())
            except Exception:
                return 10**9

        mode = str(getattr(self, "display_sort_mode", "date") or "date").lower()

        if mode == "tid":
            return sorted(range(len(self.tests)), key=lambda i: (_tid_key(getattr(self.tests[i], "tid", "")), i))

        def _key(i: int):
            t = self.tests[i]
            dt = _try_parse_dt(getattr(t, "dt", "") or "")
            dt_key = dt if dt is not None else _dt.datetime.max
            return (dt_key, _tid_key(getattr(t, "tid", "")), i)

        return sorted(range(len(self.tests)), key=_key)

    def _refresh_display_order(self):
        self.display_cols = self._sorted_display_indices()
        self._split_display_columns()
        self._rebuild_column_layout()


    def schedule_graph_redraw(self):
        prev = getattr(self, "_graph_redraw_after_id", None)
        if prev is not None:
            try:
                self.after_cancel(prev)
            except Exception:
                pass
        if not self._is_graph_panel_visible():
            self._clear_graph_layers()
            self._graph_redraw_after_id = None
            return
        self._graph_redraw_after_id = self.after(60, self._redraw_graphs_now)

    def _recompute_graph_scales(self):
        """Compute shared (file-level) X scales for graph columns."""
        qc_max = None
        fs_max = None
        try:
            cal = self._current_calibration()
            qc_full, fs_full = calc_qc_fs_from_del(
                cal.scale_div,
                cal.scale_div,
                scale_div=cal.scale_div,
                fcone_kn=cal.fcone_kn,
                fsleeve_kn=cal.fsleeve_kn,
                cone_area_cm2=cal.cone_area_cm2,
                sleeve_area_cm2=cal.sleeve_area_cm2,
            )
            qc_max = float(qc_full) if float(qc_full) > 0 else None
            fs_max = float(fs_full) if float(fs_full) > 0 else None
        except Exception:
            pass

        if qc_max is None:
            qc_max = 50.0 if str(getattr(self, "geo_kind", "K2") or "K2").upper() == "K4" else 30.0
        if fs_max is None:
            fs_max = 500.0

        self.graph_qc_max_mpa = float(qc_max)
        self.graph_fs_max_kpa = float(fs_max)

    def _clear_graph_layers(self):
        for cnv in (getattr(self, "canvas", None), getattr(self, "hcanvas", None)):
            if cnv is None:
                continue
            for tag in ("graph_axes", "graph_qc", "graph_fs", "graph_nodata", "layers_overlay", "layer_handles"):
                try:
                    cnv.delete(tag)
                except Exception:
                    pass

    def _draw_graph_axes_for_test(self, ti: int, x0: float, x1: float, qmax: float, fmax: float):
        y0 = self.pad_y
        y1 = y0 + self.hdr_h
        tag = ("graph_axes", f"graph_axes_{ti}")
        self.hcanvas.create_rectangle(x0, y0, x1, y1, fill="#fbfdff", outline=GUI_GRID, tags=tag)
        pad = 8
        xa0 = x0 + pad
        xa1 = x1 - pad
        qc_axis_y = y0 + 24
        fs_axis_y = y0 + 46
        self.hcanvas.create_line(xa0, qc_axis_y, xa1, qc_axis_y, fill=GRAPH_QC_GREEN, width=1, tags=tag)
        self.hcanvas.create_line(xa0, fs_axis_y, xa1, fs_axis_y, fill=GRAPH_FS_BLUE, width=1, tags=tag)
        for i in range(0, 6):
            xx = xa0 + ((xa1 - xa0) * i / 5.0)
            self.hcanvas.create_line(xx, qc_axis_y - 3, xx, qc_axis_y + 3, fill=GRAPH_QC_GREEN, width=1, tags=tag)
            self.hcanvas.create_line(xx, fs_axis_y - 3, xx, fs_axis_y + 3, fill=GRAPH_FS_BLUE, width=1, tags=tag)
        self.hcanvas.create_text(xa0, qc_axis_y - 10, anchor="w", text="qc, МПа", fill=GRAPH_QC_GREEN, font=("Segoe UI", 8), tags=tag)
        self.hcanvas.create_text(xa0, fs_axis_y - 10, anchor="w", text="fs, кПа", fill=GRAPH_FS_BLUE, font=("Segoe UI", 8), tags=tag)
        q_txt = f"0–{int(float(qmax))}"
        self.hcanvas.create_text(xa1, qc_axis_y - 10, anchor="e", text=q_txt, fill=GRAPH_QC_GREEN, font=("Segoe UI", 7), tags=tag)
        f_txt = f"0–{int(float(fmax))}"
        self.hcanvas.create_text(xa1, fs_axis_y - 10, anchor="e", text=f_txt, fill=GRAPH_FS_BLUE, font=("Segoe UI", 7), tags=tag)

    def _test_last_data_index(self, t) -> int | None:
        qarr = getattr(t, "qc", []) or []
        farr = getattr(t, "fs", []) or []
        last = None
        for i in range(max(len(qarr), len(farr))):
            q_raw = _parse_cell_int(qarr[i]) if i < len(qarr) else None
            f_raw = _parse_cell_int(farr[i]) if i < len(farr) else None
            if q_raw is None and f_raw is None:
                continue
            last = i
        return last

    def _depth_at_index(self, t, idx: int):
        d_arr = getattr(t, "depth", []) or []
        if 0 <= idx < len(d_arr):
            dv = _parse_depth_float(d_arr[idx])
            if dv is not None:
                return float(dv)
        step = float(getattr(self, "step_m", 0.05) or 0.05)
        try:
            depth0 = float(self.depth0_by_tid.get(int(getattr(t, "tid", 0) or 0), float(getattr(self, "depth_start", 0.0) or 0.0)))
        except Exception:
            depth0 = float(getattr(self, "depth_start", 0.0) or 0.0)
        return float(depth0 + (idx * step))

    def _test_depth_range(self, t) -> tuple[float, float]:
        dvals = []
        for ds in (getattr(t, "depth", []) or []):
            dv = _parse_depth_float(ds)
            if dv is not None:
                dvals.append(float(dv))
        if dvals:
            top = min(dvals)
            bot = max(dvals)
            if len(dvals) >= 2:
                step = abs(dvals[1] - dvals[0])
            else:
                step = float(getattr(self, "step_m", 0.05) or 0.05)
            return top, bot + max(step, 0.05)
        depth0 = float(getattr(self, "depth_start", 0.0) or 0.0)
        return depth0, depth0 + 1.0


    def _test_effective_data_depth_range(self, t) -> tuple[float, float]:
        """Фактический диапазон глубин опыта по строкам с реальными измерениями."""
        d_arr = list(getattr(t, "depth", []) or [])
        q_arr = list(getattr(t, "qc", []) or [])
        f_arr = list(getattr(t, "fs", []) or [])
        incl_arr = getattr(t, "incl", None)
        if incl_arr is None:
            incl_arr = []
        else:
            incl_arr = list(incl_arr or [])

        n = max(len(d_arr), len(q_arr), len(f_arr), len(incl_arr))
        valid_depths: list[float] = []
        for i in range(n):
            dv = _parse_depth_float(d_arr[i]) if i < len(d_arr) else None
            if dv is None:
                continue
            q_raw = _parse_cell_int(q_arr[i]) if i < len(q_arr) else None
            f_raw = _parse_cell_int(f_arr[i]) if i < len(f_arr) else None
            incl_raw = _parse_cell_int(incl_arr[i]) if i < len(incl_arr) else None
            if q_raw is None and f_raw is None and incl_raw is None:
                continue
            valid_depths.append(float(dv))

        if not valid_depths:
            return self._test_depth_range(t)

        top = min(valid_depths)
        bot = max(valid_depths)
        if bot <= top:
            return self._test_depth_range(t)
        return float(top), float(bot)

    def _ensure_test_layers(self, t) -> list[Layer]:
        raw = list(getattr(t, "layers", []) or [])
        layers: list[Layer] = []
        for item in raw:
            if isinstance(item, Layer):
                layers.append(item)
            elif isinstance(item, dict):
                try:
                    layers.append(layer_from_dict(item))
                except Exception:
                    pass
        if not layers:
            layers = self.layer_store.get_layers(t, self._test_depth_range)
        else:
            try:
                layers = normalize_layers(layers)
                validate_layers(layers)
            except Exception:
                top, bot = self._test_depth_range(t)
                layers = build_default_layers(top, bot)
            t.layers = layers
        for lyr in layers:
            self._apply_ige_to_layer(lyr)
        self._renumber_layers(t)
        return layers

    def _ensure_test_experience_column(self, t) -> ExperienceColumn:
        raw = getattr(t, "experience_column", None)
        if isinstance(raw, ExperienceColumn):
            column = raw
        elif isinstance(raw, dict):
            try:
                column = column_from_dict(raw)
            except Exception:
                column = None
        else:
            column = None
        if column is None:
            layers = self._ensure_test_layers(t)
            top, bot = self._test_depth_range(t)
            default_ige = str(getattr(layers[0], "ige_id", "") or "ИГЭ-1") if layers else "ИГЭ-1"
            column = build_column_from_layers(layers, sounding_top=float(top), sounding_bottom=float(bot), default_ige_id=default_ige)
        default_ige = "ИГЭ-1"
        if column.intervals:
            default_ige = str(column.intervals[0].ige_id or default_ige)
        try:
            column = normalize_column(column, default_ige_id=default_ige)
        except Exception:
            top, bot = self._test_depth_range(t)
            column = build_column_from_layers(self._ensure_test_layers(t), sounding_top=float(top), sounding_bottom=float(bot), default_ige_id=default_ige)
        column = self._canonicalize_experience_column_refs(column)
        t.experience_column = column
        return column

    def _canonicalize_experience_column_refs(self, column: ExperienceColumn) -> ExperienceColumn:
        clone = ExperienceColumn(
            column_depth_start=float(column.column_depth_start),
            column_depth_end=float(column.column_depth_end),
            intervals=[ColumnInterval(**column_interval_to_dict(item)) for item in (column.intervals or [])],
        )
        for item in clone.intervals:
            resolved = self._resolve_existing_ige_id(getattr(item, "ige_id", None) or getattr(item, "ige_name", None))
            if resolved:
                item.ige_id = resolved
                item.ige_name = self._ige_display_label(resolved)
            else:
                item.ige_id = str(getattr(item, "ige_id", "") or "").strip()
                item.ige_name = str(getattr(item, "ige_name", "") or "").strip()
        default_ige = self._resolve_existing_ige_id(clone.intervals[0].ige_id if clone.intervals else None) or "ИГЭ-1"
        return normalize_column(clone, default_ige_id=default_ige)

    def _normalize_all_ige_references(self) -> None:
        for t in (self.tests or []):
            for lyr in self._ensure_test_layers(t):
                resolved = self._resolve_existing_ige_id(getattr(lyr, "ige_id", None))
                if resolved:
                    lyr.ige_id = resolved
                    lyr.ige_num = self._ige_id_to_num(resolved)
            column = getattr(t, "experience_column", None)
            if column is not None:
                t.experience_column = self._canonicalize_experience_column_refs(column)

    def _column_interval_ige_id(self, interval: ColumnInterval) -> str:
        resolved = self._resolve_existing_ige_id(getattr(interval, "ige_id", None) or getattr(interval, "ige_name", None))
        if resolved:
            try:
                interval.ige_id = resolved
                interval.ige_name = self._ige_display_label(resolved)
            except Exception:
                pass
            return resolved
        return str(getattr(interval, "ige_id", "") or getattr(interval, "ige_name", "") or "ИГЭ-1")

    def _experience_column_ige_display(self, ige_id: str) -> str:
        resolved = self._resolve_existing_ige_id(ige_id)
        if resolved is None:
            return str(ige_id or "ИГЭ-1")
        return self._ige_display_label(resolved)

    def _experience_column_ige_choices(self) -> list[tuple[str, str]]:
        ids = sorted(self.ige_registry.keys(), key=self._ige_id_to_num)
        return [(ige_id, self._experience_column_ige_display(ige_id)) for ige_id in ids]

    def _validate_experience_column_iges(self, column: ExperienceColumn) -> str | None:
        known_ids = {str(ige_id or "").strip() for ige_id in (self.ige_registry or {}).keys()}
        for idx, interval in enumerate(list(getattr(column, "intervals", []) or []), start=1):
            ige_id = self._column_interval_ige_id(interval)
            if not str(ige_id or "").strip():
                return f"Для интервала {idx} не выбран ИГЭ"
            if known_ids and str(ige_id) not in known_ids:
                return f"ИГЭ «{ige_id}» из интервала {idx} не найден среди ИГЭ проекта"
        return None

    def _center_toplevel(self, win, *, parent=None):
        host = parent or self
        try:
            host.update_idletasks()
            win.update_idletasks()
            px = int(host.winfo_rootx())
            py = int(host.winfo_rooty())
            pw = int(max(1, host.winfo_width()))
            ph = int(max(1, host.winfo_height()))
            ww = int(max(1, win.winfo_reqwidth()))
            wh = int(max(1, win.winfo_reqheight()))
            x = px + max(0, (pw - ww) // 2)
            y = py + max(0, (ph - wh) // 2)
            win.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _pick_existing_ige_for_column(self, *, parent=None, title: str = "Выбор ИГЭ", current_ige_id: str | None = None) -> str | None:
        choices = self._experience_column_ige_choices()
        if not choices:
            messagebox.showinfo(
                "Нет ИГЭ",
                "Сначала создайте ИГЭ на вкладке ИГЭ проекта, затем добавляйте интервалы в колонке опыта.",
                parent=parent or self,
            )
            return None

        holder: dict[str, str | None] = {"value": None}
        win = tk.Toplevel(parent or self)
        win.title(title)
        win.transient(parent or self)
        win.grab_set()
        win.resizable(False, False)
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Выберите существующий ИГЭ:").pack(anchor="w")
        btn_col = ttk.Frame(frm)
        btn_col.pack(fill="both", expand=True, pady=(8, 0))

        def _pick(ige_id: str):
            holder["value"] = str(ige_id or "").strip() or None
            win.destroy()

        def _cancel():
            holder["value"] = None
            win.destroy()

        for ige_id, display in choices:
            text = display
            if str(current_ige_id or "").strip() == str(ige_id):
                text = f"✓ {display}"
            ttk.Button(btn_col, text=text, command=lambda ig=ige_id: _pick(ig)).pack(fill="x", pady=2)

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(12, 0))
        ttk.Button(btns, text="Отмена", command=_cancel).pack(side="right")
        self._center_toplevel(win, parent=parent or self)
        win.bind("<Escape>", lambda _e: _cancel())
        win.wait_window()
        return holder["value"]

    def _sync_experience_column_to_test_depth_range(self, ti: int):
        if ti is None or ti < 0 or ti >= len(self.tests):
            return
        t = self.tests[int(ti)]
        column = self._ensure_test_experience_column(t)
        _top, bot = self._test_depth_range(t)
        clone = ExperienceColumn(
            column_depth_start=0.0,
            column_depth_end=max(float(column.column_depth_end), float(bot)),
            intervals=[ColumnInterval(**column_interval_to_dict(item)) for item in column.intervals],
        )
        t.experience_column = normalize_column(clone, default_ige_id=self._column_interval_ige_id(clone.intervals[0]) if clone.intervals else "ИГЭ-1")

    def _sync_layers_to_test_depth_range(self, ti: int, *, depth_shift: float = 0.0):
        """Локально синхронизирует слои одного опыта с актуальным диапазоном depth."""
        if ti is None or ti < 0 or ti >= len(self.tests):
            return
        t = self.tests[int(ti)]
        layers = [layer_from_dict(layer_to_dict(x)) for x in (getattr(t, "layers", []) or [])]
        if not layers:
            return

        if abs(float(depth_shift or 0.0)) > 1e-12:
            for lyr in layers:
                lyr.top_m = float(lyr.top_m) + float(depth_shift)
                lyr.bot_m = float(lyr.bot_m) + float(depth_shift)

        top, bot = self._test_depth_range(t)
        top = float(top)
        bot = float(bot)

        clipped: list[Layer] = []
        for lyr in sorted(layers, key=lambda x: float(x.top_m)):
            lt = max(top, float(lyr.top_m))
            lb = min(bot, float(lyr.bot_m))
            if lb - lt <= 1e-9:
                continue
            lyr.top_m = lt
            lyr.bot_m = lb
            clipped.append(lyr)

        if not clipped:
            t.layers = build_default_layers(top, bot)
        else:
            clipped[0].top_m = top
            for i in range(1, len(clipped)):
                clipped[i].top_m = float(clipped[i - 1].bot_m)
            clipped[-1].bot_m = bot
            t.layers = normalize_layers(clipped)

        self._calc_layer_params_for_test(int(ti))
        self._sync_experience_column_to_test_depth_range(int(ti))
        self._sync_layers_panel()


    def _ensure_layers_defaults_for_all_tests(self):
        changed = self.layer_store.ensure_defaults_for_all_tests(self.tests, self._test_depth_range)
        for t in (self.tests or []):
            for lyr in self._ensure_test_layers(t):
                self._apply_ige_to_layer(lyr)
            self._ensure_test_experience_column(t)
        if changed:
            self._sync_layers_panel()
            self.schedule_graph_redraw()

    def _calc_layer_params_for_test(self, ti: int) -> None:
        if ti is None or ti < 0 or ti >= len(self.tests):
            return
        t = self.tests[ti]
        layers = self._ensure_test_layers(t)
        qarr = list(getattr(t, "qc", []) or [])
        farr = list(getattr(t, "fs", []) or [])

        samples: list[tuple[float, float, float, float]] = []
        n = max(len(qarr), len(farr))
        for i in range(n):
            dv = self._depth_at_index(t, i)
            if dv is None:
                continue
            q_raw = _parse_cell_int(qarr[i]) if i < len(qarr) else None
            f_raw = _parse_cell_int(farr[i]) if i < len(farr) else None
            qc_mpa, fs_kpa = self._calc_qc_fs_from_del(int(q_raw or 0), int(f_raw or 0))
            qc_kpa = float(qc_mpa) * 1000.0
            rf = 0.0 if qc_kpa <= 1e-9 else (float(fs_kpa) / qc_kpa) * 100.0
            samples.append((float(dv), float(qc_mpa), float(fs_kpa), float(rf)))

        def _stats(vals: list[float]) -> dict[str, float | None]:
            if not vals:
                return {"mean": None, "min": None, "max": None, "p10": None, "p50": None, "p90": None}
            arr = sorted(float(v) for v in vals)
            def _pct(p: float) -> float:
                if len(arr) == 1:
                    return arr[0]
                pos = (len(arr) - 1) * p
                lo = int(math.floor(pos))
                hi = int(math.ceil(pos))
                if lo == hi:
                    return arr[lo]
                w = pos - lo
                return arr[lo] * (1.0 - w) + arr[hi] * w
            return {
                "mean": sum(arr) / len(arr),
                "min": arr[0],
                "max": arr[-1],
                "p10": _pct(0.10),
                "p50": _pct(0.50),
                "p90": _pct(0.90),
            }

        for lyr in layers:
            top = float(lyr.top_m)
            bot = float(lyr.bot_m)
            in_layer = [s for s in samples if top <= s[0] < bot]
            lyr.params = {
                "qc": _stats([x[1] for x in in_layer]),
                "fs": _stats([x[2] for x in in_layer]),
                "rf": _stats([x[3] for x in in_layer]),
            }

    def _calc_layer_params_for_all_tests(self) -> None:
        for ti in range(len(self.tests or [])):
            self._calc_layer_params_for_test(ti)

    def _depth_to_canvas_y(self, depth_m: float) -> float | None:
        d = float(depth_m)
        units = getattr(self, "_grid_units", []) or []
        base_grid = getattr(self, "_grid_base", []) or []

        points: list[tuple[float, float]] = []
        for disp_r, unit in enumerate(units):
            y0r, y1r = self._row_y_bounds(disp_r)
            if unit[0] == "meter":
                meter_n = float(unit[1])
                points.append((meter_n, y0r))
                points.append((meter_n + 1.0, y1r))
                continue
            if unit[0] != "row":
                continue
            try:
                gi = int(unit[1])
            except Exception:
                continue
            if not (0 <= gi < len(base_grid)):
                continue
            cur = _parse_depth_float(base_grid[gi])
            if cur is None:
                continue
            prev = _parse_depth_float(base_grid[gi - 1]) if gi > 0 else None
            nxt = _parse_depth_float(base_grid[gi + 1]) if gi + 1 < len(base_grid) else None
            if prev is not None:
                top_d = (float(prev) + float(cur)) * 0.5
            elif nxt is not None:
                top_d = float(cur) - (float(nxt) - float(cur)) * 0.5
            else:
                top_d = float(cur) - float(getattr(self, "step_m", 0.05) or 0.05) * 0.5
            if nxt is not None:
                bot_d = (float(cur) + float(nxt)) * 0.5
            elif prev is not None:
                bot_d = float(cur) + (float(cur) - float(prev)) * 0.5
            else:
                bot_d = float(cur) + float(getattr(self, "step_m", 0.05) or 0.05) * 0.5
            points.append((top_d, y0r))
            points.append((bot_d, y1r))

        if not points:
            return None
        points.sort(key=lambda x: x[0])
        if d < points[0][0] or d > points[-1][0]:
            return None
        for dd, yy in points:
            if abs(dd - d) <= 1e-6:
                return yy

        depths = [p[0] for p in points]
        i = bisect.bisect_left(depths, d)
        if i <= 0 or i >= len(points):
            return None
        d0, y0 = points[i - 1]
        d1, y1 = points[i]
        if abs(d1 - d0) <= 1e-9:
            return y0
        ratio = (d - d0) / (d1 - d0)
        return y0 + (y1 - y0) * ratio


    def _geology_layer_fill_color(self, soil_type: str | None) -> str:
        if not bool(getattr(self, "show_layer_colors", False)):
            return "#ffffff"
        try:
            soil = SoilType(str(soil_type or "").strip())
        except Exception:
            return "#ffffff"
        return str(SOIL_TYPE_TO_COLUMN_FILL.get(soil, "#ffffff"))

    def _draw_layer_hatch(self, x0: float, y0: float, x1: float, y1: float, soil_type: str, tags, logical_rect=None, debug_ctx: dict | None = None):
        # Единая система: внешние JSON-штриховки через domain.hatching registry.
        ctx = dict(debug_ctx or {})
        self._hatch_debug_log(
            "hatch_layer_begin",
            soil_type=str(soil_type or ""),
            bbox=(float(x0), float(y0), float(x1), float(y1)),
            logical_rect=(tuple(logical_rect) if logical_rect is not None else None),
            tags=tuple(tags) if isinstance(tags, (tuple, list)) else tags,
            **ctx,
        )
        pattern = load_registered_hatch(str(soil_type or ""))
        if pattern is None:
            self._hatch_debug_log("hatch_layer_skip", reason="pattern_not_found", soil_type=str(soil_type or ""), **ctx)
            return
        trace_state = {"primitives_total": 0, "events": []}

        def _debug_hook(event: str, **payload):
            event_payload = dict(payload)
            trace_state["events"].append((event, event_payload))
            if event == "hatch_line_drawn":
                trace_state["primitives_total"] += int(event_payload.get("primitives_count", 0) or 0)
            self._hatch_debug_log(event, soil_type=str(soil_type or ""), **ctx, **event_payload)

        render_hatch_pattern(
            self.canvas,
            (float(x0), float(y0), float(x1), float(y1)),
            pattern,
            tags=tags,
            scale_info={
                "usage": HATCH_USAGE_EDITOR_EXPANDED,
                "layer_height_px": float(y1 - y0),
                "logical_rect": tuple(logical_rect) if logical_rect is not None else (float(x0), float(y0), float(x1), float(y1)),
                "debug_hook": _debug_hook if bool(getattr(self, "_debug_hatch", False)) else None,
            },
        )
        self._hatch_debug_log(
            "hatch_layer_drawn",
            soil_type=str(soil_type or ""),
            hatch_requested=True,
            hatch_built=bool(trace_state["primitives_total"] > 0),
            hatch_skipped=bool(trace_state["primitives_total"] <= 0),
            skip_reason=("no_primitives_created" if trace_state["primitives_total"] <= 0 else ""),
            primitives_count=int(trace_state["primitives_total"]),
            events_count=len(trace_state["events"]),
            **ctx,
        )

    def _draw_layers_overlay_for_test(self, ti: int, plot_rect, depth_to_y, tags):
        t = self.tests[ti]
        column = self._ensure_test_experience_column(t)
        if plot_rect is None or len(plot_rect) != 4:
            self._debug_log(f"layers_overlay: invalid plot_rect for ti={ti}: {plot_rect}")
            return
        x0, x1, y0, y1 = [float(v) for v in plot_rect]
        if x1 <= x0 or y1 <= y0:
            self._debug_log(f"layers_overlay: empty rect for ti={ti}: {plot_rect}")
            return
        if not callable(depth_to_y):
            self._debug_log(f"layers_overlay: invalid depth_to_y for ti={ti}")
            return
        label_spans = []
        for interval_index, lyr in enumerate(column.intervals):
            lt = max(float(column.column_depth_start), float(lyr.from_depth))
            lb = min(float(column.column_depth_end), float(lyr.to_depth))
            if lb - lt <= 1e-9:
                continue
            ly0 = depth_to_y(lt)
            ly1 = depth_to_y(lb)
            if ly0 is None or ly1 is None:
                self._debug_log(f"layers_overlay: depth_to_y none ti={ti}, ige={self._column_interval_ige_id(lyr)}, top={lt}, bot={lb}")
                continue
            ty0 = max(y0, min(ly0, ly1))
            ty1 = min(y1, max(ly0, ly1))
            if ty1 <= ty0:
                continue
            ige_id = self._column_interval_ige_id(lyr)
            ent = self._ensure_ige_entry(ige_id)
            soil_type = str(ent.get("soil_type") or SoilType.SANDY_LOAM.value)
            fill_color = self._geology_layer_fill_color(soil_type)
            self.canvas.create_rectangle(x0, ty0, x1, ty1, fill=fill_color, outline="", tags=tags)
            if bool(getattr(self, "show_layer_hatching", True)):
                self._draw_layer_hatch(
                    x0,
                    ty0,
                    x1,
                    ty1,
                    soil_type=soil_type,
                    tags=tags,
                    logical_rect=(x0, y0, x1, y1),
                    debug_ctx={
                        "ti": int(ti),
                        "test_id": int(getattr(t, "tid", ti) or ti),
                        "card_index": int((getattr(self, "display_cols", []) or []).index(ti)) if ti in (getattr(self, "display_cols", []) or []) else int(ti),
                        "layer_index": int(interval_index),
                        "x_range": (float(x0), float(x1)),
                        "y_range": (float(ty0), float(ty1)),
                    },
                )
            self._layer_plot_hitbox.append({"kind": "interval", "ti": ti, "interval_index": int(interval_index), "ige_id": ige_id, "top": float(lt), "bot": float(lb), "bbox": (x0, ty0, x1, ty1)})
            label_spans.append({
                "x0": x0,
                "x1": x1,
                "y0": ty0,
                "y1": ty1,
                "ige": str(ige_id),
                "ti": int(ti),
                "depth": (float(lt) + float(lb)) * 0.5,
            })
        return label_spans

    def _draw_layer_label_chip(self, span: dict, tags):
        x0 = float(span.get("x0", 0.0))
        x1 = float(span.get("x1", 0.0))
        y0 = float(span.get("y0", 0.0))
        y1 = float(span.get("y1", 0.0))
        text = str(span.get("ige", "") or "")
        ti_raw = span.get("ti", -1)
        ti = -1 if ti_raw is None else int(ti_raw)
        depth = float(span.get("depth", 0.0) or 0.0)
        if not text or x1 <= x0 or y1 <= y0:
            return
        available_h = y1 - y0
        if available_h < 8.0:
            return
        cx = (x0 + x1) * 0.5
        cy = (y0 + y1) * 0.5
        max_w = max(8.0, (x1 - x0) - 8.0)
        max_h = max(8.0, available_h - 2.0)
        for font_size in (8, 7, 6):
            font = ("Segoe UI", font_size, "bold")
            f = tkfont.Font(font=font)
            tw = float(f.measure(text))
            th = float(f.metrics("linespace"))
            pad_x = 4.0
            pad_y = 2.0
            chip_w = tw + pad_x * 2.0
            chip_h = th + pad_y * 2.0
            if chip_w <= max_w and chip_h <= max_h:
                self.canvas.create_rectangle(
                    cx - chip_w * 0.5,
                    cy - chip_h * 0.5,
                    cx + chip_w * 0.5,
                    cy + chip_h * 0.5,
                    fill=LAYER_UI_COLORS["fill"],
                    outline=LAYER_UI_COLORS["outline"],
                    width=1,
                    activefill=LAYER_UI_COLORS["fill_active"],
                    activeoutline=LAYER_UI_COLORS["outline_active"],
                    tags=tags,
                )
                self.canvas.create_text(
                    cx,
                    cy,
                    text=text,
                    fill=LAYER_UI_COLORS["text"],
                    activefill=LAYER_UI_COLORS["text"],
                    font=font,
                    tags=tags,
                )
                try:
                    self._layer_label_hitbox.append({
                        "ti": int(ti),
                        "depth": float(depth),
                        "bbox": (
                            float(cx - chip_w * 0.5 - 3.0),
                            float(cy - chip_h * 0.5 - 2.0),
                            float(cx + chip_w * 0.5 + 3.0),
                            float(cy + chip_h * 0.5 + 2.0),
                        ),
                    })
                except Exception:
                    pass
                return

    def _draw_graph_lines_for_test(self, ti: int, rect, y_points, qc_mpa, fs_kpa, qmax: float, fmax: float):
        x0, x1, y0, y1 = rect
        tag_qc = ("graph_qc", f"graph_qc_{ti}")
        tag_fs = ("graph_fs", f"graph_fs_{ti}")
        tag_nodata = ("graph_nodata", f"graph_nodata_{ti}")

        if not y_points:
            self.canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2, text="нет данных", fill="#666", font=("Segoe UI", 8), tags=tag_nodata)
            return
        qmax = max(float(qmax), 0.1)
        fmax = max(float(fmax), 1.0)

        pad = 8
        xa0 = x0 + pad
        xa1 = x1 - pad

        def _sx(v, vmax):
            return xa0 + (max(0.0, min(v, vmax)) / vmax) * (xa1 - xa0)

        qc_pts = []
        fs_pts = []
        for yy, qv, fv in zip(y_points, qc_mpa, fs_kpa):
            if yy < y0 - 1e-6 or yy > y1 + 1e-6:
                continue
            qc_pts.extend([_sx(qv, qmax), yy])
            fs_pts.extend([_sx(fv, fmax), yy])

        if len(qc_pts) >= 4:
            self.canvas.create_line(*qc_pts, fill=GRAPH_QC_GREEN, width=2, smooth=False, tags=tag_qc)
        if len(fs_pts) >= 4:
            self.canvas.create_line(*fs_pts, fill=GRAPH_FS_BLUE, width=2, smooth=False, tags=tag_fs)

    def _draw_groundwater_line_for_test(self, ti: int, rect):
        settings = dict(getattr(self, "cpt_calc_settings", {}) or {})
        gwl = settings.get("groundwater_level")
        if gwl in (None, ""):
            return
        try:
            gwl_val = float(str(gwl).replace(",", "."))
        except Exception:
            return
        y = self._depth_to_canvas_y(gwl_val)
        if y is None:
            return
        x0, x1, y0, y1 = rect
        if y < y0 or y > y1:
            return
        tags = ("graph_axes", f"graph_gwl_{ti}")
        self.canvas.create_line(x0 + 2, y, x1 - 2, y, fill="#2f6fff", width=2, dash=(6, 3), tags=tags)
        self.canvas.create_text(x1 - 4, y - 2, anchor="se", text=f"УГВ {gwl_val:.2f} м", fill="#2f6fff", font=("Segoe UI", 8, "bold"), tags=tags)

    def _redraw_graphs_now(self):
        self._graph_redraw_after_id = None
        self._clear_graph_layers()
        if not self._is_graph_panel_visible():
            return
        if not getattr(self, "tests", None):
            return

        self._calc_layer_params_for_all_tests()
        self._recompute_graph_scales()
        self._layer_handle_hitbox = []
        self._layer_depth_box_hitbox = []
        self._layer_plot_hitbox = []
        self._layer_label_hitbox = []

        self._refresh_display_order()
        for ti in (getattr(self, "expanded_cols", []) or []):
            rect = self._graph_rect_for_test(ti)
            if not rect:
                continue
            x0, x1, y0, y1 = rect
            t = self.tests[ti]
            show_graphs = bool(getattr(self, "show_graphs", False))
            show_geology = bool(getattr(self, "show_geology_column", True))

            y_points = []
            qc_vals = []
            fs_vals = []
            qarr = getattr(t, "qc", []) or []
            farr = getattr(t, "fs", []) or []
            units = getattr(self, "_grid_units", []) or []
            disp_map = (getattr(self, "_grid_row_maps", {}) or {}).get(ti, {}) or {}

            for disp_r, unit in enumerate(units):
                y0r, y1r = self._row_y_bounds(disp_r)
                row_h_cur = max(1.0, float(y1r - y0r))
                if unit[0] == "row":
                    di = disp_map.get(disp_r)
                    if di is None:
                        continue
                    q_raw = _parse_cell_int(qarr[di]) if di < len(qarr) else None
                    f_raw = _parse_cell_int(farr[di]) if di < len(farr) else None
                    if q_raw is None and f_raw is None:
                        continue
                    qc_mpa, fs_kpa = self._calc_qc_fs_from_del(int(q_raw or 0), int(f_raw or 0))
                    y_points.append(y0r + (row_h_cur * 0.5))
                    qc_vals.append(float(qc_mpa))
                    fs_vals.append(float(fs_kpa))
                elif unit[0] == "meter":
                    meter_n = int(unit[1])
                    for di in range(max(len(qarr), len(farr))):
                        dv = self._depth_at_index(t, di)
                        if dv is None or not (meter_n <= dv < (meter_n + 1)):
                            continue
                        q_raw = _parse_cell_int(qarr[di]) if di < len(qarr) else None
                        f_raw = _parse_cell_int(farr[di]) if di < len(farr) else None
                        if q_raw is None and f_raw is None:
                            continue
                        qc_mpa, fs_kpa = self._calc_qc_fs_from_del(int(q_raw or 0), int(f_raw or 0))
                        frac = max(0.0, min(0.999, float(dv) - float(meter_n)))
                        y_points.append(y0r + (frac * row_h_cur))
                        qc_vals.append(float(qc_mpa))
                        fs_vals.append(float(fs_kpa))

            plot_rect = (x0, x1, y0, y1)
            tag_axes = ("graph_axes", f"graph_axes_{ti}")
            tag_overlay = ("layers_overlay", f"layers_overlay_{ti}")
            self.canvas.create_rectangle(x0, y0, x1, y1, fill="#fbfdff", outline=GUI_GRID, tags=tag_axes)
            labels = []
            if show_geology:
                labels = self._draw_layers_overlay_for_test(ti, plot_rect, self._depth_to_canvas_y, tag_overlay) or []
            if not y_points:
                if show_graphs:
                    self._draw_graph_axes_for_test(ti, x0, x1, self.graph_qc_max_mpa, self.graph_fs_max_kpa)
                    self._draw_groundwater_line_for_test(ti, plot_rect)
                    self._draw_graph_lines_for_test(ti, plot_rect, [], [], [], self.graph_qc_max_mpa, self.graph_fs_max_kpa)
                for span in labels:
                    self._draw_layer_label_chip(span, tag_overlay)
                if show_geology:
                    self._draw_layer_handles_for_test(ti, plot_rect)
                continue
            packed = sorted(zip(y_points, qc_vals, fs_vals), key=lambda x: x[0])
            y_points = [x[0] for x in packed]
            qc_vals = [x[1] for x in packed]
            fs_vals = [x[2] for x in packed]

            if show_graphs:
                self._draw_graph_axes_for_test(ti, x0, x1, self.graph_qc_max_mpa, self.graph_fs_max_kpa)
                self._draw_groundwater_line_for_test(ti, plot_rect)
                self._draw_graph_lines_for_test(
                    ti,
                    plot_rect,
                    y_points,
                    qc_vals,
                    fs_vals,
                    self.graph_qc_max_mpa,
                    self.graph_fs_max_kpa,
                )
            for span in labels:
                self._draw_layer_label_chip(span, tag_overlay)
            if show_geology:
                self._draw_layer_handles_for_test(ti, plot_rect)
            if bool(getattr(self, "_debug_layers_overlay", False)) and bool(getattr(self, "compact_1m", False)) and bool(getattr(self, "expanded_meters", set())):
                t_layers = self._ensure_test_layers(t)
                dbg = f"LAYERS:{len(t_layers)} EDIT:True TEST:{getattr(t, 'tid', ti)}"
                self.canvas.create_text(x0 + 4, y0 + 4, anchor="nw", text=dbg, fill="#8a3d00", font=("Segoe UI", 8, "bold"), tags=("layers_overlay", f"layers_overlay_{ti}"))

    def _draw_layer_handles_for_test(self, ti: int, rect):
        if self._is_test_locked(ti):
            return
        t = self.tests[ti]
        column = self._ensure_test_experience_column(t)
        x0, x1, _y0, _y1 = rect
        # Ручка границы: центр по правому краю колонки слоёв, слегка внутри.
        handle_x = x1 - 2
        plus_x = x0 + 10

        def _draw_plus(tag: str, y_pos: float, boundary: int, kind: str, *, active: bool = True, x_pos: float | None = None):
            px = float(plus_x if x_pos is None else x_pos)
            box_fill = LAYER_UI_COLORS["fill"] if active else LAYER_UI_COLORS["fill"]
            box_outline = LAYER_UI_COLORS["outline"] if active else LAYER_UI_COLORS["outline"]
            text_fill = LAYER_UI_COLORS["text"] if active else LAYER_UI_COLORS["text_muted"]
            self.canvas.create_rectangle(
                px - 6,
                y_pos - 6,
                px + 6,
                y_pos + 6,
                fill=box_fill,
                outline=box_outline,
                width=1,
                activefill=(LAYER_UI_COLORS["fill_active"] if active else box_fill),
                activeoutline=(LAYER_UI_COLORS["outline_active"] if active else box_outline),
                tags=("layer_handles", "layer_plus_box", tag),
            )
            self.canvas.create_text(
                px,
                y_pos,
                text="+",
                fill=text_fill,
                activefill=text_fill,
                font=("Segoe UI", 9, "bold"),
                tags=("layer_handles", "layer_plus", tag),
            )
            if active:
                self._layer_handle_hitbox.append({"kind": kind, "ti": ti, "boundary": int(boundary), "tag": tag, "bbox": (px - 10, y_pos - 10, px + 10, y_pos + 10)})

        def _draw_minus(tag: str, y_pos: float, boundary: int, kind: str, *, active: bool = True, x_pos: float | None = None):
            px = float(plus_x if x_pos is None else x_pos)
            box_fill = LAYER_UI_COLORS["fill"] if active else LAYER_UI_COLORS["fill"]
            box_outline = LAYER_UI_COLORS["outline"] if active else LAYER_UI_COLORS["outline"]
            text_fill = LAYER_UI_COLORS["text"] if active else LAYER_UI_COLORS["text_muted"]
            self.canvas.create_rectangle(
                px - 6,
                y_pos - 6,
                px + 6,
                y_pos + 6,
                fill=box_fill,
                outline=box_outline,
                width=1,
                activefill=(LAYER_UI_COLORS["fill_active"] if active else box_fill),
                activeoutline=(LAYER_UI_COLORS["outline_active"] if active else box_outline),
                tags=("layer_handles", "layer_minus_box", tag),
            )
            self.canvas.create_text(
                px,
                y_pos,
                text="−",
                fill=text_fill,
                activefill=text_fill,
                font=("Segoe UI", 9, "bold"),
                tags=("layer_handles", "layer_minus", tag),
            )
            if active:
                self._layer_handle_hitbox.append({"kind": kind, "ti": ti, "boundary": int(boundary), "tag": tag, "bbox": (px - 10, y_pos - 10, px + 10, y_pos + 10)})

        if column.intervals:
            top_y = self._depth_to_canvas_y(float(column.intervals[0].from_depth))
            bot_y = self._depth_to_canvas_y(float(column.intervals[-1].to_depth))
            if top_y is not None:
                _draw_plus(f"layer_plus_top_{ti}", top_y + 6, 0, "plus_top", active=self._can_insert_layer_from_top(int(ti)))
            if bot_y is not None:
                end_tag = f"layer_end_handle_{ti}"
                self.canvas.create_line(
                    x0,
                    bot_y,
                    x1,
                    bot_y,
                    fill=LAYER_UI_COLORS["line"],
                    width=1,
                    dash=(3, 2),
                    tags=("layer_handles", "layer_boundary_line"),
                )
                self.canvas.create_rectangle(
                    handle_x - 5,
                    bot_y - 5,
                    handle_x + 5,
                    bot_y + 5,
                    fill=LAYER_UI_COLORS["fill"],
                    outline=LAYER_UI_COLORS["outline"],
                    width=1,
                    activefill=LAYER_UI_COLORS["fill_active"],
                    activeoutline=LAYER_UI_COLORS["outline_active"],
                    activewidth=2,
                    tags=("layer_handles", "layer_handle", end_tag),
                )
                bx0 = handle_x - 52
                bx1 = handle_x - 12
                self.canvas.create_rectangle(
                    bx0,
                    bot_y - 8,
                    bx1,
                    bot_y + 8,
                    fill=LAYER_UI_COLORS["fill"],
                    outline=LAYER_UI_COLORS["outline"],
                    width=1,
                    activefill=LAYER_UI_COLORS["fill_active"],
                    activeoutline=LAYER_UI_COLORS["outline_active"],
                    tags=("layer_handles", "layer_depth_box", end_tag),
                )
                self.canvas.create_text(
                    (bx0 + bx1) / 2,
                    bot_y,
                    text=f"{float(column.column_depth_end):.2f}",
                    fill=LAYER_UI_COLORS["text"],
                    activefill=LAYER_UI_COLORS["text"],
                    font=("Segoe UI", 7),
                    tags=("layer_handles", "layer_depth_label", end_tag),
                )
                self._layer_handle_hitbox.append({"kind": "column_end", "ti": ti, "boundary": int(len(column.intervals)), "tag": end_tag, "bbox": (handle_x - 6, bot_y - 6, handle_x + 6, bot_y + 6)})
                self._layer_depth_box_hitbox.append({"kind": "column_end_depth_edit", "ti": ti, "boundary": int(len(column.intervals)), "bbox": (bx0, bot_y - 9, bx1, bot_y + 9)})
                _draw_plus(f"layer_plus_bottom_{ti}", bot_y, len(column.intervals), "plus_bottom", active=self._can_insert_layer_from_bottom(int(ti)))
                _draw_minus(f"layer_minus_bottom_{ti}", bot_y, len(column.intervals) - 1, "minus_bottom", active=(len(column.intervals) > 1), x_pos=(plus_x + 14))

        for bi in range(1, len(column.intervals)):
            boundary = column.intervals[bi].from_depth
            y = self._depth_to_canvas_y(boundary)
            if y is None:
                continue
            h_tag = f"layer_handle_{ti}_{bi}"
            p_tag = f"layer_plus_{ti}_{bi}"
            m_tag = f"layer_minus_{ti}_{bi}"
            self.canvas.create_line(
                x0,
                y,
                x1,
                y,
                fill=LAYER_UI_COLORS["line"],
                width=1,
                dash=(3, 2),
                tags=("layer_handles", "layer_boundary_line"),
            )
            self.canvas.create_rectangle(
                handle_x - 5,
                y - 5,
                handle_x + 5,
                y + 5,
                fill=LAYER_UI_COLORS["fill"],
                outline=LAYER_UI_COLORS["outline"],
                width=1,
                activefill=LAYER_UI_COLORS["fill_active"],
                activeoutline=LAYER_UI_COLORS["outline_active"],
                activewidth=2,
                tags=("layer_handles", "layer_handle", h_tag),
            )
            bx0 = handle_x - 52
            bx1 = handle_x - 12
            self.canvas.create_rectangle(
                bx0,
                y - 8,
                bx1,
                y + 8,
                fill=LAYER_UI_COLORS["fill"],
                outline=LAYER_UI_COLORS["outline"],
                width=1,
                activefill=LAYER_UI_COLORS["fill_active"],
                activeoutline=LAYER_UI_COLORS["outline_active"],
                tags=("layer_handles", "layer_depth_box", h_tag),
            )
            self.canvas.create_text(
                (bx0 + bx1) / 2,
                y,
                text=f"{float(boundary):.2f}",
                fill=LAYER_UI_COLORS["text"],
                activefill=LAYER_UI_COLORS["text"],
                font=("Segoe UI", 7),
                tags=("layer_handles", "layer_depth_label", h_tag),
            )
            self._layer_handle_hitbox.append({"kind": "boundary", "ti": ti, "boundary": bi, "tag": h_tag, "bbox": (handle_x - 6, y - 6, handle_x + 6, y + 6)})
            self._layer_depth_box_hitbox.append({"kind": "boundary_depth_edit", "ti": ti, "boundary": bi, "bbox": (bx0, y - 9, bx1, y + 9)})
            _draw_plus(p_tag, y, bi, "plus", active=self._can_split_layer_index(int(ti), int(bi)))
            _draw_minus(m_tag, y + 14, bi, "minus", active=(len(column.intervals) > 1))

    def _draw_graph_layers(self):
        self._redraw_graphs_now()

    def _on_left_click(self, event):
        self._evt_widget = event.widget
        hit = self._hit_test(event.x, event.y)
        if getattr(self, "_boundary_depth_editor", None):
            editor_widget = (self._boundary_depth_editor or {}).get("entry") if isinstance(self._boundary_depth_editor, dict) else self._boundary_depth_editor
            if not hit or hit[0] != "layer_boundary_depth_edit":
                if event.widget is not editor_widget:
                    self._close_boundary_depth_editor()
        if not hit:
            # клик вне ячеек/шапки → закрываем активное редактирование
            self._end_edit(commit=True)
            self._hide_canvas_tip()
            return
        kind, ti, row, field = hit
        self._hide_layer_ige_picker(reason="left_click")
        if ti is not None:
            self._active_test_idx = int(ti)
            self._sync_layers_panel()
            self.schedule_graph_redraw()

        # Любой клик по UI (иконки/пустые/глубина) сначала закрывает активную ячейку
        # (кроме случая, когда мы тут же откроем новое редактирование).
        try:
            if getattr(self, '_editing', None):
                # не закрываем, если клик по текущему Entry
                ed = self._editing[3] if len(self._editing) >= 4 else None
                if ed is None or event.widget is not ed:
                    self._end_edit(commit=True)
        except Exception:
            pass

        if kind == "lock":
            self._toggle_test_lock(int(ti))
            return

        # --- Header controls (icons / checkbox) ---
        if kind == "edit":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            self._edit_header(ti)
            return
        if kind == "rename":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            self._edit_header_title(ti)
            return
        if kind == "dup":
            if not self._header_action_buttons_enabled(int(ti)):
                self._set_status("Кнопка недоступна для свёрнутого/заблокированного опыта")
                return
            self._duplicate_test(ti)
            return
        if kind == "trash":
            if not self._header_action_buttons_enabled(int(ti)):
                self._set_status("Кнопка недоступна для свёрнутого/заблокированного опыта")
                return
            self._delete_test(ti)
            return
        if kind == "export":
            try:
                self._push_undo()
                t = self.tests[ti]
                t.export_on = not bool(getattr(t, "export_on", True))
            except Exception:
                pass
            try:
                self._recompute_statuses_after_data_load(preview_mode=False)
            except Exception:
                self._update_footer_realtime()
                self._redraw()
            self._hide_canvas_tip()
            self.schedule_graph_redraw()
            return

        if kind == "layer_plus":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            self._insert_layer_at_boundary(ti, row)
            return
        if kind == "layer_plus_top":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            if not self._can_insert_layer_from_top(int(ti)):
                return
            self._insert_layer_from_top(ti)
            return
        if kind == "layer_plus_bottom":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            if not self._can_insert_layer_from_bottom(int(ti)):
                return
            self._insert_layer_from_bottom(ti)
            return
        if kind == "layer_minus_top":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            self._push_undo()
            self._remove_layer_from_top(ti)
            return
        if kind == "layer_minus_bottom":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            self._push_undo()
            self._remove_layer_from_bottom(ti)
            return
        if kind == "layer_minus":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            self._push_undo()
            self._remove_layer_at_index(int(ti), int(row))
            return
        if kind == "layer_boundary":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            self._push_undo()
            self._layer_drag = {"ti": int(ti), "boundary": int(row), "mode": "boundary"}
            return
        if kind == "layer_column_end":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            self._push_undo()
            self._layer_drag = {"ti": int(ti), "boundary": int(row), "mode": "column_end"}
            return
        if kind == "layer_boundary_depth_edit":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            self._open_boundary_depth_editor(int(ti), int(row))
            return "break"
        if kind == "layer_column_end_depth_edit":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            self._open_boundary_depth_editor(int(ti), int(row))
            return "break"
        if kind == "layer_interval":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            # Fallback: если hit-test попал в interval рядом с чипом ИГЭ,
            # открываем picker как для label-клика.
            try:
                cx = float(self.canvas.canvasx(event.x))
                cy = float(self.canvas.canvasy(event.y))
                label_hit = None
                for hit in (getattr(self, "_layer_label_hitbox", []) or []):
                    if int(hit.get("ti", -1)) != int(ti):
                        continue
                    bx0, by0, bx1, by1 = hit.get("bbox", (0.0, 0.0, 0.0, 0.0))
                    if (bx0 - 12.0) <= cx <= (bx1 + 12.0) and (by0 - 6.0) <= cy <= (by1 + 6.0):
                        label_hit = (float(hit.get("depth", 0.0)), (bx0, by0, bx1, by1))
                        break
                if label_hit is not None:
                    depth_hit, bbox_hit = label_hit
                    self._ige_picker_log(f"click_resolved ti={int(ti)} source=layer_interval_near_label depth={float(depth_hit):.4f}")
                    self._open_experience_column_editor(int(ti))
                    return
            except Exception:
                pass

            # Клик по телу слоя только выбирает опыт/слой, но не открывает picker ИГЭ.
            try:
                layers = self._ensure_test_experience_column(self.tests[int(ti)]).intervals
                depth = float(field if field is not None else 0.0)
                target = next((lyr for lyr in layers if float(lyr.from_depth) <= depth <= float(lyr.to_depth)), None)
                if target is not None:
                    self._select_ige_for_ribbon(self._column_interval_ige_id(target))
            except Exception:
                pass
            return
        if kind == "layer_label":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            meta = field if isinstance(field, dict) else {}
            self._ige_picker_log(f"click_resolved ti={int(ti)} source=layer_label depth={float(meta.get('depth', 0.0) if meta else 0.0):.4f}")
            self._open_experience_column_editor(int(ti))
            return
        if kind == "meter_row":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            self._toggle_meter_expanded(int(field), push_undo=True)
            return

        # --- Single-click cell edit (ironclad) ---
        if kind == "cell" and ti is not None and row is not None:
            mp = (getattr(self, "_grid_row_maps", {}) or {}).get(ti, {})
            # Depth: single click on the first depth cell opens "start depth" editor
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return

            if field == "depth":
                data_row0 = mp.get(row, None)
                if data_row0 == 0:
                    self._begin_edit_depth0(ti, display_row=row)
                    return
                meter_n = self._expanded_meter_for_depth_cell(ti, row)
                if meter_n is not None:
                    self._toggle_meter_expanded(meter_n, push_undo=True)
                    return
                return

            # qc/fs cells
            data_row = mp.get(row, None)
            if data_row is None:
                return


            # Normal in-range cell → start edit immediately
            if field in ("qc", "fs"):
                if not self._is_real_interval_cell(int(ti), int(row), str(field)):
                    return
                if self._is_test_locked(int(ti)):
                    self._set_status("Опыт заблокирован")
                    return
                self._begin_edit(ti, data_row, field, display_row=row)
                self.schedule_graph_redraw()
            return

        # otherwise: click ends edit (commit)
        self._end_edit(commit=True)


    def _on_global_click(self, event):
        """Закрывает активную ячейку при клике вне зондирования/ячейки."""
        try:
            if bool(getattr(self, "_inline_edit_active", False)):
                editor_widget = (self._boundary_depth_editor or {}).get("entry") if isinstance(self._boundary_depth_editor, dict) else None
                if event.widget is editor_widget:
                    return
                if bool(getattr(self, "_editor_just_opened", False)):
                    return
                if event.widget not in (getattr(self, "canvas", None), getattr(self, "hcanvas", None)):
                    self._close_boundary_depth_editor(commit=False)
                    return
            if getattr(self, "_boundary_depth_editor", None):
                editor_widget = (self._boundary_depth_editor or {}).get("entry") if isinstance(self._boundary_depth_editor, dict) else self._boundary_depth_editor
                if event.widget is editor_widget:
                    return
                if not bool(getattr(self, "_editor_just_opened", False)) and event.widget not in (getattr(self, "canvas", None), getattr(self, "hcanvas", None)):
                    self._close_boundary_depth_editor()
            if not self._editing:
                return
            # если клик по текущему Entry — не закрываем
            ed = None
            if len(self._editing) >= 4:
                ed = self._editing[3]
            if ed is not None and event.widget is ed:
                return
            # если клик по canvas/hcanvas — пусть _on_left_click решит (мы просто закрываем заранее)
            # но чтобы не мешать клику по ячейке, закрываем только когда клик НЕ по canvas/hcanvas
            if event.widget in (getattr(self, "canvas", None), getattr(self, "hcanvas", None)):
                return
            self._end_edit(commit=True)
        except Exception:
            pass
    def _set_hover(self, hover):
        if bool(getattr(self, "_inline_edit_active", False)):
            return
        # hover: ("dup"/"trash", test_index) or None
        if getattr(self, "_hover", None) == hover:
            return
        self._hover = hover
        self._hide_canvas_tip()
        # redraw only when state changed
        self._redraw()

    def _hide_canvas_tip(self):
        if getattr(self, "_hover_after", None):
            try:
                self.after_cancel(self._hover_after)
            except Exception:
                pass
            self._hover_after = None
        tip = getattr(self, "_hover_tip", None)
        if tip is not None:
            try:
                tip.destroy()
            except Exception:
                pass
            self._hover_tip = None

    def _schedule_canvas_tip(self, text: str, x_root: int, y_root: int, delay_ms: int = 2000):
        self._hide_canvas_tip()
        def _show():
            # small native-ish tooltip
            tw = tk.Toplevel(self)
            tw.overrideredirect(True)
            tw.attributes("-topmost", True)
            lbl = ttk.Label(tw, text=text, padding=(8, 4))
            lbl.pack()
            tw.update_idletasks()
            tw.geometry(f"+{x_root + 12}+{y_root + 14}")
            self._hover_tip = tw
        self._hover_after = self.after(delay_ms, _show)

    def _ige_picker_log(self, msg: str):
        if not bool(getattr(self, "_ige_picker_debug", False)):
            return
        try:
            print(f"[IGE_PICKER] {msg}")
        except Exception:
            pass

    def _hide_layer_ige_picker(self, reason: str | None = None):
        win = getattr(self, "_layer_ige_picker", None)
        meta = getattr(self, "_layer_ige_picker_meta", None)
        self._ige_picker_log(f"hide reason={reason or 'unspecified'} has_win={win is not None} meta={meta}")
        if win is not None:
            try:
                self._ige_picker_log(f"hide destroying id={id(win)} exists_before={bool(win.winfo_exists())} geom={win.winfo_geometry() if win.winfo_exists() else 'n/a'}")
            except Exception:
                pass
            try:
                win.destroy()
            except Exception as ex:
                self._ige_picker_log(f"hide destroy_error={ex!r}")
        self._layer_ige_picker = None
        self._layer_ige_picker_meta = None

    def _show_ige_picker_at_click(self, event, ti: int, depth: float, *, anchor_bbox=None):
        self._ige_picker_log(
            f"show ti={ti} depth={float(depth):.4f} evt_xy=({getattr(event, 'x', None)},{getattr(event, 'y', None)}) "
            f"evt_root=({getattr(event, 'x_root', None)},{getattr(event, 'y_root', None)}) active={getattr(self, '_active_test_idx', None)} hover={getattr(self, '_hover', None)}"
        )
        if ti < 0 or ti >= len(self.tests):
            self._ige_picker_log("show aborted: ti out of range")
            return
        layers = self._ensure_test_layers(self.tests[ti])
        target = None
        eps = 1e-6
        for lyr in layers:
            if float(lyr.top_m) - eps <= depth <= float(lyr.bot_m) + eps:
                target = lyr
                break
        if target is None and layers:
            # fallback: выбираем ближайший слой по центру, чтобы клик по label всегда открывал picker
            target = min(layers, key=lambda lyr: abs(((float(lyr.top_m) + float(lyr.bot_m)) * 0.5) - float(depth)))
        if target is None:
            self._ige_picker_log("show aborted: target layer not resolved")
            return
        picker_meta = (int(ti), str(self._layer_ige_id(target)))
        if getattr(self, "_layer_ige_picker", None) is not None and getattr(self, "_layer_ige_picker_meta", None) == picker_meta:
            self._ige_picker_log(f"show skip recreate: same meta={picker_meta}")
            return
        self._hide_layer_ige_picker(reason="show_open_new")
        win = tk.Toplevel(self)
        win.overrideredirect(True)
        values = []
        value_to_ige_id: dict[str, str] = {}
        ids = sorted(self.ige_registry.keys(), key=self._ige_id_to_num)
        for ige_id in ids:
            self._ensure_ige_entry(ige_id)
            display = self._ige_display_label(ige_id)
            values.append(display)
            value_to_ige_id[display] = str(ige_id)
        cb = ttk.Combobox(win, state="readonly", values=values)
        current_ige = self._layer_ige_id(target)
        self._ensure_ige_entry(current_ige)
        current_label = self._ige_display_label(current_ige)
        if current_label in values:
            cb.set(current_label)
        def _canvas_to_root(xc: float, yc: float) -> tuple[int, int]:
            # Перевод canvas-координат (с учетом текущего x/y scroll) в root-screen координаты.
            vx = float(self.canvas.canvasx(0.0))
            vy = float(self.canvas.canvasy(0.0))
            rx = int(self.canvas.winfo_rootx() + (float(xc) - vx))
            ry = int(self.canvas.winfo_rooty() + (float(yc) - vy))
            return rx, ry

        gx0 = int(event.x_root)
        gy0 = int(event.y_root)
        col_w = 240
        try:
            root_x0 = int(self.winfo_rootx())
            root_y0 = int(self.winfo_rooty())
            root_w = int(self.winfo_width())
            root_h = int(self.winfo_height())
            self._ige_picker_log(f"bbox root=({root_x0},{root_y0},{root_w},{root_h}) anchor_bbox={anchor_bbox}")
        except Exception:
            pass
        try:
            rect = self._graph_rect_for_test(int(ti))
            if rect:
                x0, x1, y0r, _y1r = rect
                gx0, gy_guess = _canvas_to_root(float(x0), float(y0r))
                col_w = max(80, int(float(x1) - float(x0)))
                gy0 = int(gy_guess)
                self._ige_picker_log(f"bbox column rect=({x0:.1f},{x1:.1f},{y0r:.1f},{_y1r:.1f}) gx0={gx0} gy0={gy0} col_w={col_w}")
        except Exception:
            pass

        # В обоих режимах ширина = ширина колонки слоя;
        # в свернутом режиме вертикаль привязываем к bbox надписи, чтобы popup не "улетал".
        if anchor_bbox is not None:
            try:
                bx0, by0, _bx1, _by1 = anchor_bbox
                _rx, gy0 = _canvas_to_root(float(bx0), float(by0))
            except Exception:
                gy0 = int(event.y_root)

        pre_clamp = (int(gx0), int(gy0))
        # Не даем popup уходить за пределы окна редактора (и экрана как fallback).
        try:
            root_x0 = int(self.winfo_rootx())
            root_y0 = int(self.winfo_rooty())
            root_x1 = root_x0 + int(max(1, self.winfo_width()))
            root_y1 = root_y0 + int(max(1, self.winfo_height()))
            gx0 = max(root_x0, min(int(gx0), max(root_x0, root_x1 - int(col_w) - 2)))
            gy0 = max(root_y0, min(int(gy0), max(root_y0, root_y1 - 28)))
            self._ige_picker_log(f"place clamp_window pre={pre_clamp} post=({gx0},{gy0}) root=({root_x0},{root_y0},{root_x1-root_x0},{root_y1-root_y0})")
        except Exception:
            try:
                sw = int(self.winfo_screenwidth())
                sh = int(self.winfo_screenheight())
                gx0 = max(0, min(int(gx0), max(0, sw - int(col_w) - 4)))
                gy0 = max(0, min(int(gy0), max(0, sh - 28)))
                self._ige_picker_log(f"place clamp_screen pre={pre_clamp} post=({gx0},{gy0}) screen=({sw},{sh})")
            except Exception:
                pass

        cb.configure(width=max(10, int((col_w - 12) / 8)))
        try:
            self._ige_picker_log(f"created id={id(win)} exists={bool(win.winfo_exists())} req=({win.winfo_reqwidth()},{win.winfo_reqheight()}) geom_before={win.winfo_geometry()}")
        except Exception:
            pass
        cb.pack(fill="x")
        win.geometry(f"{col_w}x24+{gx0}+{gy0}")
        try:
            self._ige_picker_log(f"place final=({gx0},{gy0}) col_w={col_w} geom_after={win.winfo_geometry()}")
        except Exception:
            pass

        def _after_probe(tag: str):
            w = getattr(self, "_layer_ige_picker", None)
            try:
                exists = bool(w is not None and w.winfo_exists())
                geom = w.winfo_geometry() if exists else "none"
                focus_w = self.focus_get()
                self._ige_picker_log(f"{tag} exists={exists} geom={geom} focus={focus_w}")
            except Exception as ex:
                self._ige_picker_log(f"{tag} probe_error={ex!r}")

        self.after_idle(lambda: _after_probe("after_idle"))
        self.after(50, lambda: _after_probe("after_50"))
        self.after(150, lambda: _after_probe("after_150"))

        def _on_focus_out(ev=None):
            try:
                self._ige_picker_log(f"focusout widget={getattr(ev, 'widget', None)} focus_now={self.focus_get()}")
            except Exception:
                pass

        win.bind("<FocusOut>", _on_focus_out, add="+")
        cb.bind("<FocusOut>", _on_focus_out, add="+")

        def _apply(_ev=None):
            label = str(cb.get() or "")
            ige_id = str(value_to_ige_id.get(label) or "").strip()
            if not ige_id:
                return
            self._push_undo()
            target.ige_id = ige_id
            self._apply_ige_to_layer(target)
            self.redraw_all()
            self._hide_layer_ige_picker(reason="apply_selected")

        cb.bind("<<ComboboxSelected>>", _apply)
        cb.bind("<Return>", _apply)
        cb.bind("<Escape>", lambda _e: self._hide_layer_ige_picker(reason="escape"))
        cb.focus_set()
        self._layer_ige_picker = win
        self._layer_ige_picker_meta = picker_meta

    def _open_experience_column_editor(self, ti: int):
        if ti < 0 or ti >= len(self.tests):
            return
        t = self.tests[int(ti)]
        column = self._ensure_test_experience_column(t)
        working_column = ExperienceColumn(
            column_depth_start=float(column.column_depth_start),
            column_depth_end=float(column.column_depth_end),
            intervals=[ColumnInterval(**column_interval_to_dict(item)) for item in column.intervals],
        )
        win = tk.Toplevel(self)
        win.title(f"Редактор колонки опыта — СЗ-{getattr(t, 'tid', ti)}")
        win.transient(self)
        win.grab_set()
        win.resizable(True, False)
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Интервалы колонки опыта", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        end_var = tk.StringVar(value=f"{float(working_column.column_depth_end):.2f}")
        end_row = ttk.Frame(frm)
        end_row.pack(fill="x", pady=(8, 8))
        ttk.Label(end_row, text="Глубина колонки до, м:").pack(side="left")
        ttk.Entry(end_row, textvariable=end_var, width=10).pack(side="left", padx=(8, 0))

        table = ttk.Frame(frm)
        table.pack(fill="both", expand=True)
        rows: list[dict[str, Any]] = []
        msg_var = tk.StringVar()
        max_intervals = MAX_LAYERS_PER_TEST
        min_thickness = 0.2
        input_pattern = re.compile(r"^\d*(?:[.,]\d{0,2})?$")

        def _clone_working() -> ExperienceColumn:
            return ExperienceColumn(
                column_depth_start=float(working_column.column_depth_start),
                column_depth_end=float(working_column.column_depth_end),
                intervals=[ColumnInterval(**column_interval_to_dict(item)) for item in working_column.intervals],
            )

        def _available_ige_values() -> list[tuple[str, str]]:
            return self._experience_column_ige_choices()

        def _find_ige_display(ige_id: str) -> str:
            for value, display in _available_ige_values():
                if value == ige_id:
                    return display
            return ige_id or "ИГЭ-1"

        def _set_working_column(new_column: ExperienceColumn):
            nonlocal working_column
            working_column = new_column
            end_var.set(f"{float(working_column.column_depth_end):.2f}")
            _sync_rows_from_column()
            msg_var.set("")

        def _parse_two_decimals(raw: str) -> float:
            value = str(raw or "").strip().replace(",", ".")
            if not value:
                raise ValueError("Введите глубину")
            if not input_pattern.fullmatch(value):
                raise ValueError("Допустимы только неотрицательные числа с максимум 2 знаками после запятой")
            parsed = float(value)
            if parsed < 0:
                raise ValueError("Глубина не может быть отрицательной")
            return round(parsed, 2)

        def _validate_depth_input(raw: str) -> bool:
            return input_pattern.fullmatch(str(raw or "")) is not None

        def _sync_rows_from_column():
            for idx, item in enumerate(working_column.intervals):
                if idx >= len(rows):
                    rows.append(
                        {
                            "from_var": tk.StringVar(),
                            "to_var": tk.StringVar(),
                            "ige_var": tk.StringVar(),
                        }
                    )
                rows[idx]["from_var"].set(f"{float(item.from_depth):.2f}")
                rows[idx]["to_var"].set(f"{float(item.to_depth):.2f}")
                rows[idx]["ige_var"].set(_find_ige_display(self._column_interval_ige_id(item)))
            del rows[len(working_column.intervals):]
            _rebuild_rows()

        def _apply_boundary_change(row_index: int, field_kind: str, *, restore_on_error: bool = True) -> bool:
            try:
                if field_kind == "from":
                    if row_index == 0:
                        rows[row_index]["from_var"].set("0.00")
                        return True
                    new_depth = _parse_two_decimals(rows[row_index]["from_var"].get())
                    new_column = move_experience_column_boundary(_clone_working(), row_index, new_depth)
                elif field_kind == "to":
                    if row_index < len(working_column.intervals) - 1:
                        new_depth = _parse_two_decimals(rows[row_index]["to_var"].get())
                        new_column = move_experience_column_boundary(_clone_working(), row_index + 1, new_depth)
                    else:
                        new_end = _parse_two_decimals(rows[row_index]["to_var"].get())
                        new_column = resize_experience_column_end(_clone_working(), new_end)
                else:
                    return False
            except Exception as ex:
                if restore_on_error:
                    msg_var.set(str(ex))
                    _sync_rows_from_column()
                return False
            _set_working_column(new_column)
            return True

        def _apply_ige_change(row_index: int):
            if not (0 <= row_index < len(working_column.intervals)):
                return
            current = self._column_interval_ige_id(working_column.intervals[row_index])
            ige_id = self._pick_existing_ige_for_column(parent=win, title="Выбор ИГЭ для интервала", current_ige_id=current)
            if not ige_id:
                _sync_rows_from_column()
                return
            clone = _clone_working()
            clone.intervals[row_index].ige_id = ige_id
            clone.intervals[row_index].ige_name = ige_id
            _set_working_column(normalize_column(clone, default_ige_id=self._column_interval_ige_id(clone.intervals[0])))

        def _rebuild_rows():
            for child in table.winfo_children():
                child.destroy()
            ttk.Label(table, text="От").grid(row=0, column=0, sticky="w", padx=(0, 8))
            ttk.Label(table, text="До").grid(row=0, column=1, sticky="w", padx=(0, 8))
            ttk.Label(table, text="ИГЭ").grid(row=0, column=2, sticky="w", padx=(0, 8))
            vcmd = (self.register(_validate_depth_input), "%P")
            for idx, row in enumerate(rows, start=1):
                grid_row = (idx * 2) - 1
                row["from_entry"] = ttk.Entry(table, textvariable=row["from_var"], width=10, validate="key", validatecommand=vcmd)
                row["to_entry"] = ttk.Entry(table, textvariable=row["to_var"], width=10, validate="key", validatecommand=vcmd)
                row["ige_btn"] = ttk.Button(table, textvariable=row["ige_var"], width=24, command=lambda i=idx - 1: _apply_ige_change(i))
                row["from_entry"].grid(row=grid_row, column=0, sticky="we", padx=(0, 8), pady=2)
                row["to_entry"].grid(row=grid_row, column=1, sticky="we", padx=(0, 8), pady=2)
                row["ige_btn"].grid(row=grid_row, column=2, sticky="we", padx=(0, 8), pady=2)
                row["from_entry"].bind("<FocusOut>", lambda _e, i=idx - 1: _apply_boundary_change(i, "from"))
                row["to_entry"].bind("<FocusOut>", lambda _e, i=idx - 1: _apply_boundary_change(i, "to"))
                row["from_entry"].bind("<Return>", lambda _e, i=idx - 1: _apply_boundary_change(i, "from"))
                row["to_entry"].bind("<Return>", lambda _e, i=idx - 1: _apply_boundary_change(i, "to"))
                if idx == 1:
                    row["from_entry"].state(["readonly"])
                if idx > 1:
                    ttk.Button(table, text="Удалить", command=lambda i=idx - 1: _delete_row(i)).grid(row=grid_row, column=3, sticky="e", pady=2)
                add_row = grid_row + 1
                add_label = "+ Добавить" if idx < len(rows) else "+ Добавить в низ"
                ttk.Button(table, text=add_label, command=lambda i=idx - 1: _insert_row_after(i)).grid(row=add_row, column=0, columnspan=4, sticky="w", pady=(0, 6))

        def _insert_row_after(index: int):
            if len(working_column.intervals) >= max_intervals:
                msg_var.set("Достигнут лимит 12 интервалов")
                return
            selected_ige_id = self._pick_existing_ige_for_column(parent=win, title="Выбор ИГЭ для нового интервала")
            if not selected_ige_id:
                return
            try:
                if index >= len(working_column.intervals) - 1:
                    new_column = append_bottom(_clone_working(), new_ige_id=selected_ige_id)
                else:
                    new_column = insert_between(_clone_working(), index + 1, new_ige_id=selected_ige_id)
            except Exception as ex:
                msg_var.set(str(ex))
                return
            _set_working_column(new_column)

        def _delete_row(index: int):
            if len(working_column.intervals) <= 1:
                return
            try:
                new_column = remove_column_interval(_clone_working(), index)
            except Exception as ex:
                msg_var.set(str(ex))
                return
            _set_working_column(new_column)

        def _apply_end_depth(*, restore_on_error: bool = True) -> bool:
            try:
                new_end = _parse_two_decimals(end_var.get())
                new_column = resize_experience_column_end(_clone_working(), new_end)
            except Exception as ex:
                if restore_on_error:
                    msg_var.set(str(ex))
                    end_var.set(f"{float(working_column.column_depth_end):.2f}")
                return False
            _set_working_column(new_column)
            return True

        for _ in working_column.intervals:
            rows.append({"from_var": tk.StringVar(), "to_var": tk.StringVar(), "ige_var": tk.StringVar()})
        _sync_rows_from_column()
        end_entry = end_row.winfo_children()[-1]
        end_entry.configure(validate="key", validatecommand=(self.register(_validate_depth_input), "%P"))
        end_entry.bind("<FocusOut>", lambda _e: _apply_end_depth())
        end_entry.bind("<Return>", lambda _e: _apply_end_depth())
        self._center_toplevel(win, parent=self)

        ttk.Label(frm, textvariable=msg_var, foreground="#b00020").pack(anchor="w", pady=(8, 0))

        def _commit_form() -> ExperienceColumn | None:
            if not _apply_end_depth(restore_on_error=False):
                msg_var.set("Проверьте глубину конца колонки")
                return None
            for idx in range(len(rows)):
                if not _apply_boundary_change(idx, "from", restore_on_error=False):
                    msg_var.set(f"Некорректная граница [от] в строке {idx + 1}")
                    _sync_rows_from_column()
                    return None
                if not _apply_boundary_change(idx, "to", restore_on_error=False):
                    msg_var.set(f"Некорректная граница [до] в строке {idx + 1}")
                    _sync_rows_from_column()
                    return None
            built = _clone_working()
            ige_error = self._validate_experience_column_iges(built)
            if ige_error:
                msg_var.set(ige_error)
                _sync_rows_from_column()
                return None
            return built

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(12, 0))
        def _apply_and_close():
            built = _commit_form()
            if built is None:
                return
            self._push_undo()
            t.experience_column = built
            self._redraw()
            self.schedule_graph_redraw()
            win.destroy()

        ttk.Button(btns, text="Отмена", command=win.destroy).pack(side="right")
        ttk.Button(btns, text="ОК", command=_apply_and_close).pack(side="right", padx=(0, 8))

    def _open_boundary_depth_editor(self, ti: int, boundary: int):
        if ti < 0 or ti >= len(self.tests):
            return
        if self._is_test_locked(ti):
            self._set_status("Опыт заблокирован")
            return
        self._close_boundary_depth_editor()
        self._editor_just_opened = True
        self._inline_edit_active = True
        target = None
        for hit in (self._layer_depth_box_hitbox or []):
            if int(hit.get("ti", -1)) == int(ti) and int(hit.get("boundary", -1)) == int(boundary):
                target = hit
                break
        if not target:
            self._inline_edit_active = False
            return
        bx0, by0, bx1, by1 = target.get("bbox", (0, 0, 0, 0))
        entry = tk.Entry(
            self,
            width=6,
            justify="center",
            bg=LAYER_UI_COLORS["fill"],
            fg="#111111",
            insertbackground="#111111",
            selectbackground="#2f80ed",
            selectforeground="#ffffff",
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=LAYER_UI_COLORS["outline"],
            highlightcolor=LAYER_UI_COLORS["focus"],
        )
        t = self.tests[ti]
        column = self._ensure_test_experience_column(t)
        is_column_end = int(boundary) >= len(column.intervals)
        if is_column_end:
            cur = float(column.column_depth_end)
            min_depth = max(0.0, float(column.intervals[-1].from_depth) + 0.2) if column.intervals else 0.2
            max_depth = None
        else:
            cur = float(column.intervals[boundary].from_depth) if 0 <= boundary < len(column.intervals) else 0.0
            prev_depth = float(column.intervals[boundary - 1].from_depth) if boundary - 1 >= 0 else float(column.intervals[0].from_depth)
            next_depth = float(column.intervals[boundary + 1].from_depth) if boundary + 1 < len(column.intervals) else float(column.intervals[-1].to_depth)
            min_depth = prev_depth + 0.2
            max_depth = next_depth - 0.2
        entry.insert(0, f"{cur:.2f}")
        self._place_boundary_depth_editor(entry, bx0, by0, bx1, by1)

        def _apply(_ev=None):
            try:
                val = float(str(entry.get()).replace(",", "."))
            except Exception:
                self._close_boundary_depth_editor()
                return
            snapped = round(val / 0.1) * 0.1
            if max_depth is None:
                snapped = max(min_depth, snapped)
            else:
                snapped = max(min_depth, min(max_depth, snapped))
            self._push_undo()
            if is_column_end:
                t.experience_column = resize_experience_column_end(self._ensure_test_experience_column(t), snapped)
            else:
                t.experience_column = move_experience_column_boundary(self._ensure_test_experience_column(t), int(boundary), snapped)
            self.redraw_all()
            self._close_boundary_depth_editor(commit=True)

        def _cancel(_ev=None):
            self._close_boundary_depth_editor(commit=False)

        entry.bind("<Return>", _apply)
        entry.bind("<Escape>", _cancel)
        entry.bind("<Button-1>", lambda _e: "break")
        entry.focus_set()
        entry.selection_range(0, tk.END)
        self._boundary_depth_editor = {"entry": entry, "ti": int(ti), "boundary": int(boundary)}
        self.after_idle(lambda: setattr(self, "_editor_just_opened", False))
        self.after(50, lambda: setattr(self, "_editor_just_opened", False))

    def _place_boundary_depth_editor(self, entry, bx0: float, by0: float, bx1: float, by1: float):
        try:
            vx0 = float(bx0) - float(self.canvas.canvasx(0))
            vy0 = float(by0) - float(self.canvas.canvasy(0))
            root_x = int(self.canvas.winfo_rootx() - self.winfo_rootx() + vx0)
            root_y = int(self.canvas.winfo_rooty() - self.winfo_rooty() + vy0)
            entry.place(
                x=root_x,
                y=root_y,
                width=max(44, int(bx1 - bx0)),
                height=max(18, int(by1 - by0)),
            )
        except Exception:
            pass

    def _reposition_boundary_depth_editor(self):
        ed = getattr(self, "_boundary_depth_editor", None)
        if not isinstance(ed, dict):
            return
        entry = ed.get("entry")
        ti = ed.get("ti")
        boundary = ed.get("boundary")
        if entry is None or ti is None or boundary is None:
            return
        target = None
        for hit in (self._layer_depth_box_hitbox or []):
            if int(hit.get("ti", -1)) == int(ti) and int(hit.get("boundary", -1)) == int(boundary):
                target = hit
                break
        if target:
            bx0, by0, bx1, by1 = target.get("bbox", (0, 0, 0, 0))
            self._place_boundary_depth_editor(entry, bx0, by0, bx1, by1)

    def _close_boundary_depth_editor(self, *, commit: bool = False):
        ed = getattr(self, "_boundary_depth_editor", None)
        if ed is not None:
            try:
                if isinstance(ed, dict):
                    entry = ed.get("entry")
                    if entry is not None:
                        try:
                            entry.place_forget()
                        except Exception:
                            pass
                        entry.destroy()
                else:
                    ed.destroy()
            except Exception:
                pass
        self._boundary_depth_editor = None
        self._editor_just_opened = False
        self._inline_edit_active = False

    def _insert_layer_at_boundary(self, ti: int, boundary: int):
        self._split_layer_for_plus(int(ti), int(boundary), from_bottom=False)

    def _insert_layer_from_top(self, ti: int):
        self._split_layer_for_plus(int(ti), 0, from_bottom=False)

    def _insert_layer_from_bottom(self, ti: int):
        t = self.tests[int(ti)] if (ti is not None and 0 <= int(ti) < len(self.tests)) else None
        if t is None:
            return
        column = self._ensure_test_experience_column(t)
        if not column.intervals:
            return
        self._split_layer_for_plus(int(ti), len(column.intervals) - 1, from_bottom=True)

    def _can_split_layer(self, lyr) -> bool:
        # Минимальная валидная мощность слоя = 0.20 м.
        # Для '+' слой должен делиться на 2 валидных слоя => минимум 0.40 м.
        try:
            top = float(getattr(lyr, "top_m", getattr(lyr, "from_depth", 0.0)))
            bot = float(getattr(lyr, "bot_m", getattr(lyr, "to_depth", 0.0)))
            return (bot - top) >= (0.4 - 1e-9)
        except Exception:
            return False

    def _can_split_layer_index(self, ti: int, layer_index: int) -> bool:
        if ti is None or ti < 0 or ti >= len(self.tests):
            return False
        t = self.tests[int(ti)]
        layers = list(self._ensure_test_experience_column(t).intervals)
        if not (0 <= int(layer_index) < len(layers)):
            return False
        return self._can_split_layer(layers[int(layer_index)])

    def _split_layer_for_plus(self, ti: int, layer_index: int, *, from_bottom: bool = False):
        if ti is None or ti < 0 or ti >= len(self.tests):
            return
        if self._is_test_locked(int(ti)):
            return
        t = self.tests[int(ti)]
        column = self._ensure_test_experience_column(t)
        layers = list(column.intervals)
        li = int(layer_index)
        if len(layers) >= MAX_LAYERS_PER_TEST:
            self._set_status("Достигнут лимит 12 слоёв")
            return
        if not (0 <= li < len(layers)):
            return
        base = layers[li]
        if not self._can_split_layer(base):
            self._set_status("Добавление недоступно: слой нельзя разделить на 2 слоя по ≥0.20 м")
            return

        top = float(base.from_depth)
        bot = float(base.to_depth)
        thickness = bot - top
        take = min(float(INSERT_LAYER_THICKNESS_M), max(0.2, thickness - 0.2))
        if take < 0.2 - 1e-9:
            self._set_status("Добавление недоступно: слой нельзя разделить на 2 слоя по ≥0.20 м")
            return

        selected_ige_id = self._pick_existing_ige_for_column(title="Выбор ИГЭ для нового интервала")
        if not selected_ige_id:
            return
        self._push_undo()
        if from_bottom:
            t.experience_column = append_bottom(column, thickness=take, new_ige_id=selected_ige_id)
        else:
            t.experience_column = insert_between(column, li, thickness=take, new_ige_id=selected_ige_id)
        self._redraw()
        self._redraw_graphs_now()
        self.schedule_graph_redraw()
        try:
            if getattr(self, "ribbon_view", None):
                self.ribbon_view.focus_ige_row(selected_ige_id)
        except Exception:
            pass

    def _can_insert_layer_from_top(self, ti: int) -> bool:
        if ti is None or ti < 0 or ti >= len(self.tests):
            return False
        if len(self._ensure_test_experience_column(self.tests[int(ti)]).intervals) >= MAX_LAYERS_PER_TEST:
            return False
        return self._can_split_layer_index(int(ti), 0)

    def _can_insert_layer_from_bottom(self, ti: int) -> bool:
        if ti is None or ti < 0 or ti >= len(self.tests):
            return False
        t = self.tests[int(ti)]
        layers = list(self._ensure_test_experience_column(t).intervals)
        if not layers:
            return False
        if len(layers) >= MAX_LAYERS_PER_TEST:
            return False
        return self._can_split_layer_index(int(ti), len(layers) - 1)

    def _remove_layer_from_top(self, ti: int):
        self._set_status("Верхний слой нельзя удалить напрямую")

    def _remove_layer_from_bottom(self, ti: int):
        if ti is None or ti < 0 or ti >= len(self.tests):
            return
        t = self.tests[ti]
        column = self._ensure_test_experience_column(t)
        layers = list(column.intervals)
        if len(layers) <= 1:
            self._set_status("Нельзя удалить единственный слой")
            return
        t.experience_column = remove_column_interval(column, len(layers) - 1)
        self._redraw()
        self._redraw_graphs_now()
        self.schedule_graph_redraw()

    def _remove_layer_at_index(self, ti: int, layer_index: int):
        if ti is None or ti < 0 or ti >= len(self.tests):
            return
        t = self.tests[ti]
        column = self._ensure_test_experience_column(t)
        layers = list(column.intervals)
        li = int(layer_index)
        if len(layers) <= 1 or not (0 <= li < len(layers)):
            self._set_status("Нельзя удалить единственный слой")
            return
        if li <= 0:
            self._remove_layer_from_top(int(ti))
            return
        if li >= len(layers) - 1:
            self._remove_layer_from_bottom(int(ti))
            return
        t.experience_column = remove_column_interval(column, li)
        self._redraw()
        self._redraw_graphs_now()
        self.schedule_graph_redraw()

    def _renumber_layers(self, t):
        for idx, lyr in enumerate(getattr(t, "layers", []) or [], start=1):
            lyr.ige_num = idx
            if not str(getattr(lyr, "ige_id", "") or "").strip():
                lyr.ige_id = f"ИГЭ-{idx}"
            p = dict(getattr(lyr, "params", {}) or {})
            p["ige_num"] = idx
            p["visual_order"] = idx
            p["layer_id"] = str(p.get("layer_id") or f"layer-{idx}")
            p["ige_label"] = str(p.get("ige_label") or getattr(lyr, "ige_id", "") or f"ИГЭ-{idx}")
            p["top_depth"] = float(getattr(lyr, "top_m", 0.0))
            p["bottom_depth"] = float(getattr(lyr, "bot_m", 0.0))
            p["soil_type"] = str(getattr(lyr, "soil_type", SoilType.SANDY_LOAM).value)
            lyr.params = p

    def _on_layer_drag_motion(self, event):
        drag = getattr(self, "_layer_drag", None)
        if not drag:
            return
        ti = int(drag.get("ti", -1))
        if self._is_test_locked(ti):
            return
        boundary = int(drag.get("boundary", 0))
        mode = str(drag.get("mode") or "boundary")
        if ti < 0 or ti >= len(self.tests):
            return
        depth = self._canvas_y_to_depth(self.canvas.canvasy(event.y))
        if depth is None:
            return
        t = self.tests[ti]
        column = self._ensure_test_experience_column(t)
        try:
            if mode == "column_end":
                t.experience_column = resize_experience_column_end(column, depth)
                snapped_depth = float(t.experience_column.column_depth_end)
                tip = f"Низ колонки: {snapped_depth:.2f} м"
            else:
                t.experience_column = move_experience_column_boundary(column, boundary, depth)
                snapped_depth = float(t.experience_column.intervals[boundary].from_depth) if 0 <= boundary < len(t.experience_column.intervals) else float(depth)
                tip = f"Граница: {snapped_depth:.2f} м"
            self._set_status(tip)
            self._redraw_graphs_now()
        except Exception:
            pass

    def _on_layer_drag_release(self, _event):
        drag = getattr(self, "_layer_drag", None)
        if drag:
            ti = int(drag.get("ti", -1))
            self._layer_drag = None
            try:
                if 0 <= ti < len(self.tests):
                    self._calc_layer_params_for_test(int(ti))
            except Exception:
                pass
            self._redraw()
            self.schedule_graph_redraw()

    def _canvas_y_to_depth(self, y: float) -> float | None:
        units = getattr(self, "_grid_units", []) or []
        base_grid = getattr(self, "_grid_base", []) or []
        for disp_r, unit in enumerate(units):
            y0r, y1r = self._row_y_bounds(disp_r)
            if not (y0r <= y <= y1r):
                continue
            frac = (y - y0r) / max(1.0, (y1r - y0r))
            if unit[0] == "meter":
                meter_n = float(unit[1])
                return meter_n + frac
            if unit[0] != "row":
                continue
            try:
                gi = int(unit[1])
            except Exception:
                continue
            if not (0 <= gi < len(base_grid)):
                continue
            cur = _parse_depth_float(base_grid[gi])
            if cur is None:
                continue
            prev = _parse_depth_float(base_grid[gi - 1]) if gi > 0 else None
            nxt = _parse_depth_float(base_grid[gi + 1]) if gi + 1 < len(base_grid) else None
            if prev is not None:
                top_d = (float(prev) + float(cur)) * 0.5
            elif nxt is not None:
                top_d = float(cur) - (float(nxt) - float(cur)) * 0.5
            else:
                top_d = float(cur) - float(getattr(self, "step_m", 0.05) or 0.05) * 0.5
            if nxt is not None:
                bot_d = (float(cur) + float(nxt)) * 0.5
            elif prev is not None:
                bot_d = float(cur) + (float(cur) - float(prev)) * 0.5
            else:
                bot_d = float(cur) + float(getattr(self, "step_m", 0.05) or 0.05) * 0.5
            return top_d + (bot_d - top_d) * frac
        return None


    def _on_motion(self, event):
        self._evt_widget = event.widget
        self._hide_canvas_tip()

        def _set_cursor(cur: str):
            try:
                self.canvas.configure(cursor=cur)
            except Exception:
                pass
            try:
                self.hcanvas.configure(cursor=cur)
            except Exception:
                pass

        hit = self._hit_test(event.x, event.y)
        if not hit:
            self._set_hover(None)
            _set_cursor("")
            return
        kind, ti, row, field = hit
        if kind in ("lock", "edit", "rename", "dup", "trash"):
            self._set_hover((kind, ti))
            _set_cursor("hand2")
        elif kind == "export":
            self._set_hover((kind, ti))
            _set_cursor("hand2")
        elif kind == "meter_row":
            self._set_hover(None)
            is_active = (ti is not None) and (not self._is_test_locked(int(ti)))
            _set_cursor("hand2" if is_active else "")
        elif kind == "cell" and field == "depth":
            self._set_hover(None)
            is_toggle = False
            try:
                is_toggle = (ti is not None) and (not self._is_test_locked(int(ti))) and (self._expanded_meter_for_depth_cell(int(ti), int(row)) is not None)
            except Exception:
                is_toggle = False
            _set_cursor("hand2" if is_toggle else "")
        elif kind == "layer_label":
            self._set_hover(None)
            is_active = (ti is not None) and (not self._is_test_locked(int(ti)))
            _set_cursor("hand2" if is_active else "")
        elif kind in ("layer_boundary", "layer_column_end", "layer_plus", "layer_plus_top", "layer_plus_bottom", "layer_minus", "layer_minus_top", "layer_minus_bottom", "layer_boundary_depth_edit", "layer_column_end_depth_edit"):
            self._set_hover(None)
            is_active = (ti is not None) and (not self._is_test_locked(int(ti)))
            _set_cursor("hand2" if is_active else "")
        elif kind == "layer_interval":
            self._set_hover(None)
            _set_cursor("")
        else:
            self._set_hover(None)
            _set_cursor("")

    def _is_test_locked(self, ti: int) -> bool:
        try:
            return bool(getattr(self.tests[int(ti)], "locked", False))
        except Exception:
            return False

    def _toggle_test_lock(self, ti: int):
        if ti < 0 or ti >= len(self.tests):
            return
        self._push_undo()
        t = self.tests[ti]
        t.locked = not bool(getattr(t, "locked", False))
        self._hide_layer_ige_picker(reason="toggle_lock")
        self._close_boundary_depth_editor(commit=False)
        self._end_edit(commit=False)
        self._redraw()
        self.schedule_graph_redraw()


    def _delete_test(self, ti: int):
        if ti < 0 or ti >= len(self.tests):
            return
        t = self.tests[ti]
        self._push_undo()
        self._end_edit(commit=True)
        del self.tests[ti]
        # NOTE: НЕ МУТИРУЕМ шаблонные блоки GEO при удалении/копировании.
        #       Иначе при экспорте GEO могут «воскресать» удалённые зондирования.
        #       Шаблон хранится в self._geo_template_blocks_info_full (неизменяемый).
        pass
        # rebuild flags
        self.flags = {tt.tid: self.flags.get(tt.tid, TestFlags(False, set(), set(), set(), set())) for tt in self.tests}
        if self._active_test_idx is not None and self._active_test_idx >= len(self.tests):
            self._active_test_idx = (len(self.tests) - 1) if self.tests else None
        self._redraw()
        self.schedule_graph_redraw()
        self.status.config(text=f"Опыт {t.tid} удалён.")


    def _duplicate_test(self, ti: int):
        """Duplicate a test (copy) and insert right after it.
        New tid = max(tid)+1.         New tid = max(tid)+1. New datetime = max(existing dt)+10 minutes.
        """
        if ti < 0 or ti >= len(self.tests):
            return
        if not self.tests:
            return

        self._push_undo()

        src = self.tests[ti]

        # new id sequential
        existing_ids = {t.tid for t in self.tests}
        new_id = max(existing_ids) + 1 if existing_ids else 1

        # datetime: source +10 min (try parse), else max+10
        def _parse_dt(s):
            if isinstance(s, _dt.datetime):
                return s
            s = (str(s) if s is not None else "").strip()
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M"):
                try:
                    return _dt.datetime.strptime(s, fmt)
                except Exception:
                    pass
            return None

        # datetime: max(existing dt) + 10 min (so repeated copies get unique time); fallback now()
        dts = []
        for t in self.tests:
            d = _parse_dt(getattr(t, "dt", "") or "")
            if d is not None:
                dts.append(d)
        base_dt = max(dts) if dts else (_parse_dt(getattr(src, "dt", "") or "") or _dt.datetime.now())
        new_dt_dt = (base_dt + _dt.timedelta(minutes=10)).replace(microsecond=0)
        # Добавляем случайные секунды, чтобы времена у копий были уникальнее
        new_dt_dt = new_dt_dt.replace(second=random.randint(0, 59))
        new_dt = new_dt_dt.strftime("%Y-%m-%d %H:%M:%S")

# deep copy arrays
        depth = list(getattr(src, "depth", []) or [])
        qc = list(getattr(src, "qc", []) or [])
        fs = list(getattr(src, "fs", []) or [])

        new_test = TestData(tid=new_id, dt=new_dt, depth=depth, qc=qc, fs=fs, orig_id=None, block=None,
                            layers=[layer_from_dict(layer_to_dict(x)) for x in (getattr(src, "layers", []) or [])])

        # insert right after source
        insert_at = min(len(self.tests), ti + 1)
        self.tests.insert(insert_at, new_test)

        # keep GEO template blocks aligned: duplicate source block template
        try:
            if getattr(self, "_geo_template_blocks_info", None) and ti < len(self._geo_template_blocks_info):
                bi = self._geo_template_blocks_info[ti]
                # shallow copy is enough (dataclass-like with numeric fields)
                import copy as _copy
                self._geo_template_blocks_info.insert(insert_at, _copy.copy(bi))
        except Exception:
            pass

        # copy flags (deep copy sets) so visual edits/удаления сохраняются в копии
        fl = self.flags.get(getattr(src, "tid", None), TestFlags(False, set(), set(), set(), set()))
        try:
            self.flags[new_id] = TestFlags(bool(getattr(fl, 'invalid', False)), set(getattr(fl, 'interp_cells', set()) or set()), set(getattr(fl, 'force_cells', set()) or set()), set(getattr(fl, 'user_cells', set()) or set()), set(getattr(fl, 'algo_cells', set()) or set()))
        except Exception:
            try:
                self.flags[new_id] = TestFlags(False, set(), set(), set(), set())
            except Exception:
                pass

        self._end_edit(commit=False)
        self._redraw()

        # если опыт не помещается на экран — прокручиваем по X так, чтобы он попал в видимую область
        try:
            self.update_idletasks()
        except Exception:
            pass

        def _scroll_to_new():
            try:
                self._ensure_cell_visible(insert_at, 0, 'depth', pad=12)
            except Exception:
                try:
                    self._xview_proxy("moveto", 1.0)
                except Exception:
                    pass

        try:
            self.after_idle(_scroll_to_new)
        except Exception:
            _scroll_to_new()

        try:
            self.status.config(text=f"Опыт {getattr(src,'tid','?')} продублирован → {new_id} (+10 мин).")
        except Exception:
            pass


        try:
            self._set_footer_from_scan()
        except Exception:
            pass

    def _cell_bbox(self, col: int, row: int, field: str):
        x0 = self._column_x0(col)
        # Таблица (цифры) рисуется в отдельном canvas и скроллится по Y,
        # поэтому старт по Y = 0 (без hdr_h).
        y0, y1 = self._row_y_bounds(row)

        if field == "depth":
            return x0, y0, x0 + self.w_depth, y1
        if field == "qc":
            return x0 + self.w_depth, y0, x0 + self.w_depth + self.w_val, y1
        if field == "fs":
            return x0 + self.w_depth + self.w_val, y0, x0 + self.w_depth + self.w_val + self.w_val, y1
        if field == "incl":
            return x0 + self.w_depth + self.w_val*2, y0, x0 + self.w_depth + self.w_val*3, y1
        raise ValueError("bad field")

    def _display_row_data_index(self, ti: int, display_row: int) -> int | None:
        try:
            mp = (getattr(self, "_grid_row_maps", {}) or {}).get(int(ti), {}) or {}
            data_i = mp.get(int(display_row))
            return int(data_i) if data_i is not None else None
        except Exception:
            return None

    def _is_real_interval_cell(self, ti: int, display_row: int, field: str) -> bool:
        """True only for cells that map to real data intervals and can be edited/selected."""
        if field not in ("qc", "fs", "incl"):
            return False
        units = getattr(self, "_grid_units", []) or []
        if 0 <= int(display_row) < len(units):
            unit = units[int(display_row)]
            if bool(getattr(self, "compact_1m", False)) and unit[0] == "meter":
                return False
        data_i = self._display_row_data_index(int(ti), int(display_row))
        if data_i is None:
            if self._is_tail_display_row(int(display_row)):
                self._tail_debug_log("TAIL_DEBUG", f"is_real_cell ti={int(ti)} field={field} disp_r={int(display_row)} data_i=None len_qc={len(getattr(self.tests[int(ti)], 'qc', []) or [])} len_fs={len(getattr(self.tests[int(ti)], 'fs', []) or [])} result=not_real(reason=no_data_index)", ti=int(ti))
            return False
        t = self.tests[int(ti)]
        if field == "qc":
            arr = (getattr(t, "qc", []) or [])
        elif field == "fs":
            arr = (getattr(t, "fs", []) or [])
        else:
            arr = (getattr(t, "incl", []) or [])
        real = 0 <= int(data_i) < len(arr)
        if real and bool(getattr(self, "compact_1m", False)):
            try:
                cell_raw = arr[int(data_i)]
            except Exception:
                cell_raw = ""
            # В свернутом режиме кликабельна только реально существующая ячейка
            # в текущей колонке (не пустая именно в этом поле).
            if str(cell_raw).strip() == "":
                real = False
        if self._is_tail_display_row(int(display_row)):
            try:
                mp = (getattr(self, "_grid_row_maps", {}) or {}).get(int(ti), {}) or {}
                mapped_rows = sorted(int(x) for x in mp.keys())
                start_r = (mapped_rows[0] if mapped_rows else None)
                end_r = (mapped_rows[-1] if mapped_rows else None)
            except Exception:
                start_r = None
                end_r = None
            self._tail_debug_log("TAIL_DEBUG", f"is_real_cell ti={int(ti)} field={field} disp_r={int(display_row)} data_i={int(data_i)} start_r={start_r} end_r={end_r} len_qc={len(getattr(t, 'qc', []) or [])} len_fs={len(getattr(t, 'fs', []) or [])} result={'real' if real else 'not_real'}", ti=int(ti))
        return real

    def _ensure_cell_visible(self, col: int, row: int, field: str, pad: int = 6):
        """Автопрокрутка: при навигации стрелками/Enter держим редактируемую ячейку в видимой зоне."""
        try:
            bx0, by0, bx1, by1 = self._cell_bbox(col, row, field)
        except Exception:
            return

        cnv = self.canvas
        bbox_all = cnv.bbox("all")
        if not bbox_all:
            return
        ax0, ay0, ax1, ay1 = bbox_all
        aw = max(1.0, float(ax1 - ax0))
        ah = max(1.0, float(ay1 - ay0))

        vx0, vy0, vx1, vy1 = _canvas_view_bbox(cnv)
        vw = max(1.0, float(vx1 - vx0))
        vh = max(1.0, float(vy1 - vy0))

        # Горизонталь
        target_x = None
        if bx0 < vx0 + pad:
            target_x = bx0 - pad
        elif bx1 > vx1 - pad:
            target_x = bx1 - vw + pad
        if target_x is not None:
            frac = (target_x - ax0) / aw
            frac = 0.0 if frac < 0.0 else (1.0 if frac > 1.0 else frac)
            try:
                self._xview_proxy("moveto", frac)
            except Exception:
                pass

        # Вертикаль
        target_y = None
        if by0 < vy0 + pad:
            target_y = by0 - pad
        elif by1 > vy1 - pad:
            target_y = by1 - vh + pad
        if target_y is not None:
            frac = (target_y - ay0) / ah
            frac = 0.0 if frac < 0.0 else (1.0 if frac > 1.0 else frac)
            try:
                cnv.yview_moveto(frac)
            except Exception:
                pass

    def _header_bbox(self, col: int):
        # Шапка опыта относится к табличной части и не должна зависеть
        # от видимости графика/геоколонки справа.
        col_w = self._table_col_width()
        x0_world = self._column_x0(col)
        x0 = x0_world
        y0 = self.pad_y
        x1 = x0 + col_w
        y1 = y0 + self.hdr_h
        return x0, y0, x1, y1


    def _redraw(self):
        self._sync_view_ribbon_state()
        # два холста: hcanvas (фиксированная шапка) + canvas (данные)
        try:
            self.canvas.delete("all")
        except Exception:
            pass
        try:
            self.hcanvas.delete("all")
        except Exception:
            pass
        try:
            if hasattr(self, "collapsed_dock"):
                self.collapsed_dock.delete("all")
                self.collapsed_dock.create_rectangle(
                    0,
                    0,
                    max(1, int(self._collapsed_dock_width())),
                    max(1, int(self.canvas.winfo_height() or 1)),
                    fill="white",
                    outline="",
                )
        except Exception:
            pass

        if not self.tests:
            self._sync_layers_panel()
            self._update_scrollregion()
            return

        self._build_grid()
        max_rows = len(getattr(self, "_grid", []) or [])
        grid = getattr(self, "_grid_base", []) or []

        self._refresh_display_order()

        # фиксируем высоту шапки под текущие параметры
        try:
            self.hcanvas.configure(height=int(self.pad_y + self.hdr_h))
        except Exception:
            pass

        diagnostics = self._diagnostics_report()

        # --- Левая вертикальная dock-зона для свернутых опытов ---
        dock_bottom = 0
        for dock_row, ti in enumerate(getattr(self, "collapsed_cols", []) or []):
            t = self.tests[ti]
            x0, y0, x1, y1 = self._collapsed_header_bbox(dock_row)
            ex_on = bool(getattr(t, "export_on", True))
            fl = self.flags.get(t.tid, TestFlags(False, set(), set(), set(), set()))
            td = diagnostics.by_test.get(int(getattr(t, "tid", 0) or 0))
            has_missing_values = bool(td and td.missing_rows)
            hdr_fill = self._header_fill_for_test(
                invalid=bool(td.invalid) if td is not None else bool(getattr(fl, "invalid", False)),
                has_missing=bool(has_missing_values),
                export_on=True,
            )
            hdr_text = "#111111"
            hdr_icon = "#444444"
            dock = getattr(self, "collapsed_dock", None)
            if dock is None:
                continue
            dock.create_rectangle(x0, y0, x1, y1, fill=hdr_fill, outline=GUI_GRID)
            dt_val = getattr(t, "dt", "") or ""
            if isinstance(dt_val, datetime.datetime):
                dt_line = dt_val.strftime("%d.%m.%y %H:%M")
            elif isinstance(dt_val, datetime.date):
                dt_line = dt_val.strftime("%d.%m.%y")
            else:
                dt_line = str(dt_val).strip()
                dt_line = re.sub(r"(\d{2}:\d{2}):\d{2}\b", r"\1", dt_line)
            cb_s = 12
            cb_x0 = x0 + 6
            cb_y0 = y0 + 6
            dock.create_rectangle(cb_x0, cb_y0, cb_x0 + cb_s, cb_y0 + cb_s, fill="white", outline="#b9b9b9")
            title_x = cb_x0 + cb_s + 6
            lock_on = bool(getattr(t, "locked", False))
            lock_x = (x1 - 14)
            ico_y = y0 + 12
            max_title_x = lock_x - 8
            dock.create_text(title_x, y0 + 12, anchor="w", text=f"Опыт №{t.tid}", font=("Segoe UI", 9, "bold"), fill=hdr_text, width=max(24, max_title_x - title_x))
            dock.create_text(lock_x, ico_y, text=("🔒" if lock_on else "🔓"), font=("Segoe UI", 10), fill=hdr_icon, anchor="center")
            dock.create_text(title_x, y0 + 30, anchor="w", text=dt_line, font=("Segoe UI", 8), fill=hdr_text)
            dock_bottom = max(dock_bottom, y1)

        try:
            dock = getattr(self, "collapsed_dock", None)
            if dock is not None:
                body_h = int(max(self.canvas.winfo_height() or 0, self._total_body_height() or 0, dock_bottom + 12))
                dock.configure(scrollregion=(0, 0, max(1, int(self._collapsed_dock_width())), max(1, body_h)))
        except Exception:
            pass

        # --- Основная горизонтальная лента только для expanded опытов ---
        for col, ti in enumerate(getattr(self, "expanded_cols", []) or []):
            t = self.tests[ti]
            x0, y0, x1, y1 = self._header_bbox(col)

            # checked = will be exported
            ex_on = bool(getattr(t, "export_on", True))
            fl = self.flags.get(t.tid, TestFlags(False, set(), set(), set(), set()))
            td = diagnostics.by_test.get(int(getattr(t, "tid", 0) or 0))
            has_missing_values = bool(td and td.missing_rows)
            hdr_fill = self._header_fill_for_test(
                invalid=bool(td.invalid) if td is not None else bool(getattr(fl, "invalid", False)),
                has_missing=bool(has_missing_values),
                export_on=bool(ex_on),
            )
            hdr_text = "#111" if ex_on else "#8a8a8a"
            hdr_icon = "#444" if ex_on else "#8a8a8a"

            # --- ШАПКА (hcanvas) ---
            self.hcanvas.create_rectangle(x0, y0, x1, y1, fill=hdr_fill, outline=GUI_GRID)

            dt_val = getattr(t, "dt", "") or ""
            # t.dt может быть строкой из GEO или уже datetime (после редактирования)
            if isinstance(dt_val, datetime.datetime):
                dt_line = dt_val.strftime("%d.%m.%Y %H:%M:%S")
            elif isinstance(dt_val, datetime.date):
                dt_line = dt_val.strftime("%d.%m.%Y 00:00:00")
            else:
                dt_line = str(dt_val).strip()

            # display without seconds (HH:MM)
            dt_line = re.sub(r"(\d{2}:\d{2}):\d{2}\b", r"\1", dt_line)

            # --- export checkbox (Win11 style) ---
            top_pad = 8
            row_center_y = y0 + top_pad + 6  # aligns checkbox and title vertically
            cb_s = 14
            cb_x0 = x0 + 6
            cb_y0 = int(row_center_y - cb_s/2)

            # рамка чекбокса (без hover-подсветки фоном)
            self.hcanvas.create_rectangle(cb_x0, cb_y0, cb_x0 + cb_s, cb_y0 + cb_s,
                                          fill="white", outline="#b9b9b9")
            if ex_on:
                self.hcanvas.create_line(cb_x0 + 3, cb_y0 + 7, cb_x0 + 6, cb_y0 + 10,
                                         cb_x0 + 11, cb_y0 + 4,
                                         fill="#2563eb", width=2, capstyle="round", joinstyle="round")

            # Title and datetime
            title_x = cb_x0 + cb_s + 8
            self.hcanvas.create_text(title_x, row_center_y, anchor="w",
                                     text=f"Опыт №{t.tid}", font=("Segoe UI", 9, "bold"), fill=hdr_text)
            if dt_line:
                self.hcanvas.create_text(title_x, row_center_y + 18, anchor="w",
                                         text=dt_line, font=("Segoe UI", 9), fill=hdr_text)

            # header actions (Win11-like icons + hover)
            ico_y = y0 + 14
            ico_font = _pick_icon_font(12)

            lock_on = bool(getattr(t, "locked", False))
            actions_enabled = bool(self._header_action_buttons_enabled(int(ti)))
            lock_x, dup_x, trash_x = (x1 - 66), (x1 - 40), (x1 - 14)
            box_w, box_h = 22, 20

            # hover background (только для иконок, не для галочки)
            if getattr(self, "_hover", None) == ("lock", ti):
                self.hcanvas.create_rectangle(lock_x - box_w/2, ico_y - box_h/2, lock_x + box_w/2, ico_y + box_h/2,
                                              fill="#e9e9e9", outline="")
            if getattr(self, "_hover", None) == ("dup", ti):
                self.hcanvas.create_rectangle(dup_x - box_w/2, ico_y - box_h/2, dup_x + box_w/2, ico_y + box_h/2,
                                              fill="#e9e9e9", outline="")
            if getattr(self, "_hover", None) == ("trash", ti):
                self.hcanvas.create_rectangle(trash_x - box_w/2, ico_y - box_h/2, trash_x + box_w/2, ico_y + box_h/2,
                                              fill="#e9e9e9", outline="")
            if getattr(self, "_hover", None) == ("rename", ti):
                self.hcanvas.create_rectangle(title_x - 2, row_center_y - 10, lock_x - 8, row_center_y + 10, fill="#e9e9e9", outline="")
            if getattr(self, "_hover", None) == ("edit", ti) and dt_line:
                self.hcanvas.create_rectangle(title_x - 2, row_center_y + 8, lock_x - 8, row_center_y + 28, fill="#e9e9e9", outline="")

            self.hcanvas.create_text(lock_x, ico_y, text=("🔒" if lock_on else "🔓"), font=("Segoe UI", 10), fill=hdr_icon, anchor="center")
            self.hcanvas.create_text(dup_x, ico_y, text=ICON_COPY, font=ico_font, fill=(hdr_icon if actions_enabled else "#b6b6b6"), anchor="center")
            self.hcanvas.create_text(trash_x, ico_y, text=ICON_DELETE, font=ico_font, fill=(hdr_icon if actions_enabled else "#b6b6b6"), anchor="center")

            # колонка заголовков (H/qc/fs) — в шапке и фиксирована
            sh_y = y0 + self.hdr_h - top_pad
            ptype = str(getattr(self, "project_type", "") or "")
            if ptype == "type1_mech":
                q_hdr = "Qc (лоб)"
                f_hdr = "Qt (общ)"
            elif ptype == "direct_qcfs":
                q_hdr = "qc, МПа"
                f_hdr = "fs, кПа"
            else:
                q_hdr = "qc (лоб)"
                f_hdr = "fs (бок)"
            self.hcanvas.create_text(x0 + self.w_depth / 2, sh_y, text="H, м", font=("Segoe UI", 9), fill=hdr_text)
            self.hcanvas.create_text(x0 + self.w_depth + self.w_val / 2, sh_y, text=q_hdr, font=("Segoe UI", 9), fill=hdr_text)
            self.hcanvas.create_text(x0 + self.w_depth + self.w_val + self.w_val / 2, sh_y, text=f_hdr, font=("Segoe UI", 9), fill=hdr_text)
            if str(getattr(self, "geo_kind", "K2") or "K2").upper() == "K4" and bool(getattr(self, "show_inclinometer", True)):
                self.hcanvas.create_text(x0 + self.w_depth + self.w_val*2 + self.w_val/2, sh_y, text="U", font=("Segoe UI", 9), fill=hdr_text)

            # --- ТАБЛИЦА (canvas) ---
            mp = self._grid_row_maps.get(ti, {})
            start_r = self._grid_start_rows.get(ti, 0)
            units = getattr(self, "_grid_units", []) or []

            for r in range(max_rows):
                unit = units[r] if r < len(units) else ("row", r)
                is_meter_row = (unit[0] == "meter")
                meter_n = int(unit[1]) if is_meter_row else None
                base_row = int(unit[1]) if unit[0] == "row" else None
                if base_row is not None and base_row < len(grid) and grid[base_row] is not None:
                    depth_txt = f"{grid[base_row]:.2f}"
                else:
                    depth_txt = ""

                data_i = mp.get(r, None)
                q_arr = (getattr(t, "qc", []) or [])
                f_arr = (getattr(t, "fs", []) or [])
                has_row = (data_i is not None) and (data_i < max(len(q_arr), len(f_arr)))
                qc_txt = str(q_arr[data_i]) if (data_i is not None and data_i < len(q_arr)) else ""
                fs_txt = str(f_arr[data_i]) if (data_i is not None and data_i < len(f_arr)) else ""
                if self._is_tail_display_row(int(r)):
                    self._tail_debug_log(
                        "TAIL_RENDER",
                        f"ti={int(ti)} disp_r={int(r)} data_i={data_i} qc_exists={bool(data_i is not None and data_i < len(q_arr))} fs_exists={bool(data_i is not None and data_i < len(f_arr))} qc_txt={repr(qc_txt)} fs_txt={repr(fs_txt)} has_row={bool(has_row)}",
                        ti=int(ti),
                    )
                incl_txt = ""
                incl_enabled = str(getattr(self, "geo_kind", "K2") or "K2").upper() == "K4" and bool(getattr(self, "show_inclinometer", True))
                if incl_enabled:
                    incl_list = getattr(t, "incl", None)
                    if has_row and incl_list is not None and data_i < len(incl_list):
                        incl_txt = str(incl_list[data_i])

                meter_qc_max = None
                meter_fs_max = None
                if is_meter_row:
                    depth_txt = f"{meter_n}–{meter_n + 1} м"
                    qarr = getattr(t, "qc", []) or []
                    farr = getattr(t, "fs", []) or []
                    for di in range(max(len(qarr), len(farr))):
                        dv = self._depth_at_index(t, di)
                        if dv is None or not (meter_n <= dv < (meter_n + 1)):
                            continue
                        q_raw = _parse_cell_int(qarr[di]) if di < len(qarr) else None
                        f_raw = _parse_cell_int(farr[di]) if di < len(farr) else None
                        if q_raw is None and f_raw is None:
                            continue
                        qc_mpa, fs_kpa = self._calc_qc_fs_from_del(int(q_raw or 0), int(f_raw or 0))
                        if q_raw is not None:
                            meter_qc_max = float(qc_mpa) if meter_qc_max is None else max(float(meter_qc_max), float(qc_mpa))
                        if f_raw is not None:
                            meter_fs_max = float(fs_kpa) if meter_fs_max is None else max(float(meter_fs_max), float(fs_kpa))
                    qc_txt = "" if meter_qc_max is None else (f"{meter_qc_max:.2f}".rstrip("0").rstrip("."))
                    fs_txt = "" if meter_fs_max is None else str(int(round(float(meter_fs_max))))
                    if meter_qc_max is None and meter_fs_max is None:
                        depth_txt = ""
                    if incl_enabled:
                        incl_txt = ""

                # K4: если канал инклинометра отсутствует/пустой — показываем 0
                if incl_enabled:
                    try:
                        if has_row and (incl_txt is None or str(incl_txt).strip() == ""):
                            incl_txt = "0"
                    except Exception:
                        pass


                is_blank_row = (qc_txt.strip()=="" and fs_txt.strip()=="" and (incl_txt.strip()=="" if incl_enabled else True))

                if not has_row and not is_meter_row:
                    depth_txt = ""

                # Для стартовых диапазонов новых колонок глубина должна быть видна сразу,
                # даже если qc/fs ещё пустые. Поэтому не скрываем depth для blank-row.


                meter_has_data = bool((meter_qc_max is not None) or (meter_fs_max is not None)) if is_meter_row else False

                if is_meter_row:
                    # В свернутом режиме: существующий интервал окрашен единообразно,
                    # отсутствующий интервал (пустая зона) — белый.
                    depth_fill = "#f3f6fb" if meter_has_data else "white"
                elif has_row and int(data_i) == 0:
                    depth_fill = "white"   # editable cell (только абсолютная первая data-row)
                else:
                    depth_fill = (GUI_DEPTH_BG if has_row else "white")

                if not depth_txt:
                    depth_fill = "white"

                def fill_for(kind: str):
                    # Обычная логика по существующим/пустым строкам
                    if is_meter_row:
                        # Для существующего meter-интервала все ячейки строки одного цвета.
                        return depth_fill
                    if not has_row:
                        return "white"
                    if is_blank_row:
                        return "white"

                    # Нули (пропуски) подсвечиваем оранжевым во всех опытах, включая некорректные.
                    try:
                        if has_row and kind in ("qc", "fs") and data_i is not None:
                            raw_val = (t.qc[data_i] if kind == "qc" else t.fs[data_i])
                            if (_parse_cell_int(raw_val) or 0) == 0 and (data_i, kind) not in getattr(fl, "user_cells", set()):
                                return (GUI_ORANGE_P if getattr(self, '_algo_preview_mode', False) else GUI_ORANGE)
                    except Exception:
                        pass

                    mk = (self._marks_index or {}).get(self._mark_key(int(getattr(t, 'tid', 0) or 0), self._safe_depth_m(t, int(data_i)), str(kind))) if data_i is not None else None
                    if isinstance(mk, dict):
                        clr = str(mk.get("color") or "").strip().lower()
                        if clr == "orange":
                            return GUI_ORANGE
                        if clr == "purple":
                            return GUI_PURPLE
                        if clr == "green":
                            return GUI_GREEN
                        if clr == "blue":
                            return (GUI_BLUE_P if getattr(self, '_algo_preview_mode', False) else GUI_BLUE)
                    if (data_i, kind) in getattr(fl, 'user_cells', set()):
                        return GUI_PURPLE
                    if (data_i, kind) in getattr(fl, 'algo_cells', set()):
                        return GUI_GREEN
                    if (data_i, kind) in fl.force_cells:
                        return (GUI_BLUE_P if getattr(self, '_algo_preview_mode', False) else GUI_BLUE)
                    if (data_i, kind) in fl.interp_cells:
                        return (GUI_ORANGE_P if getattr(self, '_algo_preview_mode', False) else GUI_ORANGE)

                    return "white" 

                cells = [
                    ("depth", depth_txt, depth_fill),
                    ("qc", qc_txt, fill_for("qc")),
                    ("fs", fs_txt, fill_for("fs")),
                ]
                if incl_enabled:
                    cells.append(("incl", incl_txt, fill_for("incl")))

                for field, txt, fill in cells:
                    if bool(getattr(self, "compact_1m", False)) and is_meter_row and field in ("qc", "fs"):
                        txt = ""
                    # preview highlight for context-menu deletion
                    try:
                        if getattr(self, "_rc_preview", None) == (ti, r):
                            fill = GUI_RED
                    except Exception:
                        pass
                    bx0, by0, bx1, by1 = self._cell_bbox(col, r, field)
                    self.canvas.create_rectangle(bx0, by0, bx1, by1, fill=fill, outline=GUI_GRID)
                    if field == "depth":
                        tx, anchor, color = bx1 - 4, "e", "#555"
                    else:
                        tx, anchor, color = bx1 - 4, "e", "#000"
                        if is_meter_row and field in ("qc", "fs"):
                            color = "#666"
                    self.canvas.create_text(tx, (by0 + by1) / 2, text=txt, anchor=anchor, fill=color, font=("Segoe UI", 9))

            if bool(getattr(t, "locked", False)):
                body_h = float(self._total_body_height())
                if body_h > 0:
                    self.canvas.create_rectangle(x0, 0, x1, body_h, fill="#d0d0d0", outline="", stipple="gray50")
                self.hcanvas.create_rectangle(x0, y0, x1, y1, fill="#d0d0d0", outline="", stipple="gray50")

        self._update_scrollregion()
        if self._is_graph_panel_visible():
            self._redraw_graphs_now()
        else:
            self._clear_graph_layers()
        if bool(getattr(self, "_inline_edit_active", False)):
            self._reposition_boundary_depth_editor()
    # ---------------- hit test & editing ----------------

    def _hit_test(self, x, y):
        # Определяем, по какому холсту пришло событие (шапка или таблица)
        w = getattr(self, "_evt_widget", None) or self.canvas

        if not self.tests:
            return None

        if w is getattr(self, "collapsed_dock", None):
            cx = self.collapsed_dock.canvasx(x)
            cy = self.collapsed_dock.canvasy(y)

            self._refresh_display_order()
            for row_idx, ti in enumerate(getattr(self, "collapsed_cols", []) or []):
                x0, y0, x1, y1 = self._collapsed_header_bbox(row_idx)
                if x0 <= cx <= x1 and y0 <= cy <= y1:
                    if (x0 + 6) <= cx <= (x0 + 18) and (y0 + 6) <= cy <= (y0 + 18):
                        return ("export", ti, None, None)
                    if (x1 - 24) <= cx <= (x1 - 4) and (y0 + 2) <= cy <= (y0 + 22):
                        return ("lock", ti, None, None)
                    cb_s = 12
                    title_x = x0 + 6 + cb_s + 6
                    lock_x = x1 - 14
                    if title_x <= cx <= (lock_x - 8) and (y0 + 4) <= cy <= (y0 + 20):
                        return ("rename", ti, None, None)
                    if title_x <= cx <= (lock_x - 8) and (y0 + 22) <= cy <= (y0 + 38):
                        return ("edit", ti, None, None)
                    return ("header", ti, None, None)
            return None

        if w is getattr(self, "hcanvas", None):
            cx = self.hcanvas.canvasx(x)
            cy = self.hcanvas.canvasy(y)

            self._refresh_display_order()
            y0 = self.pad_y
            for col, ti in enumerate(getattr(self, "expanded_cols", []) or []):
                x0, _hy0, x1, _hy1 = self._header_bbox(col)
                if x0 <= cx <= x1 and (y0 <= cy <= y0 + self.hdr_h):
                    # export checkbox (left)
                    if (x0 + 6) <= cx <= (x0 + 20) and (y0 + 8) <= cy <= (y0 + 22):
                        return ("export", ti, None, None)
                    # icons
                    if (x1 - 78) <= cx <= (x1 - 54) and y0 <= cy <= (y0 + 24):
                        return ("lock", ti, None, None)
                    actions_enabled = bool(self._header_action_buttons_enabled(int(ti)))
                    if actions_enabled and (x1 - 52) <= cx <= (x1 - 28) and y0 <= cy <= (y0 + 24):
                        return ("dup", ti, None, None)
                    if actions_enabled and (x1 - 26) <= cx <= (x1 - 2) and y0 <= cy <= (y0 + 24):
                        return ("trash", ti, None, None)
                    cb_s = 14
                    title_x = x0 + 6 + cb_s + 8
                    row_center_y = y0 + 14
                    lock_x = x1 - 66
                    if title_x <= cx <= (lock_x - 8) and (row_center_y - 9) <= cy <= (row_center_y + 9):
                        return ("rename", ti, None, None)
                    if title_x <= cx <= (lock_x - 8) and (row_center_y + 9) <= cy <= (row_center_y + 27):
                        return ("edit", ti, None, None)
                    return ("header", ti, None, None)
            return None

        # --- таблица (числа) ---
        cx = self.canvas.canvasx(x)
        cy = self.canvas.canvasy(y)

        for hit in (getattr(self, "_layer_depth_box_hitbox", []) or []):
            bx0, by0, bx1, by1 = hit.get("bbox", (0, 0, 0, 0))
            if bx0 <= cx <= bx1 and by0 <= cy <= by1:
                hit_kind = str(hit.get("kind") or "boundary_depth_edit")
                if hit_kind == "column_end_depth_edit":
                    return ("layer_column_end_depth_edit", int(hit.get("ti", -1)), int(hit.get("boundary", 0)), None)
                return ("layer_boundary_depth_edit", int(hit.get("ti", -1)), int(hit.get("boundary", 0)), None)

        for hit in (getattr(self, "_layer_handle_hitbox", []) or []):
            bx0, by0, bx1, by1 = hit.get("bbox", (0, 0, 0, 0))
            if bx0 <= cx <= bx1 and by0 <= cy <= by1:
                if hit.get("kind") == "boundary":
                    return ("layer_boundary", int(hit.get("ti", -1)), int(hit.get("boundary", 0)), None)
                if hit.get("kind") == "column_end":
                    return ("layer_column_end", int(hit.get("ti", -1)), int(hit.get("boundary", 0)), None)
                if hit.get("kind") == "plus":
                    return ("layer_plus", int(hit.get("ti", -1)), int(hit.get("boundary", 0)), None)
                if hit.get("kind") == "plus_top":
                    return ("layer_plus_top", int(hit.get("ti", -1)), int(hit.get("boundary", 0)), None)
                if hit.get("kind") == "plus_bottom":
                    return ("layer_plus_bottom", int(hit.get("ti", -1)), int(hit.get("boundary", 0)), None)
                if hit.get("kind") == "minus":
                    return ("layer_minus", int(hit.get("ti", -1)), int(hit.get("boundary", 0)), None)
                if hit.get("kind") == "minus_top":
                    return ("layer_minus_top", int(hit.get("ti", -1)), int(hit.get("boundary", 0)), None)
                if hit.get("kind") == "minus_bottom":
                    return ("layer_minus_bottom", int(hit.get("ti", -1)), int(hit.get("boundary", 0)), None)

        for hit in (getattr(self, "_layer_label_hitbox", []) or []):
            bx0, by0, bx1, by1 = hit.get("bbox", (0, 0, 0, 0))
            if bx0 <= cx <= bx1 and by0 <= cy <= by1:
                return ("layer_label", int(hit.get("ti", -1)), None, {"depth": float(hit.get("depth", 0.0)), "bbox": (bx0, by0, bx1, by1)})

        for hit in (getattr(self, "_layer_plot_hitbox", []) or []):
            bx0, by0, bx1, by1 = hit.get("bbox", (0, 0, 0, 0))
            if bx0 <= cx <= bx1 and by0 <= cy <= by1:
                return ("layer_interval", int(hit.get("ti", -1)), None, float(hit.get("top", 0.0) + (hit.get("bot", 0.0) - hit.get("top", 0.0)) * ((cy - by0) / max(1.0, (by1 - by0)))))

        # row/col by coordinates
        if cy < 0:
            return None

        row = self._row_from_y(cy)
        if row < 0:
            return None

        self._refresh_display_order()
        for col, ti in enumerate(getattr(self, "expanded_cols", []) or []):
            x0 = self._column_x0(col)
            x1 = x0 + self._column_block_width()
            if x0 <= cx <= x1:
                # which field
                # depth/qc/fs split
                relx = cx - x0
                if relx < self.w_depth:
                    field = "depth"
                elif relx < (self.w_depth + self.w_val):
                    field = "qc"
                elif relx < (self.w_depth + self.w_val * 2):
                    field = "fs"
                else:
                    field = "incl"
                if bool(getattr(self, "compact_1m", False)):
                    meter_n = (getattr(self, "_grid_meter_rows", {}) or {}).get(row)
                    if meter_n is not None:
                        # В свернутом meter-row интерактивна только depth-ячейка (toggle).
                        if field == "depth":
                            return ("meter_row", ti, row, int(meter_n))
                        return None
                if field in ("qc", "fs", "incl") and not self._is_real_interval_cell(int(ti), int(row), str(field)):
                    return None
                return ("cell", ti, row, field)

        return None


    def _on_double_click(self, event):
        self._evt_widget = event.widget
        hit = self._hit_test(event.x, event.y)
        if not hit:
            # клик вне ячеек/шапки → закрываем активное редактирование
            self._end_edit(commit=True)
            self._hide_canvas_tip()
            return
        kind, ti, row, field = hit
        if ti is not None:
            self._active_test_idx = int(ti)
            self.schedule_graph_redraw()
        if kind == "meter_row":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            self._toggle_meter_expanded(int(field), push_undo=True)
            return
        if kind == "header":
            return

        mp = (getattr(self, "_grid_row_maps", {}) or {}).get(ti, {})
        if field == "depth":
            data_row0 = mp.get(row, None)
            if data_row0 == 0:
                self._begin_edit_depth0(ti, display_row=row)
                return
            meter_n = self._expanded_meter_for_depth_cell(ti, row)
            if meter_n is not None:
                self._toggle_meter_expanded(meter_n, push_undo=True)
                return
            return

        data_row = mp.get(row, None)
        if data_row is None:
            return
        if field in ("qc", "fs") and not self._is_real_interval_cell(int(ti), int(row), str(field)):
            return
        self._begin_edit(ti, data_row, field, display_row=row)

    def _on_arrow_key(self, event):
        # Стрелки: открываем соседнюю ячейку и выделяем всё значение
        if not getattr(self, "_editing", None):
            return "break"
        ti, row, field = self._editing[0], self._editing[1], self._editing[2]
        if field not in ("qc", "fs"):
            return "break"
        dx = 0; dy = 0
        if event.keysym == "Up":
            dy = -1
        elif event.keysym == "Down":
            dy = 1
        elif event.keysym == "Left":
            dx = -1
        elif event.keysym == "Right":
            dx = 1
        # commit current edit, then move
        self._end_edit(commit=True)
        t = self.tests[ti]
        new_field = field
        if dx != 0:
            # без «зацикливания»: вправо из fs и влево из qc упираемся в стенку
            if dx > 0 and field == "qc":
                new_field = "fs"
            elif dx < 0 and field == "fs":
                new_field = "qc"
            else:
                new_field = field
        new_row = row + dy
        if new_row < 0:
            new_row = 0
        if new_row >= len(t.qc):
            # упираемся в низ/верх (добавление строк только Enter или кликом)
            new_row = len(t.qc) - 1 if t.qc else 0
        # open editor at new cell (display row find)
        self._begin_edit(ti, new_row, new_field, display_row=None)
        return "break"

    def _on_right_click(self, event):
        self._evt_widget = event.widget
        # Правый клик где угодно закрывает активную ячейку
        try:
            self._end_edit(commit=True)
        except Exception:
            pass

        # Контекстное меню: удалить выше / удалить ниже (включая выбранную строку)
        try:
            hit = self._hit_test(event.x, event.y)
        except Exception:
            hit = None
        if not hit:
            return
        kind, ti, row, field = hit
        if kind != "cell" or ti is None or row is None:
            return
        if self._is_test_locked(int(ti)):
            self._set_status("Опыт заблокирован")
            return

        # Не показываем меню на пустых ячейках
        try:
            t = self.tests[ti]
            mp = (getattr(self, "_grid_row_maps", {}) or {}).get(ti, {}) or {}
            data_i = mp.get(row, None)
            has_row = (data_i is not None) and (data_i < len(getattr(t, "qc", []) or []))
            if not has_row:
                return
            vq = t.qc[data_i] if has_row else None
            vf = t.fs[data_i] if has_row else None
            if vq is None and vf is None:
                return
        except Exception:
            return

        # Подсветка строки красным при вызове меню
        self._rc_preview = (ti, row)
        try:
            self._redraw()
        except Exception:
            pass

        self._ctx_target = (ti, row)
        try:
            self._ctx_menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                self._ctx_menu.grab_release()
            except Exception:
                pass
            self._rc_preview = None
            try:
                self._redraw()
            except Exception:
                pass

    def _ctx_delete_above(self):
        """Удалить строки выше выбранной по глубине отображения."""
        if not getattr(self, '_ctx_target', None):
            return
        ti, row = self._ctx_target
        self._delete_by_display_row(ti, row, mode='above')

    def _ctx_delete_below(self):
        """Удалить строки ниже выбранной (вкл.) по глубине отображения."""
        if not getattr(self, '_ctx_target', None):
            return
        ti, row = self._ctx_target
        self._delete_by_display_row(ti, row, mode='below')

    def _ctx_delete_row(self):
        """Удалить одну строку по глубине отображения."""
        if not getattr(self, '_ctx_target', None):
            return
        ti, row = self._ctx_target
        self._delete_by_display_row(ti, row, mode='row')

    def _delete_by_display_row(self, ti, display_row: int, mode: str):
        if ti < 0 or ti >= len(self.tests):
            return
        t = self.tests[ti]

        def pdepth(v):
            try:
                s = str(v).strip().replace(',', '.')
                if s == '':
                    return None
                return float(s)
            except Exception:
                return None

        # Глубина выбранной display-строки для конкретного опыта.
        target_depth = None
        try:
            mp = (getattr(self, '_grid_row_maps', {}) or {}).get(ti, {}) or {}
            data_i = mp.get(int(display_row), None)
            if data_i is not None and 0 <= int(data_i) < len(getattr(t, 'depth', []) or []):
                target_depth = pdepth(t.depth[int(data_i)])
        except Exception:
            target_depth = None

        if target_depth is None:
            try:
                units = getattr(self, '_grid_units', []) or []
                base = getattr(self, '_grid_base', []) or []
                if 0 <= int(display_row) < len(units):
                    unit = units[int(display_row)]
                    if unit and unit[0] == 'row':
                        gi = int(unit[1])
                        if 0 <= gi < len(base):
                            target_depth = pdepth(base[gi])
            except Exception:
                target_depth = None

        if target_depth is None and 0 <= int(display_row) < len(getattr(t, 'depth', []) or []):
            target_depth = pdepth(t.depth[int(display_row)])

        if target_depth is None:
            self._tail_debug_log("TAIL_TRIM", f"delete_by_display_row SKIP ti={int(ti)} disp_r={int(display_row)} mode={mode} reason=no_target_depth", ti=int(ti))
            return

        n = max(len(getattr(t, 'depth', []) or []), len(getattr(t, 'qc', []) or []), len(getattr(t, 'fs', []) or []))
        while len(t.depth) < n: t.depth.append('')
        while len(t.qc) < n: t.qc.append('')
        while len(t.fs) < n: t.fs.append('')

        # список (depth, idx)
        pairs = []
        for i in range(n):
            d = pdepth(t.depth[i])
            if d is None:
                continue
            pairs.append((d, i))
        if not pairs:
            return

        nearest_d, nearest_i = min(pairs, key=lambda di: abs(di[0] - target_depth))

        if mode == 'row':
            r0 = r1 = nearest_i
        elif mode == 'above':
            inds = [i for (d, i) in pairs if d <= nearest_d + 1e-9]
            if not inds:
                return
            r0, r1 = min(inds), max(inds)
        else:  # below
            inds = [i for (d, i) in pairs if d >= nearest_d - 1e-9]
            if not inds:
                return
            r0, r1 = min(inds), max(inds)

        self._tail_debug_log("TAIL_TRIM", f"delete_by_display_row APPLY ti={int(ti)} disp_r={int(display_row)} mode={mode} target_depth={target_depth} r0={int(r0)} r1={int(r1)}", ti=int(ti))
        self._delete_range_indices(ti, r0, r1)

    def _delete_range_indices(self, ti, r0, r1):
        if ti < 0 or ti >= len(self.tests):
            return
        t = self.tests[ti]
        n = max(len(t.depth), len(t.qc), len(t.fs))
        if n <= 0:
            return
        r0 = max(0, int(r0))
        r1 = min(n - 1, int(r1))
        if r1 < r0:
            self._tail_debug_log("TAIL_TRIM", f"delete_range SKIP ti={int(ti)} r0={int(r0)} r1={int(r1)} reason=bad_range", ti=int(ti))
            return
        while len(t.depth) < n: t.depth.append('')
        while len(t.qc) < n: t.qc.append('')
        while len(t.fs) < n: t.fs.append('')
        # K4: поддерживаем список инклинометра (U) синхронно с qc/fs
        if getattr(self, "geo_kind", "K2") == "K4":
            try:
                if getattr(t, "incl", None) is None:
                    t.incl = []
                while len(t.incl) < n:
                    t.incl.append('0')
            except Exception:
                pass


        self._tail_debug_log("TAIL_TRIM", f"delete_range START ti={int(ti)} r0={int(r0)} r1={int(r1)} before_len_depth={len(t.depth)} before_len_qc={len(t.qc)} before_len_fs={len(t.fs)}", ti=int(ti))
        self._push_undo()

        # Сдвиг флагов подсветки (жёлтый/синий/фиолетовый) при удалении строк,
        # чтобы подсветка не «съезжала» относительно данных.
        k = (r1 - r0 + 1)
        try:
            fl = self.flags.get(t.tid)
            if fl:
                def _shift_cells(cells: set[tuple[int, str]]) -> set[tuple[int, str]]:
                    out = set()
                    for (r, kind) in (cells or set()):
                        try:
                            rr = int(r)
                        except Exception:
                            continue
                        if rr < r0:
                            out.add((rr, kind))
                        elif rr > r1:
                            out.add((rr - k, kind))
                        # rr in [r0..r1] -> удалено
                    return out

                fl.interp_cells = _shift_cells(getattr(fl, "interp_cells", set()))
                fl.force_cells  = _shift_cells(getattr(fl, "force_cells", set()))
                fl.user_cells   = _shift_cells(getattr(fl, "user_cells", set()))
                self.flags[t.tid] = fl
        except Exception:
            pass

        del t.depth[r0:r1+1]

        # K4: если удаляем "выше" (с нулевой строки), сдвигаем начальную глубину на k*step
        # чтобы окно "Параметры GEO" подхватило новую начальную глубину.
        if getattr(self, "geo_kind", "K2") == "K4":
            try:
                if int(r0) == 0:
                    tid = int(getattr(t, "tid", 0) or 0)
                    step_m = float(getattr(self, "step_m", 0.05) or 0.05)
                    if tid:
                        self.depth0_by_tid[tid] = float(self.depth0_by_tid.get(tid, 0.0)) + float((r1 - r0 + 1) * step_m)
            except Exception:
                pass

        del t.qc[r0:r1+1]
        del t.fs[r0:r1+1]
        self._tail_debug_log("TAIL_TRIM", f"delete_range CUT ti={int(ti)} r0={int(r0)} r1={int(r1)} after_len_depth={len(t.depth)} after_len_qc={len(t.qc)} after_len_fs={len(t.fs)}", ti=int(ti))

        # K4: удаляем U синхронно, если есть
        if getattr(self, "geo_kind", "K2") == "K4":
            try:
                incl_list = getattr(t, "incl", None)
                if incl_list is not None and len(incl_list) >= (r1 + 1):
                    del incl_list[r0:r1+1]
            except Exception:
                pass

        # K4: после удаления строк пересчитываем начальную глубину опыта по первой строке (на всякий случай)
        try:
            if getattr(self, "geo_kind", "K2") == "K4":
                tid = int(getattr(t, "tid", 0) or 0)
                d0 = None
                for dv in (getattr(t, "depth", []) or []):
                    try:
                        dd = float(str(dv).strip().replace(',', '.'))
                    except Exception:
                        dd = None
                    if dd is not None:
                        d0 = dd
                        break
                if d0 is not None and tid:
                    self.depth0_by_tid[tid] = float(d0)
                elif tid and hasattr(self, "depth0_by_tid"):
                    self.depth0_by_tid.pop(tid, None)
        except Exception:
            pass

        try:
            self._sync_layers_to_test_depth_range(int(ti))
        except Exception:
            pass

        xview_before = None
        try:
            xview_before = tuple(self.canvas.xview())
        except Exception:
            xview_before = None

        try:
            self._build_grid()
        except Exception:
            pass
        self._redraw()
        self._redraw_graphs_now()
        if xview_before is not None:
            try:
                self._apply_shared_xview("moveto", float(xview_before[0]))
                self._sync_header_body_after_scroll()
            except Exception:
                pass
        self.schedule_graph_redraw()

        try:
            self._set_status(f"Удалено строк: {r1 - r0 + 1} (опыт {ti+1})")
        except Exception:
            pass



            
    def _edit_header(self, ti: int):
        t = self.tests[ti]
        win = tk.Toplevel(self)
        win.title("Параметры зондирования")
        win.resizable(False, False)
        # ВАЖНО: центрирование делаем ПОСЛЕ построения виджетов.
        # Иначе на Windows (особенно при масштабировании 125–175%) окно
        # центрируется по «пустому» reqsize и может оказаться меньше, чем нужно.

        


        style = ttk.Style(win)
        try:
            style.configure("Hdr.TButton", padding=(8, 1))
        except Exception:
            pass

        PADX = 12
        PADY = 6

        # ---- Date + Time ----
        ttk.Label(win, text="Дата").grid(row=0, column=0, sticky="w", padx=PADX, pady=(PADY, 2))

        parsed = _try_parse_dt(t.dt or "")
        if parsed is None:
            try:
                parsed = _dt.datetime.strptime((t.dt or "").strip(), "%d.%m.%Y")
            except Exception:
                parsed = None

        d0 = (parsed.date() if parsed else _dt.date.today())
        hh0 = (parsed.hour if parsed else 0)
        mm0 = (parsed.minute if parsed else 0)

        date_var = tk.StringVar(master=self, value=_format_date_ru(d0))
        date_entry = ttk.Entry(win, textvariable=date_var, width=12, state="readonly")
        date_entry.grid(row=0, column=1, sticky="w", padx=(0, 6), pady=(PADY, 2))

        def pick_date():
            try:
                cur = _dt.datetime.strptime(date_var.get().strip(), "%d.%m.%Y").date()
            except Exception:
                cur = _dt.date.today()
            dlg = CalendarDialog(win, initial=cur)
            self._place_calendar_near_header(dlg, ti)
            win.wait_window(dlg)
            if dlg.selected:
                date_var.set(_format_date_ru(dlg.selected))

        cal_btn = ttk.Button(win, text="📅", style="Hdr.TButton", command=pick_date)
        cal_btn.grid(row=0, column=2, sticky="w", padx=(0, PADX), pady=(PADY, 2))

        ttk.Label(win, text="Время").grid(row=1, column=0, sticky="w", padx=PADX, pady=2)

        time_frame = ttk.Frame(win)
        time_frame.grid(row=1, column=1, columnspan=2, sticky="w", padx=(0, PADX), pady=2)

        hh_var = tk.StringVar(master=self, value=f"{hh0:02d}")
        mm_var = tk.StringVar(master=self, value=f"{mm0:02d}")

        hh_entry = ttk.Entry(
            time_frame,
            textvariable=hh_var,
            width=3,
            justify="center",
            validate="key",
            validatecommand=(win.register(_validate_hh_key), "%P"),
        )
        hh_entry.pack(side="left")
        ttk.Label(time_frame, text=":").pack(side="left", padx=2)
        mm_entry = ttk.Entry(
            time_frame,
            textvariable=mm_var,
            width=3,
            justify="center",
            validate="key",
            validatecommand=(win.register(_validate_mm_key), "%P"),
        )
        mm_entry.pack(side="left")


        def apply():
            try:
                d = _dt.datetime.strptime(date_var.get().strip(), "%d.%m.%Y").date()
            except Exception:
                messagebox.showwarning("Внимание", "Некорректная дата.", parent=win)
                return

            hh_txt = (hh_var.get() or "").strip() or "0"
            mm_txt = (mm_var.get() or "").strip() or "0"
            try:
                hh = int(hh_txt); mm = int(mm_txt)
            except Exception:
                messagebox.showwarning("Внимание", "Некорректное время.", parent=win)
                return
            if not (0 <= hh <= 23 and 0 <= mm <= 59):
                messagebox.showwarning("Внимание", "Время должно быть в диапазоне 00:00–23:59.", parent=win)
                return

            dt_text = f"{d.day:02d}.{d.month:02d}.{d.year:04d} {hh:02d}:{mm:02d}"

            self._push_undo()
            dt_obj = _try_parse_dt(dt_text)
            t.dt = dt_obj.strftime("%Y-%m-%d %H:%M:%S") if dt_obj else dt_text

            self._redraw()
            win.destroy()

        # Enter = сохранить
        for _w in (hh_entry, mm_entry):
            try:
                _w.bind('<Return>', lambda _e: apply())
            except Exception:
                pass
        try:
            win.bind('<Return>', lambda _e: apply())
        except Exception:
            pass

        
        # ---- Buttons (centered) ----
        btns = ttk.Frame(win)
        btns.grid(row=2, column=0, columnspan=3, sticky="ew", padx=12, pady=(8, 12))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(2, weight=1)

        inner_btns = ttk.Frame(btns)
        inner_btns.grid(row=0, column=1)

        ttk.Button(inner_btns, text="Сохранить", style="Hdr.TButton", command=apply).pack(side="left", padx=(0, 8))
        ttk.Button(inner_btns, text="Отмена", style="Hdr.TButton", command=win.destroy).pack(side="left")

        # Enter = save (в том числе NumPad Enter)
        win.bind("<Return>", lambda _e: apply())
        win.bind("<KP_Enter>", lambda _e: apply())

        # финальная геометрия + центрирование (после того, как Tk посчитает reqsize)
        try:
            win.update_idletasks()
        except Exception:
            pass
        try:
            self._center_child(win)
        except Exception:
            pass

    def _edit_header_title(self, ti: int):
        t = self.tests[ti]
        win = tk.Toplevel(self)
        win.title("Переименовать опыт")
        win.resizable(False, False)

        PADX = 12
        PADY = 8

        ttk.Label(win, text="№ зондирования").grid(row=0, column=0, sticky="w", padx=PADX, pady=(PADY, 2))
        tid_var = tk.StringVar(master=self, value=str(t.tid))
        tid_entry = ttk.Entry(
            win,
            textvariable=tid_var,
            width=14,
            validate="key",
            validatecommand=(win.register(_validate_tid_key), "%P"),
        )
        tid_entry.grid(row=1, column=0, sticky="ew", padx=PADX, pady=(0, 8))
        tid_entry.focus_set()
        tid_entry.selection_range(0, "end")

        def apply():
            new_tid_txt = tid_var.get().strip()
            if not new_tid_txt:
                messagebox.showwarning("Внимание", "Номер зондирования не может быть пустым.", parent=win)
                return
            try:
                new_tid = int(new_tid_txt)
            except Exception:
                messagebox.showwarning("Внимание", "Номер зондирования должен быть числом.", parent=win)
                return
            if not (1 <= new_tid <= 999):
                messagebox.showwarning("Внимание", "Номер зондирования: от 1 до 999.", parent=win)
                return
            if any((i != ti and int(tt.tid) == new_tid) for i, tt in enumerate(self.tests)):
                messagebox.showwarning("Внимание", f"Номер {new_tid} уже существует.", parent=win)
                return

            self._push_undo()
            old_tid = t.tid
            t.tid = new_tid

            if old_tid in self.flags:
                self.flags[new_tid] = self.flags.pop(old_tid)
            else:
                self.flags[new_tid] = TestFlags(False, set(), set(), set(), set())

            self._redraw()
            win.destroy()

        btns = ttk.Frame(win)
        btns.grid(row=2, column=0, sticky="e", padx=PADX, pady=(0, PADY))
        ttk.Button(btns, text="Сохранить", command=apply).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Отмена", command=win.destroy).pack(side="left")

        win.bind("<Return>", lambda _e: apply())
        win.bind("<KP_Enter>", lambda _e: apply())

        try:
            win.update_idletasks()
            self._center_child(win)
        except Exception:
            pass



    def _begin_edit(self, ti: int, row: int, field: str, display_row: int | None = None, *, new_tail: bool = False):
        """Edit qc/fs cell. row is data index, display_row is grid index."""
        if self._is_test_locked(int(ti)):
            self._set_status("Опыт заблокирован")
            return
        self._end_edit(commit=True)
        t = self.tests[ti]
        # Не даём вводить значения "после конца" выбранного канала.
        vals = (getattr(t, "qc", []) or []) if field == "qc" else (getattr(t, "fs", []) or [])
        src_exists = (0 <= int(row) < len(vals))
        if row < 0 or row >= len(vals):
            self._tail_debug_log("TAIL_EDIT", f"begin_edit REJECT ti={int(ti)} field={field} row={int(row)} disp_r={display_row} data_i={int(row)} len_field={len(vals)} src_exists={src_exists} reason=row_out_of_bounds", ti=int(ti))
            return

        if display_row is None:
            try:
                mp = (getattr(self, "_grid_row_maps", {}) or {}).get(ti, {})
                for gr, di in mp.items():
                    if di == row:
                        display_row = gr
                        break
            except Exception:
                pass
        if display_row is None:
            display_row = row

        # В нижнем хвосте после commit предыдущей ячейки индекс data-row может сдвинуться.
        # Приоритетно берём актуальный data_i из текущей карты display->data.
        try:
            mp_now = (getattr(self, "_grid_row_maps", {}) or {}).get(ti, {}) or {}
            mapped_row = mp_now.get(int(display_row), None)
            if mapped_row is not None and int(mapped_row) != int(row):
                self._tail_debug_log("TAIL_ENTRY", f"begin_edit REMAP ti={int(ti)} field={field} disp_r={int(display_row)} row_arg={int(row)} row_mapped={int(mapped_row)}", ti=int(ti))
                row = int(mapped_row)
        except Exception:
            pass

        self._refresh_display_order()
        col = self._expanded_col_index(int(ti))
        if col is None:
            return

        # Автопрокрутка (стрелки/Enter): держим ячейку в видимой зоне
        self._ensure_cell_visible(col, display_row, field)

        bx0, by0, bx1, by1 = self._cell_bbox(col, display_row, field)
        vx0 = bx0 - self.canvas.canvasx(0)
        vy0 = by0 - self.canvas.canvasy(0)

        vals = (getattr(t, "qc", []) or []) if field == "qc" else (getattr(t, "fs", []) or [])
        current_raw = vals[row] if 0 <= row < len(vals) else ""
        current = "" if current_raw is None else str(current_raw)
        self._tail_debug_log("TAIL_ENTRY", f"begin_edit SOURCE ti={int(ti)} field={field} disp_r={display_row} data_i={int(row)} source_before_create={repr(current_raw)} source_norm={repr(current)} len_field={len(vals)}", ti=int(ti))
        e = tk.Entry(self.canvas, validate="key", validatecommand=(self.register(self._validate_cell_int_key), "%P"))
        self._tail_debug_log("TAIL_ENTRY", f"begin_edit CREATED ti={int(ti)} field={field} disp_r={display_row} data_i={int(row)} entry_text_after_create={repr(e.get())}", ti=int(ti))
        e.insert(0, current)
        self._tail_debug_log("TAIL_ENTRY", f"begin_edit INSERTED ti={int(ti)} field={field} disp_r={display_row} data_i={int(row)} entry_text_after_insert={repr(e.get())}", ti=int(ti))
        try:
            e.configure(bg="white")
        except Exception:
            pass
        self._tail_debug_log("TAIL_ENTRY", f"begin_edit BEFORE_SELECT ti={int(ti)} field={field} disp_r={display_row} data_i={int(row)} entry_text={repr(e.get())}", ti=int(ti))
        e.select_range(0, tk.END)
        self._tail_debug_log("TAIL_SELECT", f"begin_edit SELECT_NOW ti={int(ti)} field={field} disp_r={display_row} data_i={int(row)} text_len={len(e.get())} selection_called=True", ti=int(ti))
        e.place(x=vx0 + 1, y=vy0 + 1, width=(bx1 - bx0) - 2, height=(by1 - by0) - 2)
        e.focus_set()
        try:
            # На некоторых темах/платформах выделение теряется из-за клика,
            # поэтому закрепляем поведение «видно + выделено целиком» после фокуса.
            def _tail_select_after_idle():
                e.focus_set()
                e.icursor(tk.END)
                e.select_range(0, tk.END)
                self._tail_debug_log("TAIL_SELECT", f"begin_edit SELECT_IDLE ti={int(ti)} field={field} disp_r={display_row} data_i={int(row)} text_len={len(e.get())} final_entry_text={repr(e.get())}", ti=int(ti))
            e.after_idle(_tail_select_after_idle)
        except Exception:
            self._tail_debug_log("TAIL_SELECT", f"begin_edit SELECT_IDLE ti={int(ti)} field={field} disp_r={display_row} data_i={int(row)} selection_called=False", ti=int(ti))
            pass

        def commit_and_next():
            # Защита от "разрыва" хвоста: Enter по уже пустой ячейке без ввода
            # не должен порождать новую пустую строку.
            try:
                raw_now = str(e.get() or "").strip()
            except Exception:
                raw_now = ""
            if raw_now == "" and str(current).strip() == "":
                self._tail_debug_log("TAIL_EDIT", f"enter_block_empty ti={int(ti)} field={field} row={int(row)} disp_r={display_row}", ti=int(ti))
                return

            setattr(self, "_edit_end_reason", "return")
            self._end_edit(commit=True)

            # Enter: вниз. Если дошли до конца — добавляем новую строку и продолжаем ввод.
            next_row = row + 1
            field_vals = (getattr(t, "qc", []) or []) if field == "qc" else (getattr(t, "fs", []) or [])
            if next_row < len(field_vals):
                self._begin_edit(ti, next_row, field, (display_row or row) + 1)
            else:
                # добавляем новую строку в хвост и начинаем редактирование
                self._append_row(ti)
                try:
                    self._begin_edit(ti, next_row, field, (display_row or row) + 1, new_tail=True)
                except Exception:
                    pass

        e.bind("<Return>", lambda _ev: commit_and_next())
        for _k in ("<Up>","<Down>","<Left>","<Right>"):
            e.bind(_k, self._on_arrow_key)
        e.bind("<Escape>", lambda _ev: (setattr(self, "_edit_end_reason", "escape"), self._end_edit(commit=False)))
        e.bind("<FocusOut>", lambda _ev: (setattr(self, "_edit_end_reason", "focusout"), self._end_edit(commit=True)))

        self._editing = (ti, row, field, e, display_row)
        self._editing_meta = {"new_tail": bool(new_tail), "row": int(row), "field": str(field), "ti": int(ti)}

    def _begin_edit_depth0(self, ti: int, display_row: int = 0):
        """Редактирование первой глубины (depth[0]) с автопересчётом всей колонки depth."""
        if self._is_test_locked(int(ti)):
            self._set_status("Опыт заблокирован")
            return
        self._end_edit(commit=True)
        t = self.tests[ti]
        if not getattr(t, "depth", None):
            return

        self._refresh_display_order()
        col = self._expanded_col_index(int(ti))
        if col is None:
            return

        # Автопрокрутка (стрелки/Enter)
        self._ensure_cell_visible(col, display_row, "depth")

        bx0, by0, bx1, by1 = self._cell_bbox(col, display_row, "depth")
        vx0 = bx0 - self.canvas.canvasx(0)
        vy0 = by0 - self.canvas.canvasy(0)

        current = str(t.depth[0]).strip()
        e = tk.Entry(self.canvas, validate="key", validatecommand=(self.register(_validate_depth_0_4_key), "%P"))
        e.insert(0, current)
        e.select_range(0, tk.END)
        e.place(x=vx0 + 1, y=vy0 + 1, width=(bx1 - bx0) - 2, height=(by1 - by0) - 2)
        e.focus_set()

        def commit():
            self._push_undo()
            self._end_edit_depth0(ti, e, commit=True)

        e.bind("<Return>", lambda _ev: commit())
        e.bind("<Escape>", lambda _ev: self._end_edit_depth0(ti, e, commit=False))
        e.bind("<FocusOut>", lambda _ev: self._end_edit_depth0(ti, e, commit=True))

        self._editing = (ti, 0, "depth", e, display_row)
        self._editing_meta = {"new_tail": False, "row": 0, "field": "depth", "ti": int(ti)}

    def _end_edit_depth0(self, ti: int, e, commit: bool):
        try:
            val = e.get().strip()
        except Exception:
            val = ""
        try:
            e.place_forget()
            e.destroy()
        except Exception:
            pass
        self._editing = None
        self._editing_meta = None
        if not commit:
            self._redraw()
            self._redraw_graphs_now()
            self.schedule_graph_redraw()
            return

        t = self.tests[ti]
        old0 = _parse_depth_float(t.depth[0]) if getattr(t, "depth", None) else None
        new0 = _parse_depth_float(val)
        # ограничения: 0..4 м и шаг по 5 см (0.05 м)
        if new0 is not None:
            if new0 < 0.0 or new0 > 4.0:
                messagebox.showerror("Ошибка", "Начальная глубина должна быть в диапазоне 0…4 м.")
                self._redraw()
                return
            # Ограничение по сетке глубин:
            # - при шаге 10 см (0.10 м) разрешаем только кратность 0.10
            # - иначе (шаг 5 см) кратность 0.05
            step_m = float(self.step_m or 0.05)
            step_cm = int(round(step_m * 100.0))
            if step_cm <= 0:
                step_cm = 5
            cm = int(round(new0 * 100.0))
            if cm % step_cm != 0:
                if step_cm == 10:
                    messagebox.showerror("Ошибка", "При шаге 10 см глубина должна быть кратна 0.10 м: …0.00, …0.10, …0.20 и т.д.")
                else:
                    messagebox.showerror("Ошибка", "Глубина должна быть кратна 0.05 м (5 см): …0.00, …0.05, …0.10 и т.д.")
                self._redraw()
                return
        if new0 is None:
            self._redraw()
            self._redraw_graphs_now()
            self.schedule_graph_redraw()
            return
        if old0 is None:
            old0 = new0

        delta = new0 - old0
        if abs(delta) < 1e-9:
            t.depth[0] = f"{new0:.2f}"
            try:
                self._set_start_depth_for_test(t, float(new0))
            except Exception:
                pass
            self._redraw()
            self._redraw_graphs_now()
            return

        new_depth = []
        for ds in (getattr(t, "depth", []) or []):
            d = _parse_depth_float(ds)
            if d is None:
                new_depth.append(ds)
            else:
                new_depth.append(f"{(d + delta):.2f}")
        t.depth = new_depth
        try:
            self._set_start_depth_for_test(t, float(new0))
        except Exception:
            pass

        try:
            self._sync_layers_to_test_depth_range(int(ti), depth_shift=float(delta))
        except Exception:
            pass

        # Не сбрасываем подсветку/флаги при сдвиге глубины: qc/fs не менялись
        # (иначе пропадает фиолетовая отметка ручных правок и др. подсветки)
        self._redraw()
        self._redraw_graphs_now()
        self.schedule_graph_redraw()

    def _cleanup_new_tail_row_if_empty(self, ti: int, row: int, *, reason: str = "") -> bool:
        if ti is None or ti < 0 or ti >= len(getattr(self, "tests", []) or []):
            return False
        t = self.tests[int(ti)]
        q_arr = list(getattr(t, "qc", []) or [])
        f_arr = list(getattr(t, "fs", []) or [])
        d_arr = list(getattr(t, "depth", []) or [])
        n = max(len(q_arr), len(f_arr), len(d_arr))
        if n <= 0:
            return False
        row = int(row)
        if row < 0 or row >= n or row != (n - 1):
            return False
        qv = str(q_arr[row]).strip() if row < len(q_arr) and q_arr[row] is not None else ""
        fv = str(f_arr[row]).strip() if row < len(f_arr) and f_arr[row] is not None else ""
        if qv != "" or fv != "":
            return False
        self._tail_debug_log("TAIL_TRIM", f"new_tail_cleanup APPLY ti={int(ti)} row={int(row)} reason={reason} len_depth={len(d_arr)} len_qc={len(q_arr)} len_fs={len(f_arr)}", ti=int(ti))
        fl = self.flags.get(t.tid) or TestFlags(False, set(), set(), set(), set())
        self._delete_data_row_in_test(t, fl, row)
        self.flags[t.tid] = fl
        try:
            self._sync_layers_to_test_depth_range(int(ti))
        except Exception:
            pass
        self._redraw()
        self.schedule_graph_redraw()
        return True

    def _end_edit(self, commit: bool):
        if not self._editing:
            return
        if len(self._editing) == 4:
            ti, row, field, e = self._editing
            _disp = None
        else:
            ti, row, field, e, _disp = self._editing
        try:
            val = e.get().strip()
        except Exception:
            val = ""
        try:
            e.place_forget()
            e.destroy()
        except Exception:
            pass
        edit_meta = dict(getattr(self, "_editing_meta", {}) or {})
        self._editing = None
        self._editing_meta = None
        end_reason = str(getattr(self, "_edit_end_reason", "unknown") or "unknown")
        self._edit_end_reason = None
        self._tail_debug_log("TAIL_EDIT", f"end_edit ENTER ti={int(ti)} field={field} row={int(row)} disp_r={_disp} commit={bool(commit)} reason={end_reason} raw_val={repr(val)} new_tail={bool(edit_meta.get('new_tail', False))}", ti=int(ti))

        if bool(edit_meta.get("new_tail", False)) and str(val or "").strip() == "" and end_reason in ("focusout", "escape"):
            if self._cleanup_new_tail_row_if_empty(int(ti), int(row), reason=str(end_reason)):
                return

        if field == "depth":
            self._redraw()
            self.schedule_graph_redraw()
            return

        if commit and self.tests:
            t = self.tests[ti]
            vals = (getattr(t, 'qc', []) or []) if field == 'qc' else (getattr(t, 'fs', []) or [])
            if row < len(vals):
                # keep previous coloring info, but mark this cell as manually edited (purple)
                fl = self.flags.get(t.tid) or TestFlags(False, set(), set(), set(), set())
                old = vals[row] if 0 <= row < len(vals) else ""
                old_text = "" if old is None else str(old)
                val_text = str(val or "")
                # 1) Кликнули и ушли без изменения видимого текста: no-op.
                if old_text.strip() == val_text.strip():
                    self._tail_debug_log("TAIL_EDIT", f"end_edit NOOP_TEXT ti={int(ti)} field={field} row={int(row)} old={repr(old_text)} new={repr(val_text)}", ti=int(ti))
                    self._redraw()
                    self.schedule_graph_redraw()
                    return

                old_norm = self._sanitize_cell_int(old_text)
                newv = self._sanitize_cell_int(val_text)

                # 2) Нормализованные значения совпали: тоже no-op.
                if old_norm.strip() == newv.strip():
                    self._tail_debug_log("TAIL_EDIT", f"end_edit NOOP_NORM ti={int(ti)} field={field} row={int(row)} old_norm={repr(old_norm)} new_norm={repr(newv)}", ti=int(ti))
                    self._redraw()
                    self.schedule_graph_redraw()
                    return

                # Важная семантика: implicit focusout/blur с пустым raw значения НЕ равен
                # явному намерению очистить крайнюю строку.
                explicit_clear = (end_reason == "return") and (val_text.strip() == "")
                if val_text.strip() == "" and old_text.strip() != "" and not explicit_clear:
                    self._tail_debug_log(
                        "TAIL_EDIT",
                        f"end_edit IMPLICIT_EMPTY_NOOP ti={int(ti)} field={field} row={int(row)} reason={end_reason} old={repr(old_text)} raw={repr(val_text)}",
                        ti=int(ti),
                    )
                    self._redraw()
                    self.schedule_graph_redraw()
                    return

                # Undo: фиксируем снимок ДО изменения данных/раскраски
                if commit:
                    try:
                        self._push_undo()
                    except Exception:
                        pass
                # Запрет: в середине зондирования нельзя ставить 0 или оставлять пусто.
                # Пустое значение разрешено только на краях (первая/последняя строка) — тогда удаляем строку целиком.
                last_filled_before = self._last_filled_row(t)

                # edge-delete when clearing first/last filled row
                if newv.strip() == "":
                    if row == 0 or row == last_filled_before:
                        if end_reason != "return":
                            self._tail_debug_log("TAIL_EDIT", f"end_edit SKIP_DELETE_EDGE ti={int(ti)} field={field} row={int(row)} last_filled={int(last_filled_before)} reason={end_reason} old={repr(old_text)} raw={repr(val_text)}", ti=int(ti))
                            self._redraw()
                            self.schedule_graph_redraw()
                            return
                        self._tail_debug_log("TAIL_TRIM", f"end_edit DELETE_EDGE ti={int(ti)} field={field} row={int(row)} last_filled={int(last_filled_before)} old={repr(old_text)} new={repr(newv)}", ti=int(ti))
                        # удалить строку данных и глубину
                        fl = self.flags.get(t.tid) or TestFlags(False, set(), set(), set(), set())
                        self._delete_data_row_in_test(t, fl, row)
                        self.flags[t.tid] = fl
                        try:
                            self._sync_layers_to_test_depth_range(int(ti))
                        except Exception:
                            pass
                        self._redraw()
                        self.schedule_graph_redraw()
                        return
                    else:
                        self._tail_debug_log("TAIL_EDIT", f"end_edit REJECT_EMPTY_MIDDLE ti={int(ti)} field={field} row={int(row)} last_filled={int(last_filled_before)}", ti=int(ti))
                        self.status.config(text="Нельзя оставлять пустые значения в середине зондирования.")
                        self._redraw()
                        self.schedule_graph_redraw()
                        return

                if newv.strip() == "0" and (0 < row < last_filled_before):
                    self._tail_debug_log("TAIL_EDIT", f"end_edit REJECT_ZERO_MIDDLE ti={int(ti)} field={field} row={int(row)} last_filled={int(last_filled_before)}", ti=int(ti))
                    self.status.config(text="Нельзя записывать 0 в середине зондирования.")
                    self._redraw()
                    return
                if field == 'qc':
                    t.qc[row] = newv
                else:
                    t.fs[row] = newv
                self._tail_debug_log("TAIL_EDIT", f"end_edit APPLY ti={int(ti)} field={field} row={int(row)} old={repr(old_text)} new={repr(newv)}", ti=int(ti))
                try:
                    if str(old).strip() != str(newv).strip():
                        mark_reason = "manual_zero" if str(newv).strip() == "0" else "manual_edit"
                        mark_color = "orange" if str(newv).strip() == "0" else "purple"
                        fl.user_cells.add((row, field))
                        try:
                            fl.algo_cells.discard((row, field))
                        except Exception:
                            pass
                        try:
                            self.project_ops.append(op_cell_set(test_id=int(getattr(t, "tid", 0) or 0), row=row, field=field, before=str(old), after=str(newv), reason=mark_reason, color=mark_color, depth_m=self._safe_depth_m(t, row)))
                            _mk = self._mark_key(int(getattr(t, "tid", 0) or 0), self._safe_depth_m(t, row), str(field))
                            if _mk is not None:
                                self._marks_index[_mk] = {"reason": mark_reason, "color": mark_color}
                        except Exception:
                            pass
                except Exception:
                    pass
                fl.invalid = False
                self.flags[t.tid] = fl
            self._redraw()
            self.schedule_graph_redraw()

    def _last_filled_row(self, t: TestData) -> int:
        """Последняя строка с данными (qc или fs не пустые)."""
        q_arr = list(getattr(t, 'qc', []) or [])
        f_arr = list(getattr(t, 'fs', []) or [])
        n = max(len(q_arr), len(f_arr))
        for i in range(n - 1, -1, -1):
            qv = str(q_arr[i]).strip() if i < len(q_arr) and q_arr[i] is not None else ""
            fv = str(f_arr[i]).strip() if i < len(f_arr) and f_arr[i] is not None else ""
            if qv != "" or fv != "":
                try:
                    ti_dbg = next((idx for idx, _t in enumerate(self.tests) if _t is t), None)
                except Exception:
                    ti_dbg = None
                self._tail_debug_log("TAIL_DEBUG", f"last_filled_row ti={ti_dbg} len_qc={len(q_arr)} len_fs={len(f_arr)} result={i} rule=max_len_scan", ti=ti_dbg)
                return i
        try:
            ti_dbg = next((idx for idx, _t in enumerate(self.tests) if _t is t), None)
        except Exception:
            ti_dbg = None
        self._tail_debug_log("TAIL_DEBUG", f"last_filled_row ti={ti_dbg} len_qc={len(q_arr)} len_fs={len(f_arr)} result=-1 rule=max_len_scan", ti=ti_dbg)
        return -1


    def _delete_data_row_in_test(self, t: TestData, fl: TestFlags, row: int):
        """Удаляет строку row из depth/qc/fs и корректирует раскраски (interp/force/user)."""
        try:
            ti_dbg = next((idx for idx, _t in enumerate(self.tests) if _t is t), None)
        except Exception:
            ti_dbg = None
        self._tail_debug_log("TAIL_TRIM", f"delete_data_row START ti={ti_dbg} row={int(row)} before_len_depth={len(getattr(t, 'depth', []) or [])} before_len_qc={len(getattr(t, 'qc', []) or [])} before_len_fs={len(getattr(t, 'fs', []) or [])}", ti=ti_dbg)
        try:
            if 0 <= row < len(t.depth):
                t.depth.pop(row)
        except Exception:
            pass
        try:
            if 0 <= row < len(t.qc):
                t.qc.pop(row)
        except Exception:
            pass
        try:
            if 0 <= row < len(t.fs):
                t.fs.pop(row)
        except Exception:
            pass

        def shift_cells(cells: set[tuple[int, str]]):
            out = set()
            for r, kind in list(cells or set()):
                if r == row:
                    continue
                if r > row:
                    out.add((r - 1, kind))
                else:
                    out.add((r, kind))
            return out

        try:
            fl.interp_cells = shift_cells(getattr(fl, "interp_cells", set()))
        except Exception:
            fl.interp_cells = set()
        try:
            fl.force_cells = shift_cells(getattr(fl, "force_cells", set()))
        except Exception:
            fl.force_cells = set()
        try:
            fl.user_cells = shift_cells(getattr(fl, "user_cells", set()))
        except Exception:
            fl.user_cells = set()

        self._tail_debug_log("TAIL_TRIM", f"delete_data_row DONE ti={ti_dbg} row={int(row)} after_len_depth={len(getattr(t, 'depth', []) or [])} after_len_qc={len(getattr(t, 'qc', []) or [])} after_len_fs={len(getattr(t, 'fs', []) or [])}", ti=ti_dbg)


    def _append_row(self, ti: int):
        if self._is_test_locked(int(ti)):
            self._set_status("Опыт заблокирован")
            return
        if self.depth_start is None or self.step_m is None:
            return
        t = self.tests[ti]
        last_d = None
        for j in range(len(t.depth)-1, -1, -1):
            d = _parse_depth_float(t.depth[j])
            if d is not None:
                last_d = d
                break
        if last_d is None:
            idx = len(t.depth)
            tid = int(getattr(t, "tid", 0) or 0)
            d0 = float(self.depth0_by_tid.get(tid, float(self.depth_start or 0.0)))
            step = float(self.step_m or 0.05)
            t.depth.append(f"{(d0 + idx * step):g}")
        else:
            t.depth.append(f"{(last_d + self.step_m):g}")
        t.qc.append("")
        t.fs.append("")
        # не сбрасываем подсветку при добавлении строки; только гарантируем наличие флагов
        if t.tid not in self.flags:
            self.flags[t.tid] = TestFlags(False, set(), set(), set(), set())
        try:
            self._sync_layers_to_test_depth_range(int(ti))
        except Exception:
            pass
        self._redraw()
        self.schedule_graph_redraw()

    def _debug_header_sync(self, stage: str, **extra):
        if not bool(getattr(self, "_header_sync_debug", False)):
            return
        try:
            body_xv = tuple(self.canvas.xview())
        except Exception:
            body_xv = (0.0, 0.0)
        try:
            hdr_xv = tuple(self.hcanvas.xview())
        except Exception:
            hdr_xv = (0.0, 0.0)
        try:
            viewport_w = int(self.canvas.winfo_width() or 0)
        except Exception:
            viewport_w = 0
        try:
            content_w = float(getattr(self, "_scroll_w", 0.0) or 0.0)
        except Exception:
            content_w = 0.0
        try:
            first_world_x = float(self._column_x0(0)) if getattr(self, "expanded_cols", []) else float(self.pad_x)
        except Exception:
            first_world_x = 0.0
        try:
            body_left = float(self.canvas.canvasx(0))
        except Exception:
            body_left = 0.0
        try:
            header_left = float(self.hcanvas.canvasx(0))
        except Exception:
            try:
                header_left = float(getattr(self, "_header_offset_px", 0.0) or 0.0)
            except Exception:
                header_left = 0.0
        state = str(self.state()) if hasattr(self, "state") else ""
        incl = bool(getattr(self, "show_inclinometer", True))
        mode = str(getattr(self, "_header_sync_mode", "legacy") or "legacy")
        body_first_screen_x = first_world_x - body_left
        header_first_screen_x = first_world_x - header_left
        drift = header_first_screen_x - body_first_screen_x
        cnt = int(self._header_sync_source_counts.get(str(stage), 0) + 1)
        self._header_sync_source_counts[str(stage)] = cnt
        extras = " ".join(f"{k}={v}" for k, v in extra.items())
        print(
            f"[HDRSYNC] wheel={self._header_sync_wheel_seq} src={stage} cnt={cnt} mode={mode} "
            f"state={state} incl={int(incl)} body_xv={body_xv} hdr_xv={hdr_xv} vw={viewport_w} cw={content_w:.1f} "
            f"body_left={body_left:.2f} hdr_left={header_left:.2f} body_first={body_first_screen_x:.2f} "
            f"hdr_first={header_first_screen_x:.2f} drift={drift:.2f} pending={int(bool(getattr(self, '_header_sync_pending', False)))} {extras}"
        )

    def _begin_scroll_debug_cycle(self, source: str):
        self._header_sync_wheel_seq = int(getattr(self, "_header_sync_wheel_seq", 0) or 0) + 1
        self._header_sync_source_counts = {}
        self._debug_header_sync("wheel_begin", source=source)

    def _schedule_header_stabilize(self, source: str = ""):
        # legacy no-op: X синхронизируется только через _apply_shared_xview.
        self._header_sync_pending = False
        self._debug_header_sync("schedule_skip", source=source)

    # ---------------- scrolling ----------------
    def _on_mousewheel(self, event):
        # скролл закрывает активную ячейку
        self._begin_scroll_debug_cycle("mousewheel_y")
        self._end_edit(commit=True)
        delta = int(-1 * (event.delta / 120)) if event.delta else 0
        if delta != 0:
            self.canvas.yview_scroll(delta, "units")
            self._sync_header_body_after_scroll()
        return "break"

    def _on_mousewheel_linux(self, direction):
        # скролл закрывает активную ячейку
        self._begin_scroll_debug_cycle("mousewheel_y_linux")
        self._end_edit(commit=True)
        self.canvas.yview_scroll(direction, "units")
        self._sync_header_body_after_scroll()
        return "break"

    def _get_body_view_top_canvas_y(self) -> float:
        try:
            return float(self.canvas.canvasy(0))
        except Exception:
            return 0.0

    def _sync_header_body_after_scroll(self):
        """Нормализует вертикальный сдвиг body canvas (без участия шапки)."""
        if getattr(self, "_ysync_lock", False):
            return
        self._ysync_lock = True
        try:
            body_h = float(self._total_body_height())
            try:
                view_h = float(self.canvas.winfo_height() or 1)
            except Exception:
                view_h = 1.0
            top_y = self._get_body_view_top_canvas_y()
            max_top = max(0.0, body_h - max(1.0, view_h))
            if body_h <= max(1.0, view_h):
                target_top = 0.0
            else:
                target_top = min(max(top_y, 0.0), max_top)

            if abs(target_top - top_y) > 0.5:
                frac = 0.0 if body_h <= 1.0 else (target_top / body_h)
                frac = 0.0 if frac < 0.0 else (1.0 if frac > 1.0 else frac)
                try:
                    self.canvas.yview_moveto(frac)
                except Exception:
                    pass
        finally:
            self._ysync_lock = False

    def _on_mousewheel_x(self, event):
        """Горизонтальная прокрутка колесом шагом 1 колонка (когда курсор над шапкой или горизонтальным скроллом)."""
        self._begin_scroll_debug_cycle("mousewheel_x")
        self._end_edit(commit=True)
        try:
            delta = int(-1 * (event.delta / 120)) if getattr(event, "delta", 0) else 0
        except Exception:
            delta = 0
        if not delta:
            return "break"
        self._scroll_x_by_one_column(delta)
        return "break"

    def _on_mousewheel_linux_x(self, direction):
        """Linux: Button-4/5 для горизонтальной прокрутки шагом 1 колонка."""
        self._begin_scroll_debug_cycle("mousewheel_x_linux")
        self._end_edit(commit=True)
        try:
            direction = int(direction)
        except Exception:
            direction = 0
        if not direction:
            return "break"
        self._scroll_x_by_one_column(direction)
        return "break"

    def _on_collapsed_dock_wheel(self, event):
        dock = getattr(self, "collapsed_dock", None)
        if dock is None:
            return "break"
        try:
            delta = int(-1 * (event.delta / 120)) if getattr(event, "delta", 0) else 0
        except Exception:
            delta = 0
        if not delta:
            return "break"
        try:
            dock.yview_scroll(delta, "units")
        except Exception:
            pass
        return "break"

    def _on_collapsed_dock_wheel_linux(self, direction: int):
        dock = getattr(self, "collapsed_dock", None)
        if dock is None:
            return "break"
        try:
            direction = int(direction)
        except Exception:
            direction = 0
        if not direction:
            return "break"
        try:
            dock.yview_scroll(direction, "units")
        except Exception:
            pass
        return "break"

    def _scroll_x_by_one_column(self, direction: int):
        """Сдвиг по X на одну колонку зондирования (шаг = ширина блока шапки)."""
        try:
            direction = 1 if direction > 0 else -1
        except Exception:
            direction = 1
        # ширина одной колонки (таблица + график при включении) + зазор между колонками
        col_block = int(self._column_block_width() + self.col_gap)
        try:
            w = float(getattr(self, "_scroll_w", 0) or 0)
        except Exception:
            w = 0.0
        if w <= 1:
            # на всякий случай обновим ширину
            try:
                w = float(self._content_size()[0])
                self._scroll_w = w
            except Exception:
                w = 1.0

        try:
            x0_frac = float(self.canvas.xview()[0])
        except Exception:
            x0_frac = 0.0
        x0_px = x0_frac * w
        target_px = max(0.0, x0_px + direction * col_block)

        # ограничим по правому краю
        try:
            view_w = float(self.canvas.winfo_width())
        except Exception:
            view_w = 0.0

        # Если последний (правый) опыт уже появился в видимой области,
        # блокируем дальнейший шаг вправо. Это убирает «последний лишний скролл»,
        # который и вызывает смещение шапки на самом правом краю.
        try:
            last_right_px = float(self._last_column_right_px())
        except Exception:
            last_right_px = 0.0
        view_right_px = x0_px + max(1.0, view_w)
        # Блокируем шаг вправо ТОЛЬКО когда последняя колонка ВИДНА ПОЛНОСТЬЮ.
        if direction > 0 and view_right_px >= (last_right_px - 0.5):
            return

        max_px = max(0.0, w - max(1.0, view_w))
        if target_px > max_px:
            target_px = max_px

        frac = 0.0 if w <= 1 else (target_px / w)
        try:
            self._xview_proxy("moveto", frac)
        except Exception:
            pass


    # ---------------- fix algorithm (from v2.3.1) ----------------
    def fix_by_algorithm(self):
        if not self.tests:
            return

        self._push_undo()
        random.seed(42)
        for t in self.tests:
            tid = t.tid
            prev_flags = self.flags.get(tid) or TestFlags(False, set(), set(), set(), set())
            _prev_user_cells = set(getattr(prev_flags, 'user_cells', set()) or set())
            # Снимок значений до автокорректировки (для зелёной подсветки)
            _orig_qc = list(getattr(t, 'qc', []) or [])
            _orig_fs = list(getattr(t, 'fs', []) or [])
            _orig_depth = list(getattr(t, 'depth', []) or [])
            algo_cells: set[tuple[int, str]] = set()
            # Алгоритм не должен создавать новые строки: работаем только
            # по пересечению уже существующих пар qc/fs.
            n = min(len(getattr(t, 'qc', []) or []), len(getattr(t, 'fs', []) or []))
            if n == 0:
                # сохраняем пользовательские правки (на случай пустого зондирования)
                self.flags[tid] = TestFlags(False, set(), set(), _prev_user_cells, algo_cells)
                continue

            qc = [(_parse_cell_int(v) or 0) for v in t.qc]
            fs = [(_parse_cell_int(v) or 0) for v in t.fs]

            invalid = (_max_zero_run(qc) > 5) or (_max_zero_run(fs) > 5)
            interp_cells: set[tuple[int, str]] = set(getattr(prev_flags, 'interp_cells', set()) or set())
            force_cells: set[tuple[int, str]] = set(getattr(prev_flags, 'force_cells', set()) or set())

            if invalid:
                self.flags[tid] = TestFlags(True, interp_cells, force_cells, _prev_user_cells, algo_cells)
                continue

            def interp_in_place(arr: list[int], kind: str):
                i = 0
                while i < n:
                    if arr[i] != 0:
                        i += 1
                        continue
                    j = i
                    while j < n and arr[j] == 0:
                        j += 1
                    gap_len = j - i
                    if gap_len <= 5:
                        left = i - 1
                        right = j
                        if left >= 0 and right < n and arr[left] != 0 and arr[right] != 0:
                            a = arr[left]; b = arr[right]
                            for k in range(gap_len):
                                tt = (k + 1) / (gap_len + 1)
                                if (i + k, kind) not in _prev_user_cells and (i + k, kind) not in interp_cells and (i + k, kind) not in force_cells:
                                    arr[i + k] = int(round(_interp_with_noise(a, b, tt)))
                                interp_cells.add((i + k, kind))
                        elif left >= 0 and arr[left] != 0:
                            a = arr[left]
                            for k in range(gap_len):
                                arr[i + k] = int(round(_noise_around(a)))
                                interp_cells.add((i + k, kind))
                        elif right < n and arr[right] != 0:
                            b = arr[right]
                            for k in range(gap_len):
                                arr[i + k] = int(round(_noise_around(b)))
                                interp_cells.add((i + k, kind))
                    i = j

            interp_in_place(qc, "qc")
            interp_in_place(fs, "fs")

            # ensure no zeros
            for arr, kind in ((qc, "qc"), (fs, "fs")):
                for i in range(n):
                    if arr[i] != 0:
                        continue
                    left = i - 1
                    while left >= 0 and arr[left] == 0:
                        left -= 1
                    right = i + 1
                    while right < n and arr[right] == 0:
                        right += 1
                    if left >= 0 and right < n:
                        arr[i] = int(round(_interp_with_noise(arr[left], arr[right], 0.5)))
                    elif left >= 0:
                        arr[i] = int(round(_noise_around(arr[left])))
                    elif right < n:
                        arr[i] = int(round(_noise_around(arr[right])))
                    else:
                        arr[i] = 1
                    interp_cells.add((i, kind))

# write back with markers (for user visibility)
            for i in range(n):
                qv = int(max(1, round(qc[i])))
                fv = int(max(1, round(fs[i])))
                t.qc[i] = str(qv)
                t.fs[i] = str(fv)


            # --- зелёная подсветка: что реально поменялось алгоритмом ---
            try:
                for i2 in range(n):
                    # новые значения (после записи)
                    new_q = str(t.qc[i2]).strip() if i2 < len(t.qc) else ""
                    new_f = str(t.fs[i2]).strip() if i2 < len(t.fs) else ""
                    # исходные (до корректировки)
                    old_q = str(_orig_qc[i2]).strip() if i2 < len(_orig_qc) else ""
                    old_f = str(_orig_fs[i2]).strip() if i2 < len(_orig_fs) else ""
                    if (i2, "qc") not in _prev_user_cells and new_q != old_q:
                        algo_cells.add((i2, "qc"))
                    if (i2, "fs") not in _prev_user_cells and new_f != old_f:
                        algo_cells.add((i2, "fs"))
            except Exception:
                pass

            self.flags[tid] = TestFlags(False, interp_cells, force_cells, _prev_user_cells, algo_cells)

        try:
            changes = []
            for t in self.tests:
                fl = self.flags.get(getattr(t, "tid", 0))
                for row, fld in sorted(list(getattr(fl, "algo_cells", set()) or set())):
                    changes.append({"testId": int(getattr(t, "tid", 0) or 0), "row": int(row), "field": fld, "depthM": self._safe_depth_m(t, row), "mark": {"reason": "algo_fix", "color": "green"}})
            if changes:
                self.project_ops.append(op_algo_fix_applied(changes=changes))
            if changes:
                self._rebuild_marks_index()
        except Exception:
            pass

        self._end_edit(commit=True)
        self._redraw()
        self.schedule_graph_redraw()

        # После успешной корректировки — синяя строка в подвале
        try:
            self.footer_cmd.config(foreground="#0b5ed7")
            self.footer_cmd.config(text="Статическое зондирование откорректировано.")
        except Exception:
            pass


    # ---------------- export ----------------


    def _read_calc_params(self):
        try:
            cal = self._current_calibration()
            return cal.scale_div, cal.fcone_kn, cal.fsleeve_kn, cal.cone_area_cm2, cal.sleeve_area_cm2
        except Exception as e:
            messagebox.showerror("Ошибка", f"Некорректные параметры пересчёта: {e}")
            return None

    def _safe_sheet_name(self, name: str) -> str:
        bad = '[]:*?/\\'
        for ch in bad:
            name = name.replace(ch, "_")
        name = name.strip()
        if not name:
            name = "Sheet"
        return name[:31]


    def _collect_export_tests(self):
        selection = select_export_tests(getattr(self, "tests", []) or [])
        try:
            print(
                "[EXPORT_SELECTION] "
                f"total_tests={selection.total_tests} "
                f"exported_tests={selection.exported_tests} "
                f"skipped_hidden={selection.skipped_hidden} "
                f"skipped_deleted={selection.skipped_deleted}"
            )
        except Exception:
            pass
        return selection

    def _validate_export_rows(self) -> bool:
        """Блокируем экспорт, если есть строки, где заполнена только одна колонка (qc или fs).
        Подсвечиваем зондирование красным (как ошибка) и показываем предупреждение.
        """
        bad = False
        selected = self._collect_export_tests().tests
        selected_ids = {id(t) for t in selected}
        for t in self.tests:
            tid = t.tid
            fl = self.flags.get(tid) or TestFlags(False, set(), set(), set(), set())
            if id(t) not in selected_ids:
                self.flags[tid] = fl
                continue
            n = max(len(getattr(t, 'qc', []) or []), len(getattr(t, 'fs', []) or []))
            qc_arr = getattr(t, 'qc', []) or []
            fs_arr = getattr(t, 'fs', []) or []
            for i in range(n):
                q = (qc_arr[i].strip() if i < len(qc_arr) and qc_arr[i] is not None else '')
                f = (fs_arr[i].strip() if i < len(fs_arr) and fs_arr[i] is not None else '')
                q_filled = (q != '' and q != '0')
                f_filled = (f != '' and f != '0')
                if q_filled ^ f_filled:
                    bad = True
                    fl.invalid = True
                    break
            self.flags[tid] = fl
        if bad:
            self._redraw()
            messagebox.showwarning("Экспорт невозможен",
                                   "Есть строки, где заполнена только одна колонка (qc или fs).\n"
                                   "Заполни вторую колонку или очисти строку полностью.")
            return False
        return True


    def export_excel(self):
        if not self.tests:
            messagebox.showwarning("Нет данных", "Сначала нажми «Показать зондирования»")
            return
        if not self._validate_export_rows():
            return
        if export_excel_file is None:
            messagebox.showerror("Экспорт недоступен", "Для экспорта Excel установите зависимость openpyxl.")
            return

        out = filedialog.asksaveasfilename(
            title="Куда сохранить Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if not out:
            return

        try:
            export_excel_file(
                self.tests,
                geo_kind=getattr(self, "geo_kind", "K2"),
                out_path=Path(out),
                cal=self._current_calibration(),
                include_only_export_on=True,
            )
            messagebox.showinfo("Готово", f"Excel сохранён:\n{out}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _ask_cpt_calc_settings(self) -> dict[str, object] | None:
        dlg = tk.Toplevel(self)
        dlg.title("Настройки расчёта φ/E по CPT")
        dlg.transient(self)
        dlg.grab_set()
        frm = ttk.Frame(dlg, padding=10)
        frm.pack(fill="both", expand=True)
        current = dict(getattr(self, "cpt_calc_settings", {}) or {})
        method_var = tk.StringVar(value=str(current.get("method") or METHOD_SP446))
        alluvial_var = tk.BooleanVar(value=True)
        gwl_curr = current.get("groundwater_level")
        gwl_var = tk.StringVar(value=("" if gwl_curr in (None, "") else str(gwl_curr)))
        gwl_scale_var = tk.DoubleVar(value=float(gwl_curr) if gwl_curr not in (None, "") else 0.0)

        ttk.Label(frm, text="Методика:").pack(anchor="w")
        ttk.Radiobutton(frm, text="СП 446.1325800.2019 (с Изм. № 1), приложение Ж", variable=method_var, value=METHOD_SP446).pack(anchor="w")
        ttk.Radiobutton(frm, text="СП 11-105-97 (Приложение И)", variable=method_var, value=METHOD_SP11).pack(anchor="w")
        ttk.Label(frm, text="Пески: alluvial = да (фиксировано)", foreground="#3d5f99").pack(anchor="w", pady=(6, 0))

        gwl_box = ttk.LabelFrame(frm, text="Уровень грунтовых вод (УГВ), м", padding=6)
        gwl_box.pack(fill="x", pady=(8, 0))
        ent = ttk.Entry(gwl_box, textvariable=gwl_var, width=10)
        ent.pack(side="right")
        ttk.Label(gwl_box, text="числом:").pack(side="right", padx=(0, 4))
        scl = tk.Scale(gwl_box, from_=0, to=30, orient="horizontal", resolution=0.1, variable=gwl_scale_var, troughcolor="#4f89ff", activebackground="#2b6cff", highlightthickness=0)
        scl.pack(fill="x")

        def _sync_from_scale(_evt=None):
            gwl_var.set(f"{float(gwl_scale_var.get()):.2f}")

        def _sync_from_entry(_evt=None):
            txt = str(gwl_var.get() or "").strip().replace(",", ".")
            if not txt:
                return
            try:
                gwl_scale_var.set(float(txt))
            except Exception:
                pass

        scl.configure(command=lambda _v: _sync_from_scale())
        ent.bind("<FocusOut>", _sync_from_entry)

        none_var = tk.BooleanVar(value=(gwl_curr in (None, "")))

        def _toggle_none():
            if bool(none_var.get()):
                gwl_var.set("")

        ttk.Checkbutton(gwl_box, text="не задан", variable=none_var, command=_toggle_none).pack(anchor="w", pady=(4, 0))
        result: dict[str, object] = {"ok": False}

        def _ok():
            result["ok"] = True
            result["method"] = str(method_var.get() or METHOD_SP446)
            result["alluvial_sands"] = True
            txt = str(gwl_var.get() or "").strip().replace(",", ".")
            if bool(none_var.get()) or not txt:
                result["groundwater_level"] = None
            else:
                try:
                    result["groundwater_level"] = float(txt)
                except Exception:
                    result["groundwater_level"] = None
            dlg.destroy()

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="Отмена", command=dlg.destroy).pack(side="right")
        ttk.Button(btns, text="Рассчитать", command=_ok).pack(side="right", padx=(0, 8))
        self.wait_window(dlg)
        if not bool(result.get("ok")):
            return None
        return {"method": result["method"], "alluvial_sands": True, "groundwater_level": result.get("groundwater_level")}

    def calculate_cpt_params(self):
        settings = self._ask_cpt_calc_settings()
        if settings is None:
            return
        self._push_undo()
        self.cpt_calc_settings = dict(settings)
        calc = CptCalcSettings(method=str(settings.get("method") or METHOD_SP446), alluvial_sands=bool(settings.get("alluvial_sands", True)), groundwater_level=settings.get("groundwater_level"))
        results = calculate_ige_cpt_results(tests=list(self.tests or []), ige_registry=self.ige_registry, settings=calc)
        missing: list[str] = []
        ok_count = 0
        for ige_id in sorted(self.ige_registry.keys(), key=self._ige_id_to_num):
            ent = self._ensure_ige_entry(ige_id)
            cpt = results.get(ige_id)
            ent["cpt_result"] = cpt
            if not cpt:
                missing.append(f"{ige_id}: нет данных qc в интервалах слоя")
                continue
            if str(cpt.get("status") or "") == "ok":
                ok_count += 1
            else:
                missing.append(f"{ige_id}: {cpt.get('reason') or cpt.get('status_text') or 'не хватает данных'}")
        self._sync_layers_panel()
        self._dirty = True
        self._update_window_title()
        self._show_cpt_calc_result_dialog(ok_count=ok_count, missing=missing)

    def _show_cpt_calc_result_dialog(self, *, ok_count: int, missing: list[str]):
        dlg = tk.Toplevel(self)
        if missing:
            dlg.title("Расчёт CPT: есть нерасчётные ИГЭ или недостающие данные")
        else:
            dlg.title("Расчёт CPT: готово")
        dlg.transient(self)
        dlg.grab_set()
        frm = ttk.Frame(dlg, padding=10)
        frm.pack(fill="both", expand=True)
        if missing:
            ttk.Label(
                frm,
                text="Для части ИГЭ расчёт по данным зондирования не выполнен. Проверьте исходные данные или тип грунта:",
                foreground="#8a3d00",
            ).pack(anchor="w")
            box = tk.Text(frm, height=min(12, max(4, len(missing))), width=90, wrap="word")
            box.pack(fill="both", expand=True, pady=(6, 0))
            box.insert("1.0", "\n".join([f"• {line}" for line in missing]))
            box.configure(state="disabled")
        else:
            ttk.Label(frm, text=f"Расчёт завершён успешно. ИГЭ с результатами: {ok_count}", foreground="#1a5e1a").pack(anchor="w")

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="Сформировать отчёт", command=lambda: self.export_cpt_protocol()).pack(side="left")
        ttk.Button(btns, text="Закрыть", command=dlg.destroy).pack(side="right")
        self.wait_window(dlg)

    def export_cpt_protocol(self):
        if not (self.ige_registry or {}):
            messagebox.showwarning("Протокол CPT", "Нет ИГЭ для протокола")
            return
        rows: list[dict[str, object]] = []
        for ige_id in sorted(self.ige_registry.keys(), key=self._ige_id_to_num):
            ent = self._ensure_ige_entry(ige_id)
            cpt = dict(ent.get("cpt_result") or {})
            bounds = cpt.get("layer_bounds") or []
            bounds_txt = ", ".join([f"{a:.2f}-{b:.2f} м" for a, b in bounds]) if bounds else "-"
            rows.append(
                {
                    "ige_id": ige_id,
                    "soil_type": ent.get("soil_type") or "",
                    "bounds": bounds_txt,
                    "mid_depth": cpt.get("mid_depth", "-"),
                    "sand_class": ent.get("sand_class") or "",
                    "alluvial": True,
                    "saturated": cpt.get("saturated", ent.get("saturated")),
                    "il": ent.get("IL", ""),
                    "consistency": cpt.get("consistency", ent.get("consistency", "")),
                    "consistency_source": cpt.get("consistency_source", "manual"),
                    "note": ent.get("note", ""),
                    "source_flags": ent.get("source_flags", {"CPT": True, "LAB": False, "Stamp": False}),
                    "qc_mean": cpt.get("qc_mean", "-"),
                    "n": cpt.get("n", "-"),
                    "qc_min": cpt.get("qc_min", "-"),
                    "qc_max": cpt.get("qc_max", "-"),
                    "std": cpt.get("std", "-"),
                    "variation": cpt.get("variation", "-"),
                    "lookup_table": cpt.get("lookup_table", "-"),
                    "lookup_branch": cpt.get("lookup_branch", "-"),
                    "lookup_interval": cpt.get("lookup_interval", "-"),
                    "status": cpt.get("status_text", "-"),
                    "reason": cpt.get("reason", ""),
                    "phi_norm": cpt.get("phi_norm", "-"),
                    "E_norm": cpt.get("E_norm", "-"),
                }
            )
        out = filedialog.asksaveasfilename(title="Сохранить протокол φ и E (CPT)", defaultextension=".docx", filetypes=[("Word", "*.docx")])
        if not out:
            return
        template = Path("templates/protocol_phi_E_CPT.docx")
        try:
            export_cpt_protocol_docx(
                out_path=Path(out),
                object_name=str(getattr(self, "object_name", "") or ""),
                settings=dict(getattr(self, "cpt_calc_settings", {}) or {}),
                rows=rows,
                template_path=template,
            )
            messagebox.showinfo("Протокол CPT", f"Протокол сохранён:\n{out}")
        except Exception as e:
            messagebox.showerror("Протокол CPT", f"Не удалось сформировать протокол:\n{e}")

    def export_dxf(self):
        messagebox.showinfo(
            "Экспорт DXF",
            "Кнопка экспорта графиков в DXF добавлена. Логика экспорта будет реализована следующим шагом.",
        )

    def export_credo_zip(self):
        """Export each test into two CSV (depth;qc_MPa and depth;fs_kPa) without headers, pack into ZIP.
        Naming: 'СЗ-<№> лоб.csv' and 'СЗ-<№> бок.csv'.
        """
        if not getattr(self, "tests", None):
            messagebox.showwarning("Нет данных", "Сначала нажми «Показать зондирования»")
            return
        selection = self._collect_export_tests()
        tests_exp = list(selection.tests)
        if not tests_exp:
            messagebox.showwarning('Нет данных', 'Нет зондирований для экспорта (все исключены).')
            return

        params = self._read_calc_params()
        if not params:
            return
        scale_div, fmax_cone_kn, fmax_sleeve_kn, area_cone_cm2, area_sleeve_cm2 = params

        out_zip = filedialog.asksaveasfilename(
            title="Куда сохранить ZIP для CREDO",
            defaultextension=".zip",
            filetypes=[("ZIP архив", "*.zip")]
        )
        if not out_zip:
            messagebox.showinfo("Экспорт CREDO", "Экспорт отменён: файл не выбран.")
            return

        def fmt_float_comma(x, nd=2):
            if x is None:
                return ""
            s = f"{x:.{nd}f}"
            return s.replace(".", ",")

        def fmt_depth(x):
            if x is None:
                return ""
            s = f"{x:.2f}".replace(".", ",")
            s = s.rstrip("0").rstrip(",")
            return s

        def safe_part(s):
            s = str(s)
            return re.sub(r'[<>:"/\|?*]+', "_", s)

        tmp_dir = Path(out_zip).with_suffix("")
        try:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)
            tmp_dir.mkdir(parents=True, exist_ok=True)

            created = []
            for t in tests_exp:
                tid = safe_part(getattr(t, "tid", ""))
                rows_lob = []
                rows_bok = []
                depth_arr = getattr(t, "depth", [])
                qc_arr = getattr(t, "qc", [])
                fs_arr = getattr(t, "fs", [])
                n = max(len(depth_arr), len(qc_arr), len(fs_arr))
                for idx in range(n):
                    depth_val = _parse_depth_float(depth_arr[idx]) if idx < len(depth_arr) else None
                    if depth_val is None:
                        continue
                    qc_del = _parse_cell_int(qc_arr[idx]) if idx < len(qc_arr) else None
                    fs_del = _parse_cell_int(fs_arr[idx]) if idx < len(fs_arr) else None

                    qc_MPa = None
                    fs_kPa = None
                    if qc_del is not None:
                        qc_MPa, _ = calc_qc_fs_from_del(
                            int(qc_del),
                            0,
                            scale_div=scale_div,
                            fcone_kn=fmax_cone_kn,
                            fsleeve_kn=fmax_sleeve_kn,
                            cone_area_cm2=area_cone_cm2,
                            sleeve_area_cm2=area_sleeve_cm2,
                        )
                    if fs_del is not None:
                        _, fs_kPa = calc_qc_fs_from_del(
                            0,
                            int(fs_del),
                            scale_div=scale_div,
                            fcone_kn=fmax_cone_kn,
                            fsleeve_kn=fmax_sleeve_kn,
                            cone_area_cm2=area_cone_cm2,
                            sleeve_area_cm2=area_sleeve_cm2,
                        )

                    d_str = fmt_depth(depth_val)
                    qc_str = "" if qc_MPa is None else fmt_float_comma(round(qc_MPa, 2), nd=2)
                    fs_str = "" if fs_kPa is None else str(int(round(fs_kPa, 0)))
                    rows_lob.append(f"{d_str};{qc_str}")
                    rows_bok.append(f"{d_str};{fs_str}")

                fn_lob = tmp_dir / f"СЗ-{tid} лоб.csv"
                fn_bok = tmp_dir / f"СЗ-{tid} бок.csv"
                fn_lob.write_text("\n".join(rows_lob) + ("\n" if rows_lob else ""), encoding="utf-8")
                fn_bok.write_text("\n".join(rows_bok) + ("\n" if rows_bok else ""), encoding="utf-8")
                created.extend([fn_lob, fn_bok])

            with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
                for f in created:
                    z.write(f, arcname=f.name)

            self._credo_force_export = False
            messagebox.showinfo("Экспорт CREDO", f"ZIP сохранён:\n{out_zip}")
        except Exception as e:
            try:
                self.usage_logger.exception("Ошибка экспорта CREDO ZIP: %s", e)
            except Exception:
                pass
            messagebox.showerror("Ошибка экспорта CREDO", str(e))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _center_child(self, win: tk.Toplevel):
        try:
            win.update_idletasks()
            w = win.winfo_reqwidth()
            h = win.winfo_reqheight()
            px = self.winfo_rootx()
            py = self.winfo_rooty()
            pw = self.winfo_width()
            ph = self.winfo_height()
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            win.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass
    def _place_calendar_near_header(self, dlg: tk.Toplevel, ti: int):
        """Позиционирует календарь у шапки выбранной зондирования (колонки) на Canvas."""
        try:
            dlg.update_idletasks()
            self._refresh_display_order()
            ti = int(max(0, int(ti)))
            host_canvas = self.hcanvas
            if ti in (getattr(self, "collapsed_cols", []) or []):
                row_idx = int((getattr(self, "collapsed_cols", []) or []).index(ti))
                x0, y0, _x1, _y1 = self._collapsed_header_bbox(row_idx)
                host_canvas = getattr(self, "collapsed_dock", self.hcanvas)
            else:
                col = self._expanded_col_index(int(ti))
                if col is None:
                    col = 0
                x0, y0, _x1, _y1 = self._header_bbox(int(col))
            try:
                x_view = 0.0 if host_canvas is getattr(self, "collapsed_dock", None) else self._shared_x_offset_px()
            except Exception:
                x_view = 0.0
            sx = host_canvas.winfo_rootx() + int(x0 - x_view) + 10
            sy = host_canvas.winfo_rooty() + int(y0) + 10
            dlg.geometry(f"+{sx}+{sy}")
        except Exception:
            # fallback: центрируем по основному окну
            try:
                self._center_child(dlg)
            except Exception:
                pass

    def _ensure_object_code(self) -> str:
        """Раньше тут всплывало отдельное окно 'Объект', если поле пустое.
        По новой логике объект задаётся в окне 'Параметры GEO' и может быть пустым.
        """
        self.object_code = (getattr(self, "object_code", "") or "").strip()
        return self.object_code

    def _extract_file_map_text(self) -> str:
        """Возвращает текст FILE MAP из исходника (между маркерами)."""
        try:
            p = Path(__file__)
            src = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception as e:
            return f"Не удалось прочитать исходник для FILE MAP: {e}"

        begin = None
        end = None
        for i, line in enumerate(src):
            if "=== FILE MAP BEGIN ===" in line:
                begin = i
            if "=== FILE MAP END ===" in line:
                end = i
                break
        if begin is None or end is None or end <= begin:
            return "FILE MAP не найден в исходнике."

        # Убираем ведущие "# " для красивого отображения
        out = []
        for line in src[begin+1:end]:
            if line.startswith("# "):
                out.append(line[2:])
            elif line.startswith("#"):
                out.append(line[1:])
            else:
                out.append(line)
        return "\n".join(out).strip()

    def show_file_map(self):
        """Окно просмотра карты проекта (FILE MAP)."""
        win = tk.Toplevel(self)
        win.title("Карта проекта")
        win.geometry("860x640")
        try:
            win.iconbitmap(self._icon_path)  # type: ignore[attr-defined]
        except Exception:
            pass

        top = ttk.Frame(win, padding=(10,10))
        top.pack(fill="both", expand=True)

        hdr = ttk.Frame(top)
        hdr.pack(fill="x")
        ttk.Label(hdr, text="FILE MAP (для разработчика)", font=("Segoe UI", 12, "bold")).pack(side="left")

        def copy_all():
            data = txt.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(data)
            win.update_idletasks()

        ttk.Button(hdr, text="Копировать", command=copy_all).pack(side="right")

        body = ttk.Frame(top)
        body.pack(fill="both", expand=True, pady=(10,0))
        ysb = ttk.Scrollbar(body, orient="vertical")
        ysb.pack(side="right", fill="y")

        txt = tk.Text(body, wrap="none", height=1, yscrollcommand=ysb.set)
        txt.pack(side="left", fill="both", expand=True)
        ysb.config(command=txt.yview)

        content = self._extract_file_map_text()
        txt.insert("1.0", content)
        txt.config(state="disabled")

        # monospace-ish
        try:
            txt.config(font=("Cascadia Mono", 10))
        except Exception:
            pass

        ttk.Button(top, text="Закрыть", command=win.destroy).pack(anchor="e", pady=(10,0))


    def _common_params_from_project_settings(self, settings: ProjectSettings | None) -> dict[str, str]:
        s = settings or ProjectSettings()
        params = {
            "controller_type": str(getattr(s, "controller_type", "") or ""),
            "controller_scale_div": str(getattr(s, "controller_scale_div", "") or ""),
            "probe_type": str(getattr(s, "probe_type", "") or ""),
            "cone_kn": str(getattr(s, "cone_kn", "") or ""),
            "sleeve_kn": str(getattr(s, "sleeve_kn", "") or ""),
            "cone_area_cm2": str(getattr(s, "cone_area_cm2", "") or ""),
            "sleeve_area_cm2": str(getattr(s, "sleeve_area_cm2", "") or ""),
        }
        if not params["controller_scale_div"]:
            params["controller_scale_div"] = str(getattr(s, "scale", "") or "")
        if not params["cone_kn"]:
            params["cone_kn"] = str(getattr(s, "fcone", "") or "")
        if not params["sleeve_kn"]:
            params["sleeve_kn"] = str(getattr(s, "fsleeve", "") or "")
        if not params["cone_area_cm2"]:
            params["cone_area_cm2"] = str(getattr(s, "acon", "") or "")
        if not params["sleeve_area_cm2"]:
            params["sleeve_area_cm2"] = str(getattr(s, "asleeve", "") or "")
        return params

    def _normalized_project_state(self, project: Project) -> dict:
        state = copy.deepcopy(dict(getattr(project, "state", {}) or {}))
        settings = getattr(project, "settings", ProjectSettings())
        if "step_m" not in state:
            state["step_m"] = float(getattr(settings, "step_m", getattr(self, "step_m", 0.1) or 0.1) or 0.1)
        if "depth_start" not in state:
            state["depth_start"] = float(getattr(self, "depth_start", 0.0) or 0.0)
        if "geo_kind" not in state:
            src_kind = str((getattr(getattr(project, "source", None), "kind", "") or "")).upper()
            state["geo_kind"] = "K4" if src_kind == "GXL" else str(getattr(self, "geo_kind", "K2") or "K2")
        if "common_params" not in state:
            state["common_params"] = self._common_params_from_project_settings(settings)
        if "cpt_calc_settings" not in state:
            state["cpt_calc_settings"] = dict((getattr(settings, "extras", {}) or {}).get("cpt_calc_settings") or {})
        if "calc_tab_state" not in state:
            state["calc_tab_state"] = dict((getattr(settings, "extras", {}) or {}).get("calc_tab_state") or {})
        return state

    def _project_settings_from_ui(self) -> ProjectSettings:
        extras = {
            "cpt_calc_settings": dict(getattr(self, "cpt_calc_settings", {}) or {}),
            "calc_tab_state": dict(getattr(self, "calc_tab_state", CalculationTabState()).__dict__),
            "project_mode_params": dict(getattr(self, "project_mode_params", {}) or {}),
        }
        cp = self._current_common_params()
        scale_val = str(cp.get("controller_scale_div", "250") or "250")
        fcone_val = str(cp.get("cone_kn", "30") or "30")
        fsleeve_val = str(cp.get("sleeve_kn", "10") or "10")
        acon_val = str(cp.get("cone_area_cm2", "10") or "10")
        asleeve_val = str(cp.get("sleeve_area_cm2", "350") or "350")
        return ProjectSettings(
            scale=scale_val,
            fcone=fcone_val,
            fsleeve=fsleeve_val,
            acon=acon_val,
            asleeve=asleeve_val,
            controller_type=(self.controller_type_var.get().strip() if hasattr(self, "controller_type_var") else ""),
            controller_scale_div=scale_val,
            probe_type=(self.probe_type_var.get().strip() if hasattr(self, "probe_type_var") else ""),
            cone_kn=fcone_val,
            sleeve_kn=fsleeve_val,
            cone_area_cm2=acon_val,
            sleeve_area_cm2=asleeve_val,
            step_m=float(getattr(self, "step_m", 0.1) or 0.1),
            k2k4_mode=str(getattr(self, "k2k4_mode", "") or ""),
            extras=extras,
        )

    def _build_project_payload(self) -> Project:
        src = SourceInfo(
            kind=("GXL" if getattr(self, "is_gxl", False) else "GEO"),
            filename=(Path(self.geo_path).name if getattr(self, "geo_path", None) else ""),
            ext=((Path(self.geo_path).suffix.lower().lstrip(".")) if getattr(self, "geo_path", None) else ""),
            mime="application/octet-stream",
        )
        return Project(
            object_name=(self.object_name or self.object_code or ""),
            project_name=str(getattr(self, "project_name", "") or ""),
            project_type=str(getattr(self, "project_type", "type2_electric") or "type2_electric"),
            source=src,
            settings=self._project_settings_from_ui(),
            ops=list(getattr(self, "project_ops", []) or []),
            state=self._snapshot(),
        )

    def _safe_depth_m(self, t: TestData, row: int) -> float | None:
        try:
            if row < 0 or row >= len(getattr(t, "depth", []) or []):
                return None
            d = _parse_depth_float(str(t.depth[row]))
            if d is None:
                return None
            return float(d)
        except Exception:
            return None

    def _norm_depth_key(self, depth_m: float | int | str | None) -> float | None:
        if depth_m is None:
            return None
        try:
            return round(float(depth_m), 3)
        except Exception:
            return None

    def _row_by_depth_m(self, t: TestData, depth_m: float | int | str | None) -> int | None:
        target = self._norm_depth_key(depth_m)
        if target is None:
            return None
        for idx, d_raw in enumerate(getattr(t, "depth", []) or []):
            d = self._norm_depth_key(_parse_depth_float(str(d_raw)))
            if d is None:
                continue
            if d == target:
                return idx
        return None

    def _mark_key(self, tid: int, depth_m: float | int | str | None, field: str) -> tuple[int, float, str] | None:
        d_key = self._norm_depth_key(depth_m)
        f_key = str(field or "").strip()
        if d_key is None or not f_key:
            return None
        return (int(tid), d_key, f_key)

    def _build_marks_index_from_ops(self) -> dict[tuple[int, float, str], dict]:
        marks: dict[tuple[int, float, str], dict] = {}
        tests_by_tid = {int(getattr(t, "tid", 0) or 0): t for t in (self.tests or [])}
        ops = list(getattr(self, "project_ops", []) or [])
        self._marks_ops_count = len(ops)

        def _put_mark(*, tid: int, t: TestData | None, field: str, depth_m: float | int | str | None, row: int | None, op_mark: dict):
            row_i = int(row) if isinstance(row, int) else -1
            d_key = self._norm_depth_key(depth_m)
            if d_key is None and t is not None and row_i >= 0:
                d_key = self._safe_depth_m(t, row_i)
            key = self._mark_key(tid, d_key, field)
            if key is None:
                return
            mark = dict(op_mark or {})
            if not mark.get("color"):
                mark["color"] = "purple"
            if not mark.get("reason"):
                mark["reason"] = "manual_edit"
            marks[key] = mark

        for op in ops:
            op_type = str((op or {}).get("opType") or "")
            payload = dict((op or {}).get("payload") or {})
            op_mark = dict((op or {}).get("mark") or {})
            if op_type == "cell_set":
                try:
                    tid = int(payload.get("testId"))
                except Exception:
                    continue
                t = tests_by_tid.get(tid)
                row_i = None
                try:
                    row_i = int(payload.get("row"))
                except Exception:
                    row_i = None
                if t is not None and (row_i is not None) and row_i < 0:
                    row_i = self._row_by_depth_m(t, payload.get("depthM"))
                _put_mark(tid=tid, t=t, field=str(payload.get("colKey") or payload.get("field") or ""), depth_m=payload.get("depthM"), row=row_i, op_mark=op_mark)
            elif op_type == "algo_fix_applied":
                for ch in list(payload.get("changes") or []):
                    one = dict(ch or {})
                    try:
                        tid = int(one.get("testId"))
                    except Exception:
                        continue
                    t = tests_by_tid.get(tid)
                    row_i = None
                    try:
                        row_i = int(one.get("row"))
                    except Exception:
                        row_i = None
                    if t is not None and (row_i is not None) and row_i < 0:
                        row_i = self._row_by_depth_m(t, one.get("depthM"))
                    _put_mark(tid=tid, t=t, field=str(one.get("colKey") or one.get("field") or ""), depth_m=one.get("depthM"), row=row_i, op_mark=dict(one.get("mark") or op_mark or {}))
            elif op_type == "cells_marked":
                for cell in list(payload.get("cells") or []):
                    one = dict(cell or {})
                    try:
                        tid = int(one.get("testId"))
                    except Exception:
                        continue
                    t = tests_by_tid.get(tid)
                    row_i = None
                    try:
                        row_i = int(one.get("row"))
                    except Exception:
                        row_i = None
                    if t is not None and (row_i is not None) and row_i < 0:
                        row_i = self._row_by_depth_m(t, one.get("depthM"))
                    _put_mark(tid=tid, t=t, field=str(one.get("colKey") or one.get("field") or ""), depth_m=one.get("depthM"), row=row_i, op_mark=dict(one.get("mark") or op_mark or {}))

        self._marks_built_count = len(marks)
        return marks

    def _rebuild_marks_index(self) -> None:
        self._marks_index = self._build_marks_index_from_ops()
        self._marks_color_counts = {"green": 0, "purple": 0, "blue": 0, "orange": 0}
        try:
            tests_by_tid = {int(getattr(t, "tid", 0) or 0): t for t in (self.tests or [])}
            visible = 0
            for tid, depth_m, field in self._marks_index.keys():
                t = tests_by_tid.get(int(tid))
                if t is None or field not in {"qc", "fs", "incl", "depth"}:
                    continue
                row = self._row_by_depth_m(t, depth_m)
                if row is None:
                    continue
                visible += 1
                clr = str((self._marks_index.get((tid, depth_m, field)) or {}).get("color") or "").strip().lower()
                if clr in self._marks_color_counts:
                    self._marks_color_counts[clr] += 1
            self._marks_applied_count = visible
        except Exception:
            self._marks_applied_count = len(self._marks_index)
        print(
            "[marks] "
            f"ops={self._marks_ops_count}, marks_total={self._marks_built_count}, "
            f"marks_green={self._marks_color_counts.get('green', 0)}, "
            f"marks_purple={self._marks_color_counts.get('purple', 0)}, "
            f"marks_blue={self._marks_color_counts.get('blue', 0)}, "
            f"marks_orange={self._marks_color_counts.get('orange', 0)}, "
            f"подсвечено_marks={self._marks_applied_count}"
        )

    def _recompute_statuses_after_data_load(self, *, preview_mode: bool = False) -> dict:
        """Force full status recomputation and redraw after loading/restoring data."""
        info = self._scan_by_algorithm(preview_mode=preview_mode)
        self._algo_preview_mode = bool(preview_mode)
        self._redraw()
        self._update_footer_realtime()
        return info or {}

    def _project_open_diagnostics(self, status_info: dict | None = None) -> str:
        status_info = status_info or {}
        try:
            report = self._diagnostics_report()
        except Exception:
            report = None
        miss = int(getattr(report, "cells_missing", 0) or 0)
        invalid = int(getattr(report, "tests_invalid", 0) or 0)
        return (
            f"Проект открыт: ops={self._marks_ops_count}, marks_total={self._marks_built_count}, "
            f"marks_green={self._marks_color_counts.get('green', 0)}, "
            f"marks_purple={self._marks_color_counts.get('purple', 0)}, "
            f"marks_blue={self._marks_color_counts.get('blue', 0)}, "
            f"marks_orange={self._marks_color_counts.get('orange', 0)}, "
            f"подсвечено_marks={self._marks_applied_count}, "
            f"статус_жёлтый={miss}, некорректных_опытов={invalid}"
        )

    def save_project_file(self, save_as: bool = False):
        out = self.project_path
        if save_as or not out:
            out = filedialog.asksaveasfilename(
                title="Сохранить проект",
                defaultextension=".zproj",
                filetypes=[("ZondEditor project", "*.zproj")],
            )
            if not out:
                return False
            out = Path(out)
        payload = self._build_project_payload()
        src_bytes = getattr(self, "original_bytes", None)
        save_project(Path(out), project=payload, source_bytes=src_bytes)
        self.project_path = Path(out)
        self._dirty = False
        self._update_window_title()
        return True

    def open_project_file(self):
        if not self._confirm_discard_if_dirty():
            return
        path = filedialog.askopenfilename(
            title="Открыть проект",
            filetypes=[("ZondEditor project", "*.zproj")],
        )
        if not path:
            return
        project, source_bytes = load_project(Path(path))
        self.project_path = Path(path)
        self.object_name = project.object_name or ""
        self.object_code = self.object_name
        self.project_name = str(getattr(project, "project_name", "") or self.object_name or "Новый проект")
        self.project_type = str(getattr(project, "project_type", "") or "type2_electric")
        self.project_mode_params = dict((project.settings.extras or {}).get("project_mode_params") or {})
        self.project_ops = list(project.ops or [])
        self.original_bytes = source_bytes
        self.geo_path = Path(project.source.filename) if (project.source and project.source.filename) else None
        self.loaded_path = str(self.geo_path) if self.geo_path else str(path)
        src_kind = str((project.source.kind if project.source else "") or "").strip().upper()
        self.is_gxl = (src_kind == "GXL")
        src_ext = str((project.source.ext if project.source else "") or "").strip().lower()
        had_geo_kind_in_state = "geo_kind" in dict(getattr(project, "state", {}) or {})
        normalized_state = self._normalized_project_state(project)
        self._restore(normalized_state)
        if src_ext in {"geo", "ge0"} and not had_geo_kind_in_state:
            self.geo_kind = "K2"
            if any(getattr(t, "incl", None) not in (None, []) for t in (getattr(self, "tests", []) or [])):
                self.geo_kind = "K4"
        if not getattr(self, "_geo_template_blocks_info_full", None):
            self._geo_template_blocks_info_full = [
                t.block for t in (getattr(self, "tests", []) or []) if getattr(t, "block", None)
            ]
        self._geo_template_blocks_info = list(getattr(self, "_geo_template_blocks_info_full", []) or [])
        self._rebuild_marks_index()
        status_info = self._recompute_statuses_after_data_load(preview_mode=False)
        self.cpt_calc_settings = dict((project.settings.extras or {}).get("cpt_calc_settings") or self.cpt_calc_settings or {"method": METHOD_SP446, "alluvial_sands": True, "groundwater_level": None})
        _base_cts = CalculationTabState().__dict__
        _raw_cts = dict((project.settings.extras or {}).get("calc_tab_state") or {})
        _safe_cts = {k: v for k, v in _raw_cts.items() if k in _base_cts}
        self.calc_tab_state = CalculationTabState(**{**_base_cts, **_safe_cts})
        self._dirty = False
        self._apply_visual_mode_for_project_type()
        if getattr(self, "ribbon_view", None):
            self.ribbon_view.set_object_name(self.object_name)
            self.ribbon_view.set_project_type(self.project_type, mode_params=dict(self.project_mode_params or {}))
            self.ribbon_view.set_common_params(self._current_common_params(), geo_kind=str(getattr(self, "geo_kind", "K2")))
        self.status.config(text=self._project_open_diagnostics(status_info))
        self._update_window_title()

    def new_project_file(self):
        if not self._confirm_discard_if_dirty():
            return

        dlg = tk.Toplevel(self)
        dlg.title("Создать проект")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)

        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Выберите тип проекта:").pack(anchor="w", pady=(0, 8))

        result = {"project_type": ""}

        def _cancel(_evt=None):
            dlg.destroy()

        def _choose(project_type: str):
            result["project_type"] = str(project_type or "")
            dlg.destroy()

        ttk.Button(frm, text="Тип 1 — механический", command=lambda: _choose("type1_mech"), width=34).pack(fill="x", pady=2)
        ttk.Button(frm, text="Тип 2 — электрический", command=lambda: _choose("type2_electric"), width=34).pack(fill="x", pady=2)
        ttk.Button(frm, text="Прямой ввод — qc/fs", command=lambda: _choose("direct_qcfs"), width=34).pack(fill="x", pady=2)

        dlg.bind("<Escape>", _cancel)

        try:
            self._center_child(dlg)
        except Exception:
            pass

        self.wait_window(dlg)

        if not result.get("project_type"):
            return

        selected_type = str(result.get("project_type") or "type1_mech")
        selected_name = "Новый проект"

        self.tests = []
        self.flags = {}
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.project_ops = []
        self._marks_index = {}
        self._marks_ops_count = 0
        self._marks_built_count = 0
        self._marks_applied_count = 0
        self._marks_color_counts: dict[str, int] = {"green": 0, "purple": 0, "blue": 0, "orange": 0}
        self.project_path = None
        self.project_name = selected_name
        self.project_type = selected_type
        self.project_mode_params = {"mode_step_depth": ("0.20" if selected_type == "type1_mech" else ("0.10" if selected_type == "direct_qcfs" else "0.05"))}
        self.object_name = selected_name
        self.object_code = selected_name
        self.geo_path = None
        self.original_bytes = None
        self.depth_start = 0.0
        self.step_m = 0.2 if selected_type == "type1_mech" else (0.1 if selected_type == "direct_qcfs" else 0.05)
        self.depth0_by_tid = {}
        self.step_by_tid = {}
        self.gwl_by_tid = {}
        self.geo_kind = "K2"
        if selected_type in {"type1_mech", "type2_electric", "direct_qcfs"}:
            self._create_initial_mechanical_column()
        if selected_type == "type2_electric":
            self.show_graphs = False
            self.show_geology_column = False
            self.show_layer_colors = False
            self.show_layer_hatching = False
            self.show_inclinometer = False

        try:
            self.file_var.set("(шаблон проекта)")
        except Exception:
            pass

        self._dirty = True
        self._apply_visual_mode_for_project_type()
        self._recompute_statuses_after_data_load(preview_mode=False)
        if getattr(self, "ribbon_view", None):
            self.ribbon_view.set_object_name(self.object_name)
            self.ribbon_view.set_project_type(self.project_type, mode_params=dict(self.project_mode_params or {}))
            self.ribbon_view.set_common_params(self._current_common_params(), geo_kind=str(getattr(self, "geo_kind", "K2")))
            self.ribbon_view.select_tab("Параметры")
        self.status.config(text=f"Создан новый проект: {self.project_name}")
        self._update_window_title()

    def _create_initial_mechanical_column(self):
        # Для стартового механического шаблона фиксируем шаг 0.20 м.
        # Для type2_electric/direct_qcfs берём шаг из параметров режима (по умолчанию 0.05/0.10).
        # Это гарантирует полный предзаполненный столбец 0.00..5.00.
        if str(getattr(self, "project_type", "") or "") in {"type2_electric", "direct_qcfs"}:
            try:
                fallback = "0.10" if str(getattr(self, "project_type", "") or "") == "direct_qcfs" else "0.05"
                step_m = float(str(getattr(self, "project_mode_params", {}).get("mode_step_depth", fallback) or fallback).replace(",", "."))
            except Exception:
                step_m = 0.1 if str(getattr(self, "project_type", "") or "") == "direct_qcfs" else 0.05
        else:
            step_m = 0.2
        self.step_m = step_m
        self.project_mode_params["mode_step_depth"] = f"{step_m:.2f}"
        dt_text = _dt.datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        rows_count = max(1, int(round(5.0 / float(step_m)))) + 1
        depth_vals = [f"{(i * step_m):.2f}" for i in range(rows_count)]  # 0.00 .. 5.00
        n = len(depth_vals)
        self.tests = [TestData(tid=1, dt=dt_text, depth=depth_vals, qc=[""] * n, fs=[""] * n, incl=None, orig_id=None, block=None)]
        self.flags = {1: TestFlags(False, set(), set(), set(), set())}
        self.depth0_by_tid = {1: 0.0}
        self.step_by_tid = {1: float(step_m)}

    def _on_object_name_changed(self, value: str):
        before = self.object_name
        value = (value or "").strip()
        if before == value:
            return
        self.object_name = value
        self.object_code = value
        self.project_ops.append(op_meta_change(object_name_before=before, object_name_after=value))
        self._dirty = True
        self._update_window_title()

    def _on_close(self):
        if not self._confirm_discard_if_dirty():
            return
        self.destroy()

    def export_bundle(self) -> bool:
        if not self.tests:
            messagebox.showwarning("Нет данных", "Сначала открой файл.")
            return False
        selection = self._collect_export_tests()
        tests_exp = list(selection.tests)
        if not tests_exp:
            messagebox.showwarning('Нет данных', 'Нет зондирований для экспорта (все исключены).')
            return False

        obj = self._ensure_object_code()
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{obj}_{ts}.zip"

        out_zip = filedialog.asksaveasfilename(
            title="Сохранить архивом",
            defaultextension=".zip",
            initialfile=default_name,
            filetypes=[("ZIP", "*.zip")],
        )
        if not out_zip:
            return False

        include = {"project": True, "geo": True, "gxl": False, "excel": True, "credo": False}
        dlg = tk.Toplevel(self)
        dlg.title("Состав архива")
        dlg.transient(self)
        dlg.grab_set()
        vars_map = {k: tk.BooleanVar(master=self, value=v) for k, v in include.items()}
        labels = {
            "project": "Проект (*.zproj)",
            "geo": "GEO",
            "gxl": "GXL",
            "excel": "Excel",
            "credo": "CREDO/ZIP",
        }
        frm = ttk.Frame(dlg, padding=10)
        frm.pack(fill="both", expand=True)
        for k in ("project", "geo", "gxl", "excel", "credo"):
            ttk.Checkbutton(frm, text=labels[k], variable=vars_map[k]).pack(anchor="w")
        result = {"ok": False}
        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="OK", command=lambda: (result.update(ok=True), dlg.destroy())).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text="Отмена", command=dlg.destroy).pack(side="right")
        self.wait_window(dlg)
        if not result["ok"]:
            return False
        include = {k: bool(v.get()) for k, v in vars_map.items()}

        try:
            with tempfile.TemporaryDirectory() as td:
                td_path = Path(td)

                meta_path = td_path / "meta.json"
                meta_payload = {
                    "objectName": self.object_name or self.object_code or "",
                    "createdAt": _dt.datetime.now().isoformat(),
                    "sourceType": ("gxl" if getattr(self, "is_gxl", False) else "geo"),
                    "geoKind": getattr(self, "geo_kind", ""),
                    "step": getattr(self, "step_m", None),
                    "recalc": {
                        "scale": str(self._current_common_params().get("controller_scale_div", "") or ""),
                        "fcone": str(self._current_common_params().get("cone_kn", "") or ""),
                        "fsleeve": str(self._current_common_params().get("sleeve_kn", "") or ""),
                        "acon": str(self._current_common_params().get("cone_area_cm2", "") or ""),
                        "asleeve": str(self._current_common_params().get("sleeve_area_cm2", "") or ""),
                    },
                    "tests": [
                        {"tid": int(getattr(t, "tid", 0) or 0), "locked": bool(getattr(t, "locked", False))}
                        for t in (self.tests or [])
                    ],
                }
                meta_path.write_text(json.dumps(meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")

                gxl_path = td_path / f"{obj}.gxl"
                orig_tests = getattr(self, 'tests', None)
                try:
                    self.tests = list(tests_exp)
                    self.export_gxl_generated(str(gxl_path))
                finally:
                    if orig_tests is not None:
                        self.tests = orig_tests


                geo_path = None
                geo_err = None
                # В архив кладём GEO/GE0 ТОЛЬКО если исходно был открыт GEO/GE0 (есть original_bytes и путь).
                if (not getattr(self, "is_gxl", False)) and getattr(self, "original_bytes", None) and getattr(self, "geo_path", None):
                    try:
                        geo_out_name = bundle_geo_filename(
                            source_geo_path=getattr(self, "geo_path", None),
                            fallback_name=obj,
                        )
                        geo_path = td_path / geo_out_name
                        tests_list = tests_exp

                        # --- GEO export safety: use ONLY tests_list (respect delete/copy/export checkbox) ---
                        try:
                            _exp_ids = [int(getattr(tt, 'tid', 0) or 0) for tt in tests_list]
                            _exp_ids = [x for x in _exp_ids if x > 0]
                            _exp_set = set(_exp_ids)
                            tests_list = [pp for pp in tests_list if int(getattr(pp, 'tid', 0) or 0) in _exp_set]
                            _order = {tid: i for i, tid in enumerate(_exp_ids)}
                            tests_list.sort(key=lambda pp: _order.get(int(getattr(pp, 'tid', 0) or 0), 10**9))
                        except Exception:
                            pass
                        blocks_info = list((getattr(self, '_geo_template_blocks_info_full', None) or self._geo_template_blocks_info) or [])
                        if not blocks_info:
                            raise RuntimeError('Не удалось найти блоки опытов в исходном файле.')

                        export_bundle_geo(
                            geo_path,
                            tests=tests_list,
                            source_bytes=self.original_bytes,
                            blocks_info=blocks_info,
                        )

                        # DEBUG: сверка количества/номеров блоков в собранном GEO (ловим "воскресший первый опыт")
                        try:
                            geo_bytes = geo_path.read_bytes()
                            _pos = [m.start() for m in re.finditer(b'\xFF\xFF.\x1E\x0A', geo_bytes)]
                            _ids = [geo_bytes[p+2] for p in _pos]
                            _exp = [int(getattr(tt, 'tid', 0) or 0) for tt in tests_list]
                            dbg_path = td_path / f"{obj}_geo_debug.txt"
                            dbg_path.write_text(
                                "expected_ids=" + ",".join(map(str,_exp)) + "\n" +
                                "actual_ids=" + ",".join(map(str,_ids)) + "\n" +
                                f"expected_n={len(_exp)} actual_n={len(_ids)}\n" +
                                "tests_current_ids=" + ",".join(map(str, [int(getattr(tt,'tid',0) or 0) for tt in (self.tests or [])])) + "\n" +
                                "export_enabled_ids=" + ",".join(map(str, [int(getattr(tt,'tid',0) or 0) for tt in tests_list])) + "\n" +
                                "prepared_ids=" + ",".join(map(str, [int(getattr(tt,'tid',0) or 0) for tt in (tests_list or [])])) + "\n" +
                                f"blocks_info_n={len(blocks_info)} using_full_template={'1' if bool(getattr(self,'_geo_template_blocks_info_full',[])) else '0'}\n",
                                encoding="utf-8"
                            )
                        except Exception:
                            dbg_path = None

                    except Exception as _e:
                        geo_err = f"{type(_e).__name__}: {_e}"
                        geo_tb = traceback.format_exc()
                        geo_path = None
                # Если GEO не собрался — сохраняем лог, чтобы понять причину.
                geo_log_path = None
                if geo_err:
                    geo_log_path = td_path / f"{obj}_geo_export_error.txt"
                    try:
                        geo_log_path.write_text(geo_err + "\n\n" + geo_tb, encoding="utf-8")
                    except Exception:
                        pass

                xlsx_path = td_path / f"{obj}.xlsx"
                if include.get("excel"):
                    self._export_excel_silent(xlsx_path)

                credo_zip_path = td_path / f"{obj}_CREDO.zip"
                if include.get("credo"):
                    self._export_credo_silent(credo_zip_path)

                project_path = td_path / "project.zproj"
                if include.get("project"):
                    project_payload = self._build_project_payload()
                    save_project(project_path, project=project_payload, source_bytes=getattr(self, "original_bytes", None))

                with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
                    z.write(meta_path, "meta.json")
                    if include.get("gxl"):
                        z.write(gxl_path, gxl_path.name)
                    if include.get("geo") and geo_path and geo_path.exists():
                        z.write(geo_path, geo_path.name)
                    if geo_log_path and geo_log_path.exists():
                        z.write(geo_log_path, geo_log_path.name)

                    if 'dbg_path' in locals() and dbg_path and Path(dbg_path).exists():
                        z.write(dbg_path, Path(dbg_path).name)

                    if include.get("excel") and xlsx_path.exists():
                        z.write(xlsx_path, xlsx_path.name)
                    if include.get("credo") and credo_zip_path.exists():
                        z.write(credo_zip_path, credo_zip_path.name)
                    if include.get("project") and project_path.exists():
                        z.write(project_path, project_path.name)

            # Excel не любит открывать .xlsx прямо ИЗ zip (появляется путь вида ...zip.8a3\file.xlsx и файл недоступен).
            # Поэтому дополнительно сохраняем копию XLSX рядом с архивом, чтобы открывалась без проблем.
            try:
                side_xlsx = Path(out_zip).with_suffix('.xlsx')
                if include.get("excel") and xlsx_path.exists():
                    shutil.copy2(xlsx_path, side_xlsx)
            except Exception:
                pass


            try:
                _log_event(self.usage_logger, "EXPORT", object=self._ensure_object_code(), zip=str(out_zip))
            except Exception:
                pass

            self.status.config(text=f"Экспорт-архив сохранён: {Path(out_zip).name}")
            if geo_err:
                messagebox.showwarning(
                    "GEO не добавлен в архив",
                    "Не удалось собрать GEO из шаблона. В архив добавлен лог: "
                    f"{obj}_geo_export_error.txt",
                )
            self._dirty = False
            return True
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))
            return False

    def _write_meta_txt(self, path: Path):
        cp = self._current_common_params()
        scale = str(cp.get("controller_scale_div", "") or "").strip()
        fcone = str(cp.get("cone_kn", "") or "").strip()
        fsleeve = str(cp.get("sleeve_kn", "") or "").strip()
        step = getattr(self, "step_m", None)
        depth0 = getattr(self, "depth_start", None)
        src = getattr(self, "loaded_path", "")
        lines = [
            f"object={self._ensure_object_code()}",
            f"source={src}",
            f"scale={scale}",
            f"fcone_kN={fcone}",
            f"fsleeve_kN={fsleeve}",
            f"depth_start_m={depth0 if depth0 is not None else ''}",
            f"step_m={step if step is not None else ''}",
            f"tests={len(self._collect_export_tests().tests)}",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")

    def _export_excel_silent(self, out_path: Path):
        """Тихий экспорт в Excel без диалогов (для экспорта-архива)."""
        if export_excel_file is None:
            raise RuntimeError("openpyxl не установлен: экспорт Excel недоступен")
        export_excel_file(
            self.tests,
            geo_kind=getattr(self, "geo_kind", "K2"),
            out_path=out_path,
            cal=self._current_calibration(),
            include_only_export_on=True,
        )

    def _export_credo_silent(self, out_zip_path: Path):
        """Тихий экспорт ZIP для CREDO (две CSV на опыт) без диалогов (для экспорта-архива)."""
        export_credo_zip(
            self.tests,
            out_zip_path=out_zip_path,
            geo_kind=str(getattr(self, "geo_kind", "K2") or "K2"),
            cal=self._current_calibration(),
            include_only_export_on=True,
        )

    def save_file(self):
        """Сохранение через диалог "Сохранить как..." без silent overwrite."""
        try:
            if not getattr(self, 'tests', None):
                messagebox.showwarning("Внимание", "Нет данных для сохранения.")
                return

            from tkinter import filedialog
            import os

            base = os.path.basename(str(getattr(self, "geo_path", "data.geo") or "data.geo"))
            base_noext = os.path.splitext(base)[0]
            out_file = filedialog.asksaveasfilename(
                title="Сохранить как",
                defaultextension=".geo",
                initialfile=base_noext + ".geo",
                filetypes=[("GEO/GE0", "*.geo *.ge0 *.GEO *.GE0"), ("GXL", "*.gxl *.GXL"), ("Все файлы", "*.*")],
            )
            if not out_file:
                return

            ext = os.path.splitext(out_file)[1].lower()
            if ext == ".gxl":
                self._save_geo_path_override = out_file
                try:
                    return self.export_gxl_as()
                finally:
                    self._save_geo_path_override = None

            self._save_geo_path_override = out_file
            try:
                return self.export_geo_as()
            finally:
                self._save_geo_path_override = None
        except Exception:
            import traceback
            messagebox.showerror("Ошибка", traceback.format_exc())

    def export_gxl_as(self):
        """Экспорт GXL только через "Сохранить как..."."""
        try:
            if not getattr(self, 'tests', None):
                messagebox.showwarning("Внимание", "Нет данных для экспорта GXL.")
                return
            if not self._validate_export_rows():
                return

            out_file = getattr(self, '_save_geo_path_override', None)
            if not out_file:
                out_file = filedialog.asksaveasfilename(
                    title="Сохранить GXL как...",
                    defaultextension=".gxl",
                    initialfile="export.gxl",
                    filetypes=[('GXL', '*.gxl *.GXL'), ('Все файлы', '*.*')],
                )
            if not out_file:
                return

            self.export_gxl_generated(out_file)
            try:
                self._set_status(f"GXL сохранён: {out_file}")
            except Exception:
                pass
        except Exception:
            import traceback
            messagebox.showerror("Ошибка сохранения GXL", traceback.format_exc())

    def save_gxl(self):
        """Alias для совместимости UI: экспорт GXL всегда через "Сохранить как..."."""
        return self.export_gxl_as()

    def export_geo_as(self):
        """Экспорт GEO/GE0 только через "Сохранить как..." и без перезаписи источника."""
        try:
            if not getattr(self, 'tests', None):
                messagebox.showwarning("Экспорт GEO", "Нет данных зондирования в памяти.")
                return
            if not getattr(self, 'original_bytes', None):
                messagebox.showwarning("Экспорт GEO", "Нет исходного шаблона GEO в проекте (source bytes отсутствуют).")
                return
            if not self._validate_export_rows():
                return

            import os
            base = os.path.basename(getattr(self, 'loaded_path', '') or 'export.GEO')
            out_file = getattr(self, '_save_geo_path_override', None)
            if not out_file:
                out_file = filedialog.asksaveasfilename(
                    title="Сохранить GEO/GE0 как...",
                    defaultextension=os.path.splitext(base)[1] or '.GEO',
                    initialfile=base,
                    filetypes=[('GEO/GE0', '*.GEO *.GE0'), ('Все файлы', '*.*')],
                )
            if not out_file:
                return

            selection = self._collect_export_tests()
            tests_exp = list(selection.tests)
            if not tests_exp:
                messagebox.showwarning('Нет данных', 'Нет зондирований для экспорта (все исключены).')
                return

            tests_list = [self._normalize_test_lengths(t) for t in tests_exp]
            prepared = prepare_geo_tests(tests_list)

            blocks_info = list((getattr(self, '_geo_template_blocks_info_full', None) or self._geo_template_blocks_info) or [])
            if not blocks_info:
                blocks_info = [t.block for t in (getattr(self, 'tests', []) or []) if getattr(t, 'block', None)]
            if not blocks_info:
                messagebox.showerror("Экспорт GEO", "Не найдены блоки опытов для шаблона GEO (block metadata отсутствуют).")
                return
            # --- GEO EXPORT DISPATCH (split K2/K4, independent) ---
            if getattr(self, "geo_kind", "K2") == "K4":
                from src.zondeditor.io.geo_writer_k4 import save_k4_geo_as
                save_k4_geo_as(
                    out_file,
                    prepared,
                    source_bytes=self.original_bytes,
                )
            else:
                from src.zondeditor.io.geo_writer_k2 import save_k2_geo_as
                save_k2_geo_as(
                    out_file,
                    prepared,
                    source_bytes=self.original_bytes,
                )
            try:
                self._set_status(f"Сохранено: {out_file} | опытов: {len(tests_list)}")
            except Exception:
                pass
        except Exception:
            import traceback
            messagebox.showerror("Ошибка сохранения GEO", traceback.format_exc())

    def save_geo(self):
        """Alias для совместимости UI: экспорт GEO всегда через "Сохранить как..."."""
        return self.export_geo_as()

def export_gxl_generated(self, out_file: str):
    """Сформировать GXL максимально идентичный экспорту GeoExplorer.

    См. описание внутри функции.
    """
    try:
        import math
        if not getattr(self, 'tests', None):
            from tkinter import messagebox
            messagebox.showwarning('Внимание', 'Нет данных для экспорта в GXL.')
            return

        def xml_escape(t: str) -> str:
            t = '' if t is None else str(t)
            return (t.replace('&', '&amp;')
                     .replace('<', '&lt;')
                     .replace('>', '&gt;')
                     .replace('"', '&quot;')
                     .replace("'", '&apos;'))

        def fmt_comma_num(x, ndp=2):
            try:
                x = float(x)
            except Exception:
                x = 0.0
            s = f"{x:.{ndp}f}".rstrip('0').rstrip('.')
            if s == '':
                s = '0'
            return s.replace('.', ',')

        def fmt_date(dt_s: str) -> str:
            import re
            s = (dt_s or '').strip()
            if not s:
                return ''
            p = s.split()[0]
            if re.match(r'^\d{2}\.\d{2}\.\d{4}$', p):
                return p
            if re.match(r'^\d{4}-\d{2}-\d{2}$', p):
                y, mo, d = p.split('-')
                return f"{d}.{mo}.{y}"
            return p

        # Параметры из UI (если есть)
        cp = self._current_common_params()
        scale = str(cp.get('controller_scale_div', '250') or '250')
        fcone = str(cp.get('cone_kn', '30') or '30')
        fsleeve = str(cp.get('sleeve_kn', '10') or '10')

        # Числовая шкала для отсечения значений (GeoExplorer часто не принимает значения выше шкалы)
        try:
            _scale_int = int(str(scale).strip().replace(',', '.').split('.')[0])
        except Exception:
            _scale_int = 250
        if _scale_int <= 0:
            _scale_int = 250

        # object поля: фиксированные как просил
        obj_id = '60'
        obj_name = 'name'
        privazka = 'По плану...'

        # шаг из модельного состояния
        try:
            step_m_default = float(getattr(self, 'step_m', 0.10) or 0.10)
            if step_m_default <= 0:
                step_m_default = 0.10
        except Exception:
            step_m_default = 0.10

        # Экспортируем только тесты из единого контура selection
        tests = list(self._collect_export_tests().tests)
        try:
            tests = sorted(tests, key=lambda t: (getattr(t, 'dt', '') or ''))
        except Exception:
            pass

        def parse_d(x):
            try:
                if x is None:
                    return None
                s = str(x).strip().replace(',', '.')
                if s == '':
                    return None
                return float(s)
            except Exception:
                return None

        # max depth
        max_depth = 0.0
        for t in tests:
            ds = [parse_d(v) for v in (getattr(t, 'depth', []) or [])]
            ds = [d for d in ds if d is not None]
            if ds:
                max_depth = max(max_depth, max(ds))

        step_m = step_m_default
        for t in tests:
            ds = [parse_d(v) for v in (getattr(t, 'depth', []) or [])]
            ds = [d for d in ds if d is not None]
            if len(ds) >= 2:
                st = abs(ds[1] - ds[0])
                if 0.045 <= st <= 0.055:
                    step_m = 0.05
                    break
                if 0.095 <= st <= 0.105:
                    step_m = 0.10
                    break

        n_rows = int(math.floor(max_depth / step_m + 1e-9)) + 1
        grid = [round(i * step_m, 2) for i in range(max(1, n_rows))]

        footer = (
            '    <iges></iges>\r\n'
            '    <rdirectory>\r\n'
            '      <set>\r\n'
            '        <name>Уральский</name>\r\n'
            '        <psr>0,2</psr>\r\n'
            '        <pml>0,5</pml>\r\n'
            '        <ppy>0,9</ppy>\r\n'
            '        <supes>1,5</supes>\r\n'
            '        <sugl>5</sugl>\r\n'
            '        <glina>5</glina>\r\n'
            '      </set>\r\n'
            '      <set>\r\n'
            '        <name>Тюменский</name>\r\n'
            '        <psr>0,2</psr>\r\n'
            '        <pml>0,5</pml>\r\n'
            '        <ppy>0,9</ppy>\r\n'
            '        <supes>1,5</supes>\r\n'
            '        <sugl>2,8</sugl>\r\n'
            '        <glina>2,8</glina>\r\n'
            '      </set>\r\n'
            '      <set>\r\n'
            '        <name>Уральский1</name>\r\n'
            '        <psr>0,2</psr>\r\n'
            '        <pml>0,5</pml>\r\n'
            '        <ppy>0,9</ppy>\r\n'
            '        <supes>4</supes>\r\n'
            '        <sugl>5</sugl>\r\n'
            '        <glina>5</glina>\r\n'
            '      </set>\r\n'
            '    </rdirectory>\r\n'
        )

        out = []
        out.append('<?xml version="1.0"?>\r\n')
        out.append('<exportfile>\r\n')
        out.append('  <verfile>3</verfile>\r\n')
        out.append('  <verprogram>GeoExplorer v3.0.14.523</verprogram>\r\n')
        out.append('  <object>\r\n')
        out.append(f'    <id>{xml_escape(obj_id)}</id>\r\n')
        out.append(f'    <name>{xml_escape(obj_name)}</name>\r\n')
        out.append('    <h_abs_plan>0</h_abs_plan>\r\n')
        out.append('    <FullName></FullName>\r\n')
        out.append('    <NumArch></NumArch>\r\n')
        out.append('    <Cashman></Cashman>\r\n')
        out.append('    <Appendix></Appendix>\r\n')

        def make_dat(t):
            ds = [parse_d(v) for v in (getattr(t, 'depth', []) or [])]
            qc = getattr(t, 'qc', []) or []
            fs = getattr(t, 'fs', []) or []

            ds2 = [d for d in ds if d is not None]
            if not ds2:
                return ["0;0;0;0;0;"]

            # deepbegin/step: как в GeoExplorer — dat начинается с deepbegin
            deepbegin = min(ds2)
            # шаг пробуем взять из первых двух валидных глубин
            step = step_m
            if len(ds2) >= 2:
                st = abs(ds2[1] - ds2[0])
                if 0.045 <= st <= 0.055:
                    step = 0.05
                elif 0.095 <= st <= 0.105:
                    step = 0.10

            endd = max(ds2)
            n = int(round((endd - deepbegin) / step)) + 1
            if n < 1:
                n = 1

            grid_local = [round(deepbegin + i * step, 2) for i in range(n)]

            m = {}
            for i, d in enumerate(ds):
                if d is None:
                    continue
                key = round(d, 2)
                try:
                    q = int(str(qc[i]).strip() or '0') if i < len(qc) else 0
                except Exception:
                    q = 0
                try:
                    f = int(str(fs[i]).strip() or '0') if i < len(fs) else 0
                except Exception:
                    f = 0

                # отсечь по шкале и запретить отрицательные
                try:
                    q = int(q)
                except Exception:
                    q = 0
                try:
                    f = int(f)
                except Exception:
                    f = 0
                if q < 0:
                    q = 0
                if f < 0:
                    f = 0
                if q > _scale_int:
                    q = _scale_int
                if f > _scale_int:
                    f = _scale_int

                m[key] = (q, f)

            # GeoExplorer: qc;fs;0;0;0; (с завершающей ;)
            return [f"{m.get(d,(0,0))[0]};{m.get(d,(0,0))[1]};0;0;0;" for d in grid_local]

        for idx, t in enumerate(tests, start=1):
            numtest = getattr(t, 'tid', idx)
            dt_s = fmt_date(getattr(t, 'dt', '') or '')
            out.append('    <test>\r\n')
            out.append(f'      <numtest>{numtest}</numtest>\r\n')
            out.append('      <woker>Katko E</woker>\r\n')
            out.append(f'      <privazka>{xml_escape(privazka)}</privazka>\r\n')
            out.append(f'      <date>{xml_escape(dt_s)}</date>\r\n' if dt_s else '      <date></date>\r\n')
            out.append('      <sechsvai>0,3</sechsvai>\r\n')
            out.append(f'      <scaleostria>{xml_escape(fcone)}</scaleostria>\r\n')
            out.append(f'      <scalemufta>{xml_escape(fsleeve)}</scalemufta>\r\n')
            deepbegin_val = 0.0
            try:
                ds2 = [parse_d(v) for v in (getattr(t, 'depth', []) or [])]
                ds2 = [d for d in ds2 if d is not None]
                if ds2:
                    deepbegin_val = min(ds2)
            except Exception:
                deepbegin_val = 0.0
            out.append(f"      <deepbegin>{fmt_comma_num(deepbegin_val, 1)}</deepbegin>\r\n")
            step_for_test = step_m
            try:
                ds2 = [parse_d(v) for v in (getattr(t, 'depth', []) or [])]
                ds2 = [d for d in ds2 if d is not None]
                if len(ds2) >= 2:
                    st = abs(ds2[1] - ds2[0])
                    if 0.045 <= st <= 0.055:
                        step_for_test = 0.05
                    elif 0.095 <= st <= 0.105:
                        step_for_test = 0.10
            except Exception:
                pass
            out.append(f"      <stepzond>{fmt_comma_num(step_for_test, 2)}</stepzond>\r\n")
            out.append('      <sands>False</sands>\r\n')
            out.append('      <h_abs>0</h_abs>\r\n')
            out.append(f'      <scale>{xml_escape(scale)}</scale>\r\n')
            out.append('      <controllertype>1</controllertype>\r\n')
            out.append('      <id_zond>10</id_zond>\r\n')

            dat_lines = make_dat(t)
            if dat_lines:
                out.append(f'      <dat>{dat_lines[0]}\r\n')
                for ln in dat_lines[1:]:
                    out.append(f'{ln}\r\n')
                out.append('      </dat>\r\n')
            else:
                out.append('      <dat>0;0;0;0;0;\r\n')
                out.append('      </dat>\r\n')

            out.append('      <soils></soils>\r\n')
            out.append('      <rtable></rtable>\r\n')
            out.append('    </test>\r\n')

        out.append(footer)
        out.append('  </object>\r\n')
        out.append('</exportfile>\r\n')

        Path(out_file).write_bytes(''.join(out).encode('cp1251', errors='replace'))
        try:
            self._set_status(f"GXL сохранён: {out_file} | шкала={scale} Fкон={fcone} Fмуф={fsleeve}")
        except Exception:
            pass

    except Exception:
        import traceback
        from tkinter import messagebox
        messagebox.showerror('Ошибка', 'Не удалось сформировать GXL.\n\n' + traceback.format_exc())





# --- bind module-level helpers as methods (fix for indentation) ---
try:
    GeoCanvasEditor.save_gxl_generated = export_gxl_generated  # type: ignore[attr-defined]
except Exception:
    pass


if __name__ == "__main__":
    # CLI helpers for installer/admin
    if "--init-license" in sys.argv:
        try:
            _write_license_file()
            print("OK: license.dat created at", _license_path())
            raise SystemExit(0)
        except SystemExit:
            raise
        except Exception as e:
            print("ERROR: cannot create license.dat:", e)
            raise SystemExit(2)

    if "--open-logs" in sys.argv:
        _open_logs_folder()
        raise SystemExit(0)

    GeoCanvasEditor().mainloop()
