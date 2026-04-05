from __future__ import annotations

# === FILE MAP BEGIN ===
# FILE MAP (обновляй при правках; указывай строки Lx–Ly)
# - _expand_roles_right: L99–L142 — предзаполнение повторяющихся блоков ролей вправо.
# - ExcelImportGrid: L145–L282 — Excel-подобная сетка (буквы столбцов, номера строк, скроллы, клики).
# - ExcelImportDialog._build_ui: L314–L347 — компактный верхний toolbar + статусный блок.
# - ExcelImportDialog._apply_autodetect/_apply_detected_settings: L379–L403 — автопредзаполнение разметки.
# - ExcelImportDialog._on_column_click/_set_column_role: L405–L420 — назначение ролей по клику на букву столбца.
# - ExcelImportDialog._on_row_click/_set_row_role: L422–L446 — назначение спец-ролей строки по клику на номер.
# - ExcelImportDialog._refresh_preview: L482–L546 — пересчёт превью, диапазона отображения и списка имён.
# - ExcelImportGrid.reset_viewport: L189–L194 — сброс viewport в начало после auto/reset.
# === FILE MAP END ===

import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.zondeditor.io.excel_import_detect import (
    MODE_BLOCKS_RIGHT,
    MODE_VERTICAL,
    ROLE_BOK,
    ROLE_DEPTH,
    ROLE_FS,
    ROLE_IGNORE,
    ROLE_LOB,
    ROLE_OBSHEE,
    ROLE_QC,
    DetectedImportSettings,
    autodetect_settings,
)
from src.zondeditor.io.excel_importer import (
    ExcelImportConfig,
    ExcelImportError,
    ImportPreview,
    WorkbookData,
    WorkbookSheet,
    build_import_preview,
    make_unique_names,
    read_excel_workbook,
)

MAX_PREVIEW_ROWS = 140
MAX_PREVIEW_COLS = 40

ROLE_LABELS = {
    ROLE_IGNORE: "Игнор",
    ROLE_DEPTH: "Глубина",
    ROLE_LOB: "Лоб",
    ROLE_BOK: "Бок",
    ROLE_OBSHEE: "Общее",
    ROLE_QC: "qc, МПа",
    ROLE_FS: "fs, кПа",
}
LABEL_TO_ROLE = {v: k for k, v in ROLE_LABELS.items()}
ROLE_COLORS = {
    ROLE_DEPTH: "#dfefff",
    ROLE_LOB: "#e4f6e7",
    ROLE_QC: "#e4f6e7",
    ROLE_BOK: "#fff0da",
    ROLE_FS: "#fff0da",
    ROLE_OBSHEE: "#f1e7fb",
    ROLE_IGNORE: "#ffffff",
}


ROW_ROLE_NORMAL = "normal"
ROW_ROLE_HEADER = "header"
ROW_ROLE_DATA = "data_start"
ROW_ROLE_IGNORE = "ignore"


@dataclass(slots=True)
class GridState:
    rows: list[list[object]]
    header_row: int
    data_start_row: int
    ignored_rows: set[int]
    column_roles: dict[int, str]


def col_to_label(index: int) -> str:
    index += 1
    out = ""
    while index > 0:
        index, rem = divmod(index - 1, 26)
        out = chr(65 + rem) + out
    return out


def _cell_text(value: object) -> str:
    if value is None:
        return ""
    txt = str(value)
    return txt if len(txt) <= 64 else (txt[:61] + "...")


def _compact_path(value: str, max_chars: int = 42) -> str:
    txt = str(value or "").strip()
    if len(txt) <= max_chars:
        return txt
    return "…" + txt[-max(8, max_chars - 1) :]


def _expand_roles_right(rows: list[list[object]], base_roles: dict[int, str], repeat_enabled: bool) -> dict[int, str]:
    if not repeat_enabled:
        return dict(base_roles)
    depth_cols = [c for c, role in base_roles.items() if role == ROLE_DEPTH]
    data_cols = sorted(c for c, role in base_roles.items() if role not in (ROLE_IGNORE, ROLE_DEPTH))
    if not depth_cols or len(data_cols) < 2:
        return dict(base_roles)

    block_start = min(data_cols)
    block_end = max(data_cols)
    width = block_end - block_start + 1
    rel_map = {c - block_start: base_roles[c] for c in range(block_start, block_end + 1) if base_roles.get(c, ROLE_IGNORE) not in (ROLE_IGNORE, ROLE_DEPTH)}
    if not rel_map:
        return dict(base_roles)

    max_cols = max((len(r) for r in rows), default=0)
    expanded = dict(base_roles)
    empty_run = 0
    block_idx = 1
    while True:
        origin = block_start + block_idx * width
        if origin >= max_cols:
            break
        has_any_non_empty = False
        for row in rows:
            segment = row[origin : min(origin + width, len(row))]
            if any(v not in (None, "") for v in segment):
                has_any_non_empty = True
                break
        if not has_any_non_empty:
            empty_run += 1
            if empty_run >= 2:
                break
            block_idx += 1
            continue

        empty_run = 0
        for rel_col, role in rel_map.items():
            col = origin + rel_col
            if col < max_cols:
                expanded[col] = role
        block_idx += 1

    return expanded


class ExcelImportGrid(ttk.Frame):
    def __init__(self, master, on_column_click, on_row_click):
        super().__init__(master)
        self.on_column_click = on_column_click
        self.on_row_click = on_row_click

        self.row_h = 24
        self.col_w = 110
        self.row_header_w = 56
        self.header_h = 26
        self.state = GridState(rows=[], header_row=1, data_start_row=2, ignored_rows=set(), column_roles={})

        self.canvas = tk.Canvas(self, background="#ffffff", highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.canvas.bind("<Configure>", lambda _e: self._redraw())
        self.canvas.bind("<Button-1>", self._handle_click)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_mouse_wheel)
        self.canvas.bind("<Button-4>", lambda _e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda _e: self.canvas.yview_scroll(1, "units"))

    def set_state(self, state: GridState):
        self.state = state
        total_w = self.row_header_w + max(1, min(MAX_PREVIEW_COLS, max((len(r) for r in state.rows), default=0))) * self.col_w
        total_h = self.header_h + max(1, min(MAX_PREVIEW_ROWS, len(state.rows))) * self.row_h
        self.canvas.configure(scrollregion=(0, 0, total_w, total_h))
        self._redraw()

    def reset_viewport(self):
        self.canvas.xview_moveto(0.0)
        self.canvas.yview_moveto(0.0)
        self._redraw()

    def _handle_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        if y <= self.header_h and x > self.row_header_w:
            col = int((x - self.row_header_w) // self.col_w)
            self.on_column_click(col, event.x_root, event.y_root)
            return

        if x <= self.row_header_w and y > self.header_h:
            row = int((y - self.header_h) // self.row_h) + 1
            self.on_row_click(row, event.x_root, event.y_root)
            return

    def _bg_for_cell(self, row_idx_1: int, col_idx: int) -> str:
        if row_idx_1 in self.state.ignored_rows:
            return "#f2f2f2"
        role = self.state.column_roles.get(col_idx, ROLE_IGNORE)
        base = ROLE_COLORS.get(role, "#ffffff")
        if row_idx_1 == self.state.header_row:
            return "#eceff3"
        if row_idx_1 == self.state.data_start_row:
            return "#fff9e6"
        return base

    def _on_mouse_wheel(self, event):
        direction = -1 if int(getattr(event, "delta", 0)) > 0 else 1
        self.canvas.yview_scroll(direction, "units")

    def _on_shift_mouse_wheel(self, event):
        direction = -1 if int(getattr(event, "delta", 0)) > 0 else 1
        self.canvas.xview_scroll(direction, "units")

    def _redraw(self):
        self.canvas.delete("all")
        rows = self.state.rows[:MAX_PREVIEW_ROWS]
        n_cols = min(MAX_PREVIEW_COLS, max((len(r) for r in rows), default=0))
        if n_cols <= 0:
            self.canvas.create_text(16, 16, anchor="nw", text="Загрузите файл, чтобы увидеть таблицу", fill="#5f6b7a")
            return

        x0 = self.canvas.canvasx(0)
        y0 = self.canvas.canvasy(0)
        x1 = x0 + self.canvas.winfo_width()
        y1 = y0 + self.canvas.winfo_height()

        col_start = max(0, int((x0 - self.row_header_w) // self.col_w))
        col_end = min(n_cols, int((x1 - self.row_header_w) // self.col_w) + 2)
        row_start = max(0, int((y0 - self.header_h) // self.row_h))
        row_end = min(len(rows), int((y1 - self.header_h) // self.row_h) + 2)

        self.canvas.create_rectangle(0, 0, self.row_header_w, self.header_h, fill="#f5f5f5", outline="#d0d0d0")

        for col in range(col_start, col_end):
            cx = self.row_header_w + col * self.col_w
            role = self.state.column_roles.get(col, ROLE_IGNORE)
            col_bg = ROLE_COLORS.get(role, "#f7f7f7")
            self.canvas.create_rectangle(cx, 0, cx + self.col_w, self.header_h, fill=col_bg, outline="#d0d0d0")
            title = col_to_label(col)
            if role != ROLE_IGNORE:
                title = f"{title} · {ROLE_LABELS.get(role, role)}"
            self.canvas.create_text(cx + 6, self.header_h / 2, anchor="w", text=title, fill="#1f2d3d", font=("Segoe UI", 9, "bold"))

        for row0 in range(row_start, row_end):
            ridx = row0 + 1
            ry = self.header_h + row0 * self.row_h
            role = ROW_ROLE_NORMAL
            if ridx == self.state.header_row:
                role = ROW_ROLE_HEADER
            elif ridx == self.state.data_start_row:
                role = ROW_ROLE_DATA
            elif ridx in self.state.ignored_rows:
                role = ROW_ROLE_IGNORE

            row_head_bg = "#f7f7f7"
            if role == ROW_ROLE_HEADER:
                row_head_bg = "#dbe2ea"
            elif role == ROW_ROLE_DATA:
                row_head_bg = "#fff2c6"
            elif role == ROW_ROLE_IGNORE:
                row_head_bg = "#ececec"
            self.canvas.create_rectangle(0, ry, self.row_header_w, ry + self.row_h, fill=row_head_bg, outline="#d0d0d0")

            row_label = str(ridx)
            if role == ROW_ROLE_HEADER:
                row_label += " [Заг]"
            elif role == ROW_ROLE_DATA:
                row_label += " [Данные]"
            elif role == ROW_ROLE_IGNORE:
                row_label += " [X]"
            self.canvas.create_text(6, ry + self.row_h / 2, anchor="w", text=row_label, fill="#34495e")

            row = rows[row0]
            for col in range(col_start, col_end):
                cx = self.row_header_w + col * self.col_w
                bg = self._bg_for_cell(ridx, col)
                self.canvas.create_rectangle(cx, ry, cx + self.col_w, ry + self.row_h, fill=bg, outline="#e0e0e0")
                value = row[col] if col < len(row) else None
                self.canvas.create_text(cx + 4, ry + self.row_h / 2, anchor="w", text=_cell_text(value), fill="#202020")


class ExcelImportDialog(tk.Toplevel):
    def __init__(self, master, existing_names: set[str] | None = None, initial_path: str | None = None):
        super().__init__(master)
        self.title("Импорт Excel (БЕТА)")
        self.geometry("1280x820")
        self.transient(master)
        self.grab_set()

        self.existing_names = set(existing_names or set())
        self.workbook: WorkbookData | None = None
        self.current_sheet: WorkbookSheet | None = None
        self.autodetected_mode = MODE_VERTICAL
        self.column_roles: dict[int, str] = {}
        self.header_row = 1
        self.data_start_row = 2
        self.ignored_rows: set[int] = set()
        self.preview: ImportPreview | None = None
        self.name_overrides: list[str] = []
        self.loaded_file_path: str = ""
        self.result: dict | None = None

        self.file_var = tk.StringVar()
        self.sheet_var = tk.StringVar()
        self.repeat_blocks_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Выберите Excel-файл (.xls/.xlsx)")
        self.preview_var = tk.StringVar(value="Тип опыта: —   |   Найдено опытов: 0   |   Диапазон глубин: —")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        if initial_path:
            self.loaded_file_path = str(initial_path)
            self.file_var.set(_compact_path(str(initial_path)))
            self._load_file(str(initial_path))

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="Файл:").pack(side="left")
        self.file_entry = ttk.Entry(top, textvariable=self.file_var, width=28, state="readonly")
        self.file_entry.pack(side="left", padx=(4, 4))
        ttk.Button(top, text="...", command=self._pick_file, width=4).pack(side="left", padx=(0, 10))

        ttk.Label(top, text="Лист:").pack(side="left")
        self.sheet_combo = ttk.Combobox(top, textvariable=self.sheet_var, state="readonly", width=24)
        self.sheet_combo.pack(side="left", padx=(4, 10))
        self.sheet_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_sheet_changed())

        ttk.Checkbutton(top, text="Повторять первый блок вправо", variable=self.repeat_blocks_var, command=self._refresh_preview).pack(side="left", padx=(0, 10))
        ttk.Button(top, text="Автоопределить", command=self._apply_autodetect).pack(side="left", padx=(0, 4))
        ttk.Button(top, text="Сбросить", command=self._reset_markup).pack(side="left", padx=(0, 10))

        ttk.Button(top, text="Импорт", command=self._on_import).pack(side="right", padx=(6, 0))
        ttk.Button(top, text="Отмена", command=self._on_cancel).pack(side="right")

        center = ttk.Frame(self, padding=(8, 0, 8, 0))
        center.pack(fill="both", expand=True)
        self.grid_view = ExcelImportGrid(center, on_column_click=self._on_column_click, on_row_click=self._on_row_click)
        self.grid_view.pack(fill="both", expand=True)

        bottom = ttk.Frame(self, padding=8)
        bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self.status_var, foreground="#345995").pack(anchor="w")
        ttk.Label(bottom, textvariable=self.preview_var).pack(anchor="w", pady=(4, 2))
        meta = ttk.Frame(bottom)
        meta.pack(fill="x")
        self.names_label = ttk.Label(meta, text="Имена: —", wraplength=1120, justify="left")
        self.names_label.pack(side="left")
        ttk.Button(meta, text="Редактировать имена", command=self._open_names_editor).pack(side="left", padx=(8, 0))

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Выберите Excel",
            filetypes=[("Excel", "*.xlsx *.xls"), ("XLSX", "*.xlsx"), ("XLS", "*.xls")],
        )
        if not path:
            return
        self.loaded_file_path = path
        self.file_var.set(_compact_path(path))
        self._load_file(path)

    def _load_file(self, path: str):
        try:
            self.workbook = read_excel_workbook(path)
        except ExcelImportError as exc:
            messagebox.showerror("Ошибка чтения Excel", str(exc), parent=self)
            self.status_var.set("Не удалось загрузить файл Excel")
            return

        names = [s.name for s in self.workbook.sheets]
        self.sheet_combo["values"] = names
        self.sheet_var.set(names[0])
        self.status_var.set("Файл загружен")
        self._on_sheet_changed()

    def _on_sheet_changed(self):
        if not self.workbook:
            return
        selected = self.sheet_var.get()
        self.current_sheet = next((s for s in self.workbook.sheets if s.name == selected), self.workbook.sheets[0])
        self._apply_autodetect()

    def _apply_autodetect(self):
        if not self.current_sheet:
            return
        detected = autodetect_settings(self.current_sheet.rows)
        self._apply_detected_settings(detected)
        self.status_var.set("Автоопределение выполнено")
        self._refresh_preview(reset_view=True)

    def _reset_markup(self):
        if not self.current_sheet:
            return
        self.column_roles = {}
        self.header_row = 1
        self.data_start_row = 2
        self.ignored_rows = set()
        self.repeat_blocks_var.set(False)
        self.autodetected_mode = MODE_VERTICAL
        self.status_var.set("Разметка сброшена")
        self._refresh_preview(reset_view=True)

    def _apply_detected_settings(self, detected: DetectedImportSettings):
        self.autodetected_mode = str(detected.mode or MODE_VERTICAL)
        self.header_row = max(1, int(detected.header_row or 1))
        self.data_start_row = max(1, int(detected.data_start_row or (self.header_row + 1)))
        self.ignored_rows = set()
        self.repeat_blocks_var.set(bool(detected.repeat_first_block))
        expanded_roles = _expand_roles_right(self.current_sheet.rows if self.current_sheet else [], dict(detected.column_roles or {}), bool(self.repeat_blocks_var.get()))
        self.column_roles = expanded_roles

    def _on_column_click(self, col: int, x_root: int, y_root: int):
        if col < 0 or col >= MAX_PREVIEW_COLS:
            return
        menu = tk.Menu(self, tearoff=0)
        for role, label in ROLE_LABELS.items():
            menu.add_command(label=label, command=lambda r=role: self._set_column_role(col, r))
        menu.tk_popup(x_root, y_root)

    def _set_column_role(self, col: int, role: str):
        if role == ROLE_DEPTH:
            for c, r in list(self.column_roles.items()):
                if r == ROLE_DEPTH:
                    self.column_roles[c] = ROLE_IGNORE
        self.column_roles[col] = role
        self.status_var.set(f"Колонка {col_to_label(col)}: {ROLE_LABELS.get(role, role)}")
        self._refresh_preview()

    def _on_row_click(self, row_1based: int, x_root: int, y_root: int):
        if row_1based < 1:
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Обычная строка", command=lambda: self._set_row_role(row_1based, ROW_ROLE_NORMAL))
        menu.add_command(label="Строка заголовков", command=lambda: self._set_row_role(row_1based, ROW_ROLE_HEADER))
        menu.add_command(label="Первая строка данных", command=lambda: self._set_row_role(row_1based, ROW_ROLE_DATA))
        menu.add_command(label="Игнорировать строку", command=lambda: self._set_row_role(row_1based, ROW_ROLE_IGNORE))
        menu.tk_popup(x_root, y_root)

    def _set_row_role(self, row_1based: int, role: str):
        if role == ROW_ROLE_HEADER:
            self.header_row = row_1based
            if row_1based in self.ignored_rows:
                self.ignored_rows.discard(row_1based)
        elif role == ROW_ROLE_DATA:
            self.data_start_row = row_1based
            if row_1based in self.ignored_rows:
                self.ignored_rows.discard(row_1based)
        elif role == ROW_ROLE_IGNORE:
            self.ignored_rows.add(row_1based)
        else:
            self.ignored_rows.discard(row_1based)
        self.status_var.set(f"Строка {row_1based}: {role}")
        self._refresh_preview()

    def _effective_mode(self) -> str:
        if bool(self.repeat_blocks_var.get()):
            return MODE_BLOCKS_RIGHT
        return MODE_BLOCKS_RIGHT if self.autodetected_mode == MODE_BLOCKS_RIGHT else MODE_VERTICAL

    def _roles_for_config(self) -> dict[int, str]:
        roles = dict(self.column_roles or {})
        if not bool(self.repeat_blocks_var.get()):
            return roles

        depth_cols = sorted(c for c, role in roles.items() if role == ROLE_DEPTH)
        data_cols = sorted(c for c, role in roles.items() if role not in (ROLE_IGNORE, ROLE_DEPTH))
        if not depth_cols or not data_cols:
            return roles

        first_by_role: dict[str, int] = {}
        for col in data_cols:
            role = roles.get(col, ROLE_IGNORE)
            if role in (ROLE_IGNORE, ROLE_DEPTH):
                continue
            if role not in first_by_role:
                first_by_role[role] = col
        cfg_roles: dict[int, str] = {depth_cols[0]: ROLE_DEPTH}
        for role, col in first_by_role.items():
            cfg_roles[col] = role
        return cfg_roles

    def _build_sheet_with_ignored_rows(self) -> WorkbookSheet | None:
        if not self.current_sheet:
            return None
        if not self.ignored_rows:
            return self.current_sheet
        rows: list[list[object]] = []
        for idx, row in enumerate(self.current_sheet.rows, start=1):
            if idx in self.ignored_rows:
                rows.append([None] * len(row))
            else:
                rows.append(list(row))
        return WorkbookSheet(name=self.current_sheet.name, rows=rows)

    def _current_config(self) -> ExcelImportConfig:
        roles = self._roles_for_config()
        return ExcelImportConfig(
            mode=self._effective_mode(),
            header_row=max(1, int(self.header_row)),
            data_start_row=max(1, int(self.data_start_row)),
            column_roles=roles,
            repeat_first_block=bool(self.repeat_blocks_var.get()),
            sounding_names=list(self.name_overrides),
        )

    def _refresh_preview(self, *, reset_view: bool = False):
        sheet = self._build_sheet_with_ignored_rows()
        if not sheet:
            self.grid_view.set_state(GridState(rows=[], header_row=1, data_start_row=2, ignored_rows=set(), column_roles={}))
            if reset_view:
                self.grid_view.reset_viewport()
            self.preview_var.set("Тип опыта: —   |   Найдено опытов: 0   |   Диапазон глубин: —")
            self.names_label.configure(text="Имена: —")
            return

        cfg = self._current_config()
        visual_roles = _expand_roles_right(sheet.rows, dict(self.column_roles or {}), bool(self.repeat_blocks_var.get()))
        self.grid_view.set_state(
            GridState(
                rows=sheet.rows,
                header_row=self.header_row,
                data_start_row=self.data_start_row,
                ignored_rows=set(self.ignored_rows),
                column_roles=visual_roles,
            )
        )
        if reset_view:
            self.grid_view.reset_viewport()

        try:
            self.preview = build_import_preview(
                sheet,
                cfg,
                fallback_name=Path(self.file_var.get() or sheet.name).stem or sheet.name,
            )
            desired_names = [s.display_name for s in self.preview.soundings]
            if self.name_overrides and len(self.name_overrides) == len(desired_names):
                desired_names = [x.strip() or desired_names[i] for i, x in enumerate(self.name_overrides)]
            self.name_overrides = make_unique_names(self.existing_names, desired_names)
            type_text = str(self.preview.detected_type) if self.preview.detected_type else "не определён"
            warn_count = len(self.preview.warnings)
            warn_suffix = "" if warn_count <= 0 else f"   |   Предупреждения: {warn_count}"
            shown_rows = min(MAX_PREVIEW_ROWS, len(sheet.rows))
            total_rows = len(sheet.rows)
            shown_cols = min(MAX_PREVIEW_COLS, max((len(r) for r in sheet.rows), default=0))
            total_cols = max((len(r) for r in sheet.rows), default=0)
            self.preview_var.set(
                f"Тип опыта: {type_text}   |   Найдено опытов: {len(self.preview.soundings)}   |   Диапазон глубин: {self.preview.min_depth}–{self.preview.max_depth}{warn_suffix}\n"
                f"Показаны первые {shown_rows} строк из {total_rows}; столбцы {shown_cols} из {total_cols}"
            )
            names_text = ", ".join(self.name_overrides)
            self.names_label.configure(text=f"Имена: {names_text or '—'}")
            if self.preview.detected_type is None:
                self.status_var.set("Не удалось полностью определить структуру, проверьте разметку вручную")
            else:
                self.status_var.set("Разметка обновлена")
        except ExcelImportError as exc:
            self.preview = None
            self.preview_var.set(f"Ошибка разбора: {exc}")
            self.names_label.configure(text="Имена: —")
            self.status_var.set("Не удалось полностью определить структуру, проверьте разметку вручную")

    def _open_names_editor(self):
        if not self.name_overrides:
            return
        win = tk.Toplevel(self)
        win.title("Имена зондирований")
        win.transient(self)
        win.grab_set()
        frm = ttk.Frame(win, padding=10)
        frm.pack(fill="both", expand=True)
        vars_: list[tk.StringVar] = []
        for i, name in enumerate(self.name_overrides, start=1):
            row = ttk.Frame(frm)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=f"{i}.", width=4).pack(side="left")
            var = tk.StringVar(value=name)
            vars_.append(var)
            ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)

        def _ok():
            proposed = [v.get().strip() or f"Зондировка {i+1}" for i, v in enumerate(vars_)]
            self.name_overrides = make_unique_names(self.existing_names, proposed)
            self._refresh_preview()
            win.destroy()

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Отмена", command=win.destroy).pack(side="right")
        ttk.Button(btns, text="ОК", command=_ok).pack(side="right", padx=(0, 6))

    def _on_import(self):
        if not self.preview or not self.current_sheet:
            messagebox.showwarning("Импорт", "Нет данных для импорта.", parent=self)
            return
        cfg = self._current_config()
        names = list(self.name_overrides or [s.display_name for s in self.preview.soundings])
        self.result = {
            "workbook_path": self.loaded_file_path or self.file_var.get(),
            "sheet_name": self.current_sheet.name,
            "config": cfg,
            "preview": self.preview,
            "names": names,
        }
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


def ask_excel_import(master, existing_names: set[str] | None = None, initial_path: str | None = None) -> dict | None:
    dlg = ExcelImportDialog(master, existing_names=existing_names, initial_path=initial_path)
    master.wait_window(dlg)
    return dlg.result
