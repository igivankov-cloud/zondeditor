from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.zondeditor.ui.consts import ICON_EXPORT, ICON_IMPORT, ICON_REDO, ICON_SAVE, ICON_SETTINGS, ICON_UNDO
from src.zondeditor.ui.widgets import ToolTip


class RibbonView(ttk.Frame):
    def __init__(self, master, *, commands: dict[str, callable], icon_font=None):
        super().__init__(master)
        self.commands = commands
        self.icon_font = icon_font
        self.object_name_var = tk.StringVar(value="")
        self.show_graphs_var = tk.BooleanVar(value=False)
        self.compact_1m_var = tk.BooleanVar(value=False)
        self._buttons: dict[str, ttk.Button] = {}

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
        self._build_processing_tab()

    def _add_qat_btn(self, parent, key: str, text: str, tip: str):
        btn = ttk.Button(parent, text=text, width=3, command=self.commands.get(key))
        if self.icon_font:
            # ttk.Button does not support configure(font=...). Use a style.
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

    def _build_params_tab(self):
        tab = ttk.Frame(self.tabs, padding=4)
        self.tabs.add(tab, text="Параметры")
        self._add_btn(tab, "geo_params", f"{ICON_SETTINGS} Параметры зондирований (GEO)", "Открыть параметры GEO")
        graphs_chk = ttk.Checkbutton(
            tab,
            text="Графики",
            variable=self.show_graphs_var,
            command=lambda: self.commands.get("toggle_graphs", lambda *_: None)(bool(self.show_graphs_var.get())),
        )
        graphs_chk.pack(side="top", anchor="w", pady=(4, 0))
        ToolTip(graphs_chk, "Показывать графики")
        compact_chk = ttk.Checkbutton(
            tab,
            text="Свернуть 1 м",
            variable=self.compact_1m_var,
            command=lambda: self.commands.get("toggle_compact_1m", lambda *_: None)(bool(self.compact_1m_var.get())),
        )
        compact_chk.pack(side="top", anchor="w", pady=(2, 0))
        ToolTip(compact_chk, "Свернуть таблицу/графики по 1-метровым интервалам")

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

    def set_object_name(self, value: str):
        self.object_name_var.set(value or "")

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
