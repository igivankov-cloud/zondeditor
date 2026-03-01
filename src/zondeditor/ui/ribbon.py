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
        self._buttons: dict[str, ttk.Button] = {}

        qat = ttk.Frame(self, padding=(8, 4))
        qat.pack(side="top", fill="x")
        self._add_qat_btn(qat, "undo", ICON_UNDO, "Undo")
        self._add_qat_btn(qat, "redo", ICON_REDO, "Redo")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(side="top", fill="x", padx=4, pady=(0, 4))

        self._build_file_tab()
        self._build_params_tab()
        self._build_processing_tab()

    def _add_qat_btn(self, parent, key: str, text: str, tip: str):
        btn = ttk.Button(parent, text=text, width=3, command=self.commands.get(key))
        if self.icon_font:
            btn.configure(font=self.icon_font)
        btn.pack(side="left", padx=2)
        ToolTip(btn, tip)
        self._buttons[key] = btn

    def _add_btn(self, parent, key: str, text: str, tip: str):
        btn = ttk.Button(parent, text=text, command=self.commands.get(key))
        btn.pack(side="top", fill="x", pady=2)
        ToolTip(btn, tip)
        self._buttons[key] = btn

    def _build_file_tab(self):
        tab = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(tab, text="Файл")

        project = ttk.LabelFrame(tab, text="Проект", padding=6)
        project.pack(side="left", fill="y", padx=4)
        self._add_btn(project, "new_project", "Новый проект…", "Создать новый проект")
        self._add_btn(project, "open_project", "Открыть проект…", "Открыть *.zproj")
        self._add_btn(project, "save_project", "Сохранить проект", "Сохранить *.zproj")
        self._add_btn(project, "save_project_as", "Сохранить проект как…", "Сохранить *.zproj как новый")

        obj = ttk.LabelFrame(tab, text="Объект", padding=6)
        obj.pack(side="left", fill="y", padx=4)
        ttk.Label(obj, text="Название объекта:").pack(anchor="w")
        ent = ttk.Entry(obj, textvariable=self.object_name_var, width=28)
        ent.pack(fill="x", pady=(4, 0))
        ent.bind("<FocusOut>", lambda _e: self.commands.get("object_name_changed", lambda *_: None)(self.object_name_var.get()))
        ent.bind("<Return>", lambda _e: self.commands.get("object_name_changed", lambda *_: None)(self.object_name_var.get()))

        imp = ttk.LabelFrame(tab, text="Импорт", padding=6)
        imp.pack(side="left", fill="y", padx=4)
        self._add_btn(imp, "open_geo", f"{ICON_IMPORT} Открыть GEO…", "Открыть GEO/GE0")
        self._add_btn(imp, "open_gxl", f"{ICON_IMPORT} Открыть GXL…", "Открыть GXL")

        exp = ttk.LabelFrame(tab, text="Экспорт", padding=6)
        exp.pack(side="left", fill="y", padx=4)
        self._add_btn(exp, "export_geo", f"{ICON_EXPORT} Экспорт GEO…", "Экспорт GEO только через Сохранить как")
        self._add_btn(exp, "export_gxl", f"{ICON_EXPORT} Экспорт GXL…", "Экспорт GXL только через Сохранить как")
        self._add_btn(exp, "export_excel", f"{ICON_EXPORT} Экспорт Excel…", "Экспорт Excel")
        self._add_btn(exp, "export_credo", f"{ICON_EXPORT} Экспорт CREDO/ZIP…", "Экспорт CREDO")
        self._add_btn(exp, "export_archive", "Сохранить архивом…", "Собрать ZIP с выбранными файлами")

    def _build_params_tab(self):
        tab = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(tab, text="Параметры")
        self._add_btn(tab, "geo_params", f"{ICON_SETTINGS} Параметры зондирований (GEO)", "Открыть параметры GEO")

    def _build_processing_tab(self):
        tab = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(tab, text="Обработка")

        fix = ttk.LabelFrame(tab, text="Исправление", padding=6)
        fix.pack(side="left", fill="y", padx=4)
        self._add_btn(fix, "fix_algo", "Исправить (алгоритм)", "Автоматическая корректировка")

        step = ttk.LabelFrame(tab, text="Шаг", padding=6)
        step.pack(side="left", fill="y", padx=4)
        self._add_btn(step, "reduce_step", "Уменьшить шаг…", "Преобразовать шаг")

        calc = ttk.LabelFrame(tab, text="Параметры пересчёта", padding=6)
        calc.pack(side="left", fill="y", padx=4)
        self._add_btn(calc, "apply_calc", "Применить", "Применить параметры пересчёта")

        k2k4 = ttk.LabelFrame(tab, text="К2 → К4", padding=6)
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
