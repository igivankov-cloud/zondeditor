from __future__ import annotations

# === FILE MAP BEGIN ===
# FILE MAP (обновляй при правках; указывай строки Lx–Ly)
# - _apply_compact_ribbon_height: L109–L126 — вычисление высоты верхней ленты по фактической высоте вкладки «ИГЭ».
# - _build_layers_tab/_sync_ige_canvas: L289–L303, L332–L345 — область ИГЭ без вертикального скролла и с высотой по содержимому.
# - _set_combo_placeholder/_build_dynamic_ige_fields/_build_ige_column: L440–L555 — логика карточек ИГЭ (в т.ч. пустой тип для нового ИГЭ).
# === FILE MAP END ===


import tkinter as tk
from tkinter import ttk, simpledialog

from src.zondeditor.calculations.ige_policy import get_ige_profile
from src.zondeditor.ui.consts import ICON_REDO, ICON_SAVE, ICON_UNDO, ICON_TRASH
from src.zondeditor.ui.widgets import ToolTip


class RibbonView(ttk.Frame):
    def __init__(self, master, *, commands: dict[str, callable], icon_font=None):
        super().__init__(master)
        self.commands = commands
        self.icon_font = icon_font
        self.object_name_var = tk.StringVar(value="")
        self.controller_type_var = tk.StringVar(value="")
        self.controller_scale_div_var = tk.StringVar(value="250")
        self.probe_type_var = tk.StringVar(value="")
        self.cone_kn_var = tk.StringVar(value="30")
        self.sleeve_kn_var = tk.StringVar(value="10")
        self.cone_area_cm2_var = tk.StringVar(value="10")
        self.sleeve_area_cm2_var = tk.StringVar(value="350")
        self.show_graphs_var = tk.BooleanVar(value=False)
        self.show_geology_var = tk.BooleanVar(value=False)
        self.show_inclinometer_var = tk.BooleanVar(value=False)
        self.show_layer_colors_var = tk.BooleanVar(value=False)
        self.show_layer_hatching_var = tk.BooleanVar(value=False)
        self.compact_1m_var = tk.BooleanVar(value=False)
        self.display_sort_var = tk.StringVar(value="date")
        self.layers_edit_var = tk.BooleanVar(value=False)
        self.layer_soil_var = tk.StringVar(value="")
        self.layer_mode_var = tk.StringVar(value="")
        self.layer_ige_var = tk.StringVar(value="ИГЭ-1")
        self._buttons: dict[str, ttk.Button] = {}
        self._layer_rows: list[dict] = []
        self._ige_controls: dict[str, ttk.Combobox] = {}
        self._layer_delete_buttons: dict[str, ttk.Button] = {}
        self._layer_add_enabled = True
        self._ige_cards: dict[str, ttk.Frame] = {}
        self._ige_rows_cache: dict[str, dict] = {}
        self._ige_soil_values: list[str] = []
        self._add_ige_btn = None
        self._ige_order: list[str] = []
        self.calc_cpt_method_var = tk.StringVar(value="СП 446.1325800.2019 (с Изм. № 1), приложение Ж")
        self.calc_transition_method_var = tk.StringVar(value="СП 22.13330.2016 (с Изм. № 1–5), п. 5.3.17")
        self.calc_allow_normative_lt6_var = tk.BooleanVar(value=False)
        self.calc_legacy_sandy_loam_var = tk.BooleanVar(value=False)
        self.calc_fill_preliminary_var = tk.BooleanVar(value=False)
        self._suspend_common_emit = False
        self.project_type_mode = ""
        self.installation_name_var = tk.StringVar(value="")
        self.step_depth_var = tk.StringVar(value="0.05")
        self.mech_lob_coeff_var = tk.StringVar(value="1.00")
        self.mech_total_coeff_var = tk.StringVar(value="1.00")
        self.mech_calib_date_var = tk.StringVar(value="")
        self.mech_calib_note_var = tk.StringVar(value="")

        try:
            style = ttk.Style(self)
            style.configure("RibbonCompact.TButton", padding=(4, 1))
            style.configure("RibbonFileLeft.TButton", padding=(4, 1), anchor="w")
            style.configure("IGEHdr.TButton", padding=(3, 1))
        except Exception:
            pass

        qat = ttk.Frame(self, padding=(4, 1))
        qat.pack(side="top", fill="x")
        self._add_qat_btn(qat, "undo", ICON_UNDO, "Undo")
        self._add_qat_btn(qat, "redo", ICON_REDO, "Redo")
        self._add_qat_btn(qat, "save_project", ICON_SAVE, "Сохранить проект")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(side="top", fill="x", padx=2, pady=(0, 2))
        self.tabs.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._build_file_tab()
        self._build_params_tab()
        self._build_view_tab()
        self._build_layers_tab()
        self._build_calc_tab()
        self._build_protocol_tab()
        self.after_idle(self._apply_compact_ribbon_height)

    def _add_qat_btn(self, parent, key: str, text: str, tip: str):
        btn = ttk.Button(parent, text=text, width=3, command=self.commands.get(key))
        if self.icon_font:
            try:
                style = ttk.Style(btn)
                style.configure('Zond.QAT.TButton', font=self.icon_font)
                btn.configure(style='Zond.QAT.TButton')
            except Exception:
                pass
        btn.pack(side="left", padx=2)
        ToolTip(btn, tip)
        self._buttons[key] = btn

    def _add_btn(self, parent, key: str, text: str, tip: str, *, width: int = 12, style: str = "RibbonCompact.TButton"):
        btn = ttk.Button(parent, text=text, command=self.commands.get(key), style=style, width=width)
        btn.pack(side="top", fill="x", anchor="w", pady=1)
        ToolTip(btn, tip)
        self._buttons[key] = btn

    def _add_btn_grid(self, parent, key: str, text: str, tip: str, row: int, col: int):
        btn = ttk.Button(parent, text=text, command=self.commands.get(key), style="RibbonCompact.TButton", width=12)
        btn.grid(row=row, column=col, sticky="ew", padx=2, pady=1)
        ToolTip(btn, tip)
        self._buttons[key] = btn

    def _apply_compact_ribbon_height(self):
        params_tab = getattr(self, "_params_tab", None)
        if params_tab is None:
            return
        try:
            self.update_idletasks()
            params_h = int(params_tab.winfo_reqheight()) + 10
        except Exception:
            return
        ige_h = 0
        try:
            ige_host = getattr(self, "_ige_columns_frame", None)
            if ige_host is not None:
                ige_h = int(ige_host.winfo_reqheight()) + 14
        except Exception:
            ige_h = 0
        target_h = max(params_h, ige_h, 130)
        target_h = min(target_h, 196)
        try:
            self.tabs.configure(height=target_h)
        except Exception:
            pass

    def _build_file_tab(self):
        tab = ttk.Frame(self.tabs, padding=2)
        self.tabs.add(tab, text="Файл")
        file_group_width_px = 190
        file_btn_width = 16

        project = ttk.LabelFrame(tab, text="Проект", padding=3)
        project.pack(side="left", fill="y", anchor="nw", padx=(4, 8))
        project.configure(width=file_group_width_px)
        project.pack_propagate(False)
        self._add_btn(project, "new_project", "🆕 Создать проект", "Создать новый проект", width=file_btn_width, style="RibbonFileLeft.TButton")
        self._add_btn(project, "open_project", "📂 Открыть проект", "Открыть *.zproj", width=file_btn_width, style="RibbonFileLeft.TButton")
        self._add_btn(project, "save_project", "💾 Сохранить", "Сохранить *.zproj", width=file_btn_width, style="RibbonFileLeft.TButton")
        self._add_btn(project, "save_project_as", "💾 Сохранить как", "Сохранить *.zproj как новый", width=file_btn_width, style="RibbonFileLeft.TButton")

        imports = ttk.LabelFrame(tab, text="Импорт", padding=3)
        imports.pack(side="left", fill="y", anchor="nw", padx=8)
        imports.configure(width=file_group_width_px)
        imports.pack_propagate(False)
        self._add_btn(imports, "open_geo", "GEO", "Открыть GEO/GE0", width=file_btn_width)
        self._add_btn(imports, "open_gxl", "GXL", "Открыть GXL", width=file_btn_width)
        self._add_btn(imports, "export_excel", "Excel", "Импорт данных из Excel", width=file_btn_width)

        exports = ttk.LabelFrame(tab, text="Экспорт", padding=3)
        exports.pack(side="left", fill="y", anchor="nw", padx=(8, 4))
        exports.configure(width=file_group_width_px)
        exports.pack_propagate(False)
        self._add_btn(exports, "export_geo", "GEO", "Экспорт GEO только через Сохранить как", width=file_btn_width)
        self._add_btn(exports, "export_gxl", "GXL", "Экспорт GXL только через Сохранить как", width=file_btn_width)
        self._add_btn(exports, "export_dxf", "DXF / DWG", "Экспорт графиков в CAD (DXF / DWG)", width=file_btn_width)

    def _build_params_tab(self):
        tab = ttk.Frame(self.tabs, padding=4)
        self.tabs.add(tab, text="Параметры")
        self._params_tab = tab
        layout = ttk.Frame(tab)
        layout.pack(side="top", anchor="w")
        self._params_mode_host = ttk.Frame(layout)
        self._params_mode_host.pack(side="left", anchor="nw")
        actions = ttk.Frame(layout)
        actions.pack(side="left", anchor="nw", padx=(10, 0))
        self._add_btn(
            actions,
            "fix_algo",
            "Интерполировать отсутствующие значения",
            "Автоматическая корректировка",
            width=38,
        )
        self._render_params_by_project_type(self.project_type_mode)

    def _build_empty_params_state(self, parent):
        holder = ttk.Frame(parent, padding=(8, 12))
        holder.pack(side="top", fill="x")
        ttk.Label(holder, text="Проект не выбран").pack(side="top", anchor="w")
        ttk.Label(
            holder,
            text="Создайте новый проект или откройте существующий файл",
            foreground="#5f6b7a",
        ).pack(side="top", anchor="w", pady=(2, 0))

    def _build_type2_params_form(self, parent):
        common = ttk.LabelFrame(parent, text="Параметры — Тип 2 (электрический)", padding=4)
        common.pack(side="top", fill="x")

        common_left = ttk.Frame(common)
        common_left.pack(side="left", anchor="w", padx=(8, 0))

        col_left = ttk.Frame(common_left)
        col_right = ttk.Frame(common_left)
        col_left.grid(row=0, column=0, sticky="nw", padx=(0, 16))
        col_right.grid(row=0, column=1, sticky="nw")

        self._common_param_entries: dict[str, ttk.Entry] = {}

        def add_field(parent, row: int, label: str, var: tk.StringVar, key: str, width: int = 14):
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 4), pady=1)
            ent = ttk.Entry(parent, textvariable=var, width=width)
            ent.grid(row=row, column=1, sticky="w", pady=1)
            ent.bind("<FocusOut>", lambda _e: self._emit_common_params())
            ent.bind("<Return>", lambda _e: self._emit_common_params())
            self._common_param_entries[key] = ent

        add_field(col_left, 0, "Шаг зондирования, м", self.step_depth_var, "mode_step_depth", width=6)
        add_field(col_left, 1, "Тип контролера", self.controller_type_var, "controller_type", width=12)
        add_field(col_left, 2, "Тип зонда", self.probe_type_var, "probe_type", width=12)
        add_field(col_left, 3, "Шкала прибора", self.controller_scale_div_var, "controller_scale_div", width=4)
        add_field(col_right, 0, "Максимальная нагрузка на конус, кН", self.cone_kn_var, "cone_kn", width=4)
        add_field(col_right, 1, "Максимальная нагрузка на муфту трения, кН", self.sleeve_kn_var, "sleeve_kn", width=4)
        add_field(col_right, 2, "Площадь конуса, см²", self.cone_area_cm2_var, "cone_area_cm2", width=4)
        add_field(col_right, 3, "Площадь муфты, см²", self.sleeve_area_cm2_var, "sleeve_area_cm2", width=4)

    def _build_type1_params_form(self, parent):
        frm = ttk.LabelFrame(parent, text="Параметры — Тип 1 (механический)", padding=6)
        frm.pack(side="top", fill="x")
        self._common_param_entries = {}

        rows = [
            ("Шаг зондирования, м", self.step_depth_var, "mode_step_depth"),
            ("Тарировочный коэффициент «лоб»", self.mech_lob_coeff_var, "mode_lob_coeff"),
            ("Тарировочный коэффициент «общ»", self.mech_total_coeff_var, "mode_total_coeff"),
        ]
        for i, (label, var, key) in enumerate(rows, start=0):
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky="w", padx=(0, 6), pady=1)
            ent = ttk.Entry(frm, textvariable=var, width=26)
            ent.grid(row=i, column=1, sticky="w", pady=1)
            ent.bind("<FocusOut>", lambda _e: self._emit_common_params())
            ent.bind("<Return>", lambda _e: self._emit_common_params())
            self._common_param_entries[key] = ent

    def _build_direct_params_form(self, parent):
        frm = ttk.LabelFrame(parent, text="Параметры — Прямой ввод qc/fs", padding=6)
        frm.pack(side="top", fill="x")
        self._common_param_entries = {}
        ttk.Label(frm, text="Шаг зондирования, м").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=1)
        ent_step = ttk.Entry(frm, textvariable=self.step_depth_var, width=10)
        ent_step.grid(row=0, column=1, sticky="w", pady=1)
        ent_step.bind("<FocusOut>", lambda _e: self._emit_common_params())
        ent_step.bind("<Return>", lambda _e: self._emit_common_params())
        self._common_param_entries["mode_step_depth"] = ent_step

    def _render_params_by_project_type(self, project_type: str, *, emit: bool = True):
        self.project_type_mode = str(project_type or "").strip()
        host = getattr(self, "_params_mode_host", None)
        if host is None:
            return
        for w in list(host.winfo_children()):
            w.destroy()
        if self.project_type_mode == "type1_mech":
            self._build_type1_params_form(host)
        elif self.project_type_mode == "direct_qcfs":
            self._build_direct_params_form(host)
        elif self.project_type_mode == "type2_electric":
            self._build_type2_params_form(host)
        else:
            self.project_type_mode = ""
            self._build_empty_params_state(host)
        if emit:
            self._emit_common_params()

    def _collect_common_params(self) -> dict[str, str]:
        payload = {
            "project_type": self.project_type_mode,
            "mode_installation_name": str(self.installation_name_var.get() or "").strip(),
            "mode_step_depth": str(self.step_depth_var.get() or "").strip(),
        }
        if self.project_type_mode == "type2_electric":
            payload.update({
            "controller_type": str(self.controller_type_var.get() or "").strip(),
            "controller_scale_div": str(self.controller_scale_div_var.get() or "").strip(),
            "probe_type": str(self.probe_type_var.get() or "").strip(),
            "cone_kn": str(self.cone_kn_var.get() or "").strip(),
            "sleeve_kn": str(self.sleeve_kn_var.get() or "").strip(),
            "cone_area_cm2": str(self.cone_area_cm2_var.get() or "").strip(),
            "sleeve_area_cm2": str(self.sleeve_area_cm2_var.get() or "").strip(),
            })
        if self.project_type_mode == "type1_mech":
            payload.update({
                "mode_lob_coeff": str(self.mech_lob_coeff_var.get() or "").strip(),
                "mode_total_coeff": str(self.mech_total_coeff_var.get() or "").strip(),
                "mode_calibration_date": str(self.mech_calib_date_var.get() or "").strip(),
                "mode_calibration_note": str(self.mech_calib_note_var.get() or "").strip(),
            })
        return payload

    def _emit_common_params(self):
        if bool(getattr(self, "_suspend_common_emit", False)):
            return
        cb = self.commands.get("common_params_changed")
        if callable(cb):
            cb(self._collect_common_params())

    def _build_view_tab(self):
        tab = ttk.Frame(self.tabs, padding=4)
        self.tabs.add(tab, text="Вид")

        cols = ttk.Frame(tab)
        cols.pack(side="top", anchor="w")

        opts_col = ttk.Frame(cols)
        opts_col.grid(row=0, column=0, sticky="nw", padx=(0, 20))

        sort_col = ttk.Frame(cols)
        sort_col.grid(row=0, column=1, sticky="nw")

        opts_grid = ttk.Frame(opts_col)
        opts_grid.pack(side="top", anchor="w")

        left_opts = ttk.Frame(opts_grid)
        left_opts.grid(row=0, column=0, sticky="nw", padx=(0, 16))

        right_opts = ttk.Frame(opts_grid)
        right_opts.grid(row=0, column=1, sticky="nw")

        compact_chk = ttk.Checkbutton(
            left_opts,
            text="Развернуть / Свернуть",
            variable=self.compact_1m_var,
            command=lambda: self.commands.get("toggle_compact_1m", lambda *_: None)(bool(self.compact_1m_var.get())),
        )
        compact_chk.pack(side="top", anchor="w", pady=(2, 0))
        ToolTip(compact_chk, "Использует текущую логику сворачивания/разворачивания вида по 1-метровым интервалам")

        graphs_chk = ttk.Checkbutton(
            left_opts,
            text="График зондирования",
            variable=self.show_graphs_var,
            command=lambda: self.commands.get("toggle_graphs", lambda *_: None)(bool(self.show_graphs_var.get())),
        )
        graphs_chk.pack(side="top", anchor="w", pady=(2, 0))
        ToolTip(graphs_chk, "Показывать графическую часть зондирования")

        geology_chk = ttk.Checkbutton(
            left_opts,
            text="Геологическая колонка",
            variable=self.show_geology_var,
            command=self._on_toggle_geology_from_ui,
        )
        geology_chk.pack(side="top", anchor="w", pady=(2, 0))
        ToolTip(geology_chk, "Показывать/скрывать геологическую колонку")
        self._geology_chk = geology_chk

        layer_colors_chk = ttk.Checkbutton(
            right_opts,
            text="Цвет слоёв",
            variable=self.show_layer_colors_var,
            command=lambda: self.commands.get("toggle_layer_colors", lambda *_: None)(bool(self.show_layer_colors_var.get())),
        )
        layer_colors_chk.pack(side="top", anchor="w", pady=(2, 0))
        ToolTip(layer_colors_chk, "Мягкая заливка по типу грунта под штриховкой")
        self._layer_colors_chk = layer_colors_chk

        layer_hatching_chk = ttk.Checkbutton(
            right_opts,
            text="Штриховка",
            variable=self.show_layer_hatching_var,
            command=lambda: self.commands.get("toggle_layer_hatching", lambda *_: None)(bool(self.show_layer_hatching_var.get())),
        )
        layer_hatching_chk.pack(side="top", anchor="w", pady=(2, 0))
        ToolTip(layer_hatching_chk, "Показывать/скрывать штриховку геологической колонки")
        self._layer_hatching_chk = layer_hatching_chk

        incl_chk = ttk.Checkbutton(
            left_opts,
            text="Инклинометр",
            variable=self.show_inclinometer_var,
            command=lambda: self.commands.get("toggle_inclinometer", lambda *_: None)(bool(self.show_inclinometer_var.get())),
        )
        incl_chk.pack(side="top", anchor="w", pady=(2, 0))
        ToolTip(incl_chk, "Показывать/скрывать колонку инклинометра для К4")
        self._inclinometer_chk = incl_chk

        sort_frame = ttk.LabelFrame(sort_col, text="Сортировка отображения", padding=4)
        sort_frame.pack(side="top", anchor="w")
        sort_date = ttk.Radiobutton(
            sort_frame,
            text="Отсортировать по дате",
            value="date",
            variable=self.display_sort_var,
            command=lambda: self.commands.get("set_display_sort_mode", lambda *_: None)(str(self.display_sort_var.get())),
        )
        sort_date.pack(side="top", anchor="w")
        sort_tid = ttk.Radiobutton(
            sort_frame,
            text="Отсортировать по номеру опыта",
            value="tid",
            variable=self.display_sort_var,
            command=lambda: self.commands.get("set_display_sort_mode", lambda *_: None)(str(self.display_sort_var.get())),
        )
        sort_tid.pack(side="top", anchor="w", pady=(2, 0))
        ToolTip(sort_date, "Стандартный режим: хронологический порядок")
        ToolTip(sort_tid, "Альтернативный режим: по номеру опыта")
        self._sync_geology_dependents()

    def _on_toggle_geology_from_ui(self):
        value = bool(self.show_geology_var.get())
        self.commands.get("toggle_geology_column", lambda *_: None)(value)
        self._sync_geology_dependents()

    def _sync_geology_dependents(self):
        enabled = bool(self.show_geology_var.get())
        for attr in ("_layer_colors_chk", "_layer_hatching_chk"):
            chk = getattr(self, attr, None)
            if chk is None:
                continue
            try:
                chk.configure(state=("normal" if enabled else "disabled"))
            except Exception:
                pass

    def _build_layers_tab(self):
        tab = ttk.Frame(self.tabs, padding=4)
        self.tabs.add(tab, text="ИГЭ")

        host = ttk.Frame(tab)
        host.pack(fill="x", expand=False)
        self._ige_canvas = tk.Canvas(host, height=154, highlightthickness=0, bd=0)
        self._ige_canvas.pack(side="left", fill="x", expand=True)

        self._ige_columns_frame = ttk.Frame(self._ige_canvas)
        self._ige_window_id = self._ige_canvas.create_window((0, 0), window=self._ige_columns_frame, anchor="nw")
        self._ige_columns_frame.bind("<Configure>", lambda _e: self._sync_ige_canvas())
        self._ige_canvas.bind("<Configure>", lambda _e: self._sync_ige_canvas())
        self._ige_canvas.bind("<Enter>", lambda _e: self._ige_canvas.focus_set())
        self._ige_canvas.bind("<MouseWheel>", self._on_ige_wheel_x)
        self._ige_canvas.bind("<Button-4>", lambda _e: self._on_ige_wheel_x_linux(-1))
        self._ige_canvas.bind("<Button-5>", lambda _e: self._on_ige_wheel_x_linux(1))

    def _build_calc_tab(self):
        tab = ttk.Frame(self.tabs, padding=4)
        self.tabs.add(tab, text="Расчёт")

        params = ttk.LabelFrame(tab, text="Параметры расчёта", padding=6)
        params.pack(fill="x", expand=False)

        ttk.Label(params, text="Расчёт по результатам зондирования:").grid(row=0, column=0, sticky="w")
        ttk.Label(
            params,
            text="СП 446.1325800.2019 (с Изм. № 1), приложение Ж",
            foreground="#1f2b3a",
        ).grid(row=0, column=1, sticky="w", padx=(6, 0))

        ttk.Label(params, text="Переход от нормативных к расчётным значениям:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(
            params,
            text="СП 22.13330.2016 (с Изм. № 1–5), п. 5.3.17",
            foreground="#1f2b3a",
        ).grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(4, 0))

        ttk.Checkbutton(params, text="Рассчитывать нормативные значения при n < 6 (см. ГОСТ 20522-2012, п. 4.10)", variable=self.calc_allow_normative_lt6_var, command=lambda: self.commands.get("calc_option_changed", lambda *_: None)("allow_normative_lt6", bool(self.calc_allow_normative_lt6_var.get()))).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Checkbutton(params, text="Рассчитать супесь по редакции СП 446.1325800.2019 до Изм. № 1", variable=self.calc_legacy_sandy_loam_var, command=lambda: self.commands.get("calc_option_changed", lambda *_: None)("use_legacy_sandy_loam_sp446", bool(self.calc_legacy_sandy_loam_var.get()))).grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 0))
        ttk.Checkbutton(params, text="Разрешить предварительный расчёт насыпного по материалу", variable=self.calc_fill_preliminary_var, command=lambda: self.commands.get("calc_option_changed", lambda *_: None)("allow_fill_preliminary", bool(self.calc_fill_preliminary_var.get()))).grid(row=4, column=0, columnspan=2, sticky="w", pady=(2, 0))

    def _build_protocol_tab(self):
        tab = ttk.Frame(self.tabs, padding=4)
        self.tabs.add(tab, text="Протокол")
        ttk.Label(tab, text="Раздел протокола будет реализован на следующем этапе.", anchor="w").pack(fill="x")

    def _sync_ige_canvas(self):
        cnv = getattr(self, "_ige_canvas", None)
        if cnv is None:
            return
        try:
            req_h = int(self._ige_columns_frame.winfo_reqheight())
            if req_h > 0:
                cnv.configure(height=req_h + 2)
            cnv.configure(scrollregion=cnv.bbox("all"))
            width = max(int(cnv.winfo_width()), int(self._ige_columns_frame.winfo_reqwidth()))
            cnv.itemconfigure(self._ige_window_id, width=width)
        except Exception:
            pass

    def _on_tab_changed(self, _event=None):
        self._apply_compact_ribbon_height()
        cb = self.commands.get("ribbon_tab_changed")
        if callable(cb):
            cb(self.current_tab_title())

    def current_tab_title(self) -> str:
        try:
            tab_id = self.tabs.select()
            return str(self.tabs.tab(tab_id, "text") or "")
        except Exception:
            return ""

    def _on_ige_wheel_x(self, event):
        try:
            delta = int(getattr(event, "delta", 0))
        except Exception:
            delta = 0
        if delta == 0:
            return "break"
        step = -2 if delta > 0 else 2
        try:
            self._ige_canvas.xview_scroll(step, "units")
        except Exception:
            pass
        return "break"

    def _on_ige_wheel_x_linux(self, direction: int):
        try:
            d = int(direction)
        except Exception:
            d = 0
        if d == 0:
            return "break"
        try:
            self._ige_canvas.xview_scroll(d * 2, "units")
        except Exception:
            pass
        return "break"

    def _ige_card_metrics(self) -> tuple[int, int, int]:
        root = self.winfo_toplevel()
        try:
            w_depth = int(getattr(root, "w_depth", 64) or 64)
            w_val = int(getattr(root, "w_val", 56) or 56)
            gap = int(getattr(root, "col_gap", 12) or 12)
        except Exception:
            w_depth, w_val, gap = 64, 56, 12
        card_w = max(140, int(w_depth + (2 * w_val)))
        border_w = 1
        return card_w, gap, border_w

    def _open_ige_notes(self, ige_id: str, current_text: str):
        root = self.winfo_toplevel()
        dlg = tk.Toplevel(root)
        dlg.title(f"Описание {ige_id}")
        dlg.transient(root)
        dlg.grab_set()
        try:
            root.update_idletasks()
            rw, rh = int(root.winfo_width()), int(root.winfo_height())
            rx, ry = int(root.winfo_rootx()), int(root.winfo_rooty())
            dw, dh = 560, 300
            dx = rx + max((rw - dw) // 2, 0)
            dy = ry + max((rh - dh) // 2, 0)
            dlg.geometry(f"{dw}x{dh}+{dx}+{dy}")
        except Exception:
            pass
        frm = ttk.Frame(dlg, padding=8)
        frm.pack(fill="both", expand=True)
        txt = tk.Text(frm, width=52, height=10)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", str(current_text or ""))

        def _save():
            self._change_ige_field(ige_id, "notes", txt.get("1.0", "end").strip())
            dlg.destroy()

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="Отмена", command=dlg.destroy).pack(side="right")
        ttk.Button(btns, text="Сохранить", command=_save).pack(side="right", padx=(0, 6))

    def _edit_ige_label(self, ige_id: str, current_label: str):
        new_label = simpledialog.askstring("Имя ИГЭ", "Введите новое имя ИГЭ:", initialvalue=str(current_label or ige_id), parent=self.winfo_toplevel())
        if new_label is None:
            return
        cmd = self.commands.get("rename_ige")
        if callable(cmd):
            cmd(str(ige_id or "").strip(), str(new_label or "").strip())

    def _set_combo_placeholder(self, cb: ttk.Combobox, var: tk.StringVar, default_value: str | None = None):
        if not str(var.get() or "").strip():
            if str(default_value or "").strip():
                var.set(str(default_value))
                cb._user_selected = False
            else:
                cb._user_selected = False
        else:
            cb._user_selected = True

        def _apply():
            try:
                cb.configure(foreground=("#9aa0a6" if not getattr(cb, "_user_selected", False) else "#111111"))
            except Exception:
                pass

        _apply()
        def _on_selected(_e=None):
            cb._user_selected = True
            _apply()
        cb.bind("<<ComboboxSelected>>", _on_selected, add="+")

    def _ige_ui_profile(self, soil_name: str, row: dict | None = None) -> str:
        profile = get_ige_profile(soil_name=str(soil_name or "").strip(), params=dict(row or {}))
        mapping = {
            "sand_calculable": "sand",
            "clay_supes_calculable": "clay_supes",
            "clay_calculable": "clay_general",
            "fill_calculable": "fill",
            "descriptive": "simplified",
        }
        return mapping.get(profile.ui_profile, "simplified")

    def _build_dynamic_ige_fields(self, parent, ige_id: str, row: dict):
        soil = str(row.get("soil", "") or "").lower()
        if not soil.strip():
            return
        profile = self._ige_ui_profile(soil, row)
        if profile == "sand":
            sand_kind = tk.StringVar(value=str(row.get("sand_kind", "") or ""))
            cb_kind = ttk.Combobox(parent, state="readonly", width=16, values=["гравелистый", "крупный", "средней крупности", "мелкий", "пылеватый"], textvariable=sand_kind)
            cb_kind.grid(row=0, column=0, sticky="ew")
            self._set_combo_placeholder(cb_kind, sand_kind, "средней крупности")

            sat = tk.StringVar(value=str(row.get("sand_water_saturation", "") or ""))
            cb_sat = ttk.Combobox(parent, state="readonly", width=16, values=["малой степени", "влажный", "водонасыщенный"], textvariable=sat)
            cb_sat.grid(row=1, column=0, sticky="ew", pady=(0, 0))
            self._set_combo_placeholder(cb_sat, sat, "влажный")

            dens = tk.StringVar(value=str(row.get("density_state", "") or ""))
            cb_den = ttk.Combobox(parent, state="readonly", width=16, values=["рыхлый", "средней плотности", "плотный"], textvariable=dens)
            cb_den.grid(row=2, column=0, sticky="ew", pady=(0, 0))
            self._set_combo_placeholder(cb_den, dens, "средней плотности")

            alluvial = tk.BooleanVar(value=bool(row.get("sand_is_alluvial", False)))
            ttk.Checkbutton(parent, text="аллювиальный", variable=alluvial, command=lambda ig=ige_id, vv=alluvial: self._change_ige_field(ig, "sand_is_alluvial", bool(vv.get()))).grid(row=3, column=0, sticky="w", pady=(0, 0))

            cb_kind.bind("<<ComboboxSelected>>", lambda _e, ig=ige_id, vv=sand_kind: self._change_ige_field(ig, "sand_kind", vv.get()))
            cb_sat.bind("<<ComboboxSelected>>", lambda _e, ig=ige_id, vv=sat: self._change_ige_field(ig, "sand_water_saturation", vv.get()))
            cb_den.bind("<<ComboboxSelected>>", lambda _e, ig=ige_id, vv=dens: self._change_ige_field(ig, "density_state", vv.get()))
            return

        if profile == "fill":
            fill_sub = tk.StringVar(value=str(row.get("fill_subtype", "") or ""))
            cb_fill = ttk.Combobox(parent, state="readonly", width=18, values=["песчаный", "глинистый", "более 10% строительного материала"], textvariable=fill_sub)
            cb_fill.grid(row=0, column=0, sticky="ew")
            self._set_combo_placeholder(cb_fill, fill_sub, "песчаный")
            cb_fill.bind("<<ComboboxSelected>>", lambda _e, ig=ige_id, vv=fill_sub: self._change_ige_field(ig, "fill_subtype", vv.get()))
            return

        if profile == "clay_supes":
            cons = tk.StringVar(value=str(row.get("consistency", "") or ""))
            cb_cons = ttk.Combobox(parent, state="readonly", width=18, values=["твердая", "пластичная", "текучая"], textvariable=cons)
            cb_cons.grid(row=0, column=0, sticky="ew")
            self._set_combo_placeholder(cb_cons, cons, "пластичная")
            cb_cons.bind("<<ComboboxSelected>>", lambda _e, ig=ige_id, vv=cons: self._change_ige_field(ig, "consistency", vv.get()))
            return

        if profile == "simplified":
            return

        cons = tk.StringVar(value=str(row.get("consistency", "") or ""))
        cb_cons = ttk.Combobox(parent, state="readonly", width=18, values=["твердая", "полутвердая", "тугопластичная", "мягкопластичная", "текучепластичная", "текучая"], textvariable=cons)
        cb_cons.grid(row=0, column=0, sticky="ew")
        self._set_combo_placeholder(cb_cons, cons, "тугопластичная")
        cb_cons.bind("<<ComboboxSelected>>", lambda _e, ig=ige_id, vv=cons: self._change_ige_field(ig, "consistency", vv.get()))

    def _build_ige_column(self, parent, row: dict, soil_values: list[str], can_delete: bool, *, before=None):
        ige_id = str(row.get("ige_id", "") or "")
        card_w, gap, border_w = self._ige_card_metrics()
        card = tk.Frame(parent, padx=2, pady=1, bd=0, highlightthickness=1, highlightbackground="#d4d8de", highlightcolor="#d4d8de")
        pack_kwargs = {"side": "left", "fill": "y", "padx": (0, max(2, gap))}
        if before is not None:
            pack_kwargs["before"] = before
        card.pack(**pack_kwargs)
        try:
            card.configure(width=card_w)
        except Exception:
            pass

        hdr = ttk.Frame(card)
        hdr.pack(fill="x")
        hdr.columnconfigure(0, weight=1)
        hdr.rowconfigure(0, minsize=22)
        lbl_txt = str(row.get("label", ige_id) or ige_id)
        lbl_btn = ttk.Button(hdr, text=lbl_txt, style="IGEHdr.TButton", command=lambda ig=ige_id, txt=lbl_txt: self._edit_ige_label(ig, txt))
        lbl_btn.grid(row=0, column=0, sticky="ew")
        btn_note = ttk.Button(hdr, text="📄", width=2, style="IGEHdr.TButton", command=lambda ig=ige_id, txt=str(row.get("notes", "") or ""): self._open_ige_notes(ig, txt))
        btn_note.grid(row=0, column=1, sticky="ns", padx=(0, 1), pady=0)
        btn_del = ttk.Button(hdr, text=ICON_TRASH, width=2, style="IGEHdr.TButton", command=lambda ig=ige_id: self.commands.get("delete_ige", lambda *_: None)(ig))
        btn_del.grid(row=0, column=2, sticky="ns", pady=0)
        if not can_delete:
            btn_del.configure(state="disabled")

        body = ttk.Frame(card)
        body.pack(fill="both", expand=True, pady=(1, 0))
        body.columnconfigure(0, weight=1)
        soil_var = tk.StringVar(value=str(row.get("soil", "") or ""))
        cb_soil = ttk.Combobox(body, state="readonly", width=18, values=list(soil_values or []), textvariable=soil_var)
        cb_soil.grid(row=0, column=0, sticky="ew")
        self._set_combo_placeholder(cb_soil, soil_var, None)
        cb_soil.bind("<<ComboboxSelected>>", lambda _e, ig=ige_id, sv=soil_var: self.commands.get("edit_ige", lambda *_: None)(ig, sv.get(), ""))

        dyn = ttk.Frame(body)
        dyn.grid(row=1, column=0, sticky="ew", pady=(1, 0))
        dyn.columnconfigure(0, weight=1)
        self._build_dynamic_ige_fields(dyn, ige_id, row)

        # wheel over any card/control scrolls IGE ribbon horizontally
        for w in (card, hdr, body, dyn, lbl_btn, btn_note, btn_del, cb_soil):
            try:
                w.bind("<MouseWheel>", self._on_ige_wheel_x, add="+")
                w.bind("<Button-4>", lambda _e: self._on_ige_wheel_x_linux(-1), add="+")
                w.bind("<Button-5>", lambda _e: self._on_ige_wheel_x_linux(1), add="+")
            except Exception:
                pass
        return card

    def _change_ige_field(self, ige_id: str, field_name: str, value):
        cmd = self.commands.get("change_ige_field")
        if callable(cmd):
            cmd(str(ige_id or "").strip(), str(field_name or "").strip(), value)

    def _open_ige_params(self, ige_id: str):
        self.layer_ige_var.set(ige_id)
        cmd = self.commands.get("edit_ige_cpt")
        if callable(cmd):
            cmd()

    def _select_ige(self, ige_id: str):
        self.layer_ige_var.set(ige_id)
        cmd = self.commands.get("select_ige")
        if callable(cmd):
            cmd(ige_id)

    def _apply_ige_edit(self, ige_id: str, soil_var: tk.StringVar):
        cmd = self.commands.get("edit_ige")
        if callable(cmd):
            cmd(str(ige_id or "").strip(), str(soil_var.get() or "").strip(), "")

    def set_object_name(self, value: str):
        self.object_name_var.set(value or "")

    def set_project_type(self, project_type: str, *, mode_params: dict[str, str] | None = None, emit: bool = True):
        mp = dict(mode_params or {})
        ptype = str(project_type or "").strip()
        if not ptype:
            self._render_params_by_project_type("", emit=False)
            return
        default_step = "0.20" if ptype == "type1_mech" else ("0.10" if ptype == "direct_qcfs" else "0.05")
        self._suspend_common_emit = True
        try:
            self._render_params_by_project_type(ptype, emit=False)
            self.installation_name_var.set(str(mp.get("mode_installation_name", "") or ""))
            self.step_depth_var.set(str(mp.get("mode_step_depth", self.step_depth_var.get() or default_step) or default_step))
            self.mech_lob_coeff_var.set(str(mp.get("mode_lob_coeff", self.mech_lob_coeff_var.get() or "1.00") or "1.00"))
            self.mech_total_coeff_var.set(str(mp.get("mode_total_coeff", self.mech_total_coeff_var.get() or "1.00") or "1.00"))
            self.mech_calib_date_var.set(str(mp.get("mode_calibration_date", "") or ""))
            self.mech_calib_note_var.set(str(mp.get("mode_calibration_note", "") or ""))
        finally:
            self._suspend_common_emit = False
        if emit:
            self._emit_common_params()

    def set_common_params(self, params: dict[str, str] | None, *, geo_kind: str = "K2"):
        p = dict(params or {})
        ptype = str(p.get("project_type", "") or "").strip()
        if ptype:
            self.set_project_type(ptype, mode_params=p)
        controller_txt = str(p.get("controller_type", "") or "")
        if self.project_type_mode == "type2_electric" and controller_txt.strip() == "ТЕСТ-К2М":
            controller_txt = ""
        self.controller_type_var.set(controller_txt)
        self.controller_scale_div_var.set(str(p.get("controller_scale_div", "") or ""))
        self.probe_type_var.set(str(p.get("probe_type", "") or ""))
        self.cone_kn_var.set(str(p.get("cone_kn", "") or ""))
        self.sleeve_kn_var.set(str(p.get("sleeve_kn", "") or ""))
        self.cone_area_cm2_var.set(str(p.get("cone_area_cm2", "") or ""))
        self.sleeve_area_cm2_var.set(str(p.get("sleeve_area_cm2", "") or ""))
        ent = getattr(self, "_common_param_entries", {}).get("controller_scale_div")
        if ent is not None:
            try:
                ent.configure(state=("disabled" if str(geo_kind or "K2").upper() == "K4" else "normal"))
            except Exception:
                pass

    def select_tab(self, title: str):
        target = str(title or "").strip()
        if not target:
            return
        try:
            for tab_id in self.tabs.tabs():
                if str(self.tabs.tab(tab_id, "text") or "").strip() == target:
                    self.tabs.select(tab_id)
                    self._on_tab_changed()
                    return
        except Exception:
            return

    def set_enabled(self, key: str, enabled: bool, reason: str = ""):
        btn = self._buttons.get(key)
        if not btn:
            return
        btn.configure(state=("normal" if enabled else "disabled"))
        if reason:
            ToolTip(btn, reason)

    def set_show_graphs(self, value: bool):
        self.show_graphs_var.set(bool(value))

    def set_compact_1m(self, value: bool):
        self.compact_1m_var.set(bool(value))

    def set_show_geology_column(self, value: bool):
        self.show_geology_var.set(bool(value))
        self._sync_geology_dependents()

    def set_show_layer_colors(self, value: bool):
        self.show_layer_colors_var.set(bool(value))

    def set_show_layer_hatching(self, value: bool):
        self.show_layer_hatching_var.set(bool(value))

    def set_show_inclinometer(self, value: bool, *, enabled: bool = True):
        self.show_inclinometer_var.set(bool(value))
        chk = getattr(self, "_inclinometer_chk", None)
        if chk is not None:
            try:
                chk.configure(state=("normal" if enabled else "disabled"))
            except Exception:
                pass

    def set_display_sort_mode(self, value: str):
        self.display_sort_var.set("tid" if str(value or "").lower() == "tid" else "date")

    def set_layer_edit_mode(self, value: bool):
        self.layers_edit_var.set(bool(value))

    def _rows_signature(self, row: dict) -> tuple:
        return (
            str(row.get("ige_id", "")),
            str(row.get("label", "")),
            str(row.get("soil", "")),
            str(row.get("sand_kind", "")),
            str(row.get("sand_water_saturation", "")),
            str(row.get("density_state", "")),
            bool(row.get("sand_is_alluvial", False)),
            str(row.get("consistency", "")),
            str(row.get("fill_subtype", "")),
            str(row.get("notes", "")),
            bool(row.get("_can_delete", True)),
        )

    def _rows_structure_signature(self, rows: list[dict], can_delete: bool) -> tuple:
        return tuple((str(dict(row).get("ige_id", "")), bool(can_delete)) for row in (rows or []))

    def _replace_ige_card(self, row: dict, soil_values: list[str], can_delete: bool):
        ige_id = str(row.get("ige_id", "") or "")
        old_card = self._ige_cards.get(ige_id)
        before_widget = self._add_ige_btn
        if old_card is not None:
            try:
                siblings = list(self._ige_columns_frame.winfo_children())
                idx = siblings.index(old_card)
                if idx + 1 < len(siblings):
                    before_widget = siblings[idx + 1]
            except Exception:
                before_widget = self._add_ige_btn
            try:
                old_card.destroy()
            except Exception:
                pass
        new_card = self._build_ige_column(self._ige_columns_frame, row, soil_values, can_delete, before=before_widget)
        self._ige_cards[ige_id] = new_card
        self._ige_rows_cache[ige_id] = dict(row)
        return new_card

    def _render_ige_cards(self, rows: list[dict], soil_values: list[str], can_delete: bool):
        incoming_ids = [str(r.get("ige_id", "") or "") for r in rows]
        row_by_id = {str(r.get("ige_id", "") or ""): dict(r) for r in rows}

        # Stable visual order for field edits; for add/remove use incoming canonical order.
        if not self._ige_order:
            self._ige_order = list(incoming_ids)
        else:
            incoming_set = set(incoming_ids)
            current_set = set(self._ige_order)
            if incoming_set != current_set:
                self._ige_order = list(incoming_ids)

        # Canonical rows in stable order
        ordered_rows: list[dict] = []
        for rid in self._ige_order:
            row = dict(row_by_id.get(rid) or {})
            if not row:
                continue
            row["_can_delete"] = bool(can_delete)
            ordered_rows.append(row)

        # Rebuild all cards in canonical order (deterministic, no jumping).
        for ch in self._ige_columns_frame.winfo_children():
            ch.destroy()
        self._ige_cards = {}
        self._ige_rows_cache = {}
        for row in ordered_rows:
            rid = str(row.get("ige_id", "") or "")
            self._ige_cards[rid] = self._build_ige_column(self._ige_columns_frame, row, soil_values, can_delete)
            self._ige_rows_cache[rid] = dict(row)

    def set_layers(self, rows: list[dict], soil_values: list[str], *, can_add: bool = True, can_delete: bool = True):
        new_rows = list(rows or [])
        new_soils = list(soil_values or [])
        current_structure_sig = self._rows_structure_signature(self._layer_rows, bool(can_delete))
        new_structure_sig = self._rows_structure_signature(new_rows, bool(can_delete))
        needs_cards_rebuild = (
            current_structure_sig != new_structure_sig
            or self._ige_soil_values != new_soils
            or not getattr(self, "_ige_cards", None)
        )

        self._layer_rows = new_rows
        self._ige_soil_values = new_soils
        if not self._layer_rows:
            self._ige_order = []

        if needs_cards_rebuild:
            try:
                if self._add_ige_btn is not None:
                    self._add_ige_btn.destroy()
            except Exception:
                pass
            self._add_ige_btn = None
            self._render_ige_cards(self._layer_rows, self._ige_soil_values, bool(can_delete))
            self._add_ige_btn = ttk.Button(self._ige_columns_frame, text="+ ИГЭ", width=6, style="RibbonCompact.TButton", command=self.commands.get("add_ige"))
            _, gap, _ = self._ige_card_metrics()
            self._add_ige_btn.pack(side="left", fill="y", pady=0, padx=(0, max(2, gap)))
        else:
            rows_cache = getattr(self, "_ige_rows_cache", {})
            for row in new_rows:
                ige_id = str(row.get("ige_id", "") or "")
                new_sig = self._rows_signature({**dict(row), "_can_delete": bool(can_delete)})
                old_sig = self._rows_signature({**dict(rows_cache.get(ige_id) or {}), "_can_delete": bool(can_delete)})
                if new_sig != old_sig:
                    self._replace_ige_card(row, self._ige_soil_values, bool(can_delete))

        if self._add_ige_btn is not None:
            self._add_ige_btn.configure(state=("normal" if can_add else "disabled"))
        self._sync_ige_canvas()

    def focus_ige_row(self, ige_id: str):
        return
