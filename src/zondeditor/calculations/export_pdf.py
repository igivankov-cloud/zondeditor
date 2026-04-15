"""PDF export for the compact static sounding summary statement."""

from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont

from .preview_model import StaticCalcPreviewDocument


PAGE_W = 1654
PAGE_H = 2339
MARGIN = 72
TOP_HEADER_H = 54
BOTTOM_HEADER_H = 48
ROW_H = 44
COLUMN_WIDTHS = (95, 355, 110, 95, 95, 95, 95, 95, 95, 100)


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf")]
    for candidate in candidates:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def _draw_centered(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, font) -> None:
    l, t, r, b = box
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=2, align="center")
    x = l + max(4, ((r - l) - (bbox[2] - bbox[0])) // 2)
    y = t + max(4, ((b - t) - (bbox[3] - bbox[1])) // 2)
    draw.multiline_text((x, y), text, fill="black", font=font, spacing=2, align="center")


def _draw_left(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, font) -> None:
    l, t, r, b = box
    wrapped = "\n".join(wrap(str(text), width=max(8, int((r - l) / 12))) or [str(text)])
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=2, align="left")
    y = t + max(4, ((b - t) - (bbox[3] - bbox[1])) // 2)
    draw.multiline_text((l + 6, y), wrapped, fill="black", font=font, spacing=2, align="left")


def _draw_block(draw: ImageDraw.ImageDraw, *, x: int, y: int, width: int, heading: str, lines: tuple[str, ...] | list[str], head_font, body_font) -> int:
    draw.text((x, y), heading, fill="black", font=head_font)
    y += 26
    for line in lines:
        wrapped = "\n".join(wrap(str(line), width=max(18, int(width / 12))) or [str(line)])
        draw.multiline_text((x, y), wrapped, fill="#303030", font=body_font, spacing=4, align="left")
        y += max(26, (wrapped.count("\n") + 1) * 18 + 8)
    return y


def _draw_summary_header(draw: ImageDraw.ImageDraw, x: int, y: int, head_font, subhead_font) -> int:
    widths = COLUMN_WIDTHS
    total_w = sum(widths)
    draw.rectangle((x, y, x + total_w, y + TOP_HEADER_H + BOTTOM_HEADER_H), outline="black", width=2)
    xpos = x
    fixed = ("ИГЭ", "Наименование ИГЭ", "qc ср., МПа")
    for idx, title in enumerate(fixed):
        w = widths[idx]
        draw.rectangle((xpos, y, xpos + w, y + TOP_HEADER_H + BOTTOM_HEADER_H), outline="black", width=1, fill="#E8EEF5")
        (_draw_left if idx == 1 else _draw_centered)(draw, (xpos, y, xpos + w, y + TOP_HEADER_H + BOTTOM_HEADER_H), title, head_font)
        xpos += w
    norm_w = widths[3] + widths[4]
    draw.rectangle((xpos, y, xpos + norm_w, y + TOP_HEADER_H), outline="black", width=1, fill="#DDE7F2")
    _draw_centered(draw, (xpos, y, xpos + norm_w, y + TOP_HEADER_H), "Нормативные", head_font)
    draw.rectangle((xpos, y + TOP_HEADER_H, xpos + widths[3], y + TOP_HEADER_H + BOTTOM_HEADER_H), outline="black", width=1, fill="#E8EEF5")
    _draw_centered(draw, (xpos, y + TOP_HEADER_H, xpos + widths[3], y + TOP_HEADER_H + BOTTOM_HEADER_H), "φ, град", subhead_font)
    draw.rectangle((xpos + widths[3], y + TOP_HEADER_H, xpos + norm_w, y + TOP_HEADER_H + BOTTOM_HEADER_H), outline="black", width=1, fill="#E8EEF5")
    _draw_centered(draw, (xpos + widths[3], y + TOP_HEADER_H, xpos + norm_w, y + TOP_HEADER_H + BOTTOM_HEADER_H), "c, кПа", subhead_font)
    xpos += norm_w
    calc_w = widths[5] + widths[6] + widths[7] + widths[8]
    draw.rectangle((xpos, y, xpos + calc_w, y + TOP_HEADER_H), outline="black", width=1, fill="#DDE7F2")
    _draw_centered(draw, (xpos, y, xpos + calc_w, y + TOP_HEADER_H), "Расчетные", head_font)
    sub_titles = ("φ1, град", "c1, кПа", "φ2, град", "c2, кПа")
    sx = xpos
    for width, title in zip(widths[5:9], sub_titles):
        draw.rectangle((sx, y + TOP_HEADER_H, sx + width, y + TOP_HEADER_H + BOTTOM_HEADER_H), outline="black", width=1, fill="#E8EEF5")
        _draw_centered(draw, (sx, y + TOP_HEADER_H, sx + width, y + TOP_HEADER_H + BOTTOM_HEADER_H), title, subhead_font)
        sx += width
    xpos += calc_w
    draw.rectangle((xpos, y, xpos + widths[9], y + TOP_HEADER_H + BOTTOM_HEADER_H), outline="black", width=1, fill="#E8EEF5")
    _draw_centered(draw, (xpos, y, xpos + widths[9], y + TOP_HEADER_H + BOTTOM_HEADER_H), "E, МПа", head_font)
    return y + TOP_HEADER_H + BOTTOM_HEADER_H


def export_summary_table_pdf(*, out_path: Path, preview: StaticCalcPreviewDocument) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    title_font = _load_font(27, bold=True)
    intro_font = _load_font(18)
    head_font = _load_font(16, bold=True)
    subhead_font = _load_font(15, bold=True)
    body_font = _load_font(14)

    image = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    draw = ImageDraw.Draw(image)
    y = MARGIN
    _draw_centered(draw, (MARGIN, y, PAGE_W - MARGIN, y + 60), preview.title, title_font)
    y += 72
    for line in preview.intro_lines:
        if line.startswith("Таблица"):
            bbox = draw.multiline_textbbox((0, 0), line, font=intro_font)
            draw.text((PAGE_W - MARGIN - (bbox[2] - bbox[0]), y), line, fill="black", font=intro_font)
        else:
            draw.text((MARGIN, y), line, fill="black", font=intro_font)
        y += 24
    y += 8
    y = _draw_summary_header(draw, MARGIN, y, head_font, subhead_font)
    for row in preview.summary_rows:
        xpos = MARGIN
        draw.rectangle((MARGIN, y, MARGIN + sum(COLUMN_WIDTHS), y + ROW_H), outline="black", width=1)
        for idx, (width, value) in enumerate(zip(COLUMN_WIDTHS, row)):
            box = (xpos, y, xpos + width, y + ROW_H)
            draw.rectangle(box, outline="black", width=1)
            (_draw_left if idx == 1 else _draw_centered)(draw, box, str(value), body_font)
            xpos += width
        y += ROW_H
    if preview.note_lines:
        y += 18
        y = _draw_block(draw, x=MARGIN, y=y, width=PAGE_W - 2 * MARGIN, heading="Примечание", lines=preview.note_lines, head_font=subhead_font, body_font=body_font)
    if preview.statistics_lines:
        y += 10
        _draw_block(draw, x=MARGIN, y=y, width=PAGE_W - 2 * MARGIN, heading="Особенности расчета", lines=preview.statistics_lines, head_font=subhead_font, body_font=body_font)
    image.save(out_path, "PDF", resolution=150.0)
    return out_path
