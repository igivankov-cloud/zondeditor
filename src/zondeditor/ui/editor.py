# src/zondeditor/ui/editor.py
# Auto-generated from tools/_ui_extract/GeoCanvasEditor.py (Step19)
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
from src.zondeditor.processing.calibration import calc_qc_fs, calc_qc_fs_from_del
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
from src.zondeditor.domain.layer_store import LayerStore
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
)

from src.zondeditor.ui.consts import *
from src.zondeditor.ui.helpers import _apply_win11_style, _setup_shared_logger, _validate_nonneg_float_key, _check_license_or_exit, _parse_depth_float, _try_parse_dt, _pick_icon_font, _validate_tid_key, _validate_depth_0_4_key, _format_date_ru, _format_time_ru, _canvas_view_bbox, _validate_hh_key, _validate_mm_key, _parse_cell_int, _max_zero_run, _noise_around, _interp_with_noise, _resource_path, _open_logs_folder
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

_rebuild_geo_from_template = build_k2_geo_from_template


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
        self.gwl_by_tid = {}  # tid -> {"enabled": bool, "value": float|None}

        self.undo_stack: list[dict] = []
        self.redo_stack: list[dict] = []

        self._dirty = False

        # Algorithm preview mode (autocheck on open): use pale colors, no data modification
        self._algo_preview_mode = False
        self.object_code = ""
        self.object_name = ""
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
        self.compact_1m = False
        self.display_sort_mode = "date"
        self.expanded_meters: set[int] = set()
        self._graph_redraw_after_id = None
        self._rebuild_redraw_after_id = None
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
        self._boundary_depth_editor = None
        self._editor_just_opened = False
        self._inline_edit_active = False
        self.ige_registry: dict[str, dict[str, object]] = {
            "ИГЭ-1": {"soil_type": SoilType.SANDY_LOAM.value, "calc_mode": calc_mode_for_soil(SoilType.SANDY_LOAM).value, "style": dict(SOIL_STYLE.get(SoilType.SANDY_LOAM, {}))},
            "ИГЭ-2": {"soil_type": SoilType.SAND.value, "calc_mode": calc_mode_for_soil(SoilType.SAND).value, "style": dict(SOIL_STYLE.get(SoilType.SAND, {}))},
        }
        self.layer_store = LayerStore()
        self._debug_layers_overlay = bool(os.environ.get("ZONDEDITOR_DEBUG_LAYERS") == "1")
        self.cpt_calc_settings = {"method": METHOD_SP446, "alluvial_sands": True, "groundwater_level": None}

        try:
            self.graph_w = int(self.winfo_fpixels("4c"))
        except Exception:
            self.graph_w = 150
        if self.graph_w <= 0:
            self.graph_w = 150

        self._editing = None  # (test_idx,row,field, entry)
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
                    "tail": sorted(list(getattr(fl, "force_tail_rows", set()))),
                }
        except Exception:
            flags_snap = {}
        return {
            "tests": tests_snap,
            "flags": flags_snap,
            "step_m": float(getattr(self, "step_m", 0.05) or 0.05),
            "depth0_by_tid": dict(getattr(self, "depth0_by_tid", {}) or {}),
            "gwl_by_tid": copy.deepcopy(dict(getattr(self, "gwl_by_tid", {}) or {})),
            "compact_1m": bool(getattr(self, "compact_1m", False)),
            "show_geology_column": bool(getattr(self, "show_geology_column", True)),
            "display_sort_mode": str(getattr(self, "display_sort_mode", "date") or "date"),
            "expanded_meters": sorted(int(x) for x in (getattr(self, "expanded_meters", set()) or set())),
            "layer_edit_mode": bool(getattr(self, "layer_edit_mode", False)),
            "project_ops": copy.deepcopy(list(getattr(self, "project_ops", []) or [])),
            "ige_registry": copy.deepcopy(dict(getattr(self, "ige_registry", {}) or {})),
            "cpt_calc_settings": copy.deepcopy(dict(getattr(self, "cpt_calc_settings", {}) or {})),
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

        # restore per-test start depths (tid -> h0)
        try:
            self.depth0_by_tid = dict((snap.get("depth0_by_tid") or {}))
        except Exception:
            self.depth0_by_tid = {}
        try:
            self.gwl_by_tid = copy.deepcopy(dict((snap.get("gwl_by_tid") or {})) or {})
        except Exception:
            self.gwl_by_tid = {}

        try:
            self.compact_1m = bool(snap.get("compact_1m", getattr(self, "compact_1m", False)))
        except Exception:
            self.compact_1m = bool(getattr(self, "compact_1m", False))
        try:
            self.show_geology_column = bool(snap.get("show_geology_column", getattr(self, "show_geology_column", True)))
        except Exception:
            self.show_geology_column = bool(getattr(self, "show_geology_column", True))
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
                self.ribbon_view.set_show_geology_column(bool(self.show_geology_column))
                self.ribbon_view.set_display_sort_mode(str(self.display_sort_mode))
                self.ribbon_view.set_layer_edit_mode(True)
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
                self.flags[t.tid] = TestFlags(False, set(), set(), set(), set(), set())
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
                fl.force_tail_rows = set(int(x) for x in s.get("tail", []))
            except Exception:
                pass

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

    def _expanded_meter_for_depth_cell(self, ti: int, display_row: int) -> int | None:
        if not bool(getattr(self, "compact_1m", False)):
            return None
        try:
            mp = (getattr(self, "_grid_row_maps", {}) or {}).get(ti, {}) or {}
            data_row = mp.get(display_row)
            if data_row is None:
                return None
            t = self.tests[ti]
            dv = self._depth_at_index(t, int(data_row))
            if dv is None:
                return None
            meter_n = int(math.floor(float(dv)))
            if meter_n in (getattr(self, "expanded_meters", set()) or set()):
                return meter_n
        except Exception:
            return None
        return None

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

    def _ige_id_to_num(self, ige_id: str) -> int:
        m = re.search(r"(\d+)", str(ige_id or ""))
        return max(1, int(m.group(1))) if m else 1

    def _layer_ige_id(self, lyr: Layer) -> str:
        ige_id = str(getattr(lyr, "ige_id", "") or "").strip()
        if not ige_id:
            ige_id = f"ИГЭ-{int(getattr(lyr, 'ige_num', 1) or 1)}"
            lyr.ige_id = ige_id
        lyr.ige_num = self._ige_id_to_num(ige_id)
        return ige_id

    def _ensure_ige_entry(self, ige_id: str, *, fallback_soil: str | None = None, fallback_mode: str | None = None) -> dict[str, object]:
        key = str(ige_id or "").strip() or "ИГЭ-1"
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
        self._ensure_ige_cpt_fields(ent)
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
        used: set[int] = set()
        for ige_id in (self.ige_registry or {}).keys():
            used.add(self._ige_id_to_num(str(ige_id)))
        for t in (self.tests or []):
            for lyr in (getattr(t, "layers", []) or []):
                used.add(self._ige_id_to_num(str(getattr(lyr, "ige_id", "") or "")))
        n = 1
        while n in used:
            n += 1
        return f"ИГЭ-{n}"

    def _find_unassigned_ige_id(self) -> str | None:
        candidates: list[str] = []
        for ige_id in (self.ige_registry or {}).keys():
            ent = self._ensure_ige_entry(str(ige_id or ""))
            if ent.get("soil_type") is None:
                candidates.append(str(ige_id))
        if not candidates:
            return None
        return sorted(candidates, key=self._ige_id_to_num)[0]

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
            "ИГЭ-1": {"soil_type": SoilType.SANDY_LOAM.value, "calc_mode": calc_mode_for_soil(SoilType.SANDY_LOAM).value, "style": dict(SOIL_STYLE.get(SoilType.SANDY_LOAM, {}))},
            "ИГЭ-2": {"soil_type": SoilType.SAND.value, "calc_mode": calc_mode_for_soil(SoilType.SAND).value, "style": dict(SOIL_STYLE.get(SoilType.SAND, {}))},
        }

    def _add_unassigned_ige_from_ribbon(self):
        self._push_undo()
        new_ige_id = self._next_free_ige_id()
        self.ige_registry[new_ige_id] = {"soil_type": None, "calc_mode": CalcMode.LIMITED.value, "style": {}}
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

    def redraw_all(self):
        self._sync_layers_panel()
        self._redraw()
        self.schedule_graph_redraw()

    def _active_layers_test_index(self) -> int | None:
        if getattr(self, "_active_test_idx", None) is not None:
            return int(self._active_test_idx)
        if getattr(self, "display_cols", None):
            return int(self.display_cols[0])
        if getattr(self, "tests", None):
            return 0
        return None

    def _sync_layers_panel(self):
        self._ensure_default_iges()
        if not getattr(self, "ribbon_view", None):
            return
        ti = self._active_layers_test_index()
        if ti is None or ti < 0 or ti >= len(self.tests):
            self.ribbon_view.set_layers([], [x.value for x in SoilType])
            return
        self._calc_layer_params_for_test(int(ti))
        layers = self._ensure_test_layers(self.tests[ti])
        ige_ids = {self._layer_ige_id(lyr) for lyr in layers}
        ige_ids.update(str(x) for x in (self.ige_registry or {}).keys())
        rows = []
        for ige_id in sorted(ige_ids, key=self._ige_id_to_num):
            ent = self._ensure_ige_entry(ige_id)
            cpt = dict(ent.get("cpt_result") or {})
            rows.append(
                {
                    "ige": ige_id,
                    "soil": str(ent.get("soil_type") or ""),
                    "source": str(cpt.get("source") or "-"),
                    "phi": ("-" if cpt.get("phi_norm") is None else f"{float(cpt.get('phi_norm')):.1f}"),
                    "e": ("-" if cpt.get("E_norm") is None else f"{float(cpt.get('E_norm')):.1f}"),
                    "status": str(cpt.get("status_text") or "-")
                }
            )
        self.ribbon_view.set_layers(rows, [x.value for x in SoilType])
        if rows:
            current_ige = str(rows[0].get("ige") or "ИГЭ-1")
            ent = self._ensure_ige_entry(current_ige)
            self.ribbon_view.layer_ige_var.set(current_ige)
            self.ribbon_view.layer_soil_var.set(str(ent.get("soil_type") or ""))
            self.ribbon_view.layer_mode_var.set(str(ent.get("calc_mode") or ""))

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
                "toggle_compact_1m": self._toggle_compact_1m,
                "set_display_sort_mode": self._set_display_sort_mode,
                "toggle_layer_edit": self._toggle_layer_edit_mode,
                "edit_ige": self._edit_ige_from_ribbon,
                "select_ige": self._select_ige_for_ribbon,
                "add_ige": self._add_unassigned_ige_from_ribbon,
                "calc_cpt": self.calculate_cpt_params,
                "edit_ige_cpt": self._edit_selected_ige_cpt_params,
                "apply_calc": lambda: self._redraw(),
                "k2k4_30": lambda: messagebox.showinfo("К2→К4", "Режим 30 МПа будет добавлен в следующем шаге."),
                "k2k4_50": lambda: messagebox.showinfo("К2→К4", "Режим 50 МПа будет добавлен в следующем шаге."),
            }
            self.ribbon_view = RibbonView(self, commands=commands, icon_font=_pick_icon_font(11))
            self.ribbon_view.pack(side="top", fill="x", before=ribbon)
            self.ribbon_view.set_object_name(self.object_name)
            self.ribbon_view.set_common_params(self._current_common_params(), geo_kind=str(getattr(self, "geo_kind", "K2")))
            self.ribbon_view.set_show_graphs(bool(getattr(self, "show_graphs", False)))
            self.ribbon_view.set_show_geology_column(bool(getattr(self, "show_geology_column", True)))
            self.ribbon_view.set_compact_1m(bool(getattr(self, "compact_1m", False)))
            self.ribbon_view.set_display_sort_mode(str(getattr(self, "display_sort_mode", "date")))
            self.ribbon_view.set_layer_edit_mode(True)
            ribbon.pack_forget()
        # ========= Main canvas (fixed header) =========
        mid = ttk.Frame(self)
        mid.pack(side="top", fill="both", expand=True)

        self.mid = mid  # host for table + hscroll (between table and footer)

        # Верхняя фиксированная шапка
        self.hcanvas = tk.Canvas(mid, background="white", highlightthickness=0, height=120)
        self.hcanvas.pack(side="top", fill="x")

        # Нижняя область с данными (скролл)
        body = ttk.Frame(mid)
        body.pack(side="top", fill="both", expand=True)

        self.vbar = ttk.Scrollbar(body, orient="vertical")
        self.vbar.pack(side="right", fill="y")

        self.canvas = tk.Canvas(
            body, background="white", highlightthickness=0,
            yscrollcommand=self.vbar.set
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        def _xview_proxy(*args):
            # ЕДИНЫЙ ИСТОЧНИК X — только body canvas.
            # Шапку синхронизируем ПОСЛЕ того как Tk применит прокрутку (after_idle),
            # иначе на правом краю из-за округлений бывает дрейф.
            self._end_edit(commit=True)
            try:
                self.canvas.xview(*args)
            except Exception:
                return
            # sync header (и зажим правого края при перетаскивании ползунка/скролле):
            # как только последняя колонка ВИДНА ПОЛНОСТЬЮ — вправо больше не двигаем.
            def _sync():
                try:
                    w = float(getattr(self, "_scroll_w", 0) or 0)
                except Exception:
                    w = 0.0
                if w <= 1:
                    try:
                        w = float(self._content_size()[0])
                        self._scroll_w = w
                    except Exception:
                        w = 1.0
                try:
                    view_w = float(self.canvas.winfo_width())
                except Exception:
                    view_w = 0.0

                try:
                    frac = float(self.canvas.xview()[0])
                except Exception:
                    frac = 0.0

                # вычислим максимально допустимую позицию X, при которой последняя колонка видна полностью
                try:
                    last_right_px = float(self._last_column_right_px())
                except Exception:
                    last_right_px = 0.0
                max_px = max(0.0, w - max(1.0, view_w))
                allow_px = min(max_px, max(0.0, last_right_px - max(1.0, view_w)))

                cur_px = frac * w
                if cur_px > (allow_px + 0.5):
                    # «зажать» вправо
                    frac2 = 0.0 if w <= 1 else (allow_px / w)
                    try:
                        self.canvas.xview_moveto(frac2)
                    except Exception:
                        pass
                    try:
                        frac = float(self.canvas.xview()[0])
                    except Exception:
                        frac = frac2

                try:
                    self.hcanvas.xview_moveto(frac)
                except Exception:
                    pass
            try:
                self.after_idle(_sync)
            except Exception:
                _sync()

        def _on_xscroll_command(first, last):
            # first/last: доли [0..1] видимой области
            # Обновляем сам горизонтальный скролл (если уже создан)
            try:
                if hasattr(self, "hscroll"):
                    self.hscroll.set(first, last)
            except Exception:
                pass

            # Синхронизируем X для canvas (тело) и hcanvas (шапка) без дрожания/уезда.
            # xscrollcommand вызывается и для canvas, и для hcanvas — используем lock.
            if getattr(self, "_xsync_lock", False):
                return
            self._xsync_lock = True
            try:
                f = float(first)
                try:
                    c0 = float(self.canvas.xview()[0])
                except Exception:
                    c0 = f
                try:
                    h0 = float(self.hcanvas.xview()[0])
                except Exception:
                    h0 = f

                if abs(c0 - f) > 1e-4:
                    try:
                        self.canvas.xview_moveto(f)
                    except Exception:
                        pass
                if abs(h0 - f) > 1e-4:
                    try:
                        self.hcanvas.xview_moveto(f)
                    except Exception:
                        pass
            finally:
                self._xsync_lock = False

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
        self.hcanvas.bind("<Configure>", lambda _e: (self.hcanvas.configure(width=self.canvas.winfo_width()), self._update_scrollregion()))

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
        )
        self.footer_cmd.pack(side="left")

        leg = ttk.Frame(self.footer)
        leg.pack(side="right")

        def _leg_item(parent, color: str, text: str):
            box = tk.Label(parent, width=2, height=1, bg=color, relief="solid", bd=1)
            box.pack(side="left", padx=(8, 4), pady=2)
            ttk.Label(parent, text=text).pack(side="left")

        # ЛЕГЕНДА (строго по промту)
        _leg_item(leg, GUI_PURPLE, "исправлено")
        _leg_item(leg, GUI_YELLOW, "отсутствуют значения")
        _leg_item(leg, GUI_BLUE, "отсутствует отказ")
        _leg_item(leg, GUI_GREEN, "откорректировано")
        _leg_item(leg, GUI_ORANGE, "исправлено на 0")
        _leg_item(leg, GUI_RED, "некорректный опыт")

        self.status = ttk.Label(self, text="Готов.", padding=(12, 6))

        # статусная строка — над подвалом
        self.status.pack(side="bottom", fill="x", before=self.footer)

        # горизонтальная полоса прокрутки — СРАЗУ после таблицы (над статусом)
        # по умолчанию скрыта; при показе перепаковываем статус НИЖЕ полосы

        # hscroll живёт ВНУТРИ mid (между таблицей и нижними статус/подвал)
        self.hscroll_frame.pack(side="bottom", fill="x")
        self.hscroll_frame.pack_forget()
    def _update_window_title(self):
        obj = self.object_name.strip() if getattr(self, "object_name", "") else ""
        obj = obj or "(без названия)"
        pname = Path(self.project_path).name if getattr(self, "project_path", None) else "(без проекта)"
        self.title(f"ZondEditor — {obj} — {pname}")

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
        self.load_and_render()
        try:
            _log_event(self.usage_logger, "OPEN", file=str(self.geo_path))
        except Exception:
            pass
        self._ensure_object_code()
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

    def _parse_probe_type_values(self, probe_type: str) -> dict[str, str]:
        """Parse probe type like A3/50/20/10/350 [№115]."""
        s = str(probe_type or "").strip()
        m = re.search(r"([A-Za-zА-Яа-я]\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", s)
        if not m:
            return {}
        return {
            "probe_type": f"{m.group(1)}/{m.group(2)}/{m.group(3)}/{m.group(4)}/{m.group(5)}",
            "cone_kn": m.group(2),
            "sleeve_kn": m.group(3),
            "cone_area_cm2": m.group(4),
            "sleeve_area_cm2": m.group(5),
        }

    def _extract_sounding_params_from_geo_bytes(self, data: bytes, geo_kind: str) -> dict[str, str]:
        params = {
            "controller_type": "ТЕСТ-К4" if str(geo_kind).upper() == "K4" else "ТЕСТ-К2",
            "controller_scale_div": (self.scale_var.get().strip() if hasattr(self, "scale_var") else "250") or "250",
            "probe_type": (self.probe_type_var.get().strip() if hasattr(self, "probe_type_var") else "") or "",
            "cone_kn": (self.fcone_var.get().strip() if hasattr(self, "fcone_var") else "30") or "30",
            "sleeve_kn": (self.fsleeve_var.get().strip() if hasattr(self, "fsleeve_var") else "10") or "10",
            "cone_area_cm2": (self.acon_var.get().strip() if hasattr(self, "acon_var") else "10") or "10",
            "sleeve_area_cm2": (self.asl_var.get().strip() if hasattr(self, "asl_var") else "350") or "350",
        }
        if str(geo_kind).upper() == "K4":
            params["controller_type"] = "ТЕСТ-К4М" if (bytes([0xCA,0x34,0xCC]) in data or b"K4M" in data.upper()) else "ТЕСТ-К4"
            # try textual probe type payload
            probe_txt = ""
            for enc in ("cp1251", "cp866", "latin1"):
                try:
                    txt = data.decode(enc, errors="ignore")
                except Exception:
                    continue
                mm = re.search(r"[A-Za-zА-Яа-я]\d+\s*/\s*\d+\s*/\s*\d+\s*/\s*\d+\s*/\s*\d+(?:\s*\[[^\]]+\])?", txt)
                if mm:
                    probe_txt = mm.group(0).strip()
                    break
            if probe_txt:
                params["probe_type"] = probe_txt
                params.update(self._parse_probe_type_values(probe_txt))
            else:
                # fallback from first K4 block header bytes (empirical)
                try:
                    starts = __import__("src.zondeditor.io.k4_reader", fromlist=["_k4_find_starts"])._k4_find_starts(data)
                    if starts:
                        p = int(starts[0])
                        cone = int(data[p + 15])
                        sleeve = int(data[p + 16])
                        cone_area = int(data[p + 18])
                        sleeve_area = int(data[p + 19]) + (int(data[p + 20]) << 8)
                        if 1 <= cone <= 500:
                            params["cone_kn"] = str(cone)
                        if 1 <= sleeve <= 500:
                            params["sleeve_kn"] = str(sleeve)
                        if 1 <= cone_area <= 200:
                            params["cone_area_cm2"] = str(cone_area)
                        if 1 <= sleeve_area <= 5000:
                            params["sleeve_area_cm2"] = str(sleeve_area)
                        if not params.get("probe_type"):
                            params["probe_type"] = f"A3/{params['cone_kn']}/{params['sleeve_kn']}/{params['cone_area_cm2']}/{params['sleeve_area_cm2']}"
                except Exception:
                    pass
        return params

    def _apply_sounding_params(self, params: dict[str, str] | None):
        p = dict(params or {})
        ct = str(p.get("controller_type", "") or "")
        sc = str(p.get("controller_scale_div", "") or "")
        pr = str(p.get("probe_type", "") or "")
        ckn = str(p.get("cone_kn", "") or "")
        skn = str(p.get("sleeve_kn", "") or "")
        ca = str(p.get("cone_area_cm2", "") or "")
        sa = str(p.get("sleeve_area_cm2", "") or "")
        if hasattr(self, "controller_type_var") and ct:
            self.controller_type_var.set(ct)
        if hasattr(self, "probe_type_var") and pr:
            self.probe_type_var.set(pr)
        if sc and hasattr(self, "scale_var"):
            self.scale_var.set(sc)
        if ckn and hasattr(self, "fcone_var"):
            self.fcone_var.set(ckn)
        if skn and hasattr(self, "fsleeve_var"):
            self.fsleeve_var.set(skn)
        if ca and hasattr(self, "acon_var"):
            self.acon_var.set(ca)
        if sa and hasattr(self, "asl_var"):
            self.asl_var.set(sa)

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
            self.controller_type_var.set(vars_map["controller_type"].get().strip())
            self.probe_type_var.set(vars_map["probe_type"].get().strip())
            if str(getattr(self, "geo_kind", "K2") or "K2").upper() != "K4":
                self.scale_var.set(vars_map["controller_scale_div"].get().strip() or self.scale_var.get())
            self.fcone_var.set(vars_map["cone_kn"].get().strip() or self.fcone_var.get())
            self.fsleeve_var.set(vars_map["sleeve_kn"].get().strip() or self.fsleeve_var.get())
            self.acon_var.set(vars_map["cone_area_cm2"].get().strip() or self.acon_var.get())
            self.asl_var.set(vars_map["sleeve_area_cm2"].get().strip() or self.asl_var.get())
            try:
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
        return {
            "controller_type": (self.controller_type_var.get().strip() if hasattr(self, "controller_type_var") else ""),
            "controller_scale_div": (self.scale_var.get().strip() if hasattr(self, "scale_var") else "250"),
            "probe_type": (self.probe_type_var.get().strip() if hasattr(self, "probe_type_var") else ""),
            "cone_kn": (self.fcone_var.get().strip() if hasattr(self, "fcone_var") else "30"),
            "sleeve_kn": (self.fsleeve_var.get().strip() if hasattr(self, "fsleeve_var") else "10"),
            "cone_area_cm2": (self.acon_var.get().strip() if hasattr(self, "acon_var") else "10"),
            "sleeve_area_cm2": (self.asl_var.get().strip() if hasattr(self, "asl_var") else "350"),
        }

    def _on_common_params_changed(self, params: dict[str, str] | None = None):
        p = dict(params or {})
        if hasattr(self, "controller_type_var") and "controller_type" in p:
            self.controller_type_var.set(str(p.get("controller_type", "") or ""))
        if hasattr(self, "probe_type_var") and "probe_type" in p:
            self.probe_type_var.set(str(p.get("probe_type", "") or ""))
        if "controller_scale_div" in p and str(getattr(self, "geo_kind", "K2") or "K2").upper() != "K4":
            self.scale_var.set(str(p.get("controller_scale_div", "") or self.scale_var.get()))
        if "cone_kn" in p:
            self.fcone_var.set(str(p.get("cone_kn", "") or self.fcone_var.get()))
        if "sleeve_kn" in p:
            self.fsleeve_var.set(str(p.get("sleeve_kn", "") or self.fsleeve_var.get()))
        if "cone_area_cm2" in p:
            self.acon_var.set(str(p.get("cone_area_cm2", "") or self.acon_var.get()))
        if "sleeve_area_cm2" in p:
            self.asl_var.set(str(p.get("sleeve_area_cm2", "") or self.asl_var.get()))
        try:
            self.schedule_graph_redraw()
        except Exception:
            pass

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
            scale = self.scale_var.get().strip() if hasattr(self, "scale_var") else ""
            fcone = self.fcone_var.get().strip() if hasattr(self, "fcone_var") else ""
            fsleeve = self.fsleeve_var.get().strip() if hasattr(self, "fsleeve_var") else ""
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

        if kv.get("scale"):
            self.scale_var.set(kv["scale"])
        if kv.get("scaleostria"):
            self.fcone_var.set(kv["scaleostria"])
        if kv.get("scalemufta"):
            self.fsleeve_var.set(kv["scalemufta"])

    def _calc_qc_fs_from_del(self, qc_del: int, fs_del: int) -> tuple[float, float]:
        """Пересчёт делений в qc (МПа) и fs (кПа) как в GeoExplorer.
        Использует: шкала (дел.), Fконуса (кН), Fмуфты (кН).
        Приняты площади: конус 10 см², муфта 350 см² (типовая для GeoExplorer).
        """
        def _f(x: str, default: float) -> float:
            try:
                s = (x or '').strip().replace(',', '.')
                return float(s) if s else default
            except Exception:
                return default

        scale_div = int(round(_f(self.scale_var.get() if getattr(self, 'scale_var', None) else '250', 250.0)))
        if scale_div <= 0:
            scale_div = 250
        fcone_kn = _f(self.fcone_var.get() if getattr(self, 'fcone_var', None) else '30', 30.0)
        fsleeve_kn = _f(self.fsleeve_var.get() if getattr(self, 'fsleeve_var', None) else '10', 10.0)

        CONE_AREA_CM2 = 10.0
        SLEEVE_AREA_CM2 = 350.0

        # qc: (del/scale)*F(kN) / A(cm2) * 10 -> MPa  (1 kN/cm2 = 10 MPa)
        qc_mpa = (qc_del / scale_div) * fcone_kn * (10.0 / CONE_AREA_CM2)
        # fs: (del/scale)*F(kN) / A(cm2) * 10000 -> kPa (1 kN/cm2 = 10000 kPa)
        fs_kpa = (fs_del / scale_div) * fsleeve_kn * (10000.0 / SLEEVE_AREA_CM2)
        return qc_mpa, fs_kpa

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
        - поле 'Объект' сверху
        - общая начальная глубина + 'Применить ко всем'
        - список опытов: h0 + дата/время + кнопка календаря
        - Enter перескакивает по ячейкам h0
        - клик по неактивной ячейке снимает 'Применить ко всем' и активирует все поля
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
        # По умолчанию выключено: массовое применение только как явное действие пользователя.
        apply_all_var = tk.BooleanVar(master=self, value=False)

        # объект (встроено)
        obj_var = tk.StringVar(master=self, value=(getattr(self, "object_code", "") or ""))

        # сообщение об ошибке
        msg_var = tk.StringVar(master=self, value="")
        # msg_lbl будет создан ниже, перед кнопками

        # --- объект ---
        r = 1
        ttk.Label(frm, text="Объект:").grid(row=r, column=0, sticky="w", padx=(0, 8), pady=2)
        obj_ent = ttk.Entry(frm, textvariable=obj_var, width=52)
        obj_ent.grid(row=r, column=1, columnspan=4, sticky="we", pady=2)
        r += 1

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

        apply_all_chk = ttk.Checkbutton(frm, text="Применить ко всем", variable=apply_all_var)
        apply_all_chk.grid(row=r, column=2, columnspan=3, sticky="w", padx=(12, 0), pady=2)
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
        ttk.Label(table, text="Дата/время", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Label(table, text="УГВ", font=("Segoe UI", 9, "bold")).grid(row=0, column=3, sticky="w", padx=(12, 0))

        row_vars = []   # (t, tid, h0_var, ent, dt_var, dt_lbl, gwl_on_var, gwl_var, gwl_ent)

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

            # дата/время (парсим из файла)
            dt0 = _norm_dt(getattr(t, "dt", None))
            dt_var = tk.StringVar(master=self, value=_fmt_dt(dt0))

            dt_lbl = ttk.Label(table, textvariable=dt_var, foreground="#666666", cursor="hand2")
            dt_lbl.grid(row=i, column=2, sticky="w", padx=(12, 0), pady=2)

            gwl_state = dict((getattr(self, "gwl_by_tid", {}) or {}).get(int(tid), {}) or {})
            gwl_enabled = bool(gwl_state.get("enabled", False))
            gwl_val = gwl_state.get("value", "")
            gwl_on_var = tk.BooleanVar(master=self, value=gwl_enabled)
            gwl_var = tk.StringVar(master=self, value=("" if gwl_val in (None, "") else f"{float(gwl_val):g}"))
            gwl_box = ttk.Frame(table)
            gwl_box.grid(row=i, column=3, sticky="w", padx=(12, 0), pady=2)
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

            row_vars.append((t, tid, h0_var, ent, dt_var, dt_lbl, gwl_on_var, gwl_var, gwl_ent))

        def _open_dt_calendar(row_tuple):
            t, tid, h0_var, ent, dt_var, dt_lbl, *_rest = row_tuple
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
            row[-1].bind("<Button-1>", lambda e, r=row: _open_dt_calendar(r))
        recompute_busy = False
        def _recompute_apply_state():
            nonlocal recompute_busy
            if recompute_busy:
                return
            recompute_busy = True
            try:
                msg_var.set("")

                # Если apply_all выключен и глубины разные — показываем '(разные)' в общей ячейке.
                # Важно: не подставлять скрыто 0 как fallback.
                if (not apply_all_var.get()):
                    try:
                        vals = []
                        for (_t, tid, h0_var, _ent, _dt_var, _dt_lbl, *_rest) in row_vars:
                            dv = _parse_depth_str(h0_var.get())
                            if dv is None:
                                try:
                                    dv = float((getattr(self, "depth0_by_tid", {}) or {}).get(int(tid), self._current_start_depth_for_test(_t)))
                                except Exception:
                                    dv = float(self._current_start_depth_for_test(_t))
                            vals.append(float(dv))
                        uniq_h0 = sorted({round(float(v), 6) for v in vals})
                    except Exception:
                        uniq_h0 = []
                    cur_txt = (common_var.get() or '').strip()
                    cur_can_override = (cur_txt == '' or cur_txt.startswith('('))
                    if len(uniq_h0) > 1:
                        if cur_can_override and cur_txt != "(разные)":
                            common_var.set("(разные)")
                    elif len(uniq_h0) == 1:
                        v0 = float(uniq_h0[0])
                        if cur_can_override and cur_txt != f"{v0:g}":
                            common_var.set(f"{v0:g}")

                cd = _parse_depth_str(common_var.get())

                if apply_all_var.get():
                    # Массовое применение — только если явно введено валидное общее значение.
                    if cd is not None:
                        for (_t, _tid, h0_var, _ent, _dt_var, _dt_lbl, *_rest) in row_vars:
                            h0_var.set(f"{cd:g}")
                    for (_t, _tid, _h0_var, ent, _dt_var, _dt_lbl, *_rest) in row_vars:
                        try:
                            ent.config(state="disabled")
                        except Exception:
                            pass
                else:
                    for (_t, _tid, _h0_var, ent, _dt_var, _dt_lbl, *_rest) in row_vars:
                        try:
                            ent.config(state="normal")
                        except Exception:
                            pass

                # общая ячейка всегда доступна
                try:
                    common_ent.config(state="normal")
                except Exception:
                    pass
            finally:
                recompute_busy = False


        def _on_common_change(*_):
            nonlocal recompute_busy
            if recompute_busy:
                return
            if apply_all_var.get():
                _recompute_apply_state()

        def _on_apply_toggle(*_):
            _recompute_apply_state()

        common_var.trace_add("write", _on_common_change)
        apply_all_var.trace_add("write", _on_apply_toggle)

        _recompute_apply_state()

        # если пользователь ввёл в строке значение != общего — снимаем apply_all
        def _make_row_trace(h0_var):
            def _on_row_change(*_):
                cd = _parse_depth_str(common_var.get())
                dv = _parse_depth_str(h0_var.get())
                if dv is None:
                    return
                if (cd is not None) and abs(dv - cd) > 1e-9 and apply_all_var.get():
                    apply_all_var.set(False)
                _recompute_apply_state()
            h0_var.trace_add("write", _on_row_change)

        for (t, tid, h0_var, ent, dt_var, dt_lbl, *_rest) in row_vars:
            _make_row_trace(h0_var)

        # клик по неактивной ячейке: активировать все и снять галочку
        def _on_entry_click(event, ent_ref):
            try:
                st = str(ent_ref.cget("state"))
            except Exception:
                st = "normal"
            if st == "disabled":
                apply_all_var.set(False)
                dlg.after(0, lambda: (ent_ref.focus_set(), ent_ref.selection_range(0, "end")))
                return "break"
            return None

        for (t, tid, h0_var, ent, dt_var, dt_lbl, *_rest) in row_vars:
            ent.bind("<Button-1>", lambda e, ee=ent: _on_entry_click(e, ee), add="+")
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

        for idx, (t, tid, h0_var, ent, dt_var, dt_lbl, *_rest) in enumerate(row_vars):
            ent.bind("<Return>", lambda e, k=idx: _focus_next(k))

        # применить начальные состояния
        _recompute_apply_state()

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

            # общая глубина:
            # - при apply_all=True: обязана быть числом 0..4
            # - при apply_all=False: допускается '(разные)' / пусто, тогда валидируем только строки
            common_txt = (common_var.get() or "").strip()
            cd = _parse_depth_str(common_txt)
            if apply_all_var.get():
                if cd is None:
                    msg_var.set("Некорректная начальная глубина. Пример: 1.2")
                    return
                if not (0.0 <= cd <= 4.0):
                    msg_var.set("Начальная глубина должна быть в диапазоне 0..4 м.")
                    return
            else:
                # когда глубины разные — common может быть '(разные)' и это ОК
                if cd is not None and not (0.0 <= cd <= 4.0):
                    msg_var.set("Начальная глубина должна быть в диапазоне 0..4 м.")
                    return

            # объект
            self.object_code = (obj_var.get() or "").strip()

            # сохранить общие
            # depth_start определим ниже: либо из общей ячейки (apply_all), либо из строк (если глубины разные)
            self._depth_confirmed = True
            if apply_all_var.get() and cd is not None:
                self.depth_start = float(cd)

            if need_step:
                self.step_m = 0.05 if step_var.get().strip() == "5" else 0.10
                self._step_confirmed = True

            # индивидуальные h0 — обновляем из текущей модели, не затирая чужие значения дефолтами
            prev_depth0 = dict(getattr(self, "depth0_by_tid", {}) or {})
            new_depth0 = dict(prev_depth0)
            for (t, tid, h0_var, ent, dt_var, dt_lbl, *_rest) in row_vars:
                if apply_all_var.get():
                    # Явное массовое применение: всем назначаем только общее значение.
                    dv = cd
                else:
                    dv = _parse_depth_str(h0_var.get())
                    if dv is None:
                        # При apply_all=False никаких скрытых подстановок из common/0.
                        try:
                            dv = float(prev_depth0.get(int(tid), self._current_start_depth_for_test(t)))
                        except Exception:
                            dv = float(self._current_start_depth_for_test(t))
                if not (0.0 <= dv <= 4.0):
                    msg_var.set(f"СЗ-{tid}: начальная глубина должна быть 0..4 м.")
                    return
                new_depth0[int(tid)] = float(dv)
            self.depth0_by_tid = new_depth0

            # если глубины разные (apply_all=False) — depth_start берём как минимум из строк
            try:
                if (not apply_all_var.get()) and self.depth0_by_tid:
                    self.depth_start = float(min(self.depth0_by_tid.values()))
                elif (not apply_all_var.get()) and (cd is not None):
                    self.depth_start = float(cd)
            except Exception:
                pass

            # обновить построение глубин здесь же (без перезагрузки)
            try:
                step = float(self.step_m or 0.10)
                for (t, tid, h0_var, ent, dt_var, dt_lbl, *_rest) in row_vars:
                    d0 = float(self.depth0_by_tid.get(int(tid), float(self.depth_start or 0.0)))
                    if getattr(t, "qc", None) is not None:
                        t.depth = [f"{(d0 + i * step):g}" for i in range(len(t.qc))]
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
                for (_t, tid, _h0_var, _ent, _dt_var, _dt_lbl, gwl_on_var, gwl_var, _gwl_ent) in row_vars:
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

                    self.flags[t.tid] = TestFlags(False, set(), set(), set(), set(), set())


                self._end_edit(commit=False)

                self._ensure_layers_defaults_for_all_tests()
                self._active_test_idx = 0 if self.tests else None
                self._sync_layers_panel()
                self._redraw()

                self.undo_stack.clear()

                self.redo_stack.clear()

                self._apply_gxl_calibration_from_meta(meta_rows)
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
                self.flags[t.tid] = TestFlags(False, set(), set(), set(), set(), set())

            self._end_edit(commit=False)
            self._ensure_layers_defaults_for_all_tests()
            self._active_test_idx = 0 if self.tests else None
            self._sync_layers_panel()
            self._redraw()
            self.undo_stack.clear()
            self.redo_stack.clear()

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

                self.flags[t.tid] = TestFlags(False, set(), set(), set(), set(), set())


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
            "cells_force": 0,
            "cells_missing": 0,
        }
        if not self.tests:
            return summary

        self._algo_preview_mode = bool(preview_mode)
        summary["tests_total"] = len([t for t in self.tests if bool(getattr(t, "export_on", True))])

        for t in self.tests:
            tid = t.tid
            prev = self.flags.get(tid) or TestFlags(False, set(), set(), set(), set(), set())
            user_cells = set(getattr(prev, "user_cells", set()) or set())
            # сохраняем ранее подсвеченные (чтобы повторный скан не затирал)
            interp_cells = set(getattr(prev, "interp_cells", set()) or set())
            force_cells = set(getattr(prev, "force_cells", set()) or set())
            force_tail_rows = set(getattr(prev, "force_tail_rows", set()) or set())

            if not bool(getattr(t, "export_on", True)):
                # Отключённые опыты исключаем из статусов и убираем подсветку некорректности.
                self.flags[tid] = TestFlags(False, interp_cells, force_cells, user_cells, set(), force_tail_rows)
                continue

            qc = [(_parse_cell_int(v) or 0) for v in t.qc]
            fs = [(_parse_cell_int(v) or 0) for v in t.fs]

            # Считаем отсутствующие значения (нули/пусто) для нижней строки, даже если опыт некорректный.
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
                self.flags[tid] = TestFlags(True, interp_cells, force_cells, user_cells, set(), set())
                summary["tests_invalid"] += 1
                continue

            # отметим короткие серии нулей (<=5) как кандидаты на интерполяцию
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
                            # не перетираем ручные
                            if cell not in user_cells:
                                if cell not in interp_cells:
                                    interp_cells.add(cell)
                                    summary["cells_interp"] += 1
                    i = j

            mark_short_zero_runs(qc, "qc")
            mark_short_zero_runs(fs, "fs")

            # кандидаты на "дописать хвост": подсветить СИНЕЙ строкой ниже последней глубины
            # правило: если ни один столбец (qc и fs) не достиг 250
            try:
                qc_max = max(qc) if qc else 0
                fs_max = max(fs) if fs else 0
                # Подсветка СИНИМ (без конфликтов со скрытием строк):
                # если ОБА параметра (qc и fs) не дошли до 250, подсвечиваем ПОСЛЕДНИЕ 2 ЯЧЕЙКИ (qc+fs)
                # последней существующей строки опыта.
                if qc and fs and (qc_max < 250 and fs_max < 250):
                    last_row = max(0, len(t.depth) - 1)
                    # force_cells подсвечивает конкретные ячейки (row, 'qc'/'fs')
                    if (last_row, "qc") not in user_cells:
                        force_cells.add((last_row, "qc"))
                    if (last_row, "fs") not in user_cells:
                        force_cells.add((last_row, "fs"))
                    # cells_force считаем как "опытов без отказа" (1 раз на опыт)
                    summary["cells_force"] += 1
                    force_tail_rows = set(getattr(prev, "force_tail_rows", set()) or set())
                else:
                    force_tail_rows = set(getattr(prev, "force_tail_rows", set()) or set())
            except Exception:
                force_tail_rows = set(getattr(prev, "force_tail_rows", set()) or set())


            # сохраняем зелёную подсветку откорректированных ячеек и хвостовые строки (Undo/Redo + скан)
            prev_algo_cells = set(getattr(prev, 'algo_cells', set()) or set())
            prev_force_tail_rows = set(getattr(prev, 'force_tail_rows', set()) or set())
            self.flags[tid] = TestFlags(False, interp_cells, force_cells, user_cells, prev_algo_cells, force_tail_rows or prev_force_tail_rows)

        self._redraw()
        return summary


    def _set_footer_from_scan(self):
        """Поставить НИЖНЮЮ строку (footer_cmd) по текущей автопроверке.
        Важно: всегда перезаписывает цвет (красный/серый), чтобы не оставалось синего после отката.
        """
        try:
            info = self._scan_by_algorithm()
        except Exception:
            info = {}
        try:
            inv = int(info.get("tests_invalid", 0) or 0)
            miss = int(info.get("cells_missing", 0) or 0)
            no_ref = int(info.get("cells_force", 0) or 0)

            parts = []
            if inv:
                parts.append(f"Некорректный опыт {inv}")
            if miss:
                parts.append(f"отсутствуют значения {miss}")
            if no_ref:
                parts.append(f"отсутствует отказ {no_ref}")

            msg = ", ".join(parts)
            # Сначала цвет, потом текст — так надёжнее для ttk
            try:
                self.footer_cmd.config(foreground=("#8B0000" if msg else "#666666"))
            except Exception:
                pass
            self.footer_cmd.config(text=msg)
        except Exception:
            pass

    def _compute_footer_realtime(self):
        """Пересчитать нижнюю строку (в реальном времени) по ТЕКУЩИМ данным.
        Правила:
          - 'Некорректный опыт X' — количество опытов с invalid=True (или по критерию >5 нулей подряд).
          - 'отсутствуют значения Y' — количество нулевых ячеек qc/fs ТОЛЬКО по корректным опытам.
          - 'отсутствует отказ Z' — количество корректных опытов, где qc_max<250 И fs_max<250.
        """
        try:
            tests = list(getattr(self, "tests", []) or [])
            if not tests:
                return {"inv": 0, "miss": 0, "no_ref": 0}

            inv = 0
            miss = 0
            no_ref = 0

            for t in tests:
                tid = getattr(t, "tid", None)
                # Если опыт отключён галочкой (не экспортировать) — исключаем его из пересчёта.
                if not bool(getattr(t, "export_on", True)):
                    continue
                qc = [(_parse_cell_int(v) or 0) for v in (getattr(t, "qc", []) or [])]
                fs = [(_parse_cell_int(v) or 0) for v in (getattr(t, "fs", []) or [])]

                # invalid: считаем по критерию ВСЕГДА (и учитываем сохранённый флаг),
                # иначе добавленные/новые опыты с флагом invalid=False и нулями не попадут в статистику.
                fl = (getattr(self, "flags", {}) or {}).get(tid)
                invalid_flag = bool(getattr(fl, "invalid", False)) if fl is not None else False
                try:
                    invalid_calc = (_max_zero_run(qc) > 5) or (_max_zero_run(fs) > 5)
                except Exception:
                    invalid_calc = False
                invalid = bool(invalid_flag or invalid_calc)


                if invalid:
                    inv += 1
                    continue  # нули некорректного опыта не считаем в 'отсутствуют значения' и 'отсутствует отказ'

                # missing zeros (only valid tests)
                user_cells = set(getattr(fl, "user_cells", set()) or set()) if fl is not None else set()
                n = min(len(qc), len(fs))
                for i0 in range(n):
                    if qc[i0] == 0 and (i0, "qc") not in user_cells:
                        miss += 1
                    if fs[i0] == 0 and (i0, "fs") not in user_cells:
                        miss += 1

                try:
                    qc_max = max(qc) if qc else 0
                    fs_max = max(fs) if fs else 0
                    if qc and fs and (qc_max < 250 and fs_max < 250):
                        no_ref += 1
                except Exception:
                    pass

            return {"inv": inv, "miss": miss, "no_ref": no_ref}
        except Exception:
            return {"inv": 0, "miss": 0, "no_ref": 0}

    def _update_footer_realtime(self):
        """Обновить нижнюю строку (красная/серая) по текущему состоянию."""
        try:
            res = self._compute_footer_realtime()
            inv = int(res.get("inv", 0) or 0)
            miss = int(res.get("miss", 0) or 0)
            no_ref = int(res.get("no_ref", 0) or 0)

            parts = []
            if inv:
                parts.append(f"Некорректный опыт {inv}")
            if miss:
                parts.append(f"отсутствуют значения {miss}")
            if no_ref:
                parts.append(f"отсутствует отказ {no_ref}")

            msg = ", ".join(parts)
            # Если всё ОК (включая учёт отключённых опытов) — показываем синюю надпись
            if not msg:
                try:
                    self.footer_cmd.config(foreground="#0b5ed7")
                except Exception:
                    pass
                self.footer_cmd.config(text="Статическое зондирование откорректировано.")
                return
            try:
                self.footer_cmd.config(foreground="#8B0000")
            except Exception:
                pass
            self.footer_cmd.config(text=msg)
        except Exception:
            pass

    def _footer_live_tick(self):
        """Таймер: держит нижнюю строку актуальной при удалениях/ручных правках."""
        try:
            # Не перебиваем синее сообщение 'откорректировано' сразу после корректировки:
            # если пользователь ничего не менял, оно останется до следующего действия.
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
            bad = (info.get("tests_invalid", 0) + info.get("cells_interp", 0) + info.get("cells_force", 0))
            if bad <= 0:
                self._algo_preview_mode = False
                self._redraw()
                self.footer_cmd.config(text="")
                return

            # оставляем предпросмотр (бледная подсветка)
            self._algo_preview_mode = True
            self._redraw()

            # Сформировать нижнюю строку по заданному формату:
            # 'Некорректный опыт 1, отсутствуют значения 14, отсутствует отказ 2'
            inv = int(info.get("tests_invalid", 0) or 0)
            miss = int(info.get("cells_missing", 0) or 0)
            no_ref = int(info.get("cells_force", 0) or 0)

            parts = []
            if inv:
                parts.append(f"Некорректный опыт {inv}")
            if miss:
                parts.append(f"отсутствуют значения {miss}")
            if no_ref:
                parts.append(f"отсутствует отказ {no_ref}")

            msg = ", ".join(parts)
            self.footer_cmd.config(text=msg)
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
        self.flags[tid] = TestFlags(False, set(), set(), set(), set(), set())

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
            old_flags = self.flags.get(t.tid) or TestFlags(False, set(), set(), set(), set(), set())

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
            new_tail: set[int] = set()

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
            for r in (old_flags.force_tail_rows or set()):
                if r in map_old_to_new:
                    new_tail.add(map_old_to_new[r])

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

            self.flags[t.tid] = TestFlags(bool(invalid_now), new_interp, new_force, new_user, new_algo, new_tail)

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
        return self.w_depth + self.w_val*2 + (self.w_val if getattr(self, "geo_kind", "K2")=="K4" else 0)

    def _is_graph_panel_visible(self) -> bool:
        return bool(getattr(self, "show_graphs", False) or getattr(self, "show_geology_column", True))

    def _column_block_width(self) -> int:
        graph_w = int(getattr(self, "graph_w", 150) or 150) if self._is_graph_panel_visible() else 0
        return self._table_col_width() + graph_w

    def _column_x0(self, col: int) -> int:
        return self.pad_x + col * (self._column_block_width() + self.col_gap)

    def _last_column_right_px(self) -> float:
        """Правая граница последнего блока в пикселях (с учетом графиков)."""
        try:
            n_cols = len(getattr(self, "display_cols", []) or [])
        except Exception:
            n_cols = 0
        if n_cols <= 0:
            try:
                n_cols = len(getattr(self, "tests", []) or [])
            except Exception:
                n_cols = 0
        try:
            col_w = float(self._column_block_width())
        except Exception:
            col_w = 0.0
        try:
            gap = float(self.col_gap)
        except Exception:
            gap = 0.0
        try:
            pad = float(self.pad_x)
        except Exception:
            pad = 0.0
        last_left_px = pad + (col_w + gap) * max(0, n_cols - 1)
        return last_left_px + col_w

    def _graph_rect_for_test(self, ti: int, r: int | None = None):
        try:
            col = int(self.display_cols.index(ti))
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

        block_w = self._column_block_width()
        self._last_col_w = block_w
        total_w = self.pad_x * 2 + (block_w * len(self.tests)) + (self.col_gap * max(0, len(self.tests) - 1))
        body_h = self._total_body_height() if max_rows > 0 else 0
        header_h = int(self.pad_y + self.hdr_h)  # фиксированная область
        return total_w, body_h, header_h

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
        w_content = w

        # вычисляем "правый зазор" (даёт свободное место справа, чтобы последняя шапка не прилипала к краю)
        try:
            vw = int(self.canvas.winfo_width() or 1)
        except Exception:
            vw = 1
        gap = int(getattr(self, "_last_col_w", 0) or 0)
        if gap < 24:
            gap = 24

        need_h = (w_content > max(vw, 1))
        if not need_h:
            gap = 0

        w_total = w_content + gap
        # SAFETY: небольшой запас по ширине, чтобы горизонтальный скролл доходил до конца
        try:
            if getattr(self, "geo_kind", "K2") == "K4":
                w_total += int(self.w_val)  # +1 колонка запаса
        except Exception:
            pass

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
        # шапка: только X-сдвиг, Y фиксирован
        try:
            self.hcanvas.configure(scrollregion=(0, 0, w_total, header_h))
            self.hcanvas.configure(height=header_h)
        except Exception:
            pass


        # восстановить X-сдвиг в пикселях
        try:
            self._scroll_w = float(w_total or 1)
        except Exception:
            self._scroll_w = float(w_total or 1)
        try:
            new_frac = 0.0 if (w_total <= 1) else (old_px / float(w_total))
            if new_frac < 0.0:
                new_frac = 0.0
            if new_frac > 1.0:
                new_frac = 1.0
            # двигаем через moveto, чтобы шапка и тело совпали и на правом краю
            self.canvas.xview_moveto(new_frac)
            try:
                self.hcanvas.xview_moveto(new_frac)
            except Exception:
                pass
        except Exception:
            pass

        # Горизонтальная прокрутка: показываем только если колонки не помещаются в видимую область
        if not need_h:
            try:
                self.canvas.xview_moveto(0)
                self.hcanvas.xview_moveto(0)
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

        # ---- qc max (MPa): use existing calibration source first, then kind fallback ----
        qc_max = None
        try:
            fcone = float((self.fcone_var.get() if getattr(self, "fcone_var", None) else "").strip().replace(",", "."))
            if abs(fcone - 30.0) < 1e-6:
                qc_max = 30.0
            elif abs(fcone - 50.0) < 1e-6:
                qc_max = 50.0
        except Exception:
            pass

        if qc_max is None:
            # data hint: if any qc exceeds 30 MPa, choose 50
            try:
                seen_above_30 = False
                for t in (getattr(self, "tests", None) or []):
                    qarr = getattr(t, "qc", []) or []
                    farr = getattr(t, "fs", []) or []
                    for i in range(max(len(qarr), len(farr))):
                        q_raw = _parse_cell_int(qarr[i]) if i < len(qarr) else None
                        f_raw = _parse_cell_int(farr[i]) if i < len(farr) else None
                        if q_raw is None and f_raw is None:
                            continue
                        q_mpa, _ = self._calc_qc_fs_from_del(int(q_raw or 0), int(f_raw or 0))
                        if float(q_mpa) > 30.0:
                            seen_above_30 = True
                            break
                    if seen_above_30:
                        break
                if seen_above_30:
                    qc_max = 50.0
            except Exception:
                pass

        if qc_max is None:
            qc_max = 50.0 if str(getattr(self, "geo_kind", "K2") or "K2").upper() == "K4" else 30.0

        # ---- fs max (kPa): global max rounded to a fixed pretty scale ----
        fs_max_global = 0.0
        try:
            for t in (getattr(self, "tests", None) or []):
                farr = getattr(t, "fs", []) or []
                for i in range(len(farr)):
                    f_raw = _parse_cell_int(farr[i])
                    if f_raw is None:
                        continue
                    _, fs_kpa = self._calc_qc_fs_from_del(0, int(f_raw or 0))
                    fs_max_global = max(fs_max_global, float(fs_kpa))
        except Exception:
            pass

        pretty = [50, 100, 200, 300, 500, 800, 1000, 1500, 2000, 3000, 5000]
        if fs_max_global <= 0:
            fs_max = 500.0
        else:
            fs_max = float(pretty[-1])
            for v in pretty:
                if fs_max_global <= float(v):
                    fs_max = float(v)
                    break

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
        q_txt = f"0..{int(round(qmax))}" if abs(qmax - round(qmax)) < 1e-6 else f"0..{qmax:.1f}"
        self.hcanvas.create_text(xa1, qc_axis_y - 10, anchor="e", text=q_txt, fill=GRAPH_QC_GREEN, font=("Segoe UI", 7), tags=tag)
        self.hcanvas.create_text(xa1, fs_axis_y - 10, anchor="e", text=f"0..{int(round(fmax))}", fill=GRAPH_FS_BLUE, font=("Segoe UI", 7), tags=tag)

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
        """Фактический диапазон глубин опыта по depth-массиву (без ухода за пределы данных)."""
        d_arr = getattr(t, "depth", []) or []
        dvals: list[float] = []
        for ds in d_arr:
            dv = _parse_depth_float(ds)
            if dv is not None:
                dvals.append(float(dv))
        if not dvals:
            return self._test_depth_range(t)
        top = min(dvals)
        bot = max(dvals)
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
        return layers

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
        self._sync_layers_panel()


    def _ensure_layers_defaults_for_all_tests(self):
        changed = self.layer_store.ensure_defaults_for_all_tests(self.tests, self._test_depth_range)
        for t in (self.tests or []):
            for lyr in self._ensure_test_layers(t):
                self._apply_ige_to_layer(lyr)
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


    def _draw_layer_hatch(self, x0: float, y0: float, x1: float, y1: float, color: str, hatch: str, tags):
        drew_any = False

        def _draw_diag_segment(b: float, slope: int):
            nonlocal drew_any
            pts = []
            if slope > 0:
                # y = x + b
                yy = x0 + b
                if y0 <= yy <= y1:
                    pts.append((x0, yy))
                yy = x1 + b
                if y0 <= yy <= y1:
                    pts.append((x1, yy))
                xx = y0 - b
                if x0 <= xx <= x1:
                    pts.append((xx, y0))
                xx = y1 - b
                if x0 <= xx <= x1:
                    pts.append((xx, y1))
            else:
                # y = -x + b
                yy = -x0 + b
                if y0 <= yy <= y1:
                    pts.append((x0, yy))
                yy = -x1 + b
                if y0 <= yy <= y1:
                    pts.append((x1, yy))
                xx = b - y0
                if x0 <= xx <= x1:
                    pts.append((xx, y0))
                xx = b - y1
                if x0 <= xx <= x1:
                    pts.append((xx, y1))
            uniq = []
            for p in pts:
                if not any(abs(p[0] - q[0]) < 1e-6 and abs(p[1] - q[1]) < 1e-6 for q in uniq):
                    uniq.append(p)
            if len(uniq) >= 2:
                self.canvas.create_line(uniq[0][0], uniq[0][1], uniq[1][0], uniq[1][1], fill=color, width=1, tags=tags)
                drew_any = True

        spacing = 10 if hatch in ("diag_sparse", "dot") else 6
        if hatch == "cross":
            for offs in range(int(y0) - int(x1), int(y1 + x1), spacing):
                _draw_diag_segment(float(offs), +1)
            for offs in range(int(y0) + int(x0), int(y1 + x1), spacing):
                _draw_diag_segment(float(offs), -1)
            return
        if hatch == "dot":
            for yy in range(int(y0) + 3, int(y1), spacing):
                for xx in range(int(x0) + 3, int(x1), spacing):
                    self.canvas.create_rectangle(xx, yy, xx + 1, yy + 1, outline=color, fill=color, tags=tags)
                    drew_any = True
            return
        for offs in range(int(y0) - int(x1), int(y1 + x1), spacing):
            _draw_diag_segment(float(offs), +1)

        if not drew_any and y1 > y0 and x1 > x0:
            ym = (y0 + y1) * 0.5
            self.canvas.create_line(x0, ym, x1, ym, fill=color, width=1, tags=tags)

    def _draw_layers_overlay_for_test(self, ti: int, plot_rect, depth_to_y, tags):
        t = self.tests[ti]
        layers = self._ensure_test_layers(t)
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
        data_top, data_bot = self._test_effective_data_depth_range(t)
        data_top = float(data_top)
        data_bot = float(data_bot)
        label_spans = []
        for lyr in layers:
            lt = max(data_top, float(lyr.top_m))
            lb = min(data_bot, float(lyr.bot_m))
            if lb - lt <= 1e-9:
                continue
            ly0 = depth_to_y(lt)
            ly1 = depth_to_y(lb)
            if ly0 is None or ly1 is None:
                self._debug_log(f"layers_overlay: depth_to_y none ti={ti}, layer={lyr.ige_num}, top={lyr.top_m}, bot={lyr.bot_m}")
                continue
            ty0 = max(y0, min(ly0, ly1))
            ty1 = min(y1, max(ly0, ly1))
            if ty1 <= ty0:
                continue
            ige_id = self._layer_ige_id(lyr)
            ent = self._ensure_ige_entry(ige_id, fallback_soil=lyr.soil_type.value, fallback_mode=lyr.calc_mode.value)
            style = dict(ent.get("style") or {})
            fill = style.get("color") or "#f2f2f2"
            hatch = style.get("hatch") or ""
            self.canvas.create_rectangle(x0, ty0, x1, ty1, fill=fill, outline="", tags=tags)
            if hatch:
                hatch_color = style.get("hatch_color") or "#000000"
                self._draw_layer_hatch(x0, ty0, x1, ty1, color=hatch_color, hatch=hatch, tags=tags)
            self._layer_plot_hitbox.append({"kind": "interval", "ti": ti, "ige_id": ige_id, "top": float(lt), "bot": float(lb), "bbox": (x0, ty0, x1, ty1)})
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
                    fill="#ffffff",
                    outline="#d0d0d0",
                    width=1,
                    tags=tags,
                )
                self.canvas.create_text(cx, cy, text=text, fill="#4e4335", font=font, tags=tags)
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
        for ti in self.display_cols:
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
        layers = self._ensure_test_layers(t)
        x0, x1, _y0, _y1 = rect
        # Ручка границы: центр по правому краю колонки слоёв, слегка внутри.
        handle_x = x1 - 2
        plus_x = x0 + 10

        def _draw_plus(tag: str, y_pos: float, boundary: int, kind: str, *, active: bool = True, x_pos: float | None = None):
            px = float(plus_x if x_pos is None else x_pos)
            self.canvas.create_rectangle(px - 6, y_pos - 6, px + 6, y_pos + 6, fill="#ffffff", outline="#8f8f8f", width=1, tags=("layer_handles", "layer_plus_box", tag))
            self.canvas.create_text(px, y_pos, text="+", fill=("#1d4f7c" if active else "#bdbdbd"), font=("Segoe UI", 9, "bold"), tags=("layer_handles", "layer_plus", tag))
            if active:
                self._layer_handle_hitbox.append({"kind": kind, "ti": ti, "boundary": int(boundary), "tag": tag, "bbox": (px - 10, y_pos - 10, px + 10, y_pos + 10)})

        def _draw_minus(tag: str, y_pos: float, boundary: int, kind: str, *, active: bool = True, x_pos: float | None = None):
            px = float(plus_x if x_pos is None else x_pos)
            self.canvas.create_rectangle(px - 6, y_pos - 6, px + 6, y_pos + 6, fill="#ffffff", outline="#8f8f8f", width=1, tags=("layer_handles", "layer_minus_box", tag))
            self.canvas.create_text(px, y_pos, text="−", fill=("#7c1d1d" if active else "#bdbdbd"), font=("Segoe UI", 9, "bold"), tags=("layer_handles", "layer_minus", tag))
            if active:
                self._layer_handle_hitbox.append({"kind": kind, "ti": ti, "boundary": int(boundary), "tag": tag, "bbox": (px - 10, y_pos - 10, px + 10, y_pos + 10)})

        if layers:
            top_y = self._depth_to_canvas_y(float(layers[0].top_m))
            bot_y = self._depth_to_canvas_y(float(layers[-1].bot_m))
            if top_y is not None:
                _draw_plus(f"layer_plus_top_{ti}", top_y + 6, 0, "plus_top", active=self._can_insert_layer_from_top(int(ti)))
                _draw_minus(f"layer_minus_top_{ti}", top_y + 20, 0, "minus_top", active=(len(layers) > 1))
            if bot_y is not None:
                _draw_plus(f"layer_plus_bottom_{ti}", bot_y, len(layers), "plus_bottom", active=self._can_insert_layer_from_bottom(int(ti)))
                _draw_minus(f"layer_minus_bottom_{ti}", bot_y, len(layers) - 1, "minus_bottom", active=(len(layers) > 1), x_pos=(plus_x + 14))

        for bi in range(1, len(layers)):
            boundary = layers[bi].top_m
            y = self._depth_to_canvas_y(boundary)
            if y is None:
                continue
            h_tag = f"layer_handle_{ti}_{bi}"
            p_tag = f"layer_plus_{ti}_{bi}"
            m_tag = f"layer_minus_{ti}_{bi}"
            self.canvas.create_line(x0, y, x1, y, fill="#ab9f8a", width=1, dash=(3, 2), tags=("layer_handles", "layer_boundary_line"))
            self.canvas.create_rectangle(handle_x - 5, y - 5, handle_x + 5, y + 5, fill="#fefefe", outline="#555", tags=("layer_handles", "layer_handle", h_tag))
            bx0 = handle_x - 52
            bx1 = handle_x - 12
            self.canvas.create_rectangle(bx0, y - 8, bx1, y + 8, fill="#ffffff", outline="#555", tags=("layer_handles", "layer_depth_box", h_tag))
            self.canvas.create_text((bx0 + bx1) / 2, y, text=f"{float(boundary):.2f}", fill="#3f3f3f", font=("Segoe UI", 7), tags=("layer_handles", "layer_depth_label", h_tag))
            self._layer_handle_hitbox.append({"kind": "boundary", "ti": ti, "boundary": bi, "tag": h_tag, "bbox": (handle_x - 6, y - 6, handle_x + 6, y + 6)})
            self._layer_depth_box_hitbox.append({"kind": "boundary_depth_edit", "ti": ti, "boundary": bi, "bbox": (bx0, y - 9, bx1, y + 9)})
            _draw_plus(p_tag, y, bi, "plus", active=self._can_split_layer_index(int(ti), int(bi)))
            _draw_minus(m_tag, y + 14, bi, "minus", active=(len(layers) > 1))

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
            self._edit_header(ti)
            return
        if kind == "dup":
            self._duplicate_test(ti)
            return
        if kind == "trash":
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
            self._push_undo()
            self._insert_layer_at_boundary(ti, row)
            return
        if kind == "layer_plus_top":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            if not self._can_insert_layer_from_top(int(ti)):
                return
            self._push_undo()
            self._insert_layer_from_top(ti)
            return
        if kind == "layer_plus_bottom":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            if not self._can_insert_layer_from_bottom(int(ti)):
                return
            self._push_undo()
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
            self._layer_drag = {"ti": int(ti), "boundary": int(row)}
            return
        if kind == "layer_boundary_depth_edit":
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
                    self._show_ige_picker_at_click(event, int(ti), float(depth_hit), anchor_bbox=bbox_hit)
                    return
            except Exception:
                pass

            # Клик по телу слоя только выбирает опыт/слой, но не открывает picker ИГЭ.
            try:
                layers = self._ensure_test_layers(self.tests[int(ti)])
                depth = float(field if field is not None else 0.0)
                target = next((lyr for lyr in layers if float(lyr.top_m) <= depth <= float(lyr.bot_m)), None)
                if target is not None:
                    self._select_ige_for_ribbon(self._layer_ige_id(target))
            except Exception:
                pass
            return
        if kind == "layer_label":
            if self._is_test_locked(int(ti)):
                self._set_status("Опыт заблокирован")
                return
            meta = field if isinstance(field, dict) else {}
            self._ige_picker_log(f"click_resolved ti={int(ti)} source=layer_label depth={float(meta.get('depth', 0.0) if meta else 0.0):.4f}")
            self._show_ige_picker_at_click(
                event,
                int(ti),
                float(meta.get("depth", 0.0) if meta else 0.0),
                anchor_bbox=(meta.get("bbox") if meta else None),
            )
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
                # Вставка строки СВЕРХУ/СНИЗУ (без разрывов).
                #   - Снизу: клик только в СЛЕДУЮЩУЮ строку после последней существующей.
                #   - Сверху: клик только в СТРОКУ ПЕРЕД первой существующей.
                if field in ("qc", "fs"):
                    t = self.tests[ti]

                    # --- TOP: разрешаем дописывать "верх" по принципу "низа" ---
                    top_disp = start_r - 1
                    if row == top_disp:
                        # не даём создавать "дырки" сверху: если первая строка уже пустая — заполни её сначала
                        if len(t.qc) > 0:
                            try:
                                q0 = t.qc[0]
                                f0 = t.fs[0]
                            except Exception:
                                q0 = None
                                f0 = None
                            if (q0 in (None, "")) and (f0 in (None, "")):
                                self._set_status("Сначала заполните следующую строку")
                                return
                        # вычисляем шаг по глубинам (если есть), иначе дефолт
                        step = 0.05
                        try:
                            if len(t.depth) >= 2:
                                step = float(str(t.depth[1]).replace(",", ".")) - float(str(t.depth[0]).replace(",", "."))
                                if step <= 0:
                                    step = 0.05
                            elif getattr(self, "current_step", None):
                                step = float(self.current_step)
                        except Exception:
                            step = 0.05
                        # новая глубина = первая - step
                        d_new = 0.0
                        try:
                            if len(t.depth) >= 1:
                                d_new = float(str(t.depth[0]).replace(",", ".")) - step
                            else:
                                d_new = 0.0
                        except Exception:
                            d_new = 0.0
                        t.depth.insert(0, f"{d_new:.2f}")
                        t.qc.insert(0, "")
                        t.fs.insert(0, "")
                        # сдвигаем подсветку (флаги) вниз на 1 строку
                        try:
                            fl = self.flags.get(getattr(t, "tid", None))
                            if fl:
                                # сдвиг всех cell-наборов на +1 (вставка строки в начале)
                                def _bump(cells):
                                    out=set()
                                    for (r, knd) in (cells or set()):
                                        try:
                                            rr=int(r)
                                        except Exception:
                                            continue
                                        out.add((rr+1, knd))
                                    return out
                                fl.user_cells = _bump(getattr(fl, 'user_cells', set()))
                                fl.interp_cells = _bump(getattr(fl, 'interp_cells', set()))
                                fl.force_cells = _bump(getattr(fl, 'force_cells', set()))
                        except Exception:
                            pass
                        self._redraw()
                        self.schedule_graph_redraw()
                        self._begin_edit(ti, 0, field, display_row=row)
                        return

                    # --- BOTTOM (tail) ---
                    next_disp = start_r + len(t.qc)
                    if row != next_disp:
                        return
                    # если последняя строка существует, но она полностью пустая — не даём добавлять следующую
                    if len(t.qc) > 0:
                        try:
                            q_last = t.qc[-1]
                            f_last = t.fs[-1]
                        except Exception:
                            q_last = None
                            f_last = None
                        if (q_last in (None, "") ) and (f_last in (None, "") ):
                            self._set_status("Сначала заполните предыдущую строку")
                            return
                    new_idx = len(t.qc)
                    self._append_row(ti)
                    self._begin_edit(ti, new_idx, field, display_row=row)
                return


            # Normal in-range cell → start edit immediately
            if field in ("qc", "fs"):
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
        ids = sorted(self.ige_registry.keys(), key=self._ige_id_to_num)
        for ige_id in ids:
            ent = self._ensure_ige_entry(ige_id)
            soil_label = str(ent.get("soil_type") or "не назначен")
            values.append(f"{ige_id} ({soil_label})")
        cb = ttk.Combobox(win, state="readonly", values=values)
        current_ige = self._layer_ige_id(target)
        current_soil = str(self._ensure_ige_entry(current_ige).get("soil_type") or "не назначен")
        current_label = f"{current_ige} ({current_soil})"
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
            ige_id = label.split("(", 1)[0].strip()
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
            bg="#ffffff",
            fg="#111111",
            insertbackground="#111111",
            selectbackground="#2f80ed",
            selectforeground="#ffffff",
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground="#666666",
            highlightcolor="#2f80ed",
        )
        t = self.tests[ti]
        layers = self._ensure_test_layers(t)
        cur = float(layers[boundary].top_m) if 0 <= boundary < len(layers) else 0.0
        entry.insert(0, f"{cur:.2f}")
        self._place_boundary_depth_editor(entry, bx0, by0, bx1, by1)

        prev_depth = float(layers[boundary - 1].top_m) if boundary - 1 >= 0 else float(layers[0].top_m)
        next_depth = float(layers[boundary + 1].top_m) if boundary + 1 < len(layers) else float(layers[-1].bot_m)

        def _apply(_ev=None):
            try:
                val = float(str(entry.get()).replace(",", "."))
            except Exception:
                self._close_boundary_depth_editor()
                return
            snapped = round(val / 0.1) * 0.1
            snapped = max(prev_depth + 0.2, min(next_depth - 0.2, snapped))
            self._push_undo()
            cloned = [layer_from_dict(layer_to_dict(x)) for x in self._ensure_test_layers(t)]
            t.layers = move_layer_boundary(cloned, int(boundary), snapped)
            self._calc_layer_params_for_test(int(ti))
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
        layers = [layer_from_dict(layer_to_dict(x)) for x in self._ensure_test_layers(t)]
        if not layers:
            return
        self._split_layer_for_plus(int(ti), len(layers) - 1, from_bottom=True)

    def _can_split_layer(self, lyr: Layer) -> bool:
        # Минимальная валидная мощность слоя = 0.20 м.
        # Для '+' слой должен делиться на 2 валидных слоя => минимум 0.40 м.
        try:
            return (float(lyr.bot_m) - float(lyr.top_m)) >= (0.4 - 1e-9)
        except Exception:
            return False

    def _can_split_layer_index(self, ti: int, layer_index: int) -> bool:
        if ti is None or ti < 0 or ti >= len(self.tests):
            return False
        t = self.tests[int(ti)]
        layers = [layer_from_dict(layer_to_dict(x)) for x in self._ensure_test_layers(t)]
        if not (0 <= int(layer_index) < len(layers)):
            return False
        return self._can_split_layer(layers[int(layer_index)])

    def _split_layer_for_plus(self, ti: int, layer_index: int, *, from_bottom: bool = False):
        if ti is None or ti < 0 or ti >= len(self.tests):
            return
        if self._is_test_locked(int(ti)):
            return
        t = self.tests[int(ti)]
        layers = [layer_from_dict(layer_to_dict(x)) for x in self._ensure_test_layers(t)]
        li = int(layer_index)
        if not (0 <= li < len(layers)):
            return
        base = layers[li]
        if not self._can_split_layer(base):
            self._set_status("Добавление недоступно: слой нельзя разделить на 2 слоя по ≥0.20 м")
            return

        top = float(base.top_m)
        bot = float(base.bot_m)
        thickness = bot - top
        take = min(float(INSERT_LAYER_THICKNESS_M), max(0.2, thickness - 0.2))
        if take < 0.2 - 1e-9:
            self._set_status("Добавление недоступно: слой нельзя разделить на 2 слоя по ≥0.20 м")
            return

        if from_bottom:
            new_bot = bot
            new_top = round((new_bot - take) / 0.1) * 0.1
            new_top = max(top + 0.2, min(new_bot - 0.2, new_top))
            base.bot_m = new_top
            ins_top, ins_bot, ins_idx = float(new_top), float(new_bot), li + 1
        else:
            new_top = top
            new_bot = round((new_top + take) / 0.1) * 0.1
            new_bot = min(bot - 0.2, max(new_top + 0.2, new_bot))
            base.top_m = new_bot
            ins_top, ins_bot, ins_idx = float(new_top), float(new_bot), li

        new_ige_id = self._find_unassigned_ige_id() or self._next_free_ige_id()
        soil = SoilType.SANDY_LOAM
        layers.insert(ins_idx, Layer(top_m=ins_top, bot_m=ins_bot, ige_id=new_ige_id, soil_type=soil, calc_mode=calc_mode_for_soil(soil), style=dict(SOIL_STYLE.get(soil, {})), ige_num=self._ige_id_to_num(new_ige_id)))
        t.layers = normalize_layers(layers)
        self.ige_registry[new_ige_id] = {"soil_type": None, "calc_mode": CalcMode.LIMITED.value, "style": {}}
        try:
            self._apply_ige_to_layer(t.layers[int(ins_idx)])
        except Exception:
            pass
        self._calc_layer_params_for_test(int(ti))
        self._sync_layers_panel()
        self._redraw()
        self._redraw_graphs_now()
        self.schedule_graph_redraw()
        try:
            if getattr(self, "ribbon_view", None):
                self.ribbon_view.focus_ige_row(new_ige_id)
        except Exception:
            pass

    def _can_insert_layer_from_top(self, ti: int) -> bool:
        return self._can_split_layer_index(int(ti), 0)

    def _can_insert_layer_from_bottom(self, ti: int) -> bool:
        if ti is None or ti < 0 or ti >= len(self.tests):
            return False
        t = self.tests[int(ti)]
        layers = [layer_from_dict(layer_to_dict(x)) for x in self._ensure_test_layers(t)]
        if not layers:
            return False
        return self._can_split_layer_index(int(ti), len(layers) - 1)

    def _remove_layer_from_top(self, ti: int):
        if ti is None or ti < 0 or ti >= len(self.tests):
            return
        t = self.tests[ti]
        layers = [layer_from_dict(layer_to_dict(x)) for x in self._ensure_test_layers(t)]
        if len(layers) <= 1:
            self._set_status("Нельзя удалить единственный слой")
            return
        removed = layers.pop(0)
        layers[0].top_m = float(removed.top_m)
        t.layers = normalize_layers(layers)
        self._calc_layer_params_for_test(int(ti))
        self._sync_layers_panel()
        self._redraw()
        self._redraw_graphs_now()
        self.schedule_graph_redraw()

    def _remove_layer_from_bottom(self, ti: int):
        if ti is None or ti < 0 or ti >= len(self.tests):
            return
        t = self.tests[ti]
        layers = [layer_from_dict(layer_to_dict(x)) for x in self._ensure_test_layers(t)]
        if len(layers) <= 1:
            self._set_status("Нельзя удалить единственный слой")
            return
        removed = layers.pop()
        layers[-1].bot_m = float(removed.bot_m)
        t.layers = normalize_layers(layers)
        self._calc_layer_params_for_test(int(ti))
        self._sync_layers_panel()
        self._redraw()
        self._redraw_graphs_now()
        self.schedule_graph_redraw()

    def _remove_layer_at_index(self, ti: int, layer_index: int):
        if ti is None or ti < 0 or ti >= len(self.tests):
            return
        t = self.tests[ti]
        layers = [layer_from_dict(layer_to_dict(x)) for x in self._ensure_test_layers(t)]
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
        removed = layers.pop(li)
        # Внутренний слой поглощается нижележащим соседним слоем.
        layers[li].top_m = float(removed.top_m)
        t.layers = normalize_layers(layers)
        self._calc_layer_params_for_test(int(ti))
        self._sync_layers_panel()
        self._redraw()
        self._redraw_graphs_now()
        self.schedule_graph_redraw()

    def _on_layer_drag_motion(self, event):
        drag = getattr(self, "_layer_drag", None)
        if not drag:
            return
        ti = int(drag.get("ti", -1))
        if self._is_test_locked(ti):
            return
        boundary = int(drag.get("boundary", 0))
        if ti < 0 or ti >= len(self.tests):
            return
        depth = self._canvas_y_to_depth(self.canvas.canvasy(event.y))
        if depth is None:
            return
        t = self.tests[ti]
        layers = [layer_from_dict(layer_to_dict(x)) for x in self._ensure_test_layers(t)]
        try:
            t.layers = move_layer_boundary(layers, boundary, depth)
            self._calc_layer_params_for_test(int(ti))
            snapped_depth = float(t.layers[boundary].top_m) if 0 <= boundary < len(t.layers) else float(depth)
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
                    self._sync_layers_panel()
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
        if kind in ("lock", "edit", "dup", "trash"):
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
        elif kind in ("layer_boundary", "layer_plus", "layer_plus_top", "layer_plus_bottom", "layer_minus", "layer_minus_top", "layer_minus_bottom", "layer_boundary_depth_edit"):
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
        self.flags = {tt.tid: self.flags.get(tt.tid, TestFlags(False, set(), set(), set(), set(), set())) for tt in self.tests}
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
        fl = self.flags.get(getattr(src, "tid", None), TestFlags(False, set(), set(), set(), set(), set()))
        try:
            self.flags[new_id] = TestFlags(bool(getattr(fl, 'invalid', False)), set(getattr(fl, 'interp_cells', set()) or set()), set(getattr(fl, 'force_cells', set()) or set()), set(getattr(fl, 'user_cells', set()) or set()), set(getattr(fl, 'algo_cells', set()) or set()), set(getattr(fl, 'force_tail_rows', set()) or set()))
        except Exception:
            try:
                self.flags[new_id] = TestFlags(False, set(), set(), set(), set(), set())
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
        col_w = self._table_col_width()
        x0 = self._column_x0(col)
        y0 = self.pad_y
        x1 = x0 + col_w
        y1 = y0 + self.hdr_h
        return x0, y0, x1, y1


    def _redraw(self):
        # два холста: hcanvas (фиксированная шапка) + canvas (данные)
        try:
            self.canvas.delete("all")
        except Exception:
            pass
        try:
            self.hcanvas.delete("all")
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

        for col, ti in enumerate(self.display_cols):
            t = self.tests[ti]
            x0, y0, x1, y1 = self._header_bbox(col)

            # checked = will be exported
            ex_on = bool(getattr(t, "export_on", True))
            hdr_fill = GUI_HDR if ex_on else "#f2f2f2"
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
                                     text=f"Опыт {t.tid}", font=("Segoe UI", 9, "bold"), fill=hdr_text)
            if dt_line:
                self.hcanvas.create_text(title_x, row_center_y + 18, anchor="w",
                                         text=dt_line, font=("Segoe UI", 9), fill=hdr_text)

            # header actions (Win11-like icons + hover)
            ico_y = y0 + 14
            ico_font = _pick_icon_font(12)

            lock_on = bool(getattr(t, "locked", False))
            lock_x, edit_x, dup_x, trash_x = (x1 - 92), (x1 - 66), (x1 - 40), (x1 - 14)
            box_w, box_h = 22, 20

            # hover background (только для иконок, не для галочки)
            if getattr(self, "_hover", None) == ("lock", ti):
                self.hcanvas.create_rectangle(lock_x - box_w/2, ico_y - box_h/2, lock_x + box_w/2, ico_y + box_h/2,
                                              fill="#e9e9e9", outline="")
            if getattr(self, "_hover", None) == ("edit", ti):
                self.hcanvas.create_rectangle(edit_x - box_w/2, ico_y - box_h/2, edit_x + box_w/2, ico_y + box_h/2,
                                              fill="#e9e9e9", outline="")
            if getattr(self, "_hover", None) == ("dup", ti):
                self.hcanvas.create_rectangle(dup_x - box_w/2, ico_y - box_h/2, dup_x + box_w/2, ico_y + box_h/2,
                                              fill="#e9e9e9", outline="")
            if getattr(self, "_hover", None) == ("trash", ti):
                self.hcanvas.create_rectangle(trash_x - box_w/2, ico_y - box_h/2, trash_x + box_w/2, ico_y + box_h/2,
                                              fill="#e9e9e9", outline="")

            self.hcanvas.create_text(lock_x, ico_y, text=("🔒" if lock_on else "🔓"), font=("Segoe UI", 10), fill=hdr_icon, anchor="center")
            self.hcanvas.create_text(edit_x, ico_y, text=ICON_CALENDAR, font=ico_font, fill=hdr_icon, anchor="center")
            self.hcanvas.create_text(dup_x, ico_y, text=ICON_COPY, font=ico_font, fill=hdr_icon, anchor="center")
            self.hcanvas.create_text(trash_x, ico_y, text=ICON_DELETE, font=ico_font, fill=hdr_icon, anchor="center")

            # колонка заголовков (H/qc/fs) — в шапке и фиксирована
            sh_y = y0 + self.hdr_h - top_pad
            self.hcanvas.create_text(x0 + self.w_depth / 2, sh_y, text="H, м", font=("Segoe UI", 9), fill=hdr_text)
            self.hcanvas.create_text(x0 + self.w_depth + self.w_val / 2, sh_y, text="qc", font=("Segoe UI", 9), fill=hdr_text)
            self.hcanvas.create_text(x0 + self.w_depth + self.w_val + self.w_val / 2, sh_y, text="fs", font=("Segoe UI", 9), fill=hdr_text)
            if getattr(self, "geo_kind", "K2") == "K4":
                self.hcanvas.create_text(x0 + self.w_depth + self.w_val*2 + self.w_val/2, sh_y, text="U", font=("Segoe UI", 9), fill=hdr_text)

            # --- ТАБЛИЦА (canvas) ---
            fl = self.flags.get(t.tid, TestFlags(False, set(), set(), set(), set(), set()))
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
                has_row = (data_i is not None) and (data_i < len(getattr(t, "qc", []) or []))
                qc_txt = str(t.qc[data_i]) if has_row else ""
                fs_txt = str(t.fs[data_i]) if has_row else ""
                incl_txt = ""
                if getattr(self, "geo_kind", "K2") == "K4":
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
                    if getattr(self, "geo_kind", "K2") == "K4":
                        incl_txt = ""

                # K4: если канал инклинометра отсутствует/пустой — показываем 0
                if getattr(self, "geo_kind", "K2") == "K4":
                    try:
                        if has_row and (incl_txt is None or str(incl_txt).strip() == ""):
                            incl_txt = "0"
                    except Exception:
                        pass


                is_blank_row = (qc_txt.strip()=="" and fs_txt.strip()=="" and (incl_txt.strip()=="" if getattr(self, "geo_kind", "K2")=="K4" else True))

                if not has_row and not is_meter_row:
                    depth_txt = ""

                # Если строка данных пустая (оба значения пустые) — скрываем глубину напротив,
                # но во время редактирования показываем глубину (чтобы было понятно, куда вводим).
                _is_editing_this = False
                try:
                    ed = getattr(self, '_editing', None)
                    if ed and len(ed) >= 3:
                        ed_ti, ed_row, _ed_field = ed[0], ed[1], ed[2]
                        if ed_ti == ti and data_i is not None and ed_row == data_i:
                            _is_editing_this = True
                except Exception:
                    _is_editing_this = False
                if has_row and is_blank_row and not _is_editing_this and not is_meter_row:
                    depth_txt = ""


                if is_meter_row:
                    depth_fill = "#f3f6fb"
                elif has_row and int(data_i) == 0:
                    depth_fill = "white"   # editable cell (только абсолютная первая data-row)
                else:
                    depth_fill = (GUI_DEPTH_BG if has_row else "white")

                if not depth_txt:
                    depth_fill = "white"
                if fl.invalid and has_row:
                    depth_fill = GUI_RED

                def fill_for(kind: str):
                    # Некорректный опыт перекрывает остальные статусы/marks.
                    if fl.invalid and has_row:
                        return GUI_RED
                    # Сначала — специальные подсветки, которые могут относиться к "пустым" строкам (хвост).
                    if data_i in getattr(fl, 'force_tail_rows', set()) and kind in ('depth','qc','fs','incl'):
                        return (GUI_BLUE_P if getattr(self, '_algo_preview_mode', False) else GUI_BLUE)

                    # Далее — обычная логика по существующим/пустым строкам
                    if is_meter_row:
                        return "#f3f6fb"
                    if not has_row or is_blank_row:
                        return "white"

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
                if getattr(self, "geo_kind", "K2") == "K4":
                    cells.append(("incl", incl_txt, fill_for("incl")))

                for field, txt, fill in cells:
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

        col_w = self._table_col_width()

        if w is getattr(self, "hcanvas", None):
            cx = self.hcanvas.canvasx(x)
            cy = self.hcanvas.canvasy(y)
            y0 = self.pad_y  # верхний отступ внутри шапки

            self._refresh_display_order()
            for col, ti in enumerate(self.display_cols):
                x0 = self._column_x0(col)
                x1 = x0 + col_w
                if x0 <= cx <= x1 and (y0 <= cy <= y0 + self.hdr_h):
                    # export checkbox (left)
                    if (x0 + 6) <= cx <= (x0 + 20) and (y0 + 8) <= cy <= (y0 + 22):
                        return ("export", ti, None, None)
                    # icons
                    if (x1 - 104) <= cx <= (x1 - 80) and y0 <= cy <= (y0 + 24):
                        return ("lock", ti, None, None)
                    if (x1 - 78) <= cx <= (x1 - 54) and y0 <= cy <= (y0 + 24):
                        return ("edit", ti, None, None)
                    if (x1 - 52) <= cx <= (x1 - 28) and y0 <= cy <= (y0 + 24):
                        return ("dup", ti, None, None)
                    if (x1 - 26) <= cx <= (x1 - 2) and y0 <= cy <= (y0 + 24):
                        return ("trash", ti, None, None)
                    return ("header", ti, None, None)
            return None

        # --- таблица (числа) ---
        cx = self.canvas.canvasx(x)
        cy = self.canvas.canvasy(y)

        for hit in (getattr(self, "_layer_depth_box_hitbox", []) or []):
            bx0, by0, bx1, by1 = hit.get("bbox", (0, 0, 0, 0))
            if bx0 <= cx <= bx1 and by0 <= cy <= by1:
                return ("layer_boundary_depth_edit", int(hit.get("ti", -1)), int(hit.get("boundary", 0)), None)

        for hit in (getattr(self, "_layer_handle_hitbox", []) or []):
            bx0, by0, bx1, by1 = hit.get("bbox", (0, 0, 0, 0))
            if bx0 <= cx <= bx1 and by0 <= cy <= by1:
                if hit.get("kind") == "boundary":
                    return ("layer_boundary", int(hit.get("ti", -1)), int(hit.get("boundary", 0)), None)
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
        for col, ti in enumerate(self.display_cols):
            x0 = self._column_x0(col)
            x1 = x0 + col_w
            if x0 <= cx <= x1:
                # which field
                # depth/qc/fs split
                relx = cx - x0
                if relx < self.w_depth:
                    field = "depth"
                elif relx < (self.w_depth + self.w_val):
                    field = "qc"
                else:
                    field = "fs"
                if bool(getattr(self, "compact_1m", False)):
                    meter_n = (getattr(self, "_grid_meter_rows", {}) or {}).get(row)
                    if meter_n is not None:
                        # В свернутом meter-row интерактивна только depth-ячейка (toggle).
                        if field == "depth":
                            return ("meter_row", ti, row, int(meter_n))
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
            # Клик по пустой строке ниже конца зондирования: добавляем строку и даём ввод
            if field in ("qc", "fs"):
                new_idx = len(self.tests[ti].qc)
                self._append_row(ti)
                self._begin_edit(ti, new_idx, field, display_row=row)
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
                self.canvas.xview_moveto(float(xview_before[0]))
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

        # ---- № ----
        ttk.Label(win, text="№ зондирования").grid(row=0, column=0, sticky="w", padx=PADX, pady=(PADY, 2))
        tid_var = tk.StringVar(master=self, value=str(t.tid))
        tid_entry = ttk.Entry(
            win,
            textvariable=tid_var,
            width=10,
            validate="key",
            validatecommand=(win.register(_validate_tid_key), "%P"),
        )
        tid_entry.grid(row=0, column=1, sticky="w", padx=(0, PADX), pady=(PADY, 2), columnspan=2)

        # ---- Date + Time ----
        ttk.Label(win, text="Дата").grid(row=1, column=0, sticky="w", padx=PADX, pady=2)

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
        date_entry.grid(row=1, column=1, sticky="w", padx=(0, 6), pady=2)

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
        cal_btn.grid(row=1, column=2, sticky="w", padx=(0, PADX), pady=2)

        ttk.Label(win, text="Время").grid(row=2, column=0, sticky="w", padx=PADX, pady=2)

        time_frame = ttk.Frame(win)
        time_frame.grid(row=2, column=1, columnspan=2, sticky="w", padx=(0, PADX), pady=2)

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
            old_tid = t.tid
            t.tid = new_tid
            dt_obj = _try_parse_dt(dt_text)
            t.dt = dt_obj.strftime("%Y-%m-%d %H:%M:%S") if dt_obj else dt_text

            if old_tid in self.flags:
                self.flags[new_tid] = self.flags.pop(old_tid)
            else:
                self.flags[new_tid] = TestFlags(False, set(), set(), set(), set(), set())

            self._redraw()
            win.destroy()

        # Enter = сохранить
        for _w in (tid_entry, hh_entry, mm_entry):
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
        btns.grid(row=3, column=0, columnspan=3, sticky="ew", padx=12, pady=(8, 12))
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



    def _begin_edit(self, ti: int, row: int, field: str, display_row: int | None = None):
        """Edit qc/fs cell. row is data index, display_row is grid index."""
        if self._is_test_locked(int(ti)):
            self._set_status("Опыт заблокирован")
            return
        self._end_edit(commit=True)
        t = self.tests[ti]
        # Не даём вводить значения "после конца" зондирования.
        if row < 0 or row >= len(t.qc):
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

        self._refresh_display_order()
        col = self.display_cols.index(ti)

        # Автопрокрутка (стрелки/Enter): держим ячейку в видимой зоне
        self._ensure_cell_visible(col, display_row, field)

        bx0, by0, bx1, by1 = self._cell_bbox(col, display_row, field)
        vx0 = bx0 - self.canvas.canvasx(0)
        vy0 = by0 - self.canvas.canvasy(0)

        current = t.qc[row] if field == "qc" else t.fs[row]
        e = tk.Entry(self.canvas, validate="key", validatecommand=(self.register(_validate_int_0_300_key), "%P"))
        e.insert(0, current)
        try:
            e.configure(bg="white")
        except Exception:
            pass
        e.select_range(0, tk.END)
        e.place(x=vx0 + 1, y=vy0 + 1, width=(bx1 - bx0) - 2, height=(by1 - by0) - 2)
        e.focus_set()

        def commit_and_next():
            self._end_edit(commit=True)

            # Enter: вниз. Если дошли до конца — добавляем новую строку и продолжаем ввод.
            next_row = row + 1
            if next_row < len(t.qc):
                self._begin_edit(ti, next_row, field, (display_row or row) + 1)
            else:
                # добавляем новую строку в хвост и начинаем редактирование
                self._append_row(ti)
                try:
                    self._begin_edit(ti, next_row, field, (display_row or row) + 1)
                except Exception:
                    pass

        e.bind("<Return>", lambda _ev: commit_and_next())
        for _k in ("<Up>","<Down>","<Left>","<Right>"):
            e.bind(_k, self._on_arrow_key)
        e.bind("<Escape>", lambda _ev: self._end_edit(commit=False))
        e.bind("<FocusOut>", lambda _ev: self._end_edit(commit=True))

        self._editing = (ti, row, field, e, display_row)

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
        col = self.display_cols.index(ti)

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
    def _end_edit(self, commit: bool):
        if not self._editing:
            return
        if len(self._editing) == 4:
            ti, row, field, e = self._editing
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
        self._editing = None

        if field == "depth":
            self._redraw()
            self.schedule_graph_redraw()
            return

        if commit and self.tests:
            t = self.tests[ti]
            if row < len(t.qc):
                # keep previous coloring info, but mark this cell as manually edited (purple)
                fl = self.flags.get(t.tid) or TestFlags(False, set(), set(), set(), set(), set())
                old = t.qc[row] if field == 'qc' else t.fs[row]
                newv = _sanitize_int_0_300(val)
                # Undo: фиксируем снимок ДО изменения данных/раскраски
                if commit:
                    try:
                        # если реально меняем значение или удаляем строку
                        if (str(old).strip() != str(newv).strip()):
                            self._push_undo()
                    except Exception:
                        self._push_undo()
                # Запрет: в середине зондирования нельзя ставить 0 или оставлять пусто.
                # Пустое значение разрешено только на краях (первая/последняя строка) — тогда удаляем строку целиком.
                last_filled_before = self._last_filled_row(t)

                # edge-delete when clearing first/last filled row
                if newv.strip() == "":
                    if row == 0 or row == last_filled_before:
                        # удалить строку данных и глубину
                        fl = self.flags.get(t.tid) or TestFlags(False, set(), set(), set(), set(), set())
                        self._delete_data_row_in_test(t, fl, row)
                        self.flags[t.tid] = fl
                        self._redraw()
                        self.schedule_graph_redraw()
                        return
                    else:
                        self.status.config(text="Нельзя оставлять пустые значения в середине зондирования.")
                        self._redraw()
                        self.schedule_graph_redraw()
                        return

                if newv.strip() == "0" and (0 < row < last_filled_before):
                    self.status.config(text="Нельзя записывать 0 в середине зондирования.")
                    self._redraw()
                    return
                if field == 'qc':
                    t.qc[row] = newv
                else:
                    t.fs[row] = newv
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
        try:
            n = min(len(getattr(t, 'qc', []) or []), len(getattr(t, 'fs', []) or []))
        except Exception:
            return -1
        for i in range(n - 1, -1, -1):
            if str(t.qc[i]).strip() != "" or str(t.fs[i]).strip() != "":
                return i
        return -1


    def _delete_data_row_in_test(self, t: TestData, fl: TestFlags, row: int):
        """Удаляет строку row из depth/qc/fs и корректирует раскраски (interp/force/user)."""
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
            self.flags[t.tid] = TestFlags(False, set(), set(), set(), set(), set())
        self._redraw()
        self.schedule_graph_redraw()

    # ---------------- scrolling ----------------
    def _on_mousewheel(self, event):
        # скролл закрывает активную ячейку
        self._end_edit(commit=True)
        delta = int(-1 * (event.delta / 120)) if event.delta else 0
        if delta != 0:
            self.canvas.yview_scroll(delta, "units")
            self._sync_header_body_after_scroll()
        return "break"

    def _on_mousewheel_linux(self, direction):
        # скролл закрывает активную ячейку
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
        self._end_edit(commit=True)
        try:
            direction = int(direction)
        except Exception:
            direction = 0
        if not direction:
            return "break"
        self._scroll_x_by_one_column(direction)
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
    def _choose_tail_k(self, last_val: int) -> int:
        d = abs(250 - last_val)
        if d <= 10:
            return 1
        if d <= 35:
            return 2
        return 3

    def fix_by_algorithm(self):
        if not self.tests:
            return

        self._push_undo()
        random.seed(42)
        tail_fill_cells: list[dict] = []

        for t in self.tests:
            tid = t.tid
            prev_flags = self.flags.get(tid) or TestFlags(False, set(), set(), set(), set(), set())
            _prev_user_cells = set(getattr(prev_flags, 'user_cells', set()) or set())
            # Снимок значений до автокорректировки (для зелёной подсветки)
            _orig_qc = list(getattr(t, 'qc', []) or [])
            _orig_fs = list(getattr(t, 'fs', []) or [])
            _orig_depth = list(getattr(t, 'depth', []) or [])
            algo_cells: set[tuple[int, str]] = set()
            n = len(t.qc)
            if n == 0:
                # сохраняем пользовательские правки (на случай пустого зондирования)
                self.flags[tid] = TestFlags(False, set(), set(), _prev_user_cells, algo_cells, set())
                continue

            qc = [(_parse_cell_int(v) or 0) for v in t.qc]
            fs = [(_parse_cell_int(v) or 0) for v in t.fs]

            invalid = (_max_zero_run(qc) > 5) or (_max_zero_run(fs) > 5)
            interp_cells: set[tuple[int, str]] = set(getattr(prev_flags, 'interp_cells', set()) or set())
            force_cells: set[tuple[int, str]] = set(getattr(prev_flags, 'force_cells', set()) or set())

            if invalid:
                self.flags[tid] = TestFlags(True, interp_cells, force_cells, _prev_user_cells, algo_cells, set())
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

            # --- finish to 250 (choose closer) ---
            # Важно: если в опыте уже был «отказ» (значения доходили/превышали 250),
            # НИЧЕГО не дописываем вниз. Исправляем только нули/пробелы.
            refusal = False
            try:
                mx = max((qc + fs) or [0])
                refusal = (mx >= 250)
            except Exception:
                refusal = False

            if not refusal:
                # добавляем 1–3 строки ниже, не перетирая хвост
                last_filled = -1
                for rr in range(n - 1, -1, -1):
                    if qc[rr] != 0 or fs[rr] != 0:
                        last_filled = rr
                        break
                if last_filled < 0:
                    last_filled = n - 1

                target_kind = "qc" if abs(250 - qc[last_filled]) <= abs(250 - fs[last_filled]) else "fs"
                main_arr = qc if target_kind == "qc" else fs
                other_arr = fs if target_kind == "qc" else qc

                last_main = max(1, main_arr[last_filled])
                last_other = max(1, other_arr[last_filled])

                add_cnt = max(1, min(3, self._choose_tail_k(last_main)))

                step = self.step_m if self.step_m is not None else 0.05
                last_depth = None
                if t.depth and last_filled < len(t.depth):
                    last_depth = _parse_depth_float(t.depth[last_filled])
                if last_depth is None:
                    base = self.depth_start if self.depth_start is not None else 0.0
                    last_depth = base + step * last_filled

                for k_i in range(1, add_cnt + 1):
                    tt = k_i / add_cnt
                    new_main = _interp_with_noise(last_main, 250, tt)
                    new_main = max(last_main, min(250, new_main))
                    if k_i == add_cnt:
                        new_main = 250

                    # второй показатель тоже слегка растёт (примерно 15–25% от прироста main)
                    inc_main = max(0, new_main - last_main)
                    inc_other = max(1, int(round(inc_main * 0.22))) if inc_main > 0 else 1
                    new_other = min(250, max(last_other, _noise_around(last_other + inc_other)))

                    # добавляем строку
                    qc.append(0); fs.append(0)
                    t.qc.append(""); t.fs.append(""); t.depth.append("")
                    n += 1

                    if target_kind == "qc":
                        qc[-1] = int(new_main); fs[-1] = int(new_other)
                        force_cells.add((n - 1, "qc")); force_cells.add((n - 1, "fs"))
                    else:
                        fs[-1] = int(new_main); qc[-1] = int(new_other)
                        force_cells.add((n - 1, "fs")); force_cells.add((n - 1, "qc"))

                    dd = last_depth + step * k_i
                    t.depth[-1] = f"{dd:.2f}"
                    tail_fill_cells.append({"testId": int(getattr(t, "tid", 0) or 0), "depthM": round(float(dd), 3), "field": "qc", "before": "", "after": str(int(qc[-1]))})
                    tail_fill_cells.append({"testId": int(getattr(t, "tid", 0) or 0), "depthM": round(float(dd), 3), "field": "fs", "before": "", "after": str(int(fs[-1]))})
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
                # если хвост добавлен — помечаем его целиком (qc/fs)
                if len(t.qc) > len(_orig_qc):
                    for i2 in range(len(_orig_qc), len(t.qc)):
                        if (i2, "qc") not in _prev_user_cells:
                            algo_cells.add((i2, "qc"))
                        if (i2, "fs") not in _prev_user_cells:
                            algo_cells.add((i2, "fs"))
            except Exception:
                pass

            self.flags[tid] = TestFlags(False, interp_cells, force_cells, _prev_user_cells, algo_cells, set())

        try:
            changes = []
            for t in self.tests:
                fl = self.flags.get(getattr(t, "tid", 0))
                for row, fld in sorted(list(getattr(fl, "algo_cells", set()) or set())):
                    changes.append({"testId": int(getattr(t, "tid", 0) or 0), "row": int(row), "field": fld, "depthM": self._safe_depth_m(t, row), "mark": {"reason": "algo_fix", "color": "green"}})
            if changes:
                self.project_ops.append(op_algo_fix_applied(changes=changes))
            if tail_fill_cells:
                self.project_ops.append(op_cells_marked(reason="tail_fill", color="blue", cells=tail_fill_cells))
            if changes or tail_fill_cells:
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
            scale_div = int(float(self.scale_var.get().replace(",", ".")))
            fmax_cone_kn = float(self.fcone_var.get().replace(",", "."))
            fmax_sleeve_kn = float(self.fsleeve_var.get().replace(",", "."))
            area_cone_cm2 = float(self.acon_var.get().replace(",", "."))
            area_sleeve_cm2 = float(self.asl_var.get().replace(",", "."))
            if scale_div <= 0:
                raise ValueError("Шкала делений должна быть > 0")
            if fmax_cone_kn <= 0 or fmax_sleeve_kn <= 0:
                raise ValueError("Диапазоны калибровки должны быть > 0")
            if area_cone_cm2 <= 0 or area_sleeve_cm2 <= 0:
                raise ValueError("Площади должны быть > 0")
            return scale_div, fmax_cone_kn, fmax_sleeve_kn, area_cone_cm2, area_sleeve_cm2
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
            fl = self.flags.get(tid) or TestFlags(False, set(), set(), set(), set(), set())
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
        ttk.Radiobutton(frm, text="СП 446.1325800.2019 (Приложение Ж)", variable=method_var, value=METHOD_SP446).pack(anchor="w")
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
            dlg.title("Расчёт CPT: нужны дополнительные данные")
        else:
            dlg.title("Расчёт CPT: готово")
        dlg.transient(self)
        dlg.grab_set()
        frm = ttk.Frame(dlg, padding=10)
        frm.pack(fill="both", expand=True)
        if missing:
            ttk.Label(frm, text="Для части ИГЭ не хватает данных. Заполните параметры и повторите расчёт:", foreground="#8a3d00").pack(anchor="w")
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
        A_cone = _cm2_to_m2(area_cone_cm2)
        A_sleeve = _cm2_to_m2(area_sleeve_cm2)

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
                    if qc_del is not None and A_cone:
                        F_cone_N = (qc_del / scale_div) * (fmax_cone_kn * 1000.0)
                        qc_MPa = (F_cone_N / A_cone) / 1e6
                    if fs_del is not None and A_sleeve:
                        F_sleeve_N = (fs_del / scale_div) * (fmax_sleeve_kn * 1000.0)
                        fs_kPa = (F_sleeve_N / A_sleeve) / 1e3

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
            x0, y0, x1, y1 = self._header_bbox(max(0, int(ti)))
            # учесть прокрутку canvas (canvas coords -> screen coords)
            vx = self.canvas.canvasx(0)
            vy = self.canvas.canvasy(0)
            sx = self.canvas.winfo_rootx() + int(x0 - vx) + 10
            sy = self.canvas.winfo_rooty() + int(y0 - vy) + 10
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


    def _project_settings_from_ui(self) -> ProjectSettings:
        extras = {"cpt_calc_settings": dict(getattr(self, "cpt_calc_settings", {}) or {})}
        scale_val = (self.scale_var.get().strip() if hasattr(self, "scale_var") else "250") or "250"
        fcone_val = (self.fcone_var.get().strip() if hasattr(self, "fcone_var") else "30") or "30"
        fsleeve_val = (self.fsleeve_var.get().strip() if hasattr(self, "fsleeve_var") else "10") or "10"
        acon_val = (self.acon_var.get().strip() if hasattr(self, "acon_var") else "10") or "10"
        asleeve_val = (self.asl_var.get().strip() if hasattr(self, "asl_var") else "350") or "350"
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
            status_now = self._compute_footer_realtime()
        except Exception:
            status_now = {}
        no_ref = int(status_now.get("no_ref", 0) or 0)
        miss = int(status_now.get("miss", 0) or 0)
        invalid = int(status_now.get("inv", 0) or 0)
        return (
            f"Проект открыт: ops={self._marks_ops_count}, marks_total={self._marks_built_count}, "
            f"marks_green={self._marks_color_counts.get('green', 0)}, "
            f"marks_purple={self._marks_color_counts.get('purple', 0)}, "
            f"marks_blue={self._marks_color_counts.get('blue', 0)}, "
            f"marks_orange={self._marks_color_counts.get('orange', 0)}, "
            f"подсвечено_marks={self._marks_applied_count}, статус_синий={no_ref}, "
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
        self.project_ops = list(project.ops or [])
        self.original_bytes = source_bytes
        self.geo_path = Path(project.source.filename) if (project.source and project.source.filename) else None
        self.loaded_path = str(self.geo_path) if self.geo_path else str(path)
        src_kind = str((project.source.kind if project.source else "") or "").strip().upper()
        self.is_gxl = (src_kind == "GXL")
        src_ext = str((project.source.ext if project.source else "") or "").strip().lower()
        self._restore(project.state or {})
        if src_ext in {"geo", "ge0"}:
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
        if hasattr(self, "scale_var"):
            self.scale_var.set(project.settings.scale)
            self.fcone_var.set(project.settings.fcone)
            self.fsleeve_var.set(project.settings.fsleeve)
            self.acon_var.set(project.settings.acon)
            self.asl_var.set(project.settings.asleeve)
        if hasattr(self, "controller_type_var"):
            self.controller_type_var.set(str(getattr(project.settings, "controller_type", "") or ""))
        if hasattr(self, "probe_type_var"):
            self.probe_type_var.set(str(getattr(project.settings, "probe_type", "") or ""))
        try:
            if str(getattr(project.settings, "controller_scale_div", "") or "").strip() and hasattr(self, "scale_var"):
                self.scale_var.set(str(project.settings.controller_scale_div))
            if str(getattr(project.settings, "cone_kn", "") or "").strip() and hasattr(self, "fcone_var"):
                self.fcone_var.set(str(project.settings.cone_kn))
            if str(getattr(project.settings, "sleeve_kn", "") or "").strip() and hasattr(self, "fsleeve_var"):
                self.fsleeve_var.set(str(project.settings.sleeve_kn))
            if str(getattr(project.settings, "cone_area_cm2", "") or "").strip() and hasattr(self, "acon_var"):
                self.acon_var.set(str(project.settings.cone_area_cm2))
            if str(getattr(project.settings, "sleeve_area_cm2", "") or "").strip() and hasattr(self, "asl_var"):
                self.asl_var.set(str(project.settings.sleeve_area_cm2))
        except Exception:
            pass
        self.cpt_calc_settings = dict((project.settings.extras or {}).get("cpt_calc_settings") or self.cpt_calc_settings or {"method": METHOD_SP446, "alluvial_sands": True, "groundwater_level": None})
        self._dirty = False
        if getattr(self, "ribbon_view", None):
            self.ribbon_view.set_object_name(self.object_name)
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

        ttk.Label(frm, text="Глубина (м):").grid(row=0, column=0, sticky="w", pady=(0, 6))
        depth_var = tk.StringVar(master=self, value="10")
        e_depth = ttk.Entry(frm, textvariable=depth_var, width=12)
        e_depth.grid(row=0, column=1, sticky="w", pady=(0, 6))

        ttk.Label(frm, text="Шаг (м):").grid(row=1, column=0, sticky="w", pady=(0, 6))
        step_var = tk.StringVar(master=self, value="0.10")
        e_step = ttk.Entry(frm, textvariable=step_var, width=12)
        e_step.grid(row=1, column=1, sticky="w", pady=(0, 6))

        incl_var = tk.BooleanVar(master=self, value=True)
        ttk.Checkbutton(
            frm,
            text="Инклинометр при глубине > 10 м",
            variable=incl_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 10))

        result = {"ok": False}

        def _cancel(_evt=None):
            dlg.destroy()

        def _ok(_evt=None):
            try:
                depth_m = float(str(depth_var.get()).replace(",", ".").strip())
                step_m = float(str(step_var.get()).replace(",", ".").strip())
                if depth_m <= 0 or step_m <= 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("Ошибка", "Введите корректные значения глубины и шага.", parent=self)
                return
            result.update(ok=True, depth=depth_m, step=step_m, incl=bool(incl_var.get()))
            dlg.destroy()

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=2, sticky="e")
        ttk.Button(btns, text="Отмена", command=_cancel).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="OK", command=_ok).pack(side="right")

        dlg.bind("<Return>", _ok)
        dlg.bind("<Escape>", _cancel)

        try:
            self._center_child(dlg)
        except Exception:
            pass

        e_depth.focus_set()
        self.wait_window(dlg)

        if not result.get("ok"):
            return

        depth_m = float(result["depth"])
        step_m = float(result["step"])
        with_incl = bool(result["incl"])

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
        self.object_name = ""
        self.object_code = ""
        self.geo_path = None
        self.original_bytes = None
        self.depth_start = 0.0
        self.step_m = step_m
        self.depth0_by_tid = {1: 0.0}

        dt_now = _dt.datetime.now().replace(microsecond=0)
        dt_text = dt_now.strftime("%Y-%m-%d %H:%M:%S")

        depth_vals = []
        cur = 0.0
        guard = 0
        while cur <= depth_m + 1e-9 and guard < 200000:
            depth_vals.append(f"{round(cur, 2):g}")
            cur = round(cur + step_m, 6)
            guard += 1
        if not depth_vals:
            depth_vals = ["0"]

        n = len(depth_vals)
        qc = ["0"] * n
        fs = ["0"] * n

        incl_data = None
        self.geo_kind = "K2"
        if depth_m > 10 and with_incl:
            self.geo_kind = "K4"
            incl_data = ["0"] * n

        self.tests.append(TestData(tid=1, dt=dt_text, depth=depth_vals, qc=qc, fs=fs, incl=incl_data, orig_id=None, block=None))
        self.flags[1] = TestFlags(False, set(), set(), set(), set(), set())

        try:
            self.file_var.set("(шаблон проекта)")
        except Exception:
            pass

        self._dirty = True
        self._recompute_statuses_after_data_load(preview_mode=False)
        if getattr(self, "ribbon_view", None):
            self.ribbon_view.set_object_name(self.object_name)
        self.status.config(text="Создан новый проект-шаблон: 1 опыт")
        self._update_window_title()

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
                        "scale": self.scale_var.get() if hasattr(self, "scale_var") else "",
                        "fcone": self.fcone_var.get() if hasattr(self, "fcone_var") else "",
                        "fsleeve": self.fsleeve_var.get() if hasattr(self, "fsleeve_var") else "",
                        "acon": self.acon_var.get() if hasattr(self, "acon_var") else "",
                        "asleeve": self.asl_var.get() if hasattr(self, "asl_var") else "",
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
        scale = self.scale_var.get().strip() if hasattr(self, "scale_var") else ""
        fcone = self.fcone_var.get().strip() if hasattr(self, "fcone_var") else ""
        fsleeve = self.fsleeve_var.get().strip() if hasattr(self, "fsleeve_var") else ""
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
            f"tests={len([t for t in self.tests if bool(getattr(t, 'export_on', True))])}",
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
            include_only_export_on=True,
        )

    def _export_credo_silent(self, out_zip_path: Path):
        """Тихий экспорт ZIP для CREDO (две CSV на опыт) без диалогов (для экспорта-архива)."""
        import zipfile

        selection = self._collect_export_tests()
        tests_exp = list(selection.tests)
        if not tests_exp:
            # нечего экспортировать
            with zipfile.ZipFile(out_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
                pass
            return

        def fmt_comma(x, nd=2):
            s = f"{x:.{nd}f}"
            return s.replace(".", ",")

        def fmt_depth(x):
            # GeoExplorer/CREDO ожидает глубину с 2 знаками после запятой
            return f"{x:.2f}".replace(".", ",")

        with zipfile.ZipFile(str(out_zip_path), "w", compression=zipfile.ZIP_DEFLATED) as z:
            for t in tests_exp:
                tid = str(getattr(t, "tid", ""))
                qc_lines = []
                fs_lines = []
                depth_arr = getattr(t, "depth", []) or []
                qc_arr = getattr(t, "qc", []) or []
                fs_arr = getattr(t, "fs", []) or []
                n = max(len(depth_arr), len(qc_arr), len(fs_arr))
                for i in range(n):
                    d = _parse_depth_float(depth_arr[i]) if i < len(depth_arr) else None
                    qv = _parse_cell_int(qc_arr[i]) if i < len(qc_arr) else None
                    fv = _parse_cell_int(fs_arr[i]) if i < len(fs_arr) else None
                    if d is None and qv is None and fv is None:
                        continue
                    if d is None:
                        continue
                    if qv is None: qv = 0
                    if fv is None: fv = 0
                    qc_mpa, fs_kpa = self._calc_qc_fs_from_del(int(qv), int(fv))
                    qc_lines.append(f"{fmt_depth(d)};{fmt_comma(qc_mpa, 2)}")
                    fs_lines.append(f"{fmt_depth(d)};{int(round(fs_kpa))}")
                z.writestr(f"СЗ-{tid} лоб.csv", "\n".join(qc_lines))
                z.writestr(f"СЗ-{tid} бок.csv", "\n".join(fs_lines))
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
        scale = (self.scale_var.get().strip() if getattr(self, 'scale_var', None) else '') or '250'
        fcone = (self.fcone_var.get().strip() if getattr(self, 'fcone_var', None) else '') or '30'
        fsleeve = (self.fsleeve_var.get().strip() if getattr(self, 'fsleeve_var', None) else '') or '10'

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

        # шаг
        step_cm = getattr(self, 'step_cm', None)
        step_m_default = 0.10 if step_cm == 10 else (0.05 if step_cm == 5 else 0.10)

        # Сортировка опытов по времени (как в UI)
        tests = list(self.tests)
        try:
            tests = sorted(tests, key=lambda t: (t.dt or ''))
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
    GeoCanvasEditor.save_gxl_generated = save_gxl_generated  # type: ignore[attr-defined]
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
