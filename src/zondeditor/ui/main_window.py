# src/zondeditor/ui/main_window.py
from __future__ import annotations

from src.zondeditor.ui.editor import GeoCanvasEditor

def main() -> None:
    GeoCanvasEditor().mainloop()

if __name__ == "__main__":
    main()
