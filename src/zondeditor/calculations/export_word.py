"""Word export for static sounding calculation protocols."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from .preview_model import StaticCalcPreviewDocument, xml_text


WORD_TABLE_WIDTHS = (700, 2500, 900, 820, 820, 820, 820, 820, 820, 900)


def _paragraph_xml(text: str, *, bold: bool = False, align: str = "left", size_half_points: int = 22) -> str:
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return (
        "<w:p>"
        f'<w:pPr><w:jc w:val="{align}"/></w:pPr>'
        "<w:r>"
        f'{rpr}<w:rPr><w:sz w:val="{int(size_half_points)}"/><w:szCs w:val="{int(size_half_points)}"/></w:rPr>'
        f'<w:t xml:space="preserve">{xml_text(text)}</w:t>'
        "</w:r>"
        "</w:p>"
    )


def _table_cell_xml(text: str, *, width: int, bold: bool = False, align: str = "center", grid_span: int = 1, v_merge: str | None = None) -> str:
    tc_pr_parts = [f'<w:tcW w:w="{int(width)}" w:type="dxa"/>']
    if grid_span > 1:
        tc_pr_parts.append(f'<w:gridSpan w:val="{int(grid_span)}"/>')
    if v_merge is not None:
        tc_pr_parts.append(f'<w:vMerge w:val="{v_merge}"/>')
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return (
        "<w:tc>"
        f"<w:tcPr>{''.join(tc_pr_parts)}</w:tcPr>"
        "<w:p>"
        f'<w:pPr><w:jc w:val="{align}"/></w:pPr>'
        f'<w:r>{rpr}<w:t xml:space="preserve">{xml_text(text)}</w:t></w:r>'
        "</w:p>"
        "</w:tc>"
    )


def _build_summary_table_xml(rows: tuple[tuple[str, ...], ...]) -> str:
    widths = WORD_TABLE_WIDTHS
    top_headers = (
        _table_cell_xml("ИГЭ", width=widths[0], bold=True, v_merge="restart"),
        _table_cell_xml("Наименование ИГЭ", width=widths[1], bold=True, align="left", v_merge="restart"),
        _table_cell_xml("qc ср., МПа", width=widths[2], bold=True, v_merge="restart"),
        _table_cell_xml("Нормативные", width=widths[3] + widths[4], bold=True, grid_span=2),
        _table_cell_xml("Расчетные", width=widths[5] + widths[6] + widths[7] + widths[8], bold=True, grid_span=4),
        _table_cell_xml("E, МПа", width=widths[9], bold=True, v_merge="restart"),
    )
    second_headers = (
        _table_cell_xml("", width=widths[0], v_merge="continue"),
        _table_cell_xml("", width=widths[1], align="left", v_merge="continue"),
        _table_cell_xml("", width=widths[2], v_merge="continue"),
        _table_cell_xml("φ, град", width=widths[3], bold=True),
        _table_cell_xml("c, кПа", width=widths[4], bold=True),
        _table_cell_xml("φ1, град", width=widths[5], bold=True),
        _table_cell_xml("c1, кПа", width=widths[6], bold=True),
        _table_cell_xml("φ2, град", width=widths[7], bold=True),
        _table_cell_xml("c2, кПа", width=widths[8], bold=True),
        _table_cell_xml("", width=widths[9], v_merge="continue"),
    )
    row_xml = [
        "<w:tr>" + "".join(top_headers) + "</w:tr>",
        "<w:tr>" + "".join(second_headers) + "</w:tr>",
    ]
    for row in rows:
        cells = []
        for idx, value in enumerate(row):
            cells.append(_table_cell_xml(str(value), width=widths[idx], align="left" if idx == 1 else "center"))
        row_xml.append("<w:tr>" + "".join(cells) + "</w:tr>")
    return (
        "<w:tbl><w:tblPr><w:tblBorders>"
        "<w:top w:val=\"single\" w:sz=\"8\"/><w:left w:val=\"single\" w:sz=\"8\"/>"
        "<w:bottom w:val=\"single\" w:sz=\"8\"/><w:right w:val=\"single\" w:sz=\"8\"/>"
        "<w:insideH w:val=\"single\" w:sz=\"5\"/><w:insideV w:val=\"single\" w:sz=\"5\"/>"
        "</w:tblBorders></w:tblPr><w:tblGrid>"
        + "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)
        + "</w:tblGrid>"
        + "".join(row_xml)
        + "</w:tbl>"
    )


def _document_xml(blocks: list[str]) -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
        "<w:body>"
        + "".join(blocks) +
        "<w:sectPr/>"
        "</w:body></w:document>"
    )


def _write_docx(out_path: Path, document_xml: str) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(out_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )
        archive.writestr("word/document.xml", document_xml)
    return out_path


def _build_common_blocks(preview: StaticCalcPreviewDocument) -> list[str]:
    blocks = [_paragraph_xml(preview.title, bold=True, align="center", size_half_points=28)]
    for line in preview.intro_lines:
        blocks.append(_paragraph_xml(line, align="right" if line.startswith("Таблица") else "left"))
    return blocks


def export_detailed_protocol_word(*, out_path: Path, preview: StaticCalcPreviewDocument) -> Path:
    blocks = _build_common_blocks(preview)
    blocks.append(_build_summary_table_xml(preview.summary_rows))
    if preview.note_lines:
        blocks.append(_paragraph_xml("Примечание", bold=True))
        for line in preview.note_lines:
            blocks.append(_paragraph_xml(line, size_half_points=20))
    if preview.statistics_lines:
        blocks.append(_paragraph_xml("Особенности расчета", bold=True))
        for line in preview.statistics_lines:
            blocks.append(_paragraph_xml(line, size_half_points=20))
    for section in preview.sections:
        blocks.append(_paragraph_xml(section.heading, bold=True))
        for line in section.lines:
            blocks.append(_paragraph_xml(line, size_half_points=20))
    return _write_docx(Path(out_path), _document_xml(blocks))


def export_summary_table_word(*, out_path: Path, preview: StaticCalcPreviewDocument) -> Path:
    blocks = _build_common_blocks(preview)
    blocks.append(_build_summary_table_xml(preview.summary_rows))
    if preview.note_lines:
        blocks.append(_paragraph_xml("Примечание", bold=True))
        for line in preview.note_lines:
            blocks.append(_paragraph_xml(line, size_half_points=20))
    if preview.statistics_lines:
        blocks.append(_paragraph_xml("Особенности расчета", bold=True))
        for line in preview.statistics_lines:
            blocks.append(_paragraph_xml(line, size_half_points=20))
    return _write_docx(Path(out_path), _document_xml(blocks))
