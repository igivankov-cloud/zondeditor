from src.zondeditor.ui.soil_hatches import SOIL_CODE_TO_RENDERER, draw_hatch, soil_code_from_value


class DummyCanvas:
    def __init__(self):
        self.lines = []
        self.ovals = []
        self.rects = []

    def create_line(self, *args, **kwargs):
        self.lines.append((args, kwargs))

    def create_oval(self, *args, **kwargs):
        self.ovals.append((args, kwargs))

    def create_rectangle(self, *args, **kwargs):
        self.rects.append((args, kwargs))


def test_soil_code_aliases():
    assert soil_code_from_value("суглинок") == "SiL"
    assert soil_code_from_value("Sand") == "Sand"
    assert soil_code_from_value("unknown") == ""


def test_draw_hatch_all_codes_do_not_crash_and_draw():
    bbox = (0.0, 0.0, 120.0, 80.0)
    for code in SOIL_CODE_TO_RENDERER:
        canvas = DummyCanvas()
        draw_hatch(canvas, bbox, code, {"layer_height_px": 80.0}, tags=("t",))
        assert (canvas.lines or canvas.ovals or canvas.rects), f"No primitives drawn for {code}"


def test_draw_hatch_fallback_unknown_code():
    canvas = DummyCanvas()
    draw_hatch(canvas, (0.0, 0.0, 80.0, 40.0), "UNKNOWN", {"layer_height_px": 40.0}, tags=("t",))
    assert canvas.lines
