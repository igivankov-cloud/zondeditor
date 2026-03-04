from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path
from typing import Any

try:
    from docx import Document
except Exception:  # pragma: no cover
    Document = None


def _git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def export_cpt_protocol_docx(*, out_path: Path, object_name: str, settings: dict[str, Any], rows: list[dict[str, Any]], template_path: Path | None = None) -> Path:
    if Document is None:
        raise RuntimeError("python-docx не установлен")
    if template_path and template_path.exists():
        doc = Document(str(template_path))
    else:
        doc = Document()

    doc.add_heading("Расчёт φ и E (CPT)", level=1)
    doc.add_paragraph(f"Объект: {object_name or '-'}")
    doc.add_paragraph(f"Дата: {dt.datetime.now().strftime('%d.%m.%Y %H:%M')}")
    doc.add_paragraph(f"Версия программы (git hash): {_git_hash()}")

    method = str(settings.get("method") or "SP446_APP_J")
    method_label = "СП 446.1325800.2019 (Приложение Ж)" if method == "SP446_APP_J" else "СП 11-105-97 (Приложение И)"
    doc.add_paragraph(f"Методика расчёта: {method_label}")
    doc.add_paragraph(f"Аллювиальные пески: {'да' if bool(settings.get('alluvial_sands')) else 'нет'}")
    doc.add_paragraph("Нормативные ссылки: ГОСТ 19912, ГОСТ 25100, ГОСТ 20522-2012, СП 22.13330.2016.")

    for row in rows:
        doc.add_heading(str(row.get("ige_id") or "ИГЭ"), level=2)
        doc.add_paragraph(f"Тип грунта: {row.get('soil_type') or '-'}")
        doc.add_paragraph(f"Границы слоёв: {row.get('bounds') or '-'}")
        doc.add_paragraph(
            f"qc_ср={row.get('qc_mean', '-')}, n={row.get('n', '-')}, min/max={row.get('qc_min', '-')}/{row.get('qc_max', '-')}, V={row.get('variation', '-')}"
        )
        doc.add_paragraph(f"Табличный диапазон qc: {row.get('lookup_interval') or '-'}")
        doc.add_paragraph(f"Итог: φ_norm={row.get('phi_norm', '-')}, E_norm={row.get('E_norm', '-')}")
        doc.add_paragraph("Примечание: источник значений — CPT (таблично по выбранной методике РФ НД).")

    doc.add_heading("Сводная таблица по ИГЭ", level=2)
    table = doc.add_table(rows=max(1, len(rows)) + 1, cols=4)
    hdr = table.rows[0].cells
    hdr[0].text = "ИГЭ"
    hdr[1].text = "qc_ср"
    hdr[2].text = "φ_norm"
    hdr[3].text = "E_norm"
    for i, row in enumerate(rows, start=1):
        cells = table.rows[i].cells
        cells[0].text = str(row.get("ige_id") or "")
        cells[1].text = str(row.get("qc_mean") or "")
        cells[2].text = str(row.get("phi_norm") or "")
        cells[3].text = str(row.get("E_norm") or "")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    return out_path

