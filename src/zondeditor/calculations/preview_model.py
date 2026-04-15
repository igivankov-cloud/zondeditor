"""Preview models and formatting helpers for static sounding calculation."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Iterable


LOOKUP_RELATIVE_PATH = "raschet/sp446_static_calc_lookup_final.csv"
STATIC_CALC_ALGORITHM_VERSION = "SP446-static-qc-lookup-2026.04"
EXPORT_PROTOCOL_TITLE = (
    "Нормативные и расчетные значения основных физико-механических "
    "характеристик грунтов по выделенным ИГЭ"
)

QC_DISPLAY_DECIMALS = 2
E_DISPLAY_DECIMALS = 1
PHI_DISPLAY_DECIMALS = 0
C_DISPLAY_DECIMALS = 0

NOTE_LEGACY_SUPES = "*"
NOTE_PRELIM_FILL = "**"
NOTE_REFERENCE_ONLY = "***"

NOTE_LEGENDS = {
    NOTE_LEGACY_SUPES: "супеси рассчитаны по редакции СП 446.1325800.2019 до Изм. № 1",
    NOTE_PRELIM_FILL: "насыпной грунт рассчитан предварительно по материалу",
    NOTE_REFERENCE_ONLY: "расчетные значения приведены справочно при n < 6 и/или V > 0,30",
}

EXPORT_SUMMARY_HEADERS = (
    "ИГЭ",
    "Наименование ИГЭ",
    "qc ср., МПа",
    "φ, град",
    "c, кПа",
    "φ1, град",
    "c1, кПа",
    "φ2, град",
    "c2, кПа",
    "E, МПа",
)

SUMMARY_HEADERS = EXPORT_SUMMARY_HEADERS

INDEX_NOTE_LINES = (
    "1 — доверительная вероятность 0,95",
    "2 — доверительная вероятность 0,85",
)


def _format_number(value: float | None, decimals: int) -> str:
    if value is None:
        return "—"
    return f"{float(value):.{int(decimals)}f}"


def format_qc(value: float | None) -> str:
    return _format_number(value, QC_DISPLAY_DECIMALS)


def format_e(value: float | None) -> str:
    return _format_number(value, E_DISPLAY_DECIMALS)


def format_phi(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{round(float(value)):.0f}"


def format_c(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{round(float(value)):.0f}"


def _marks_suffix(marks: Iterable[str]) -> str:
    parts = [str(mark or "").strip() for mark in marks if str(mark or "").strip()]
    return " ".join(parts)


def format_with_marks(value: str, marks: Iterable[str]) -> str:
    if value == "—":
        return value
    suffix = _marks_suffix(marks)
    return value if not suffix else f"{value}{suffix}"


def export_decimal_text(value: str) -> str:
    return str(value or "").replace(".", ",")


def format_variation(value: float | None) -> str:
    if value is None:
        return "—"
    return export_decimal_text(f"{float(value):.2f}")


def compact_ige_label(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "—"
    upper = text.upper()
    if upper.startswith("ИГЭ-"):
        return text[4:]
    if upper.startswith("ИГЭ"):
        return text[3:].lstrip(" -")
    return text


def xml_text(value: object) -> str:
    return escape(str(value or ""))


@dataclass(frozen=True)
class StaticCalcRow:
    ige_id: str
    soil_name: str
    qc_avg_mpa: float | None
    e_n_mpa: float | None
    phi_n_deg: float | None
    c_n_kpa: float | None
    phi_i_deg: float | None
    c_i_kpa: float | None
    phi_ii_deg: float | None
    c_ii_kpa: float | None
    note_marks: tuple[str, ...] = ()
    n_points: int = 0
    v_qc: float | None = None
    avg_depth_m: float | None = None
    reference_only: bool = False
    blocked: bool = False
    status_text: str = ""
    detail_reason: str = ""
    lookup_label: str = ""
    interpolation_summary: str = ""
    density_class: str = ""
    selected_lookup_rules: tuple[str, ...] = ()
    sounding_labels: tuple[str, ...] = ()
    qc_by_sounding: tuple[tuple[str, tuple[float, ...]], ...] = ()
    qc_design_i_mpa: float | None = None
    qc_design_ii_mpa: float | None = None
    warning_lines: tuple[str, ...] = ()

    def normative_marks(self) -> tuple[str, ...]:
        return tuple(mark for mark in self.note_marks if mark in (NOTE_LEGACY_SUPES, NOTE_PRELIM_FILL))

    def design_marks(self) -> tuple[str, ...]:
        marks = list(self.normative_marks())
        if NOTE_REFERENCE_ONLY in self.note_marks:
            marks.append(NOTE_REFERENCE_ONLY)
        return tuple(marks)

    def export_summary_values(self) -> tuple[str, ...]:
        normative_marks = self.normative_marks()
        design_marks = self.design_marks()
        return (
            compact_ige_label(self.ige_id),
            self.soil_name or "—",
            export_decimal_text(format_qc(self.qc_avg_mpa)),
            export_decimal_text(format_with_marks(format_phi(self.phi_n_deg), normative_marks)),
            export_decimal_text(format_with_marks(format_c(self.c_n_kpa), normative_marks)),
            export_decimal_text(format_with_marks(format_phi(self.phi_i_deg), design_marks)),
            export_decimal_text(format_with_marks(format_c(self.c_i_kpa), design_marks)),
            export_decimal_text(format_with_marks(format_phi(self.phi_ii_deg), design_marks)),
            export_decimal_text(format_with_marks(format_c(self.c_ii_kpa), design_marks)),
            export_decimal_text(format_with_marks(format_e(self.e_n_mpa), normative_marks)),
        )


@dataclass(frozen=True)
class StaticCalcRunResult:
    title: str
    project_name: str
    calculation_date: str
    algorithm_version: str
    lookup_path: str
    rows: tuple[StaticCalcRow, ...]
    used_note_marks: tuple[str, ...] = ()
    global_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class StaticCalcPreviewSection:
    heading: str
    lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class StaticCalcPreviewDocument:
    title: str
    intro_lines: tuple[str, ...]
    sections: tuple[StaticCalcPreviewSection, ...]
    summary_headers: tuple[str, ...] = SUMMARY_HEADERS
    summary_rows: tuple[tuple[str, ...], ...] = ()
    note_lines: tuple[str, ...] = ()
    statistics_lines: tuple[str, ...] = ()


def render_preview_document_text(document: StaticCalcPreviewDocument) -> str:
    lines: list[str] = [document.title]
    if document.intro_lines:
        lines.extend(["", *document.intro_lines])
    if document.summary_rows:
        lines.extend(["", "Итоговая таблица"])
        lines.append(" | ".join(document.summary_headers))
        for row in document.summary_rows:
            lines.append(" | ".join(row))
    if document.note_lines:
        lines.extend(["", "Примечание", *document.note_lines])
    if document.statistics_lines:
        lines.extend(["", "Особенности расчета", *document.statistics_lines])
    for section in document.sections:
        lines.extend(["", section.heading, *(section.lines or ("—",))])
    return "\n".join(lines).strip()


def render_screen_protocol_text(document: StaticCalcPreviewDocument) -> str:
    """The calc tab now shows only the compact table, so screen protocol is hidden."""

    return ""
