from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.zondeditor.ui.consts import ICON_EXPORT, ICON_IMPORT, ICON_REDO, ICON_SAVE, ICON_UNDO
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
        self.show_geology_var = tk.BooleanVar(value=True)
        self.compact_1m_var = tk.BooleanVar(value=False)
        self.display_sort_var = tk.StringVar(value="date")
        self.layers_edit_var = tk.BooleanVar(value=False)
        self.layer_soil_var = tk.StringVar(value="")
        self.layer_mode_var = tk.StringVar(value="")
        self.layer_ige_var = tk.StringVar(value="ИГЭ-1")
        self._buttons: dict[str, ttk.Button] = {}
        self._layer_rows: list[dict] = []
        self._ige_controls: dict[str, ttk.Combobox] = {}

        try:
            style = ttk.Style(self)
            style.configure("RibbonCompact.TButton", padding=(4, 1))
        except Exception:
            pass

        qat = ttk.Frame(self, padding=(4, 1))
        qat.pack(side="top", fill="x")
        self._add_qat_btn(qat, "undo", ICON_UNDO, "Undo")
        self._add_qat_btn(qat, "redo", ICON_REDO, "Redo")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(side="top", fill="x", padx=2, pady=(0, 2))

        self._build_file_tab()
        self._build_params_tab()
        self._build_view_tab()
        self._build_layers_tab()
        self._build_processing_tab()

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

    def _add_btn(self, parent, key: str, text: str, tip: str):
        btn = ttk.Button(parent, text=text, command=self.commands.get(key), style="RibbonCompact.TButton", width=12)
        btn.pack(side="top", fill="x", pady=1)
        ToolTip(btn, tip)
        self._buttons[key] = btn

    def _add_btn_grid(self, parent, key: str, text: str, tip: str, row: int, col: int):
        btn = ttk.Button(parent, text=text, command=self.commands.get(key), style="RibbonCompact.TButton", width=12)
        btn.grid(row=row, column=col, sticky="ew", padx=2, pady=1)
        ToolTip(btn, tip)
        self._buttons[key] = btn

    def _build_file_tab(self):
        tab = ttk.Frame(self.tabs, padding=2)
        self.tabs.add(tab, text="Файл")
        project = ttk.LabelFrame(tab, text="Проект", padding=3)
        project.pack(side="left", fill="y", padx=4)
        project.columnconfigure(0, weight=1)
        project.columnconfigure(1, weight=1)
        self._add_btn_grid(project, "new_project", "🆕 Новый", "Создать новый проект", 0, 0)
        self._add_btn_grid(project, "open_project", "📂 Открыть", "Открыть *.zproj", 0, 1)
        self._add_btn_grid(project, "save_project", "💾 Сохранить", "Сохранить *.zproj", 1, 0)
        self._add_btn_grid(project, "save_project_as", "💾 Как…", "Сохранить *.zproj как новый", 1, 1)

        obj = ttk.LabelFrame(tab, text="Объект", padding=3)
        obj.pack(side="left", fill="y", padx=4)
        ttk.Label(obj, text="Название объекта:").pack(anchor="w")
        ent = ttk.Entry(obj, textvariable=self.object_name_var, width=28)
        ent.pack(fill="x", pady=(2, 0))
        ent.bind("<FocusOut>", lambda _e: self.commands.get("object_name_changed", lambda *_: None)(self.object_name_var.get()))
        ent.bind("<Return>", lambda _e: self.commands.get("object_name_changed", lambda *_: None)(self.object_name_var.get()))

        actions = ttk.LabelFrame(tab, text="Импорт / Экспорт", padding=3)
        actions.pack(side="left", fill="y", padx=4)
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        self._add_btn_grid(actions, "open_geo", f"{ICON_IMPORT} GEO", "Открыть GEO/GE0", 0, 0)
        self._add_btn_grid(actions, "export_geo", f"{ICON_EXPORT} GEO", "Экспорт GEO только через Сохранить как", 0, 1)
        self._add_btn_grid(actions, "open_gxl", f"{ICON_IMPORT} GXL", "Открыть GXL", 1, 0)
        self._add_btn_grid(actions, "export_gxl", f"{ICON_EXPORT} GXL", "Экспорт GXL только через Сохранить как", 1, 1)
        self._add_btn_grid(actions, "export_excel", f"{ICON_EXPORT} Excel", "Экспорт Excel", 2, 0)
        self._add_btn_grid(actions, "export_credo", f"{ICON_EXPORT} CREDO", "Экспорт CREDO", 2, 1)
        self._add_btn_grid(actions, "export_archive", "🗜 Архив", "Собрать ZIP с выбранными файлами", 3, 0)
        self._add_btn_grid(actions, "export_dxf", f"{ICON_EXPORT} DXF", "Экспорт графиков в DXF (заглушка)", 3, 1)
        self._add_btn_grid(actions, "export_cpt_protocol", "📄 φ/E (CPT)", "Экспорт Word-протокола расчёта φ и E по CPT", 4, 0)

    def _build_params_tab(self):
        tab = ttk.Frame(self.tabs, padding=4)
        self.tabs.add(tab, text="Параметры")

        common = ttk.LabelFrame(tab, text="Общие параметры прибора и зонда", padding=4)
        common.pack(side="top", fill="x")

        common_right = ttk.Frame(common)
        common_right.pack(side="right", anchor="e")

        col_buttons = ttk.Frame(common_right)
        col_type = ttk.Frame(common_right)
        col_loads = ttk.Frame(common_right)
        col_buttons.grid(row=0, column=0, sticky="nw", padx=(0, 10))
        col_type.grid(row=0, column=1, sticky="nw", padx=(0, 10))
        col_loads.grid(row=0, column=2, sticky="nw")

        self._common_param_entries: dict[str, ttk.Entry] = {}

        btn = ttk.Button(col_buttons, text="Параметры СЗ", command=self.commands.get("geo_params"), style="RibbonCompact.TButton", width=14)
        btn.pack(anchor="w")
        ToolTip(btn, "Открыть параметры зондирований")
        self._buttons["geo_params"] = btn

        def add_field(parent, row: int, label: str, var: tk.StringVar, key: str, width: int = 14):
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 4), pady=1)
            ent = ttk.Entry(parent, textvariable=var, width=width)
            ent.grid(row=row, column=1, sticky="w", pady=1)
            ent.bind("<FocusOut>", lambda _e: self._emit_common_params())
            ent.bind("<Return>", lambda _e: self._emit_common_params())
            self._common_param_entries[key] = ent

        add_field(col_type, 0, "Тип контроллера", self.controller_type_var, "controller_type", width=12)
        add_field(col_type, 1, "Тип зонда", self.probe_type_var, "probe_type", width=12)
        add_field(col_type, 2, "Шкала прибора", self.controller_scale_div_var, "controller_scale_div", width=4)
        add_field(col_loads, 0, "Максимальная нагрузка на конус, кН", self.cone_kn_var, "cone_kn", width=4)
        add_field(col_loads, 1, "Максимальная нагрузка на муфту трения, кН", self.sleeve_kn_var, "sleeve_kn", width=4)
        add_field(col_loads, 2, "Площадь конуса, см²", self.cone_area_cm2_var, "cone_area_cm2", width=4)
        add_field(col_loads, 3, "Площадь муфты, см²", self.sleeve_area_cm2_var, "sleeve_area_cm2", width=4)

    def _collect_common_params(self) -> dict[str, str]:
        return {
            "controller_type": str(self.controller_type_var.get() or "").strip(),
            "controller_scale_div": str(self.controller_scale_div_var.get() or "").strip(),
            "probe_type": str(self.probe_type_var.get() or "").strip(),
            "cone_kn": str(self.cone_kn_var.get() or "").strip(),
            "sleeve_kn": str(self.sleeve_kn_var.get() or "").strip(),
            "cone_area_cm2": str(self.cone_area_cm2_var.get() or "").strip(),
            "sleeve_area_cm2": str(self.sleeve_area_cm2_var.get() or "").strip(),
        }

    def _emit_common_params(self):
        cb = self.commands.get("common_params_changed")
        if callable(cb):
            cb(self._collect_common_params())

    def _build_view_tab(self):
        tab = ttk.Frame(self.tabs, padding=4)
        self.tabs.add(tab, text="Вид")

        compact_chk = ttk.Checkbutton(
            tab,
            text="Развернуть / Свернуть",
            variable=self.compact_1m_var,
            command=lambda: self.commands.get("toggle_compact_1m", lambda *_: None)(bool(self.compact_1m_var.get())),
        )
        compact_chk.pack(side="top", anchor="w", pady=(2, 0))
        ToolTip(compact_chk, "Использует текущую логику сворачивания/разворачивания вида по 1-метровым интервалам")

        graphs_chk = ttk.Checkbutton(
            tab,
            text="График зондирования",
            variable=self.show_graphs_var,
            command=lambda: self.commands.get("toggle_graphs", lambda *_: None)(bool(self.show_graphs_var.get())),
        )
        graphs_chk.pack(side="top", anchor="w", pady=(2, 0))
        ToolTip(graphs_chk, "Показывать графическую часть зондирования")

        geology_chk = ttk.Checkbutton(
            tab,
            text="Геологическая колонка",
            variable=self.show_geology_var,
            command=lambda: self.commands.get("toggle_geology_column", lambda *_: None)(bool(self.show_geology_var.get())),
        )
        geology_chk.pack(side="top", anchor="w", pady=(2, 0))
        ToolTip(geology_chk, "Показывать/скрывать геологическую колонку")

        sort_frame = ttk.LabelFrame(tab, text="Сортировка отображения", padding=4)
        sort_frame.pack(side="top", fill="x", pady=(6, 0))
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

    def _build_layers_tab(self):
        tab = ttk.Frame(self.tabs, padding=4)
        self.tabs.add(tab, text="Слои")

        tools = ttk.Frame(tab)
        tools.pack(fill="x", expand=False, pady=(0, 4))
        self._add_btn_grid(tools, "add_ige", "+ ИГЭ", "Добавить ИГЭ без назначенного грунта", 0, 0)
        self._add_btn_grid(tools, "calc_cpt", "Рассчитать CPT", "Рассчитать qc_ср, φнорм и Eнорм по ИГЭ", 0, 1)

        tbl = ttk.Frame(tab)
        tbl.pack(fill="x", expand=False)
        ttk.Label(tbl, text="Параметр", width=12, anchor="w").grid(row=1, column=0, sticky="w", padx=(0, 8))
        ttk.Label(tbl, text="Грунт", width=12, anchor="w").grid(row=2, column=0, sticky="w", padx=(0, 8))
        ttk.Label(tbl, text="Параметры", width=12, anchor="w").grid(row=3, column=0, sticky="w", padx=(0, 8))
        ttk.Label(tbl, text="Источник", width=12, anchor="w").grid(row=4, column=0, sticky="w", padx=(0, 8))
        ttk.Label(tbl, text="φ / E (CPT)", width=12, anchor="w").grid(row=5, column=0, sticky="w", padx=(0, 8))
        ttk.Label(tbl, text="Статус", width=12, anchor="w").grid(row=6, column=0, sticky="w", padx=(0, 8))
        self.layers_table = tbl

    def _build_processing_tab(self):
        tab = ttk.Frame(self.tabs, padding=4)
        self.tabs.add(tab, text="Обработка")
        fix = ttk.LabelFrame(tab, text="Исправление", padding=4)
        fix.pack(side="left", fill="y", padx=4)
        self._add_btn(fix, "fix_algo", "Исправить (алгоритм)", "Автоматическая корректировка")
        step = ttk.LabelFrame(tab, text="Шаг", padding=4)
        step.pack(side="left", fill="y", padx=4)
        self._add_btn(step, "reduce_step", "Уменьшить шаг…", "Преобразовать шаг")
        calc = ttk.LabelFrame(tab, text="Параметры пересчёта", padding=4)
        calc.pack(side="left", fill="y", padx=4)
        self._add_btn(calc, "apply_calc", "Применить", "Применить параметры пересчёта")
        k2k4 = ttk.LabelFrame(tab, text="К2 → К4", padding=4)
        k2k4.pack(side="left", fill="y", padx=4)
        self._add_btn(k2k4, "k2k4_30", "Пересчитать К2→К4 (30 МПа)", "Режим 30 МПа")
        self._add_btn(k2k4, "k2k4_50", "Пересчитать К2→К4 (50 МПа)", "Режим 50 МПа")

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

    def set_common_params(self, params: dict[str, str] | None, *, geo_kind: str = "K2"):
        p = dict(params or {})
        self.controller_type_var.set(str(p.get("controller_type", "") or ""))
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

    def set_display_sort_mode(self, value: str):
        self.display_sort_var.set("tid" if str(value or "").lower() == "tid" else "date")

    def set_layer_edit_mode(self, value: bool):
        self.layers_edit_var.set(bool(value))

    def set_layers(self, rows: list[dict], soil_values: list[str]):
        self._layer_rows = list(rows or [])
        self._ige_controls = {}
        if not hasattr(self, "layers_table"):
            return
        for child in self.layers_table.grid_slaves():
            if int(child.grid_info().get("column", 0)) > 0:
                child.destroy()

        for idx, row in enumerate(self._layer_rows, start=1):
            ige_id = str(row.get("ige", "") or "")
            soil_var = tk.StringVar(value=str(row.get("soil", "") or ""))
            self.layers_table.columnconfigure(idx, weight=0)
            lbl = ttk.Label(self.layers_table, text=ige_id, anchor="center", width=18)
            lbl.grid(row=1, column=idx, sticky="ew", padx=2, pady=(0, 1))
            cb = ttk.Combobox(self.layers_table, state="readonly", width=16, textvariable=soil_var, values=list(soil_values or []))
            cb.grid(row=2, column=idx, sticky="ew", padx=2, pady=1)
            btn_params = ttk.Button(self.layers_table, text="Выбрать…", width=16, style="RibbonCompact.TButton", command=lambda ig=ige_id: self._open_ige_params(ig))
            btn_params.grid(row=3, column=idx, sticky="ew", padx=2, pady=1)
            ttk.Label(self.layers_table, text=str(row.get("source", "")), width=18, anchor="center").grid(row=4, column=idx, sticky="ew", padx=2, pady=1)
            ttk.Label(self.layers_table, text=f"{row.get('phi', '-')} / {row.get('e', '-')}", width=18, anchor="center").grid(row=5, column=idx, sticky="ew", padx=2, pady=1)
            ttk.Label(self.layers_table, text=str(row.get("status", "")), width=18, anchor="center").grid(row=6, column=idx, sticky="ew", padx=2, pady=1)
            cb.bind("<<ComboboxSelected>>", lambda _e, ig=ige_id, sv=soil_var: self._apply_ige_edit(ig, sv))
            lbl.bind("<Button-1>", lambda _e, ig=ige_id: self._select_ige(ig))
            cb.bind("<Button-1>", lambda _e, ig=ige_id: self._select_ige(ig), add="+")
            self._ige_controls[ige_id] = cb

    def focus_ige_row(self, ige_id: str):
        ig = str(ige_id or "").strip()
        cb = self._ige_controls.get(ig)
        if cb is not None:
            try:
                cb.focus_set()
            except Exception:
                pass
            self._select_ige(ig)
