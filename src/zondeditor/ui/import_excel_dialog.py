from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.zondeditor.io.excel_import_detect import (
    MODE_BLOCKS_RIGHT,
    MODE_VERTICAL,
    ROLE_BOK,
    ROLE_DEPTH,
    ROLE_EXTRA,
    ROLE_FS,
    ROLE_IGNORE,
    ROLE_LOB,
    ROLE_OBSHEE,
    ROLE_QC,
    autodetect_settings,
)
from src.zondeditor.io.excel_importer import (
    ExcelImportConfig,
    ExcelImportError,
    ImportPreview,
    WorkbookData,
    WorkbookSheet,
    build_import_preview,
    read_excel_workbook,
)

ROLE_LABELS = {
    ROLE_IGNORE: "Игнор",
    ROLE_DEPTH: "Глубина",
    ROLE_LOB: "Лоб",
    ROLE_BOK: "Бок",
    ROLE_OBSHEE: "Общее",
    ROLE_QC: "qc, МПа",
    ROLE_FS: "fs, кПа",
    ROLE_EXTRA: "Доп. поле",
}
LABEL_TO_ROLE = {v: k for k, v in ROLE_LABELS.items()}


class ExcelImportDialog(tk.Toplevel):
    def __init__(self, master, existing_names: set[str] | None = None):
        super().__init__(master)
        self.title("Импорт Excel (БЕТА)")
        self.geometry("1200x760")
        self.transient(master)
        self.grab_set()

        self.existing_names = set(existing_names or set())
        self.workbook: WorkbookData | None = None
        self.current_sheet: WorkbookSheet | None = None
        self.column_role_vars: dict[int, tk.StringVar] = {}
        self.name_vars: list[tk.StringVar] = []
        self.preview: ImportPreview | None = None
        self.result: dict | None = None

        self.file_var = tk.StringVar()
        self.sheet_var = tk.StringVar()
        self.mode_var = tk.StringVar(value=MODE_VERTICAL)
        self.header_row_var = tk.IntVar(value=1)
        self.data_start_var = tk.IntVar(value=2)
        self.repeat_blocks_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Выберите файл Excel")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Файл:").pack(side="left")
        ttk.Entry(top, textvariable=self.file_var, width=70).pack(side="left", padx=6)
        ttk.Button(top, text="...", command=self._pick_file, width=4).pack(side="left")

        ttk.Label(top, text="Лист:").pack(side="left", padx=(16, 4))
        self.sheet_combo = ttk.Combobox(top, textvariable=self.sheet_var, state="readonly", width=24)
        self.sheet_combo.pack(side="left")
        self.sheet_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_sheet_changed())

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=6)

        left = ttk.Frame(body)
        body.add(left, weight=3)
        right = ttk.Frame(body)
        body.add(right, weight=2)

        self.preview_table = ttk.Treeview(left, columns=[str(i) for i in range(20)], show="headings", height=22)
        for i in range(20):
            self.preview_table.heading(str(i), text=f"{i+1}")
            self.preview_table.column(str(i), width=90, stretch=False)
        self.preview_table.pack(fill="both", expand=True)

        settings = ttk.LabelFrame(right, text="Настройки")
        settings.pack(fill="x", padx=4, pady=(0, 6))
        ttk.Radiobutton(settings, text="Один опыт вниз", variable=self.mode_var, value=MODE_VERTICAL, command=self._refresh_preview).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(settings, text="Блоки вправо", variable=self.mode_var, value=MODE_BLOCKS_RIGHT, command=self._refresh_preview).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(settings, text="Повторять первый блок вправо", variable=self.repeat_blocks_var, command=self._refresh_preview).grid(row=2, column=0, sticky="w")

        ttk.Label(settings, text="Строка заголовков").grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(settings, from_=1, to=9999, textvariable=self.header_row_var, width=8, command=self._refresh_preview).grid(row=4, column=0, sticky="w")
        ttk.Label(settings, text="Первая строка данных").grid(row=5, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(settings, from_=1, to=9999, textvariable=self.data_start_var, width=8, command=self._refresh_preview).grid(row=6, column=0, sticky="w")

        cols = ttk.LabelFrame(right, text="Роли столбцов (первые 20)")
        cols.pack(fill="both", expand=True, padx=4, pady=(0, 6))
        self.roles_host = ttk.Frame(cols)
        self.roles_host.pack(fill="both", expand=True)

        result = ttk.LabelFrame(right, text="Превью результата")
        result.pack(fill="both", expand=True, padx=4)
        self.result_text = tk.Text(result, height=8)
        self.result_text.pack(fill="x")
        self.names_host = ttk.Frame(result)
        self.names_host.pack(fill="both", expand=True)

        bottom = ttk.Frame(self, padding=8)
        bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self.status_var, foreground="#2f4f7f").pack(side="left")
        ttk.Button(bottom, text="Отмена", command=self._on_cancel).pack(side="right")
        ttk.Button(bottom, text="Импорт", command=self._on_import).pack(side="right", padx=(0, 6))

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Выберите Excel",
            filetypes=[("Excel", "*.xlsx *.xls"), ("XLSX", "*.xlsx"), ("XLS", "*.xls")],
        )
        if not path:
            return
        self.file_var.set(path)
        self._load_file(path)

    def _load_file(self, path: str):
        try:
            self.workbook = read_excel_workbook(path)
        except ExcelImportError as exc:
            messagebox.showerror("Ошибка импорта Excel", str(exc), parent=self)
            return
        names = [s.name for s in self.workbook.sheets]
        self.sheet_combo["values"] = names
        self.sheet_var.set(names[0])
        self._on_sheet_changed()

    def _on_sheet_changed(self):
        if not self.workbook:
            return
        target = self.sheet_var.get()
        self.current_sheet = next((s for s in self.workbook.sheets if s.name == target), self.workbook.sheets[0])
        settings = autodetect_settings(self.current_sheet.rows)
        self.mode_var.set(settings.mode)
        self.header_row_var.set(settings.header_row)
        self.data_start_var.set(settings.data_start_row)
        self.repeat_blocks_var.set(settings.repeat_first_block)
        self.column_role_vars = {}
        self._render_column_roles(settings.column_roles)
        self._render_sheet_preview()
        self._refresh_preview()

    def _render_sheet_preview(self):
        self.preview_table.delete(*self.preview_table.get_children())
        if not self.current_sheet:
            return
        for i, row in enumerate(self.current_sheet.rows[:100], start=1):
            vals = [("" if c is None else str(c)) for c in row[:20]]
            while len(vals) < 20:
                vals.append("")
            self.preview_table.insert("", "end", values=vals)

    def _render_column_roles(self, detected: dict[int, str]):
        for w in self.roles_host.winfo_children():
            w.destroy()
        if not self.current_sheet:
            return
        header_idx = max(0, self.header_row_var.get() - 1)
        header = self.current_sheet.rows[header_idx] if header_idx < len(self.current_sheet.rows) else []
        for col in range(20):
            h = header[col] if col < len(header) else ""
            frm = ttk.Frame(self.roles_host)
            frm.pack(fill="x", padx=2, pady=1)
            ttk.Label(frm, text=f"{col+1}. {h}", width=28).pack(side="left")
            var = self.column_role_vars.get(col) or tk.StringVar(value=ROLE_LABELS.get(detected.get(col, ROLE_IGNORE), "Игнор"))
            self.column_role_vars[col] = var
            cb = ttk.Combobox(frm, textvariable=var, values=list(ROLE_LABELS.values()), width=14, state="readonly")
            cb.pack(side="left")
            cb.bind("<<ComboboxSelected>>", lambda _e: self._refresh_preview())

    def _current_config(self) -> ExcelImportConfig | None:
        if not self.current_sheet:
            return None
        roles: dict[int, str] = {}
        for col, var in self.column_role_vars.items():
            roles[col] = LABEL_TO_ROLE.get(var.get(), ROLE_IGNORE)
        return ExcelImportConfig(
            mode=self.mode_var.get(),
            header_row=max(1, int(self.header_row_var.get())),
            data_start_row=max(1, int(self.data_start_var.get())),
            column_roles=roles,
            repeat_first_block=bool(self.repeat_blocks_var.get()),
            sounding_names=[v.get().strip() for v in self.name_vars],
        )

    def _refresh_preview(self):
        cfg = self._current_config()
        if not cfg or not self.current_sheet:
            return
        try:
            self.preview = build_import_preview(
                self.current_sheet,
                cfg,
                fallback_name=Path(self.file_var.get() or self.current_sheet.name).stem or self.current_sheet.name,
            )
        except ExcelImportError as exc:
            self.preview = None
            self.result_text.delete("1.0", "end")
            self.result_text.insert("1.0", f"Ошибка: {exc}")
            self.status_var.set(str(exc))
            return

        self.result_text.delete("1.0", "end")
        self.result_text.insert(
            "1.0",
            (
                f"Тип опыта: {self.preview.detected_type or 'не определён'}\n"
                f"Количество опытов: {len(self.preview.soundings)}\n"
                f"Диапазон глубин: {self.preview.min_depth} .. {self.preview.max_depth}\n"
                f"Предупреждения: {len(self.preview.warnings)}"
            ),
        )
        self.status_var.set("Готово к импорту" if self.preview.soundings else "Нет данных")
        self._render_name_editors()

    def _render_name_editors(self):
        for w in self.names_host.winfo_children():
            w.destroy()
        self.name_vars = []
        if not self.preview:
            return
        for i, snd in enumerate(self.preview.soundings, start=1):
            frm = ttk.Frame(self.names_host)
            frm.pack(fill="x", pady=1)
            ttk.Label(frm, text=f"{i}:", width=3).pack(side="left")
            var = tk.StringVar(value=snd.display_name)
            self.name_vars.append(var)
            ttk.Entry(frm, textvariable=var).pack(side="left", fill="x", expand=True)

    def _on_import(self):
        if not self.preview or not self.current_sheet:
            messagebox.showwarning("Импорт", "Нет данных для импорта.", parent=self)
            return
        cfg = self._current_config()
        if not cfg:
            return
        names = [v.get().strip() or f"Зондировка {i+1}" for i, v in enumerate(self.name_vars)]
        self.result = {
            "workbook_path": self.file_var.get(),
            "sheet_name": self.current_sheet.name,
            "config": cfg,
            "preview": self.preview,
            "names": names,
        }
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


def ask_excel_import(master, existing_names: set[str] | None = None) -> dict | None:
    dlg = ExcelImportDialog(master, existing_names=existing_names)
    master.wait_window(dlg)
    return dlg.result
