# src/zondeditor/ui/main_window.py
from __future__ import annotations

from src.zondeditor.ui.patches import patch_geo_canvas_editor
from src.zondeditor.ui.editor import GeoCanvasEditor

def main() -> None:
    patch_geo_canvas_editor()
    GeoCanvasEditor().mainloop()

if __name__ == "__main__":
    main()
