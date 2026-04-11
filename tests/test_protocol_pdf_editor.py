from pathlib import Path

from src.zondeditor.ui import editor as editor_module
from src.zondeditor.ui.editor import GeoCanvasEditor


class _DummyStatus:
    def config(self, **_kwargs):
        return None


def test_pdf_export_respects_show_layer_colors(monkeypatch, tmp_path):
    ed = GeoCanvasEditor.__new__(GeoCanvasEditor)
    ed.show_layer_colors = True
    ed.status = _DummyStatus()
    ed._protocol_export_stem = lambda: "protocol_demo"

    captured = {}

    class _Result:
        scene = object()
        height_mm = 123.0

    def _fake_build_protocol_cad_results(*, colorize_sections=False):
        captured["colorize_sections"] = colorize_sections
        return [_Result()]

    def _fake_export_protocols_to_pdf(*, scenes, heights_mm, out_path):
        captured["scenes"] = scenes
        captured["heights_mm"] = heights_mm
        captured["out_path"] = out_path
        return Path(out_path)

    monkeypatch.setattr(editor_module.filedialog, "asksaveasfilename", lambda **_kwargs: str(tmp_path / "out.pdf"))
    monkeypatch.setattr(editor_module, "export_protocols_to_pdf", _fake_export_protocols_to_pdf)
    ed._build_protocol_cad_results = _fake_build_protocol_cad_results

    GeoCanvasEditor.export_sounding_protocols_pdf(ed)

    assert captured["colorize_sections"] is True
    assert captured["heights_mm"] == [123.0]
    assert str(captured["out_path"]).endswith("out.pdf")
