from __future__ import annotations

import tkinter as tk
from tkinter import ttk, simpledialog

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
        self._ige_cards: dict[str, ttk.Frame] = {}
        self._ige_rows_cache: dict[str, dict] = {}
        self._ige_soil_values: list[str] = []
        self._add_ige_btn = None

        try:
            style = ttk.Style(self)
            style.configure("RibbonCompact.TButton", padding=(4, 1))
            style.configure("IGEHdr.TButton", padding=(3, 1))
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
        self._build_calc_tab()
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
        self.tabs.add(tab, text="ИГЭ")

        host = ttk.Frame(tab)
        host.pack(fill="x", expand=False)
        self._ige_canvas = tk.Canvas(host, height=190, highlightthickness=0, bd=0)
        self._ige_canvas.pack(side="top", fill="x", expand=True)

        self._ige_columns_frame = ttk.Frame(self._ige_canvas)
        self._ige_window_id = self._ige_canvas.create_window((0, 0), window=self._ige_columns_frame, anchor="nw")
        self._ige_columns_frame.bind("<Configure>", lambda _e: self._sync_ige_canvas())
        self._ige_canvas.bind("<Configure>", lambda _e: self._sync_ige_canvas())

    def _build_calc_tab(self):
        tab = ttk.Frame(self.tabs, padding=4)
        self.tabs.add(tab, text="Расчёт")
        info = ttk.LabelFrame(tab, text="Подготовка расчётных параметров", padding=6)
        info.pack(fill="x", expand=False)
        ttk.Label(info, text="Эта вкладка предназначена для статистики и расчёта (qc_avg, n, V, φ, c, E).", anchor="w").pack(fill="x")
        ttk.Label(info, text="На текущем шаге поля вынесены из вкладки ИГЭ и будут развиваться здесь.", anchor="w").pack(fill="x", pady=(2, 0))

    def _sync_ige_canvas(self):
        cnv = getattr(self, "_ige_canvas", None)
        if cnv is None:
            return
        try:
            cnv.configure(scrollregion=cnv.bbox("all"))
            width = max(int(cnv.winfo_width()), int(self._ige_columns_frame.winfo_reqwidth()))
            cnv.itemconfigure(self._ige_window_id, width=width)
        except Exception:
            pass

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

    def _set_combo_placeholder(self, cb: ttk.Combobox, var: tk.StringVar, default_value: str):
        if not str(var.get() or "").strip():
            var.set(default_value)
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

    def _build_dynamic_ige_fields(self, parent, ige_id: str, row: dict):
        soil = str(row.get("soil", "") or "").lower()
        if "пес" in soil and "супес" not in soil:
            sand_kind = tk.StringVar(value=str(row.get("sand_kind", "") or ""))
            cb_kind = ttk.Combobox(parent, state="readonly", width=18, values=["гравелистый", "крупный", "средней крупности", "мелкий", "пылеватый"], textvariable=sand_kind)
            cb_kind.grid(row=0, column=0, sticky="ew")
            self._set_combo_placeholder(cb_kind, sand_kind, "средней крупности")

            sat = tk.StringVar(value=str(row.get("sand_water_saturation", "") or ""))
            cb_sat = ttk.Combobox(parent, state="readonly", width=18, values=["малой степени", "влажный", "водонасыщенный"], textvariable=sat)
            cb_sat.grid(row=1, column=0, sticky="ew", pady=(2, 0))
            self._set_combo_placeholder(cb_sat, sat, "влажный")

            dens = tk.StringVar(value=str(row.get("density_state", "") or ""))
            cb_den = ttk.Combobox(parent, state="readonly", width=18, values=["рыхлый", "средней плотности", "плотный"], textvariable=dens)
            cb_den.grid(row=2, column=0, sticky="ew", pady=(2, 0))
            self._set_combo_placeholder(cb_den, dens, "средней плотности")

            alluvial = tk.BooleanVar(value=bool(row.get("sand_is_alluvial", False)))
            ttk.Checkbutton(parent, text="аллювиальный", variable=alluvial, command=lambda ig=ige_id, vv=alluvial: self._change_ige_field(ig, "sand_is_alluvial", bool(vv.get()))).grid(row=3, column=0, sticky="w", pady=(2, 0))

            cb_kind.bind("<<ComboboxSelected>>", lambda _e, ig=ige_id, vv=sand_kind: self._change_ige_field(ig, "sand_kind", vv.get()))
            cb_sat.bind("<<ComboboxSelected>>", lambda _e, ig=ige_id, vv=sat: self._change_ige_field(ig, "sand_water_saturation", vv.get()))
            cb_den.bind("<<ComboboxSelected>>", lambda _e, ig=ige_id, vv=dens: self._change_ige_field(ig, "density_state", vv.get()))
            return

        if "супес" in soil:
            cons = tk.StringVar(value=str(row.get("consistency", "") or ""))
            cb_cons = ttk.Combobox(parent, state="readonly", width=18, values=["твердая", "пластичная", "текучая"], textvariable=cons)
            cb_cons.grid(row=0, column=0, sticky="ew")
            self._set_combo_placeholder(cb_cons, cons, "пластичная")
            cb_cons.bind("<<ComboboxSelected>>", lambda _e, ig=ige_id, vv=cons: self._change_ige_field(ig, "consistency", vv.get()))
            return

        cons = tk.StringVar(value=str(row.get("consistency", "") or ""))
        cb_cons = ttk.Combobox(parent, state="readonly", width=18, values=["твердая", "полутвердая", "тугопластичная", "мягкопластичная", "текучепластичная", "текучая"], textvariable=cons)
        cb_cons.grid(row=0, column=0, sticky="ew")
        self._set_combo_placeholder(cb_cons, cons, "тугопластичная")
        cb_cons.bind("<<ComboboxSelected>>", lambda _e, ig=ige_id, vv=cons: self._change_ige_field(ig, "consistency", vv.get()))

    def _build_ige_column(self, parent, row: dict, soil_values: list[str], can_delete: bool):
        ige_id = str(row.get("ige_id", "") or "")
        card_w, gap, border_w = self._ige_card_metrics()
        card = ttk.Frame(parent, padding=(4, 3), relief="solid", borderwidth=border_w)
        card.pack(side="left", fill="y", padx=(0, max(2, gap)))
        try:
            card.configure(width=card_w, height=176)
            card.pack_propagate(False)
        except Exception:
            pass

        hdr = ttk.Frame(card)
        hdr.pack(fill="x")
        hdr.columnconfigure(0, weight=1)
        lbl_txt = str(row.get("label", ige_id) or ige_id)
        lbl_btn = ttk.Button(hdr, text=lbl_txt, style="IGEHdr.TButton", command=lambda ig=ige_id, txt=lbl_txt: self._edit_ige_label(ig, txt))
        lbl_btn.grid(row=0, column=0, sticky="ew")
        btn_note = ttk.Button(hdr, text="📄", width=2, style="IGEHdr.TButton", command=lambda ig=ige_id, txt=str(row.get("notes", "") or ""): self._open_ige_notes(ig, txt))
        btn_note.grid(row=0, column=1, sticky="e", padx=(0, 1))
        btn_del = ttk.Button(hdr, text=ICON_TRASH, width=2, style="IGEHdr.TButton", command=lambda ig=ige_id: self.commands.get("delete_ige", lambda *_: None)(ig))
        btn_del.grid(row=0, column=2, sticky="e")
        if not can_delete:
            btn_del.configure(state="disabled")

        body = ttk.Frame(card)
        body.pack(fill="both", expand=True, pady=(3, 0))
        body.columnconfigure(0, weight=1)
        soil_var = tk.StringVar(value=str(row.get("soil", "") or ""))
        cb_soil = ttk.Combobox(body, state="readonly", width=18, values=list(soil_values or []), textvariable=soil_var)
        cb_soil.grid(row=0, column=0, sticky="ew")
        self._set_combo_placeholder(cb_soil, soil_var, "супесь")
        cb_soil.bind("<<ComboboxSelected>>", lambda _e, ig=ige_id, sv=soil_var: self.commands.get("edit_ige", lambda *_: None)(ig, sv.get(), ""))

        dyn = ttk.Frame(body)
        dyn.grid(row=1, column=0, sticky="ew", pady=(3, 0))
        dyn.columnconfigure(0, weight=1)
        self._build_dynamic_ige_fields(dyn, ige_id, row)

    def _change_ige_field(self, ige_id: str, field_name: str, value):
        cmd = self.commands.get("change_ige_field")
        if callable(cmd):
            cmd(str(ige_id or "").strip(), str(field_name or "").strip(), value)

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

    def _rows_signature(self, row: dict) -> tuple:
        return (
            str(row.get("label", "")),
            str(row.get("soil", "")),
            str(row.get("sand_kind", "")),
            str(row.get("sand_water_saturation", "")),
            str(row.get("density_state", "")),
            bool(row.get("sand_is_alluvial", False)),
            str(row.get("consistency", "")),
            str(row.get("notes", "")),
            bool(row.get("_can_delete", True)),
        )

    def _render_ige_cards(self, rows: list[dict], soil_values: list[str], can_delete: bool):
        ids = [str(r.get("ige_id", "") or "") for r in rows]
        existing = list(self._ige_cards.keys())
        if ids != existing:
            for ch in self._ige_columns_frame.winfo_children():
                ch.destroy()
            self._ige_cards = {}
            self._ige_rows_cache = {}
            for row in rows:
                row = dict(row)
                row["_can_delete"] = bool(can_delete)
                self._build_ige_column(self._ige_columns_frame, row, soil_values, can_delete)
                self._ige_cards[str(row.get("ige_id", "") or "")] = self._ige_columns_frame.winfo_children()[-1]
                self._ige_rows_cache[str(row.get("ige_id", "") or "")] = row
            return

        for row in rows:
            rid = str(row.get("ige_id", "") or "")
            cur = dict(row)
            cur["_can_delete"] = bool(can_delete)
            if self._rows_signature(cur) == self._rows_signature(self._ige_rows_cache.get(rid, {})):
                continue
            card = self._ige_cards.get(rid)
            if card is None:
                continue
            children = list(self._ige_columns_frame.winfo_children())
            try:
                idx = children.index(card)
            except Exception:
                idx = -1
            next_sibling = None
            if idx >= 0 and idx + 1 < len(children):
                next_sibling = children[idx + 1]
            try:
                card.destroy()
            except Exception:
                continue
            self._build_ige_column(self._ige_columns_frame, cur, soil_values, can_delete)
            new_card = self._ige_columns_frame.winfo_children()[-1]
            new_card.pack_forget()
            _, gap, _ = self._ige_card_metrics()
            if next_sibling is not None and str(next_sibling) != str(getattr(self, '_add_ige_btn', None)):
                new_card.pack(side="left", fill="y", padx=(0, max(2, gap)), before=next_sibling)
            else:
                new_card.pack(side="left", fill="y", padx=(0, max(2, gap)))
            self._ige_cards[rid] = new_card
            self._ige_rows_cache[rid] = cur

    def set_layers(self, rows: list[dict], soil_values: list[str], *, can_add: bool = True, can_delete: bool = True):
        self._layer_rows = list(rows or [])
        self._ige_soil_values = list(soil_values or [])
        try:
            if self._add_ige_btn is not None:
                self._add_ige_btn.destroy()
        except Exception:
            pass
        self._add_ige_btn = None

        self._render_ige_cards(self._layer_rows, self._ige_soil_values, bool(can_delete))
        self._add_ige_btn = ttk.Button(self._ige_columns_frame, text="+ ИГЭ", style="RibbonCompact.TButton", command=self.commands.get("add_ige"))
        if not can_add:
            self._add_ige_btn.configure(state="disabled")
        _, gap, _ = self._ige_card_metrics()
        self._add_ige_btn.pack(side="left", pady=(2, 0), padx=(0, max(2, gap)))
        self._sync_ige_canvas()

    def focus_ige_row(self, ige_id: str):
        return
