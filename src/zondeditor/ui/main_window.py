# src/zondeditor/ui/main_window.py
from __future__ import annotations

from src.zondeditor.ui.patches import patch_geo_canvas_editor
from src.zondeditor.ui.editor import GeoCanvasEditor

def main() -> None:
    patch_geo_canvas_editor()
    app = GeoCanvasEditor()
    # Apply sv_ttk theme AFTER Tk root exists (prevents extra 'tk' window)
    try:
        import sv_ttk
        sv_ttk.set_theme('light')
    except Exception:
        pass
    app.mainloop()
if __name__ == "__main__":
    main()
