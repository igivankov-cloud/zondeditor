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

    def delete(self, *_args, **_kwargs):
        # нужен для helper draw_broken_diagonal_lines (в тестовом canvas просто no-op)
        return None


def _diagonal_lines(canvas: DummyCanvas):
    out = []
    for args, _kw in canvas.lines:
        if len(args) != 4:
            continue
        x0, y0, x1, y1 = [float(v) for v in args]
        if abs(x1 - x0) > 5 and abs(y1 - y0) > 5:
            out.append((x0, y0, x1, y1))
    return out


def _horizontal_lines(canvas: DummyCanvas):
    out = []
    for args, _kw in canvas.lines:
        if len(args) != 4:
            continue
        x0, y0, x1, y1 = [float(v) for v in args]
        if abs(y1 - y0) < 1e-6 and abs(x1 - x0) > 10:
            out.append((x0, y0, x1, y1))
    return out


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


def test_sugl_and_supes_use_reversed_diagonal_direction():
    bbox = (0.0, 0.0, 120.0, 80.0)
    for code in ("SiL", "Si"):
        canvas = DummyCanvas()
        draw_hatch(canvas, bbox, code, {"layer_height_px": 80.0}, tags=("t",))
        diags = _diagonal_lines(canvas)
        assert diags
        neg = [1 for x0, y0, x1, y1 in diags if (x1 - x0) * (y1 - y0) < 0]
        assert neg


def test_sand_and_sandgravel_have_smaller_sand_dots():
    bbox = (0.0, 0.0, 120.0, 80.0)
    for code in ("Sand", "SandGravel"):
        canvas = DummyCanvas()
        draw_hatch(canvas, bbox, code, {"layer_height_px": 80.0}, tags=("t",))
        assert canvas.rects
        max_dot_w = max(float(args[2]) - float(args[0]) for args, _ in canvas.rects)
        assert max_dot_w <= 1.8


def test_sandstone_crosses_between_horizontal_lines():
    canvas = DummyCanvas()
    draw_hatch(canvas, (0.0, 0.0, 140.0, 96.0), "Sandstone", {"layer_height_px": 96.0}, tags=("t",))
    hs = _horizontal_lines(canvas)
    assert len(hs) >= 2
    yset = {round(y0, 2) for _x0, y0, _x1, _y1 in hs}
    has_cross_between = False
    for args, _kw in canvas.lines:
        x0, y0, x1, y1 = [float(v) for v in args]
        if abs(x1 - x0) < 2 or abs(y1 - y0) < 2:
            continue
        cy = round((y0 + y1) * 0.5, 2)
        if cy not in yset:
            has_cross_between = True
            break
    assert has_cross_between


def test_draw_hatch_fallback_unknown_code():
    canvas = DummyCanvas()
    draw_hatch(canvas, (0.0, 0.0, 80.0, 40.0), "UNKNOWN", {"layer_height_px": 40.0}, tags=("t",))
    assert canvas.lines
