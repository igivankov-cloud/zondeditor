from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class SoundingsViewport(ttk.Frame):
    """Single horizontal scroll source for the sounding workspace."""

    def __init__(self, master, *, header_height: int = 120):
        super().__init__(master)
        self.canvas = tk.Canvas(self, background="white", highlightthickness=0)
        self.canvas.pack(side="top", fill="both", expand=True)

        self.strip = ttk.Frame(self)
        self._strip_window = self.canvas.create_window((0, 0), window=self.strip, anchor="nw")

        self.header_canvas = tk.Canvas(self.strip, background="white", highlightthickness=0, height=header_height)
        self.header_canvas.pack(side="top", fill="x")

        self.body_host = ttk.Frame(self.strip)
        self.body_host.pack(side="top", fill="both", expand=True)

        self.body_canvas = tk.Canvas(self.body_host, background="white", highlightthickness=0)
        self.body_canvas.pack(side="left", fill="both", expand=True)

        self.vscroll = ttk.Scrollbar(self.body_host, orient="vertical", command=self.body_canvas.yview)
        self.vscroll.pack(side="right", fill="y")
        self.body_canvas.configure(yscrollcommand=self.vscroll.set)

        self.hscroll_frame = ttk.Frame(self, padding=(12, 0, 12, 0))
        self.hscroll = ttk.Scrollbar(self.hscroll_frame, orient="horizontal", command=self.canvas.xview)
        self.hscroll.pack(fill="x")
        self.canvas.configure(xscrollcommand=self.hscroll.set)

        self.canvas.bind("<Configure>", self._on_canvas_configure, add="+")
        self.strip.bind("<Configure>", self._on_strip_configure, add="+")

    def _on_canvas_configure(self, event=None):
        try:
            self.canvas.itemconfigure(self._strip_window, height=self.canvas.winfo_height())
        except Exception:
            pass

    def _on_strip_configure(self, event=None):
        try:
            bbox = self.canvas.bbox(self._strip_window)
            if bbox:
                self.canvas.configure(scrollregion=bbox)
        except Exception:
            pass

    def set_content_size(self, *, width: int, body_height: int, header_height: int):
        width = max(1, int(width))
        body_height = max(0, int(body_height))
        header_height = max(1, int(header_height))

        self.header_canvas.configure(width=width, height=header_height, scrollregion=(0, 0, width, header_height))
        self.body_canvas.configure(width=width, scrollregion=(0, 0, width, body_height))

        try:
            self.canvas.itemconfigure(self._strip_window, width=width)
        except Exception:
            pass
        self.update_idletasks()
        self._on_strip_configure()

    def xview(self, *args):
        self.canvas.xview(*args)

    def xview_moveto(self, fraction: float):
        self.canvas.xview_moveto(fraction)

    def xview_scroll(self, number: int, what: str):
        self.canvas.xview_scroll(number, what)

    def xview_fractions(self):
        return self.canvas.xview()

