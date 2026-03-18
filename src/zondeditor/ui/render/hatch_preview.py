from __future__ import annotations

from typing import Any, Iterable

from src.zondeditor.domain.hatching import BUILTIN_HATCH_PATTERNS, HatchPattern
from src.zondeditor.ui.render.hatch_renderer import render_hatch_pattern

PREVIEW_ORDER: tuple[str, ...] = (
    "glina",
    "sugl",
    "supes",
    "pesok_g",
    "pesok_k",
    "pesok_s",
    "pesok_m",
    "pesok_p",
    "graviy",
    "gravel",
    "pesch",
    "argill",
    "torf_I",
    "tehno",
    "pochva",
)


def iter_builtin_preview_patterns() -> list[HatchPattern]:
    """Возвращает встроенные паттерны в стабильном порядке для dev/demo-preview."""
    return [BUILTIN_HATCH_PATTERNS[name] for name in PREVIEW_ORDER if name in BUILTIN_HATCH_PATTERNS]


def draw_hatch_preview_grid(
    canvas: Any,
    *,
    x0: float = 0.0,
    y0: float = 0.0,
    cell_w: float = 180.0,
    cell_h: float = 92.0,
    columns: int = 2,
    padding: float = 10.0,
    patterns: Iterable[HatchPattern] | None = None,
    tags: Any = ("hatch_preview",),
) -> tuple[float, float, float, float]:
    """Dev/demo preview: рисует все встроенные штриховки с подписями в одном месте."""
    pats = list(patterns or iter_builtin_preview_patterns())
    if not pats:
        return (x0, y0, x0, y0)

    cols = max(1, int(columns or 1))
    for idx, pattern in enumerate(pats):
        row = idx // cols
        col = idx % cols
        bx0 = float(x0 + col * cell_w)
        by0 = float(y0 + row * cell_h)
        bx1 = bx0 + cell_w - padding
        by1 = by0 + cell_h - padding
        canvas.create_rectangle(bx0, by0, bx1, by1, fill="#ffffff", outline="#cfcfcf", width=1, tags=tags)
        canvas.create_text(bx0 + 6, by0 + 6, anchor="nw", text=f"{pattern.name} — {pattern.title}", fill="#202020", font=("Segoe UI", 8, "bold"), tags=tags)
        render_hatch_pattern(
            canvas,
            (bx0 + 6, by0 + 24, bx1 - 6, by1 - 6),
            pattern,
            tags=tags,
            scale_info={"layer_height_px": float(max(1.0, (by1 - by0) - 30.0))},
        )

    rows = ((len(pats) - 1) // cols) + 1
    return (x0, y0, x0 + cols * cell_w - padding, y0 + rows * cell_h - padding)
