from __future__ import annotations

import datetime as _dt
import tkinter as tk
from tkinter import ttk

_MONTHS_RU = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]


class ToolTip:
    """Simple tooltip for tkinter widgets."""

    def __init__(self, widget, text: str, delay_ms: int = 450):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id = None
        self.tip = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, _evt=None):
        self._schedule()

    def _on_leave(self, _evt=None):
        self._unschedule()
        self._hide()

    def _schedule(self):
        self._unschedule()
        try:
            self._after_id = self.widget.after(self.delay_ms, self._show)
        except Exception:
            self._after_id = None

    def _unschedule(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        if self.tip or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
            self.tip = tk.Toplevel(self.widget)
            self.tip.wm_overrideredirect(True)
            self.tip.wm_geometry(f"+{x}+{y}")
            lbl = tk.Label(
                self.tip,
                text=self.text,
                justify="left",
                background="#ffffe0",
                relief="solid",
                borderwidth=1,
                font=("Segoe UI", 9),
            )
            lbl.pack(ipadx=6, ipady=3)
        except Exception:
            self.tip = None

    def _hide(self):
        if self.tip is not None:
            try:
                self.tip.destroy()
            except Exception:
                pass
            self.tip = None


class CalendarDialog(tk.Toplevel):
    """Calendar dialog without external deps. Returns selected date via self.selected."""

    def __init__(self, parent, initial: _dt.date | None = None, title: str = "Выбор даты"):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.selected: _dt.date | None = None
        self._max_date = _dt.date.today()

        self._cur = initial or self._max_date
        if self._cur > self._max_date:
            self._cur = self._max_date

        self._view_year = self._cur.year
        self._view_month = self._cur.month

        self._hdr = ttk.Frame(self)
        self._hdr.pack(fill="x", padx=10, pady=(10, 0))

        self._btn_prev = ttk.Button(self._hdr, text="◀", width=3, command=self._prev_month)
        self._btn_prev.pack(side="left")
        self._lbl = ttk.Label(self._hdr, text="", width=18, anchor="center")
        self._lbl.pack(side="left", padx=6)
        self._btn_next = ttk.Button(self._hdr, text="▶", width=3, command=self._next_month)
        self._btn_next.pack(side="left")

        self._grid = ttk.Frame(self)
        self._grid.pack(padx=10, pady=10)

        self._build()

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Сегодня", command=self._pick_today).pack(side="left")
        ttk.Button(btns, text="Отмена", command=self._cancel).pack(side="right")

        self.bind("<Escape>", lambda _e: self._cancel())

    def _prev_month(self):
        month = self._view_month - 1
        year = self._view_year
        if month == 0:
            month = 12
            year -= 1
        self._view_year, self._view_month = year, month
        self._build()

    def _next_month(self):
        max_y, max_m = self._max_date.year, self._max_date.month
        if (self._view_year, self._view_month) >= (max_y, max_m):
            return
        month = self._view_month + 1
        year = self._view_year
        if month == 13:
            month = 1
            year += 1
        if (year, month) > (max_y, max_m):
            return
        self._view_year, self._view_month = year, month
        self._build()

    def _pick_today(self):
        self.selected = self._max_date
        self.destroy()

    def _cancel(self):
        self.selected = None
        self.destroy()

    def _select(self, day: int):
        try:
            date_val = _dt.date(self._view_year, self._view_month, day)
            if date_val > self._max_date:
                return
            self.selected = date_val
        except Exception:
            self.selected = None
        self.destroy()

    def _build(self):
        import calendar as _cal

        for w in self._grid.winfo_children():
            w.destroy()

        month_name = f"{_MONTHS_RU[self._view_month - 1]} {self._view_year}"
        self._lbl.config(text=month_name)

        max_y, max_m = self._max_date.year, self._max_date.month
        try:
            self._btn_next.config(
                state=("disabled" if (self._view_year, self._view_month) >= (max_y, max_m) else "normal")
            )
        except Exception:
            pass

        headers = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for c, h in enumerate(headers):
            ttk.Label(self._grid, text=h, width=3, anchor="center").grid(row=0, column=c, padx=1, pady=(0, 2))

        cal = _cal.Calendar(firstweekday=_cal.MONDAY)
        weeks = cal.monthdayscalendar(self._view_year, self._view_month)

        sel = self._cur
        if sel and (sel.year, sel.month) != (self._view_year, self._view_month):
            sel = None

        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    ttk.Label(self._grid, text=" ", width=3).grid(row=r, column=c, padx=1, pady=1)
                    continue

                date_val = _dt.date(self._view_year, self._view_month, day)
                is_future = date_val > self._max_date
                is_sel = sel is not None and date_val == sel

                b = tk.Button(
                    self._grid,
                    text=str(day),
                    width=3,
                    relief="ridge",
                    bd=1,
                    command=(lambda dd=day: self._select(dd)),
                    state=("disabled" if is_future else "normal"),
                )
                if is_sel:
                    b.config(
                        background="#1e6bd6",
                        foreground="white",
                        activebackground="#1e6bd6",
                        activeforeground="white",
                    )
                b.grid(row=r, column=c, padx=1, pady=1)
