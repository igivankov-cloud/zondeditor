from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HatchLine:
    angle_deg: float
    x0: float
    y0: float
    dx: float
    dy: float
    pattern: list[float]


@dataclass(frozen=True)
class HatchPattern:
    name: str
    title: str
    source_file: str
    lines: list[HatchLine]


def _line(*, angle_deg: float, x0: float, y0: float, dx: float, dy: float, pattern: list[float]) -> HatchLine:
    return HatchLine(angle_deg=angle_deg, x0=x0, y0=y0, dx=dx, dy=dy, pattern=list(pattern))


# Встроенный каталог PAT-derived штриховок (без PAT-парсера).
BUILTIN_HATCH_PATTERNS: dict[str, HatchPattern] = {
    "argill": HatchPattern(
        name="argill",
        title="Аргиллит",
        source_file="argill.pat",
        lines=[
            _line(angle_deg=0.0, x0=0.0, y0=0.1, dx=0.0, dy=0.2, pattern=[]),
            _line(angle_deg=135.0, x0=0.0, y0=0.03, dx=0.0, dy=0.28284, pattern=[0.2, -0.36569]),
        ],
    ),
    "glina": HatchPattern(
        name="glina",
        title="Глина",
        source_file="glina.pat",
        lines=[_line(angle_deg=0.0, x0=0.0, y0=0.0375, dx=0.0, dy=0.075, pattern=[])],
    ),
    "gravel": HatchPattern(
        name="gravel",
        title="Гравелит",
        source_file="glina.pat",
        lines=[
            _line(angle_deg=0.0, x0=0.0, y0=0.0, dx=0.5774, dy=0.1, pattern=[0.05774, -0.11547, 0.05774]),
            _line(angle_deg=60.0, x0=0.0, y0=0.0, dx=0.14434, dy=-0.05, pattern=[-0.34641, 0.11547]),
            _line(angle_deg=120.0, x0=0.0, y0=0.0, dx=0.31754, dy=-0.05, pattern=[-0.34641, 0.11547]),
        ],
    ),
    "graviy": HatchPattern(
        name="graviy",
        title="Гравий",
        source_file="graviy.pat",
        lines=[
            _line(angle_deg=0.0, x0=0.0, y0=0.043301, dx=0.1732051, dy=0.3, pattern=[-0.025, 0.05, -0.2714102]),
            _line(angle_deg=0.0, x0=0.0, y0=-0.043301, dx=0.1732051, dy=0.3, pattern=[-0.025, 0.05, -0.2714102]),
            _line(angle_deg=60.0, x0=0.0, y0=0.0, dx=0.1732051, dy=0.3, pattern=[0.05, -0.2964102]),
            _line(angle_deg=60.0, x0=0.1, y0=0.0, dx=0.1732051, dy=0.3, pattern=[-0.2964102, 0.05]),
            _line(angle_deg=120.0, x0=0.0, y0=0.0, dx=0.1732051, dy=0.3, pattern=[-0.2964102, 0.05]),
            _line(angle_deg=120.0, x0=0.1, y0=0.0, dx=0.1732051, dy=0.3, pattern=[0.05, -0.2964102]),
        ],
    ),
    "pesch": HatchPattern(
        name="pesch",
        title="Песчаник",
        source_file="pesch.pat",
        lines=[
            _line(angle_deg=0.0, x0=0.0, y0=0.1, dx=0.0, dy=0.2, pattern=[]),
            _line(angle_deg=0.0, x0=-0.005, y0=0.0, dx=0.34641, dy=0.2, pattern=[0.01, -0.128564]),
            _line(angle_deg=60.0, x0=0.0, y0=0.0, dx=0.34641, dy=0.2, pattern=[0.11547, -0.57735]),
            _line(angle_deg=120.0, x0=0.0, y0=0.0, dx=0.34641, dy=0.2, pattern=[0.11547, -0.57735]),
        ],
    ),
    "pesok_g": HatchPattern(
        name="pesok_g",
        title="Песок гравелистый",
        source_file="pesok_g.pat",
        lines=[
            _line(angle_deg=0.0, x0=0.0, y0=0.0, dx=0.141421, dy=0.141421, pattern=[0.0282842, -0.25456]),
            _line(angle_deg=45.0, x0=0.09428, y0=0.0, dx=0.0, dy=0.2, pattern=[-0.048, 0.002]),
            _line(angle_deg=45.0, x0=0.18856, y0=0.0, dx=0.0, dy=0.2, pattern=[-0.048, 0.002]),
            _line(angle_deg=45.0, x0=0.0, y0=0.0, dx=0.0, dy=0.2, pattern=[0.02, -0.059, 0.002, -0.059, 0.002, -0.058]),
            _line(angle_deg=135.0, x0=0.0282842, y0=0.0, dx=0.0, dy=0.2, pattern=[0.02, -0.18]),
        ],
    ),
    "pesok_k": HatchPattern(
        name="pesok_k",
        title="Песок крупный",
        source_file="pesok_k.pat",
        lines=[_line(angle_deg=45.0, x0=0.0, y0=0.0, dx=0.0, dy=0.1, pattern=[0.005, -0.1])],
    ),
    "pesok_m": HatchPattern(
        name="pesok_m",
        title="Песок мелкий",
        source_file="pesok_m.pat",
        lines=[_line(angle_deg=45.0, x0=0.0, y0=0.0, dx=0.0, dy=0.05, pattern=[0.005, -0.05])],
    ),
    "pesok_p": HatchPattern(
        name="pesok_p",
        title="Песок пылеватый",
        source_file="pesok_p.pat",
        lines=[_line(angle_deg=45.0, x0=0.0, y0=0.0, dx=0.0, dy=0.03, pattern=[0.002, -0.03])],
    ),
    "pesok_s": HatchPattern(
        name="pesok_s",
        title="Песок средний",
        source_file="pesok_s.pat",
        lines=[_line(angle_deg=45.0, x0=0.0, y0=0.0, dx=0.0, dy=0.07, pattern=[0.005, -0.07])],
    ),
    "pochva": HatchPattern(
        name="pochva",
        title="Почвенно-растительный слой",
        source_file="pochva.pat",
        lines=[
            _line(angle_deg=0.0, x0=0.0, y0=0.0, dx=0.15, dy=0.2, pattern=[0.12, -0.18]),
            _line(angle_deg=0.0, x0=0.02, y0=-0.03, dx=0.15, dy=0.2, pattern=[0.08, -0.22]),
            _line(angle_deg=0.0, x0=0.04, y0=-0.06, dx=0.15, dy=0.2, pattern=[0.04, -0.26]),
            _line(angle_deg=90.0, x0=0.06, y0=-0.13, dx=0.2, dy=0.15, pattern=[0.1, -0.3]),
            _line(angle_deg=53.13, x0=0.13, y0=-0.108, dx=-0.18, dy=0.24, pattern=[0.13, -0.12]),
            _line(angle_deg=53.13, x0=0.17, y0=-0.13, dx=-0.18, dy=0.24, pattern=[0.13, -0.12]),
            _line(angle_deg=53.13, x0=0.21, y0=-0.152, dx=-0.18, dy=0.24, pattern=[0.13, -0.12]),
        ],
    ),
    "sugl": HatchPattern(
        name="sugl",
        title="Суглинок",
        source_file="sugl.pat",
        lines=[_line(angle_deg=120.0, x0=0.0, y0=0.0, dx=0.0, dy=0.15, pattern=[1.0])],
    ),
    "supes": HatchPattern(
        name="supes",
        title="Супесь",
        source_file="supes.pat",
        lines=[_line(angle_deg=120.0, x0=0.066025, y0=0.0, dx=0.05, dy=0.15, pattern=[0.2, -0.06])],
    ),
    "tehno": HatchPattern(
        name="tehno",
        title="Насыпной",
        source_file="tehno.pat",
        lines=[
            _line(angle_deg=45.0, x0=0.0, y0=0.0, dx=0.0, dy=0.125, pattern=[]),
            _line(angle_deg=135.0, x0=0.0, y0=0.0, dx=0.0, dy=0.125, pattern=[]),
        ],
    ),
    "torf_I": HatchPattern(
        name="torf_I",
        title="Торф IБ / СНИПИН",
        source_file="torf_I.pat",
        lines=[
            _line(angle_deg=0.0, x0=0.0, y0=0.0, dx=0.0, dy=0.15, pattern=[]),
            _line(angle_deg=90.0, x0=0.075, y0=0.0, dx=0.0, dy=0.15, pattern=[]),
            _line(angle_deg=45.0, x0=0.075, y0=0.0, dx=0.0, dy=0.2121320344, pattern=[]),
            _line(angle_deg=135.0, x0=-0.075, y0=0.0, dx=0.0, dy=0.2121320344, pattern=[]),
        ],
    ),
}


SOIL_TYPE_TO_HATCH: dict[str, str] = {
    "глина": "glina",
    "суглинок": "sugl",
    "супесь": "supes",
    "песок гравелистый": "pesok_g",
    "песок крупный": "pesok_k",
    "песок средний": "pesok_s",
    "песок мелкий": "pesok_m",
    "песок пылеватый": "pesok_p",
    "гравий": "graviy",
    "гравелит": "gravel",
    "песчаник": "pesch",
    "аргиллит": "argill",
    "торф": "torf_I",
    "насыпной": "tehno",
    "техногенный": "tehno",
    "почвенно-растительный": "pochva",
    "почвенно-растительный слой": "pochva",
    "прс": "pochva",
    # алиасы проекта
    "гравийный грунт": "graviy",
    "песок": "pesok_s",
}


def resolve_hatch_name(soil_type: str) -> str | None:
    raw = str(soil_type or "").strip().lower()
    if not raw:
        return None
    return SOIL_TYPE_TO_HATCH.get(raw)


def resolve_hatch_pattern(soil_type: str) -> HatchPattern | None:
    name = resolve_hatch_name(soil_type)
    if not name:
        return None
    return BUILTIN_HATCH_PATTERNS.get(name)
