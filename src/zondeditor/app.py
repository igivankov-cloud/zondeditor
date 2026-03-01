# src/zondeditor/app.py
from __future__ import annotations

import sys


def _show_blocking_message(title: str, text: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, text, parent=root)
        root.destroy()
    except Exception:
        print(f"{title}: {text}", file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)

    # --- Win11-like theme (safe) ---
    try:
        import sv_ttk  # type: ignore
        sv_ttk.set_theme("light")
    except Exception:
        pass

    # --- init license mode (used by installer) ---
    # Creates a valid license.dat for THIS machine and exits.
    if "--init-license" in argv:
        try:
            from src.zondeditor.licensing.license import machine_id, expected_license_token, write_license, LICENSE_PATH
            tok = expected_license_token(machine_id())
            write_license(tok, LICENSE_PATH)
        except Exception as e:
            # Do not show UI in installer mode; write to stderr
            print("ERROR: init-license failed:", e, file=sys.stderr)
            raise
        return

    # --- license gate ---
    try:
        from src.zondeditor.licensing.license import check_license
        st = check_license()
        if not st.ok:
            _show_blocking_message(
                "ZondEditor — лицензия",
                st.reason + "\n\n"
                "Чтобы получить лицензию для этого ПК:\n"
                "  1) Откройте CMD в папке программы\n"
                "  2) Выполните: py tools\\make_license.py --print\n"
                "  3) Пришлите строку LicenseToken администратору\n"
            )
            return
    except Exception:
        _show_blocking_message("ZondEditor — лицензия", "Ошибка проверки лицензии.")
        return

    # --- run UI ---
    from src.zondeditor.ui.main_window import main as ui_main
    ui_main()


if __name__ == "__main__":
    main()
