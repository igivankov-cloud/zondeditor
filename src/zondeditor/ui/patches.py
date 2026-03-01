# src/zondeditor/ui/patches.py
from __future__ import annotations

def patch_geo_canvas_editor() -> None:
    """Hotfix: ensure GeoCanvasEditor has export_gxl_generated() method.

    During modularization some helpers were left at module scope, but UI calls
    self.export_gxl_generated(...). This patch injects a safe method onto the
    class at runtime, without touching the big editor.py file.
    """
    from pathlib import Path
    import traceback
    from tkinter import messagebox

    from src.zondeditor.ui import editor as editor_mod

    GeoCanvasEditor = getattr(editor_mod, "GeoCanvasEditor", None)
    if GeoCanvasEditor is None:
        return

    def _ensure_obj(self) -> str:
        try:
            if hasattr(self, "_ensure_object_code"):
                return (self._ensure_object_code() or "").strip()
        except Exception:
            pass
        try:
            return (getattr(self, "object_code", "") or "").strip()
        except Exception:
            return ""

    def export_gxl_generated(self, out_file: str) -> None:
        try:
            from src.zondeditor.export.gxl_export import export_gxl_generated as export_gxl_generated_file
            tests = list(getattr(self, "tests", []) or [])
            obj = _ensure_obj(self) or "OBJ"
            out_path = Path(out_file)

            export_gxl_generated_file(
                tests,
                out_path=out_path,
                object_code=obj,
                include_only_export_on=True,
            )

            # status (optional)
            try:
                n_exp = sum(1 for t in tests if bool(getattr(t, "export_on", True)))
            except Exception:
                n_exp = len(tests)
            if hasattr(self, "_update_status_loaded"):
                try:
                    self._update_status_loaded(prefix=f"Сохранено GXL: {out_file} | опытов {n_exp}")
                except Exception:
                    pass

        except Exception:
            messagebox.showerror("Ошибка сохранения GXL", traceback.format_exc())

    # Install/override
    setattr(GeoCanvasEditor, "export_gxl_generated", export_gxl_generated)
