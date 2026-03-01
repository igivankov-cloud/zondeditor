from __future__ import annotations

import os
import traceback
from datetime import datetime
from pathlib import Path


def _guard_enabled() -> bool:
    return str(os.environ.get("ZONDEDITOR_TK_GUARD", "")).strip() == "1"


def _log_path() -> Path:
    return Path(r"C:\ProgramData\ZondEditor\logs\tk_guard.log")


def _mk_logger():
    logfile = None
    if _guard_enabled():
        try:
            p = _log_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            logfile = p
        except Exception:
            logfile = None

    def _log(message: str) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{stamp}] {message}"
        try:
            print(line)
        except Exception:
            pass
        if logfile is not None:
            try:
                with logfile.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except Exception:
                pass

    return _log


def install_tk_window_guard() -> bool:
    if not _guard_enabled():
        return False

    try:
        import tkinter as tk
    except Exception:
        return False

    if getattr(tk, "_zondeditor_tk_guard_installed", False):
        return True

    log = _mk_logger()
    original_tk = tk.Tk
    original_toplevel = tk.Toplevel

    state: dict[str, object] = {"root": None}

    def _window_title(win) -> str:
        try:
            return str(win.title() or "")
        except Exception:
            return ""

    def _stack() -> str:
        return "".join(traceback.format_stack())

    def _attach_close_logger(win, kind: str) -> None:
        try:
            old_handler = win.protocol("WM_DELETE_WINDOW")
        except Exception:
            old_handler = ""

        def _on_close() -> None:
            log(
                f"WINDOW_CLOSE type={kind} title={_window_title(win)!r} stack=\n{_stack()}"
            )
            try:
                if callable(old_handler):
                    old_handler()
                elif isinstance(old_handler, str) and old_handler.strip():
                    win.tk.call(old_handler)
                else:
                    win.destroy()
            except Exception:
                try:
                    win.destroy()
                except Exception:
                    pass

        try:
            win.protocol("WM_DELETE_WINDOW", _on_close)
        except Exception:
            pass

    class GuardTk(original_tk):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            title = _window_title(self)
            extra = ""
            if state.get("root") is not None and state.get("root") is not self:
                extra = " SECOND_ROOT"
            else:
                state["root"] = self
            log(f"WINDOW_CREATE type=Tk{extra} title={title!r} stack=\n{_stack()}")
            _attach_close_logger(self, "Tk")

    class GuardToplevel(original_toplevel):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            log(
                f"WINDOW_CREATE type=Toplevel title={_window_title(self)!r} stack=\n{_stack()}"
            )
            _attach_close_logger(self, "Toplevel")

    tk.Tk = GuardTk
    tk.Toplevel = GuardToplevel
    tk._zondeditor_tk_guard_installed = True
    log("tk_guard installed")
    return True
