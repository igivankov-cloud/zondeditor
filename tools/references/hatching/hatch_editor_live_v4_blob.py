import json
import math
import struct
import tkinter as tk
import zlib
from pathlib import Path
from dataclasses import dataclass, field, asdict
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "Мини-редактор штриховки v4"
LINE_TYPES = ["Сплошная", "Штрих", "Точка"]
SEGMENT_TYPES = ["Штрих", "Точка"]
DEFAULT_DASH = "0.300000"
DEFAULT_GAP = "3.856920"
DEFAULT_POINT_GAP = "1.000000"
# Keep disabled by default: PAT rows are emitted from the same local coordinates
# (X/dX along stroke, Y/dY across stroke) as used by the editor itself.
PAT_SWAP_LOCAL_AXES = False


def parse_float(value: str, default: float = 0.0) -> float:
    try:
        value = (value or "").strip().replace(",", ".")
        if not value:
            return default
        return float(value)
    except Exception:
        return default


def fmt6(v: float) -> str:
    return f"{v:.6f}"


def parse_angle_deg(value: str, default: float = 0.0) -> float:
    s = (value or "").strip()
    if not s:
        return default
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        pass
    try:
        s2 = s.replace("°", " ").replace("'", " ").replace('"', " ")
        parts = [p for p in s2.split() if p]
        if not parts:
            return default
        deg = float(parts[0])
        minute = float(parts[1]) if len(parts) > 1 else 0.0
        second = float(parts[2]) if len(parts) > 2 else 0.0
        sign = -1.0 if deg < 0 else 1.0
        deg = abs(deg)
        return sign * (deg + minute / 60.0 + second / 3600.0)
    except Exception:
        return default


def angle_to_dms_string(angle_deg: float) -> str:
    ang = angle_deg % 360.0
    d = int(math.floor(ang))
    m_float = (ang - d) * 60.0
    m = int(math.floor(m_float))
    s = round((m_float - m) * 60.0)
    if s >= 60:
        s = 0
        m += 1
    if m >= 60:
        m = 0
        d += 1
    d %= 360
    return f'{d}°{m:02d}\'{s:02d}"'


def color_from_hex(s: str) -> str:
    s = (s or "000000").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        s = "000000"
    try:
        int(s, 16)
        return f"#{s.lower()}"
    except Exception:
        return "#000000"


def world_to_screen(x, y, scale, cx, cy):
    return cx + x * scale, cy - y * scale


def clip_segment_to_rect(x1, y1, x2, y2, xmin, ymin, xmax, ymax):
    dx = x2 - x1
    dy = y2 - y1
    p = [-dx, dx, -dy, dy]
    q = [x1 - xmin, xmax - x1, y1 - ymin, ymax - y1]
    u1, u2 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if abs(pi) < 1e-12:
            if qi < 0:
                return None
        else:
            t = qi / pi
            if pi < 0:
                if t > u2:
                    return None
                if t > u1:
                    u1 = t
            else:
                if t < u1:
                    return None
                if t < u2:
                    u2 = t
    return x1 + u1 * dx, y1 + u1 * dy, x1 + u2 * dx, y1 + u2 * dy


def clock_basis(angle_deg: float):
    a = math.radians(angle_deg % 360.0)
    ex = (math.sin(a), math.cos(a))
    ey = (ex[1], -ex[0])
    return ex, ey


def local_to_world(angle_deg: float, lx: float, ly: float):
    ex, ey = clock_basis(angle_deg)
    return lx * ex[0] + ly * ey[0], lx * ex[1] + ly * ey[1]


@dataclass
class SegmentData:
    kind: str = "Штрих"
    dash: str = DEFAULT_DASH
    gap: str = DEFAULT_GAP


@dataclass
class RowData:
    enabled: bool = True
    angle: str = '90°00\'00"'
    dx: str = "0.000000"
    dy: str = "-6.000000"
    x: str = "0.000000"
    y: str = "-3.000000"
    color: str = "000000"
    thickness: str = "0.000000"
    line_type: str = "Сплошная"
    dash: str = DEFAULT_DASH
    gap: str = DEFAULT_GAP
    segments: list = field(default_factory=list)


def make_dash_segment(dash=DEFAULT_DASH, gap=DEFAULT_GAP):
    return {"kind": "Штрих", "dash": str(dash), "gap": str(gap)}


def make_point_segment(gap=DEFAULT_POINT_GAP):
    return {"kind": "Точка", "dash": "0.000000", "gap": str(gap)}


def infer_line_type(segments):
    if not segments:
        return "Сплошная"
    if len(segments) == 1 and (segments[0].get("kind") or "").strip() == "Точка":
        return "Точка"
    return "Штрих"


def normalize_segments(row_dict):
    segments = row_dict.get("segments") or []
    normalized = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        kind = (seg.get("kind") or "Штрих").strip()
        if kind not in SEGMENT_TYPES:
            kind = "Штрих"
        dash = seg.get("dash", DEFAULT_DASH)
        gap = seg.get("gap", DEFAULT_GAP if kind == "Штрих" else DEFAULT_POINT_GAP)
        if kind == "Точка":
            normalized.append(make_point_segment(gap=gap))
        else:
            normalized.append(make_dash_segment(dash=dash, gap=gap))
    if not normalized:
        line_type = (row_dict.get("line_type") or "Сплошная").strip()
        dash = row_dict.get("dash", DEFAULT_DASH)
        gap = row_dict.get("gap", DEFAULT_GAP)
        if line_type == "Точка":
            normalized = [make_point_segment(gap=gap or DEFAULT_POINT_GAP)]
        elif line_type == "Штрих":
            normalized = [make_dash_segment(dash=dash or DEFAULT_DASH, gap=gap or DEFAULT_GAP)]
    row_dict["segments"] = normalized
    row_dict["line_type"] = infer_line_type(normalized)
    if normalized:
        row_dict["dash"] = normalized[0].get("dash", DEFAULT_DASH)
        row_dict["gap"] = normalized[0].get("gap", DEFAULT_GAP)
    return row_dict


DEFAULT_ROWS = [
    RowData(
        enabled=True,
        angle='90°00\'00"',
        dx="0.000000",
        dy="-6.000000",
        x="0.000000",
        y="-3.000000",
        color="000000",
        thickness="0.000000",
        line_type="Сплошная",
        segments=[],
    ),
    RowData(
        enabled=True,
        angle='90°00\'00"',
        dx="10.392300",
        dy="-6.000000",
        x="-0.150000",
        y="-0.000000",
        color="000000",
        thickness="0.000000",
        line_type="Штрих",
        dash="0.300000",
        gap="3.856920",
        segments=[make_dash_segment("0.300000", "3.856920")],
    ),
    RowData(
        enabled=True,
        angle='30°00\'00"',
        dx="10.392300",
        dy="-6.000000",
        x="-3.464100",
        y="0.000000",
        color="000000",
        thickness="0.000000",
        line_type="Штрих",
        dash="6.928200",
        gap="13.856400",
        segments=[make_dash_segment("6.928200", "13.856400")],
    ),
    RowData(
        enabled=True,
        angle='330°00\'00"',
        dx="10.392300",
        dy="-6.000000",
        x="-3.464100",
        y="0.000000",
        color="000000",
        thickness="0.000000",
        line_type="Штрих",
        dash="6.928200",
        gap="13.856400",
        segments=[make_dash_segment("6.928200", "13.856400")],
    ),
]


class EditableCell(ttk.Entry):
    def __init__(self, master, textvariable, width=12, **kwargs):
        super().__init__(master, textvariable=textvariable, width=width, **kwargs)
        self.bind("<FocusIn>", self._select_all, add=True)
        self.bind("<Control-c>", self._copy, add=True)
        self.bind("<Control-C>", self._copy, add=True)
        self.bind("<Control-v>", self._paste, add=True)
        self.bind("<Control-V>", self._paste, add=True)
        self.bind("<Control-x>", self._cut, add=True)
        self.bind("<Control-X>", self._cut, add=True)

    def _select_all(self, _event=None):
        self.after(1, lambda: self.select_range(0, tk.END))

    def _selected_text(self):
        try:
            return self.selection_get()
        except Exception:
            return ""

    def _copy(self, _event=None):
        text = self._selected_text() or self.get()
        self.clipboard_clear()
        self.clipboard_append(text)
        return "break"

    def _cut(self, _event=None):
        self._copy()
        try:
            if self.selection_present():
                self.delete("sel.first", "sel.last")
            else:
                self.delete(0, tk.END)
        except Exception:
            pass
        return "break"

    def _paste(self, _event=None):
        try:
            text = self.clipboard_get()
        except Exception:
            return "break"
        try:
            if self.selection_present():
                self.delete("sel.first", "sel.last")
            else:
                self.delete(0, tk.END)
        except Exception:
            pass
        self.insert(tk.INSERT, text)
        return "break"


class HatchEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1420x860")
        self.minsize(1180, 740)

        self.rows = []
        self.selected_row = tk.IntVar(value=0)
        self.preview_scale = tk.DoubleVar(value=14.0)
        self.preview_margin = 12
        self._update_job = None
        self._suspend_selected_sync = False
        self._suspend_segment_sync = False
        self.selected_segment_index = None
        self.current_json_path: Path | None = None

        self._build_ui()
        for row in DEFAULT_ROWS:
            self.add_row(row)
        self.after(80, self.update_preview)

    def _build_ui(self):
        root = ttk.Frame(self, padding=8)
        root.pack(fill="both", expand=True)

        topbar = ttk.Frame(root)
        topbar.pack(fill="x", pady=(0, 6))

        ttk.Button(topbar, text="Добавить строку", command=self.add_empty_row).pack(side="left")
        ttk.Button(topbar, text="Копировать строку", command=self.clone_selected_row).pack(side="left", padx=6)
        ttk.Button(topbar, text="Удалить строку", command=self.delete_selected_row).pack(side="left")
        ttk.Separator(topbar, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(topbar, text="Импорт blob.bin", command=self.import_blob_file).pack(side="left")
        ttk.Button(topbar, text="Сбросить пример", command=self.reset_default).pack(side="left", padx=6)
        ttk.Button(topbar, text="Сохранить JSON", command=self.save_json).pack(side="left")
        ttk.Button(topbar, text="Загрузить JSON", command=self.load_json).pack(side="left", padx=6)
        ttk.Button(topbar, text="Экспорт AutoCAD PAT", command=self.save_autocad_pat).pack(side="left", padx=6)
        ttk.Separator(topbar, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Label(topbar, text="Масштаб, px/мм:").pack(side="left")
        scale_spin = ttk.Spinbox(topbar, from_=2, to=40, increment=1, textvariable=self.preview_scale, width=6, command=self.schedule_preview_update)
        scale_spin.pack(side="left", padx=(4, 0))
        self.preview_scale.trace_add("write", lambda *_: self.schedule_preview_update())

        paned = ttk.Panedwindow(root, orient="horizontal")
        paned.pack(fill="both", expand=True)

        left = ttk.Frame(paned, padding=(0, 0, 6, 0))
        right = ttk.Frame(paned, padding=(6, 0, 0, 0))
        paned.add(left, weight=4)
        paned.add(right, weight=2)

        table_wrap = ttk.LabelFrame(left, text="Параметры объекта")
        table_wrap.pack(fill="x")
        self.table_inner = ttk.Frame(table_wrap, padding=6)
        self.table_inner.pack(fill="x")

        headers = [
            ("Вкл", 4),
            ("", 3),
            ("Угол, град.", 14),
            ("dX, мм", 12),
            ("dY, мм", 12),
            ("X, мм", 12),
            ("Y, мм", 12),
            ("Цвет", 10),
            ("Толщина, мм", 12),
            ("Линия", 12),
        ]
        for col, (text, width) in enumerate(headers):
            ttk.Label(self.table_inner, text=text, width=width, anchor="w").grid(row=0, column=col, padx=2, pady=(0, 4), sticky="w")

        preview_wrap = ttk.LabelFrame(left, text="Просмотр объекта")
        preview_wrap.pack(fill="both", expand=True, pady=(8, 0))
        self.canvas = tk.Canvas(preview_wrap, bg="#ffffff", highlightthickness=1, highlightbackground="#bdbdbd")
        self.canvas.pack(fill="both", expand=True, padx=6, pady=6)
        self.canvas.bind("<Configure>", lambda _e: self.schedule_preview_update())

        detail_wrap = ttk.LabelFrame(right, text="Линия")
        detail_wrap.pack(fill="both", expand=False)

        info_row = ttk.Frame(detail_wrap)
        info_row.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(info_row, text="Тип строки:", width=12).pack(side="left")
        self.el_type_lbl = ttk.Label(info_row, text="—")
        self.el_type_lbl.pack(side="left")

        btns = ttk.Frame(detail_wrap)
        btns.pack(fill="x", padx=8, pady=(2, 4))
        ttk.Button(btns, text="+ Штрих", command=self.add_dash_segment).pack(side="left")
        ttk.Button(btns, text="+ Точка", command=self.add_point_segment).pack(side="left", padx=6)
        ttk.Button(btns, text="Удалить элемент", command=self.delete_selected_segment).pack(side="left")

        tree_frame = ttk.Frame(detail_wrap)
        tree_frame.pack(fill="both", expand=False, padx=8)
        self.seg_tree = ttk.Treeview(tree_frame, columns=("kind", "dash", "gap"), show="headings", height=7, selectmode="browse")
        self.seg_tree.heading("kind", text="Элемент")
        self.seg_tree.heading("dash", text="Штрих, мм")
        self.seg_tree.heading("gap", text="Пробел, мм")
        self.seg_tree.column("kind", width=90, anchor="w")
        self.seg_tree.column("dash", width=90, anchor="w")
        self.seg_tree.column("gap", width=100, anchor="w")
        self.seg_tree.pack(side="left", fill="both", expand=True)
        self.seg_tree.bind("<<TreeviewSelect>>", self.on_segment_select)
        ysb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.seg_tree.yview)
        ysb.pack(side="left", fill="y")
        self.seg_tree.configure(yscrollcommand=ysb.set)

        edit = ttk.Frame(detail_wrap)
        edit.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(edit, text="Элемент", width=12).grid(row=0, column=0, sticky="w")
        self.seg_kind_lbl = ttk.Label(edit, text="—")
        self.seg_kind_lbl.grid(row=0, column=1, sticky="w")
        ttk.Label(edit, text="Длина, мм", width=12).grid(row=0, column=2, sticky="w", padx=(10, 0))

        self.dash_label = ttk.Label(edit, text="Штрих", width=12)
        self.gap_label = ttk.Label(edit, text="Пробел", width=12)
        self.dash_label.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.gap_label.grid(row=2, column=0, sticky="w", pady=(4, 0))

        self.dash_var = tk.StringVar(value=DEFAULT_DASH)
        self.gap_var = tk.StringVar(value=DEFAULT_GAP)
        self.dash_entry = EditableCell(edit, self.dash_var, width=14)
        self.gap_entry = EditableCell(edit, self.gap_var, width=14)
        self.dash_entry.grid(row=1, column=1, sticky="w", pady=(6, 0))
        self.gap_entry.grid(row=2, column=1, sticky="w", pady=(4, 0))
        self.dash_var.trace_add("write", self._selected_segment_changed)
        self.gap_var.trace_add("write", self._selected_segment_changed)

        ttk.Separator(detail_wrap, orient="horizontal").pack(fill="x", padx=8, pady=8)

        help_text = (
            "Окончательная логика редактора:\n"
            "• X и dX — локально вдоль линии;\n"
            "• Y и dY — локально поперёк линии;\n"
            "• затем это поворачивается на угол строки.\n\n"
            "Угол: 0° вверх, далее по часовой.\n"
            "Строки можно временно отключать.\n"
            "Точка использует только ‘Пробел’.\n"
            "Ctrl+C / Ctrl+V в полях работает как копировать / вставить.\n"
            "Импорт blob.bin: JSON/zlib JSON + best-effort бинарные раскладки."
        )
        ttk.Label(detail_wrap, text=help_text, justify="left").pack(fill="x", padx=8, pady=(0, 8))

        self.status = ttk.Label(right, text="")
        self.status.pack(fill="x", pady=(8, 0))

    def make_row_vars(self, row_data: RowData):
        row_dict = asdict(row_data)
        normalize_segments(row_dict)
        vars_map = {
            "enabled": tk.BooleanVar(value=bool(row_dict.get("enabled", True))),
            "angle": tk.StringVar(value=row_dict.get("angle", '90°00\'00"')),
            "dx": tk.StringVar(value=row_dict.get("dx", "0.000000")),
            "dy": tk.StringVar(value=row_dict.get("dy", "-6.000000")),
            "x": tk.StringVar(value=row_dict.get("x", "0.000000")),
            "y": tk.StringVar(value=row_dict.get("y", "-3.000000")),
            "color": tk.StringVar(value=row_dict.get("color", "000000")),
            "thickness": tk.StringVar(value=row_dict.get("thickness", "0.000000")),
            "line_type": tk.StringVar(value=row_dict.get("line_type", "Сплошная")),
            "dash": tk.StringVar(value=row_dict.get("dash", DEFAULT_DASH)),
            "gap": tk.StringVar(value=row_dict.get("gap", DEFAULT_GAP)),
        }
        for name, var in vars_map.items():
            if name != "line_type":
                var.trace_add("write", lambda *_: self.schedule_preview_update())
        return vars_map, row_dict.get("segments", [])

    def add_row(self, row_data: RowData):
        idx = len(self.rows)
        vars_map, segments = self.make_row_vars(row_data)
        row_widgets = {}
        r = idx + 1

        cb = ttk.Checkbutton(self.table_inner, variable=vars_map["enabled"], command=self.schedule_preview_update)
        cb.grid(row=r, column=0, padx=(0, 2), pady=2)
        row_widgets["cb"] = cb

        rb = ttk.Radiobutton(self.table_inner, variable=self.selected_row, value=idx, command=self.sync_selected_panel)
        rb.grid(row=r, column=1, padx=(0, 2), pady=2)
        row_widgets["rb"] = rb

        cells = []
        fields = [
            ("angle", 14),
            ("dx", 12),
            ("dy", 12),
            ("x", 12),
            ("y", 12),
            ("color", 10),
            ("thickness", 12),
        ]
        for c, (name, width) in enumerate(fields, start=2):
            e = EditableCell(self.table_inner, vars_map[name], width=width)
            e.grid(row=r, column=c, padx=2, pady=2, sticky="we")
            cells.append(e)

        combo = ttk.Combobox(self.table_inner, textvariable=vars_map["line_type"], width=10, state="readonly", values=LINE_TYPES)
        combo.grid(row=r, column=9, padx=2, pady=2, sticky="we")
        combo.bind("<<ComboboxSelected>>", lambda _e, row_index=idx: self._line_type_changed(row_index))

        for col in range(2, 10):
            self.table_inner.grid_columnconfigure(col, weight=1 if col in (2, 9) else 0)

        self.rows.append({
            "vars": vars_map,
            "segments": [dict(seg) for seg in segments],
            "selected_segment": 0 if segments else None,
            "widgets": row_widgets,
            "entries": cells,
            "combo": combo,
            "row": r,
        })
        self.renumber_rows()
        self.selected_row.set(idx)
        self.sync_selected_panel()
        self.schedule_preview_update()

    def add_empty_row(self):
        self.add_row(RowData())

    def clone_selected_row(self):
        idx = self.get_selected_index()
        if idx is None:
            return
        data = self.get_row_data(idx)
        self.add_row(RowData(**data))

    def delete_selected_row(self):
        idx = self.get_selected_index()
        if idx is None or not self.rows:
            return
        if len(self.rows) == 1:
            messagebox.showinfo(APP_TITLE, "Должна остаться хотя бы одна строка.")
            return
        row = self.rows.pop(idx)
        for widget in row["widgets"].values():
            widget.destroy()
        for widget in row["entries"]:
            widget.destroy()
        row["combo"].destroy()
        self.rebuild_rows_ui()
        self.selected_row.set(max(0, min(idx, len(self.rows) - 1)))
        self.sync_selected_panel()
        self.schedule_preview_update()

    def rebuild_rows_ui(self):
        for i, row in enumerate(self.rows):
            r = i + 1
            row["row"] = r
            row["widgets"]["cb"].grid_configure(row=r, column=0)
            row["widgets"]["rb"].grid_configure(row=r, column=1)
            for c, widget in enumerate(row["entries"], start=2):
                widget.grid_configure(row=r, column=c)
            row["combo"].grid_configure(row=r, column=9)
            row["combo"].bind("<<ComboboxSelected>>", lambda _e, row_index=i: self._line_type_changed(row_index))
        self.renumber_rows()

    def renumber_rows(self):
        for i, row in enumerate(self.rows):
            row["widgets"]["rb"].configure(value=i)

    def get_selected_index(self):
        if not self.rows:
            return None
        idx = self.selected_row.get()
        if idx < 0 or idx >= len(self.rows):
            return 0
        return idx

    def get_row_data(self, idx):
        row = self.rows[idx]
        vars_map = row["vars"]
        data = {k: (bool(v.get()) if k == "enabled" else v.get()) for k, v in vars_map.items()}
        data["segments"] = [dict(seg) for seg in row.get("segments", [])]
        data["line_type"] = infer_line_type(data["segments"])
        return data

    def _line_type_changed(self, row_index=None):
        idx = self.get_selected_index() if row_index is None else row_index
        if idx is None:
            return
        row = self.rows[idx]
        vars_map = row["vars"]
        lt = (vars_map["line_type"].get() or "Сплошная").strip()
        if lt == "Сплошная":
            row["segments"] = []
            row["selected_segment"] = None
        elif lt == "Точка":
            gap = row["segments"][0]["gap"] if row["segments"] else vars_map["gap"].get() or DEFAULT_POINT_GAP
            row["segments"] = [make_point_segment(gap=gap)]
            row["selected_segment"] = 0
        else:
            if not row["segments"]:
                row["segments"] = [make_dash_segment(dash=vars_map["dash"].get() or DEFAULT_DASH, gap=vars_map["gap"].get() or DEFAULT_GAP)]
                row["selected_segment"] = 0
            vars_map["line_type"].set(infer_line_type(row["segments"]))
        self.sync_selected_panel()
        self.schedule_preview_update()

    def sync_selected_panel(self):
        idx = self.get_selected_index()
        if idx is None:
            return
        row = self.rows[idx]
        lt = infer_line_type(row["segments"])
        row["vars"]["line_type"].set(lt)
        self.el_type_lbl.configure(text=lt or "—")
        self.refresh_segment_tree()
        sel = row.get("selected_segment")
        if sel is None and row["segments"]:
            sel = 0
            row["selected_segment"] = 0
        if sel is not None and 0 <= sel < len(row["segments"]):
            iid = str(sel)
            if iid in self.seg_tree.get_children():
                self.seg_tree.selection_set(iid)
                self.seg_tree.focus(iid)
        else:
            self.seg_tree.selection_remove(*self.seg_tree.selection())
        self.sync_segment_editor_from_selected()
        self.schedule_preview_update()

    def refresh_segment_tree(self):
        idx = self.get_selected_index()
        if idx is None:
            return
        for iid in self.seg_tree.get_children():
            self.seg_tree.delete(iid)
        row = self.rows[idx]
        for i, seg in enumerate(row["segments"]):
            kind = seg.get("kind", "Штрих")
            dash = "" if kind == "Точка" else seg.get("dash", DEFAULT_DASH)
            gap = seg.get("gap", DEFAULT_GAP if kind == "Штрих" else DEFAULT_POINT_GAP)
            self.seg_tree.insert("", "end", iid=str(i), values=(kind, dash, gap))

    def on_segment_select(self, _event=None):
        idx = self.get_selected_index()
        if idx is None:
            return
        sel = self.seg_tree.selection()
        if not sel:
            self.rows[idx]["selected_segment"] = None
        else:
            self.rows[idx]["selected_segment"] = int(sel[0])
        self.sync_segment_editor_from_selected()

    def sync_segment_editor_from_selected(self):
        idx = self.get_selected_index()
        if idx is None:
            return
        row = self.rows[idx]
        seg_idx = row.get("selected_segment")
        self._suspend_segment_sync = True
        try:
            if seg_idx is None or seg_idx >= len(row["segments"]):
                self.seg_kind_lbl.configure(text="—")
                self.dash_var.set("")
                self.gap_var.set("")
                self.dash_entry.state(["disabled"])
                self.gap_entry.state(["disabled"])
                return
            seg = row["segments"][seg_idx]
            kind = seg.get("kind", "Штрих")
            self.seg_kind_lbl.configure(text=kind)
            if kind == "Точка":
                self.dash_label.configure(text="Точка")
                self.gap_label.configure(text="Пробел")
                self.dash_var.set(seg.get("dash", "0.000000"))
                self.gap_var.set(seg.get("gap", DEFAULT_POINT_GAP))
                self.dash_entry.state(["disabled"])
                self.gap_entry.state(["!disabled"])
            else:
                self.dash_label.configure(text="Штрих")
                self.gap_label.configure(text="Пробел")
                self.dash_var.set(seg.get("dash", DEFAULT_DASH))
                self.gap_var.set(seg.get("gap", DEFAULT_GAP))
                self.dash_entry.state(["!disabled"])
                self.gap_entry.state(["!disabled"])
        finally:
            self._suspend_segment_sync = False

    def _selected_segment_changed(self, *_):
        if self._suspend_segment_sync:
            return
        idx = self.get_selected_index()
        if idx is None:
            return
        row = self.rows[idx]
        seg_idx = row.get("selected_segment")
        if seg_idx is None or seg_idx >= len(row["segments"]):
            return
        seg = row["segments"][seg_idx]
        kind = seg.get("kind", "Штрих")
        if kind == "Точка":
            seg["dash"] = "0.000000"
            seg["gap"] = self.gap_var.get()
        else:
            seg["dash"] = self.dash_var.get()
            seg["gap"] = self.gap_var.get()
        row["vars"]["line_type"].set(infer_line_type(row["segments"]))
        if row["segments"]:
            row["vars"]["dash"].set(row["segments"][0].get("dash", DEFAULT_DASH))
            row["vars"]["gap"].set(row["segments"][0].get("gap", DEFAULT_GAP))
        self.refresh_segment_tree()
        self.seg_tree.selection_set(str(seg_idx))
        self.schedule_preview_update()

    def add_dash_segment(self):
        idx = self.get_selected_index()
        if idx is None:
            return
        row = self.rows[idx]
        insert_at = row.get("selected_segment")
        seg = make_dash_segment()
        if insert_at is None:
            row["segments"].append(seg)
            row["selected_segment"] = len(row["segments"]) - 1
        else:
            row["segments"].insert(insert_at + 1, seg)
            row["selected_segment"] = insert_at + 1
        row["vars"]["line_type"].set(infer_line_type(row["segments"]))
        self.sync_selected_panel()

    def add_point_segment(self):
        idx = self.get_selected_index()
        if idx is None:
            return
        row = self.rows[idx]
        insert_at = row.get("selected_segment")
        seg = make_point_segment()
        if insert_at is None:
            row["segments"].append(seg)
            row["selected_segment"] = len(row["segments"]) - 1
        else:
            row["segments"].insert(insert_at + 1, seg)
            row["selected_segment"] = insert_at + 1
        row["vars"]["line_type"].set(infer_line_type(row["segments"]))
        self.sync_selected_panel()

    def delete_selected_segment(self):
        idx = self.get_selected_index()
        if idx is None:
            return
        row = self.rows[idx]
        seg_idx = row.get("selected_segment")
        if seg_idx is None or seg_idx >= len(row["segments"]):
            return
        row["segments"].pop(seg_idx)
        if row["segments"]:
            row["selected_segment"] = max(0, min(seg_idx, len(row["segments"]) - 1))
        else:
            row["selected_segment"] = None
        row["vars"]["line_type"].set(infer_line_type(row["segments"]))
        self.sync_selected_panel()

    def schedule_preview_update(self):
        if self._update_job:
            self.after_cancel(self._update_job)
        self._update_job = self.after(120, self.update_preview)

    def draw_grid(self, width, height):
        step = 24
        for x in range(0, width, step):
            self.canvas.create_line(x, 0, x, height, fill="#f0f0f0")
        for y in range(0, height, step):
            self.canvas.create_line(0, y, width, y, fill="#f0f0f0")

    def _draw_point(self, x, y, color, scale, cx, cy, thickness_mm):
        dot_r_px = max(1, int(round(max(0.15, thickness_mm if thickness_mm > 0 else 0.15) * scale * 0.35)))
        sx, sy = world_to_screen(x, y, scale, cx, cy)
        self.canvas.create_oval(sx - dot_r_px, sy - dot_r_px, sx + dot_r_px, sy + dot_r_px, fill=color, outline=color)
        return 1

    def _draw_pattern_sequence(self, px, py, ux, uy, t1, t2, segments, color, scale, cx, cy, thickness_mm, line_px):
        parts = []
        total = 0.0
        for seg in segments:
            kind = (seg.get("kind") or "Штрих").strip()
            if kind == "Точка":
                gap = max(1e-9, parse_float(seg.get("gap"), 1.0))
                parts.append(("Точка", 0.0, gap))
                total += gap
            else:
                dash = max(0.0, parse_float(seg.get("dash"), 0.3))
                gap = max(0.0, parse_float(seg.get("gap"), 3.8))
                parts.append(("Штрих", dash, gap))
                total += max(1e-9, dash + gap)
        if total <= 1e-9:
            return 0

        drawn = 0
        n_start = math.floor(t1 / total) - 1
        n_end = math.ceil(t2 / total) + 1
        for n in range(n_start, n_end + 1):
            cursor = n * total
            for kind, dash, gap in parts:
                if kind == "Точка":
                    t = cursor
                    if t1 <= t <= t2:
                        x = px + t * ux
                        y = py + t * uy
                        drawn += self._draw_point(x, y, color, scale, cx, cy, thickness_mm)
                    cursor += gap
                else:
                    a = cursor
                    b = cursor + dash
                    if b >= t1 and a <= t2 and b > a:
                        sa = max(t1, a)
                        sb = min(t2, b)
                        if sb > sa:
                            ax = px + sa * ux
                            ay = py + sa * uy
                            bx = px + sb * ux
                            by = py + sb * uy
                            sx1, sy1 = world_to_screen(ax, ay, scale, cx, cy)
                            sx2, sy2 = world_to_screen(bx, by, scale, cx, cy)
                            self.canvas.create_line(sx1, sy1, sx2, sy2, fill=color, width=line_px)
                            drawn += 1
                    cursor += dash + gap
        return drawn

    def update_preview(self):
        self._update_job = None
        self.canvas.delete("all")
        width = max(200, self.canvas.winfo_width())
        height = max(160, self.canvas.winfo_height())
        self.draw_grid(width, height)

        margin = self.preview_margin
        xmin_s, ymin_s, xmax_s, ymax_s = margin, margin, width - margin, height - margin
        self.canvas.create_rectangle(xmin_s, ymin_s, xmax_s, ymax_s, outline="#8e8e8e")

        scale = max(1.0, parse_float(str(self.preview_scale.get()), 14.0))
        cx = width / 2.0
        cy = height / 2.0
        xmin = (xmin_s - cx) / scale
        xmax = (xmax_s - cx) / scale
        ymin = -(ymax_s - cy) / scale
        ymax = -(ymin_s - cy) / scale
        diag = math.hypot(xmax - xmin, ymax - ymin)

        errors = []
        drawn = 0
        enabled_count = 0
        for i, row in enumerate(self.rows):
            v = row["vars"]
            if not bool(v["enabled"].get()):
                continue
            enabled_count += 1
            try:
                angle = parse_angle_deg(v["angle"].get(), 0.0)
                dx_local = parse_float(v["dx"].get(), 0.0)
                dy_local = parse_float(v["dy"].get(), 0.0)
                x_local = parse_float(v["x"].get(), 0.0)
                y_local = parse_float(v["y"].get(), 0.0)
                color = color_from_hex(v["color"].get())
                thickness_mm = parse_float(v["thickness"].get(), 0.0)
                line_type = infer_line_type(row["segments"])

                ex, ey = clock_basis(angle)
                ux, uy = ex
                base_x, base_y = local_to_world(angle, x_local, y_local)
                step_x, step_y = local_to_world(angle, dx_local, dy_local)
                perp_step = step_x * ey[0] + step_y * ey[1]
                line_px = max(1, int(round(max(0.0, thickness_mm) * scale)))

                if abs(perp_step) < 1e-9:
                    k_values = [0]
                else:
                    kmax = int(diag / abs(perp_step)) + 6
                    k_values = range(-kmax, kmax + 1)

                half_len = diag * 2.5
                for k in k_values:
                    px = base_x + k * step_x
                    py = base_y + k * step_y

                    x1 = px - ux * half_len
                    y1 = py - uy * half_len
                    x2 = px + ux * half_len
                    y2 = py + uy * half_len
                    clipped = clip_segment_to_rect(x1, y1, x2, y2, xmin, ymin, xmax, ymax)
                    if not clipped:
                        continue
                    cx1, cy1, cx2, cy2 = clipped
                    t1 = (cx1 - px) * ux + (cy1 - py) * uy
                    t2 = (cx2 - px) * ux + (cy2 - py) * uy
                    if t2 < t1:
                        t1, t2 = t2, t1

                    if line_type == "Сплошная" or not row["segments"]:
                        sx1, sy1 = world_to_screen(cx1, cy1, scale, cx, cy)
                        sx2, sy2 = world_to_screen(cx2, cy2, scale, cx, cy)
                        self.canvas.create_line(sx1, sy1, sx2, sy2, fill=color, width=line_px)
                        drawn += 1
                    else:
                        drawn += self._draw_pattern_sequence(
                            px, py, ux, uy, t1, t2, row["segments"], color, scale, cx, cy, thickness_mm, line_px
                        )
            except Exception as e:
                errors.append(f"Строка {i + 1}: {e}")

        text = f"Строк: {len(self.rows)}   Включено: {enabled_count}   Отрисовано элементов: {drawn}"
        if errors:
            text += f"   Ошибки: {len(errors)}"
        self.status.configure(text=text)
        if errors:
            self.canvas.create_text(14, 14, anchor="nw", fill="#b00020", text=errors[0])

    def _clear_rows(self):
        for row in self.rows[:]:
            for widget in row["widgets"].values():
                widget.destroy()
            for widget in row["entries"]:
                widget.destroy()
            row["combo"].destroy()
        self.rows.clear()
        self.selected_row.set(0)
        for iid in self.seg_tree.get_children():
            self.seg_tree.delete(iid)

    def reset_default(self):
        self._clear_rows()
        for row in DEFAULT_ROWS:
            self.add_row(row)
        self.sync_selected_panel()
        self.schedule_preview_update()

    def collect_data(self):
        return [self.get_row_data(i) for i in range(len(self.rows))]

    def save_json(self):
        initial_name = self.current_json_path.name if self.current_json_path else None
        path = filedialog.asksaveasfilename(
            title="Сохранить параметры",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Все файлы", "*.*")],
            initialfile=initial_name,
        )
        if not path:
            return
        payload = {"rows": self.collect_data(), "scale": self.preview_scale.get()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        self.current_json_path = Path(path)

    def _row_to_pat_descriptor(self, row):
        # Editor math:
        # - angle 0° points UP and grows clockwise
        # - local X/dX are along line direction
        # - local Y/dY are across line direction
        #
        # AutoCAD PAT expects:
        # - angle from +X axis, CCW
        # - base point and offsets in world XY
        angle_editor = parse_angle_deg(row.get("angle"), 0.0)
        angle_pat = (90.0 - angle_editor) % 360.0
        x = parse_float(row.get("x"), 0.0)
        y = parse_float(row.get("y"), 0.0)
        dx = parse_float(row.get("dx"), 0.0)
        dy = parse_float(row.get("dy"), 0.0)
        # Optional legacy compatibility switch for very old blobs.
        # Main path keeps coordinates unchanged.
        if PAT_SWAP_LOCAL_AXES:
            x, y = y, x
        # PAT expects local definition row values after angle conversion:
        # use editor-local X/Y/dX/dY directly to preserve pattern phase.
        parts = [fmt6(angle_pat), fmt6(x), fmt6(y), fmt6(dx), fmt6(dy)]
        segments = list(row.get("segments") or [])
        if segments:
            for seg in segments:
                kind = (seg.get("kind") or "Штрих").strip()
                if kind == "Точка":
                    gap = max(1e-9, parse_float(seg.get("gap"), 1.0))
                    parts.append("0")
                    parts.append(fmt6(-gap))
                else:
                    dash = max(0.0, parse_float(seg.get("dash"), 0.3))
                    gap = max(0.0, parse_float(seg.get("gap"), 3.85692))
                    if dash > 0.0:
                        parts.append(fmt6(dash))
                    if gap > 0.0:
                        parts.append(fmt6(-gap))
        return ", ".join(parts)

    def save_autocad_pat(self):
        initial_pat_name = f"{self.current_json_path.stem}.pat" if self.current_json_path else None
        path = filedialog.asksaveasfilename(
            title="Экспорт AutoCAD PAT",
            defaultextension=".pat",
            filetypes=[("AutoCAD Pattern", "*.pat"), ("Все файлы", "*.*")],
            initialfile=initial_pat_name,
        )
        if not path:
            return
        rows = [r for r in self.collect_data() if bool(r.get("enabled", True))]
        if not rows:
            messagebox.showerror(APP_TITLE, "Нет включённых строк для экспорта в PAT.")
            return
        pat_name = Path(path).stem
        lines = [f"*{pat_name}, Generated by {APP_TITLE}"]
        for row in rows:
            lines.append(self._row_to_pat_descriptor(row))
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        messagebox.showinfo(APP_TITLE, f"PAT сохранён:\n{path}")

    def _load_payload(self, payload):
        rows = payload.get("rows", [])
        if not isinstance(rows, list) or not rows:
            messagebox.showerror(APP_TITLE, "В файле нет строк штриховки.")
            return
        self._clear_rows()
        for item in rows:
            base = asdict(RowData())
            if isinstance(item, dict):
                base.update(item)
            normalize_segments(base)
            self.add_row(RowData(**base))
        self.preview_scale.set(str(payload.get("scale", self.preview_scale.get())))
        self.selected_row.set(0)
        self.sync_selected_panel()
        self.schedule_preview_update()

    def load_json(self):
        path = filedialog.askopenfilename(title="Загрузить параметры", filetypes=[("JSON", "*.json"), ("Все файлы", "*.*")])
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        self._load_payload(payload)
        self.current_json_path = Path(path)

    def import_blob_file(self):
        path = filedialog.askopenfilename(
            title="Импорт blob.bin",
            filetypes=[("BIN/Blob", "*.bin *.blob"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            payload, info = self._parse_blob_file(path)
            self._load_payload(payload)
            messagebox.showinfo(APP_TITLE, f"Импорт выполнен.\n{info}")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Не удалось импортировать blob.bin:\n{e}")

    def _parse_blob_file(self, path):
        with open(path, "rb") as f:
            data = f.read()
        # 1) plain JSON
        json_candidates = [("JSON", data)]
        if len(data) > 2 and data[:2] in (b"x\x9c", b"x\xda"):
            try:
                json_candidates.append(("zlib+JSON", zlib.decompress(data)))
            except Exception:
                pass
        for decoder_name, raw in json_candidates:
            if raw is None:
                continue
            try:
                payload = json.loads(raw.decode("utf-8"))
                if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
                    return payload, f"Формат: {decoder_name}. Строк: {len(payload['rows'])}"
                if isinstance(payload, list):
                    return {"rows": payload, "scale": self.preview_scale.get()}, f"Формат: {decoder_name}. Строк: {len(payload)}"
            except Exception:
                pass

        # 2) binary layouts (best effort)
        payload, info = self._try_binary_layouts(data)
        if payload:
            return payload, info
        raise ValueError("Формат не распознан. Сейчас поддерживаются JSON, zlib+JSON и несколько типовых бинарных раскладок little-endian.")

    def _try_binary_layouts(self, data):
        candidates = []

        def row_from_type(type_code, angle, dx, dy, x, y, dash, gap, enabled=True):
            type_code = int(round(type_code))
            if type_code == 0:
                segments = []
            elif type_code == 2:
                segments = [make_point_segment(gap=fmt6(gap))]
            else:
                segments = [make_dash_segment(fmt6(dash), fmt6(gap))]
            row = {
                "enabled": bool(enabled),
                "angle": angle_to_dms_string(angle),
                "dx": fmt6(dx),
                "dy": fmt6(dy),
                "x": fmt6(x),
                "y": fmt6(y),
                "color": "000000",
                "thickness": "0.000000",
                "line_type": infer_line_type(segments),
                "dash": fmt6(dash),
                "gap": fmt6(gap),
                "segments": segments,
            }
            return row

        def plausible(row):
            try:
                angle = parse_angle_deg(row["angle"], 0.0)
                return (
                    -360.001 <= angle <= 360.001
                    and abs(parse_float(row["dx"], 0.0)) < 1e6
                    and abs(parse_float(row["dy"], 0.0)) < 1e6
                    and abs(parse_float(row["x"], 0.0)) < 1e6
                    and abs(parse_float(row["y"], 0.0)) < 1e6
                    and 0.0 <= parse_float(row["gap"], 0.0) < 1e6
                    and 0.0 <= parse_float(row["dash"], 0.0) < 1e6
                )
            except Exception:
                return False

        layouts = [
            ("<i7d", lambda t: row_from_type(*t)),
            ("<2i7d", lambda t: row_from_type(t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8], enabled=bool(t[0]))),
            ("<8d", lambda t: row_from_type(t[7], t[0], t[1], t[2], t[3], t[4], t[5], t[6])),
            ("<i7f", lambda t: row_from_type(*t)),
            ("<2i7f", lambda t: row_from_type(t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8], enabled=bool(t[0]))),
            ("<8f", lambda t: row_from_type(t[7], t[0], t[1], t[2], t[3], t[4], t[5], t[6])),
        ]

        for fmt, mapper in layouts:
            size = struct.calcsize(fmt)
            for offset in range(0, min(size, 16)):
                if len(data) - offset < size:
                    continue
                count = (len(data) - offset) // size
                if count < 1:
                    continue
                rows = []
                bad = 0
                pos = offset
                for _ in range(count):
                    chunk = data[pos:pos + size]
                    pos += size
                    try:
                        values = struct.unpack(fmt, chunk)
                        row = mapper(values)
                        if plausible(row):
                            rows.append(row)
                        else:
                            bad += 1
                    except Exception:
                        bad += 1
                if rows and bad <= len(rows) * 2:
                    score = len(rows) * 10 - bad - offset * 0.1
                    candidates.append((score, {"rows": rows, "scale": self.preview_scale.get()}, f"Бинарный формат {fmt}, offset={offset}, строк={len(rows)}, отбраковано={bad}"))

        # variants with count prefix
        for fmt, mapper in layouts:
            size = struct.calcsize(fmt)
            for count_fmt in ("<I", "<Q"):
                cnt_size = struct.calcsize(count_fmt)
                if len(data) < cnt_size + size:
                    continue
                try:
                    count = struct.unpack(count_fmt, data[:cnt_size])[0]
                except Exception:
                    continue
                if count <= 0 or count > 100000:
                    continue
                rows = []
                pos = cnt_size
                for _ in range(count):
                    if pos + size > len(data):
                        break
                    chunk = data[pos:pos + size]
                    pos += size
                    try:
                        row = mapper(struct.unpack(fmt, chunk))
                        if plausible(row):
                            rows.append(row)
                    except Exception:
                        pass
                if rows:
                    score = len(rows) * 10 + 1
                    candidates.append((score, {"rows": rows, "scale": self.preview_scale.get()}, f"Бинарный формат {count_fmt}+{fmt}, строк={len(rows)}"))

        if not candidates:
            return None, None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1], candidates[0][2]


def main():
    app = HatchEditorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
