from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.zondeditor.ui.consts import ICON_EXPORT, ICON_IMPORT, ICON_REDO, ICON_SAVE, ICON_UNDO, ICON_TRASH
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
        self.show_inclinometer_var = tk.BooleanVar(value=True)
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

        common_left = ttk.Frame(common)
        common_left.pack(side="left", anchor="w", padx=(8, 0))

        col_left = ttk.Frame(common_left)
        col_right = ttk.Frame(common_left)
        col_left.grid(row=0, column=0, sticky="nw", padx=(0, 16))
        col_right.grid(row=0, column=1, sticky="nw")

        self._common_param_entries: dict[str, ttk.Entry] = {}

        btn = ttk.Button(col_left, text="Параметры СЗ", command=self.commands.get("geo_params"), style="RibbonCompact.TButton", width=14)
        btn.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        ToolTip(btn, "Открыть параметры зондирований")
        self._buttons["geo_params"] = btn

        def add_field(parent, row: int, label: str, var: tk.StringVar, key: str, width: int = 14):
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 4), pady=1)
            ent = ttk.Entry(parent, textvariable=var, width=width)
            ent.grid(row=row, column=1, sticky="w", pady=1)
            ent.bind("<FocusOut>", lambda _e: self._emit_common_params())
            ent.bind("<Return>", lambda _e: self._emit_common_params())
            self._common_param_entries[key] = ent

        add_field(col_left, 1, "Тип контроллера", self.controller_type_var, "controller_type", width=12)
        add_field(col_left, 2, "Тип зонда", self.probe_type_var, "probe_type", width=12)
        add_field(col_left, 3, "Шкала прибора", self.controller_scale_div_var, "controller_scale_div", width=4)
        add_field(col_right, 0, "Максимальная нагрузка на конус, кН", self.cone_kn_var, "cone_kn", width=4)
        add_field(col_right, 1, "Максимальная нагрузка на муфту трения, кН", self.sleeve_kn_var, "sleeve_kn", width=4)
        add_field(col_right, 2, "Площадь конуса, см²", self.cone_area_cm2_var, "cone_area_cm2", width=4)
        add_field(col_right, 3, "Площадь муфты, см²", self.sleeve_area_cm2_var, "sleeve_area_cm2", width=4)

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

        cols = ttk.Frame(tab)
        cols.pack(side="top", anchor="w")

        opts_col = ttk.Frame(cols)
        opts_col.grid(row=0, column=0, sticky="nw", padx=(0, 20))

        sort_col = ttk.Frame(cols)
        sort_col.grid(row=0, column=1, sticky="nw")

        compact_chk = ttk.Checkbutton(
            opts_col,
            text="Развернуть / Свернуть",
            variable=self.compact_1m_var,
            command=lambda: self.commands.get("toggle_compact_1m", lambda *_: None)(bool(self.compact_1m_var.get())),
        )
        compact_chk.pack(side="top", anchor="w", pady=(2, 0))
        ToolTip(compact_chk, "Использует текущую логику сворачивания/разворачивания вида по 1-метровым интервалам")

        graphs_chk = ttk.Checkbutton(
            opts_col,
            text="График зондирования",
            variable=self.show_graphs_var,
            command=lambda: self.commands.get("toggle_graphs", lambda *_: None)(bool(self.show_graphs_var.get())),
        )
        graphs_chk.pack(side="top", anchor="w", pady=(2, 0))
        ToolTip(graphs_chk, "Показывать графическую часть зондирования")

        geology_chk = ttk.Checkbutton(
            opts_col,
            text="Геологическая колонка",
            variable=self.show_geology_var,
            command=lambda: self.commands.get("toggle_geology_column", lambda *_: None)(bool(self.show_geology_var.get())),
        )
        geology_chk.pack(side="top", anchor="w", pady=(2, 0))
        ToolTip(geology_chk, "Показывать/скрывать геологическую колонку")

        incl_chk = ttk.Checkbutton(
            opts_col,
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

    def _build_layers_tab(self):
        tab = ttk.Frame(self.tabs, padding=4)
        self.tabs.add(tab, text="Слои")

        tools = ttk.Frame(tab)
        tools.pack(fill="x", expand=False, pady=(0, 4))
        self._add_btn_grid(tools, "add_layer", "+ Слой", "Добавить новый слой в активном опыте", 0, 0)
        self._add_btn_grid(tools, "add_ige", "+ ИГЭ", "Добавить ИГЭ без назначенного грунта", 0, 1)
        self._add_btn_grid(tools, "calc_cpt", "Рассчитать CPT", "Рассчитать qc_ср, φнорм и Eнорм по ИГЭ", 0, 2)

        host = ttk.Frame(tab)
        host.pack(fill="x", expand=False)
        self._layers_canvas = tk.Canvas(host, height=235, highlightthickness=0, bd=0)
        self._layers_hsb = ttk.Scrollbar(host, orient="horizontal", command=self._layers_canvas.xview)
        self._layers_canvas.configure(xscrollcommand=self._layers_hsb.set)
        self._layers_canvas.pack(side="top", fill="x", expand=True)
        self._layers_hsb.pack(side="top", fill="x")
        self.layers_table = ttk.Frame(self._layers_canvas)
        self._layers_window_id = self._layers_canvas.create_window((0, 0), window=self.layers_table, anchor="nw")
        self.layers_table.bind("<Configure>", lambda _e: self._sync_layers_canvas())
        self._layers_canvas.bind("<Configure>", lambda _e: self._sync_layers_canvas())

    def _sync_layers_canvas(self):
        cnv = getattr(self, "_layers_canvas", None)
        if cnv is None or not hasattr(self, "layers_table"):
            return
        try:
            cnv.configure(scrollregion=cnv.bbox("all"))
            width = max(int(cnv.winfo_width()), int(self.layers_table.winfo_reqwidth()))
            cnv.itemconfigure(self._layers_window_id, width=width)
        except Exception:
            pass

    def _build_layer_card(self, parent, row: dict, soil_values: list[str], can_delete: bool):
        layer_key = str(row.get("layer_id", "") or "")
        card = ttk.Frame(parent, padding=(4, 4), relief="solid", borderwidth=1)
        card.pack(side="left", fill="y", padx=(0, 6))

        header = ttk.Frame(card)
        header.pack(fill="x", pady=(0, 2))
        ttk.Label(header, text=f"Слой {int(row.get('visual_order', 0) or 0)}", font=("Segoe UI", 8, "bold")).pack(side="left")
        btn_del = ttk.Button(header, text=ICON_TRASH, width=3, command=lambda lk=layer_key: self._request_delete_layer(lk))
        if self.icon_font:
            try:
                style = ttk.Style(btn_del)
                style.configure("Zond.LayerTrash.TButton", font=self.icon_font)
                btn_del.configure(style="Zond.LayerTrash.TButton")
            except Exception:
                pass
        btn_del.pack(side="right")
        if not can_delete:
            btn_del.configure(state="disabled")
        ToolTip(btn_del, "Удалить слой")

        ttk.Label(card, text=str(row.get("ige_label", "") or "ИГЭ-1")).pack(anchor="w")

        grid = ttk.Frame(card)
        grid.pack(fill="x", pady=(3, 0))
        soil_var = tk.StringVar(value=str(row.get("soil", "") or ""))
        ttk.Label(grid, text="Тип").grid(row=0, column=0, sticky="w")
        cb = ttk.Combobox(grid, state="readonly", width=14, values=list(soil_values or []), textvariable=soil_var)
        cb.grid(row=1, column=0, sticky="ew")
        self._ige_controls[layer_key] = cb

        source_var = tk.StringVar(value=str(row.get("data_source", "manual") or "manual"))
        ttk.Label(grid, text="Источник").grid(row=2, column=0, sticky="w", pady=(2, 0))
        source_cb = ttk.Combobox(grid, state="readonly", width=14, values=["auto", "manual", "lab"], textvariable=source_var)
        source_cb.grid(row=3, column=0, sticky="ew")

        qc_var = tk.StringVar(value="" if row.get("qc_avg") is None else str(row.get("qc_avg")))
        ttk.Label(grid, text="qc_avg").grid(row=4, column=0, sticky="w", pady=(2, 0))
        qc_ent = ttk.Entry(grid, width=14, textvariable=qc_var)
        qc_ent.grid(row=5, column=0, sticky="ew")

        n_var = tk.StringVar(value="" if row.get("n_points") is None else str(row.get("n_points")))
        ttk.Label(grid, text="n").grid(row=6, column=0, sticky="w", pady=(2, 0))
        n_ent = ttk.Entry(grid, width=14, textvariable=n_var)
        n_ent.grid(row=7, column=0, sticky="ew")

        v_var = tk.StringVar(value="" if row.get("variation_coeff") is None else str(row.get("variation_coeff")))
        ttk.Label(grid, text="V").grid(row=8, column=0, sticky="w", pady=(2, 0))
        v_ent = ttk.Entry(grid, width=14, textvariable=v_var)
        v_ent.grid(row=9, column=0, sticky="ew")

        dynamic = ttk.Frame(card)
        dynamic.pack(fill="x", pady=(3, 0))
        self._rebuild_dynamic_fields(dynamic, row, layer_key)

        adv = ttk.Frame(card)
        adv.pack(fill="x", pady=(3, 0))
        notes_var = tk.StringVar(value=str(row.get("notes", "") or ""))
        show_adv = tk.BooleanVar(value=False)
        notes_lbl = ttk.Label(adv, text="Примеч.")
        notes_ent = ttk.Entry(adv, width=14, textvariable=notes_var)
        def _toggle_adv():
            if show_adv.get():
                notes_lbl.grid(row=1, column=0, sticky="w", pady=(2, 0))
                notes_ent.grid(row=2, column=0, sticky="ew")
            else:
                notes_lbl.grid_forget()
                notes_ent.grid_forget()
        ttk.Checkbutton(adv, text="ещё", variable=show_adv, command=_toggle_adv).grid(row=0, column=0, sticky="w")

        cb.bind("<<ComboboxSelected>>", lambda _e, lk=layer_key, sv=soil_var: self._apply_layer_soil(lk, sv.get()))
        source_cb.bind("<<ComboboxSelected>>", lambda _e, lk=layer_key, vv=source_var: self._change_layer_field(lk, "data_source", vv.get()))
        qc_ent.bind("<FocusOut>", lambda _e, lk=layer_key, vv=qc_var: self._change_layer_field(lk, "qc_avg", vv.get()))
        n_ent.bind("<FocusOut>", lambda _e, lk=layer_key, vv=n_var: self._change_layer_field(lk, "n_points", vv.get()))
        v_ent.bind("<FocusOut>", lambda _e, lk=layer_key, vv=v_var: self._change_layer_field(lk, "variation_coeff", vv.get()))
        notes_ent.bind("<FocusOut>", lambda _e, lk=layer_key, vv=notes_var: self._change_layer_field(lk, "notes", vv.get()))

    def _apply_layer_soil(self, layer_key: str, soil_value: str):
        cmd = self.commands.get("set_layer_soil")
        if callable(cmd):
            cmd(str(layer_key or ""), str(soil_value or ""))

    def _rebuild_dynamic_fields(self, holder, row: dict, layer_key: str):
        for ch in holder.winfo_children():
            ch.destroy()
        soil = str(row.get("soil", "") or "").lower()

        if "пес" in soil and "супес" not in soil:
            sk = tk.StringVar(value=str(row.get("sand_kind", "") or ""))
            ttk.Label(holder, text="Песок").grid(row=0, column=0, sticky="w")
            sk_cb = ttk.Combobox(holder, state="readonly", width=14, values=["гравелистый", "крупный", "средней крупности", "мелкий", "пылеватый"], textvariable=sk)
            sk_cb.grid(row=1, column=0, sticky="ew")
            sat = tk.StringVar(value=str(row.get("sand_water_saturation", "") or ""))
            ttk.Label(holder, text="Вода").grid(row=2, column=0, sticky="w")
            sat_cb = ttk.Combobox(holder, state="readonly", width=14, values=["малой степени", "влажный", "водонасыщенный"], textvariable=sat)
            sat_cb.grid(row=3, column=0, sticky="ew")
            dens = tk.StringVar(value=str(row.get("density_state", "") or ""))
            ttk.Label(holder, text="Плотн.").grid(row=4, column=0, sticky="w")
            dens_cb = ttk.Combobox(holder, state="readonly", width=14, values=["рыхлый", "средней плотности", "плотный"], textvariable=dens)
            dens_cb.grid(row=5, column=0, sticky="ew")
            alluvial = tk.BooleanVar(value=bool(row.get("sand_is_alluvial", False)))
            ttk.Checkbutton(holder, text="аллювиальный", variable=alluvial, command=lambda lk=layer_key, vv=alluvial: self._change_layer_field(lk, "sand_is_alluvial", bool(vv.get()))).grid(row=6, column=0, sticky="w")
            sk_cb.bind("<<ComboboxSelected>>", lambda _e, lk=layer_key, vv=sk: self._change_layer_field(lk, "sand_kind", vv.get()))
            sat_cb.bind("<<ComboboxSelected>>", lambda _e, lk=layer_key, vv=sat: self._change_layer_field(lk, "sand_water_saturation", vv.get()))
            dens_cb.bind("<<ComboboxSelected>>", lambda _e, lk=layer_key, vv=dens: self._change_layer_field(lk, "density_state", vv.get()))
            return

        if "супес" in soil:
            sl_kind = tk.StringVar(value=str(row.get("sandy_loam_kind", "") or ""))
            ttk.Label(holder, text="Супесь").grid(row=0, column=0, sticky="w")
            slk_cb = ttk.Combobox(holder, state="readonly", width=14, values=["песчанистая", "пылеватая"], textvariable=sl_kind)
            slk_cb.grid(row=1, column=0, sticky="ew")
            cons = tk.StringVar(value=str(row.get("consistency", "") or ""))
            ttk.Label(holder, text="Состояние").grid(row=2, column=0, sticky="w")
            cons_cb = ttk.Combobox(holder, state="readonly", width=14, values=["твердая", "пластичная", "текучая"], textvariable=cons)
            cons_cb.grid(row=3, column=0, sticky="ew")
            il = tk.StringVar(value="" if row.get("IL") is None else str(row.get("IL")))
            ttk.Label(holder, text="IL").grid(row=4, column=0, sticky="w")
            il_ent = ttk.Entry(holder, width=14, textvariable=il)
            il_ent.grid(row=5, column=0, sticky="ew")
            slk_cb.bind("<<ComboboxSelected>>", lambda _e, lk=layer_key, vv=sl_kind: self._change_layer_field(lk, "sandy_loam_kind", vv.get()))
            cons_cb.bind("<<ComboboxSelected>>", lambda _e, lk=layer_key, vv=cons: self._change_layer_field(lk, "consistency", vv.get()))
            il_ent.bind("<FocusOut>", lambda _e, lk=layer_key, vv=il: self._change_layer_field(lk, "IL", vv.get()))
            return

        cons = tk.StringVar(value=str(row.get("consistency", "") or ""))
        ttk.Label(holder, text="Состояние").grid(row=0, column=0, sticky="w")
        cons_cb = ttk.Combobox(holder, state="readonly", width=14, values=["твердая", "полутвердая", "тугопластичная", "мягкопластичная", "текучепластичная", "текучая"], textvariable=cons)
        cons_cb.grid(row=1, column=0, sticky="ew")
        il = tk.StringVar(value="" if row.get("IL") is None else str(row.get("IL")))
        ttk.Label(holder, text="IL").grid(row=2, column=0, sticky="w")
        il_ent = ttk.Entry(holder, width=14, textvariable=il)
        il_ent.grid(row=3, column=0, sticky="ew")
        cons_cb.bind("<<ComboboxSelected>>", lambda _e, lk=layer_key, vv=cons: self._change_layer_field(lk, "consistency", vv.get()))
        il_ent.bind("<FocusOut>", lambda _e, lk=layer_key, vv=il: self._change_layer_field(lk, "IL", vv.get()))

    def _request_delete_layer(self, layer_key: str):
        cmd = self.commands.get("delete_layer")
        if callable(cmd):
            cmd(str(layer_key or "").strip())

    def _change_layer_field(self, layer_key: str, field_name: str, value):
        cmd = self.commands.get("change_layer_field")
        if callable(cmd):
            cmd(str(layer_key or "").strip(), str(field_name or "").strip(), value)

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

    def set_layers(self, rows: list[dict], soil_values: list[str], *, can_add: bool = True, can_delete: bool = True):
        self._layer_rows = list(rows or [])
        self._ige_controls = {}
        self._layer_add_enabled = bool(can_add)
        if not hasattr(self, "layers_table"):
            return
        for child in self.layers_table.winfo_children():
            child.destroy()
        self.set_enabled("add_layer", bool(can_add), ("Достигнут лимит 12 слоёв" if not can_add else ""))

        for row in self._layer_rows:
            self._build_layer_card(self.layers_table, row, soil_values, can_delete)
        self._sync_layers_canvas()

    def focus_ige_row(self, ige_id: str):
        ig = str(ige_id or "").strip()
        cb = self._ige_controls.get(ig)
        if cb is not None:
            try:
                cb.focus_set()
            except Exception:
                pass
            self._select_ige(ig)
