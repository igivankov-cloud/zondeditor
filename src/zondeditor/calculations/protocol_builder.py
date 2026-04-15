"""Builders for compact and detailed static sounding calculation previews."""

from __future__ import annotations

from .preview_model import (
    EXPORT_PROTOCOL_TITLE,
    EXPORT_SUMMARY_HEADERS,
    INDEX_NOTE_LINES,
    NOTE_LEGENDS,
    StaticCalcPreviewDocument,
    StaticCalcPreviewSection,
    StaticCalcRow,
    StaticCalcRunResult,
    compact_ige_label,
    export_decimal_text,
    format_c,
    format_e,
    format_phi,
    format_qc,
    format_variation,
)


DETAILED_PROTOCOL_TITLE = "Подробный протокол расчета по результатам статического зондирования"


def _used_experiments_text(result: StaticCalcRunResult) -> str:
    labels: list[str] = []
    for row in result.rows:
        for label in row.sounding_labels:
            if label not in labels:
                labels.append(label)
    return "; ".join(labels) if labels else "—"


def _note_lines(result: StaticCalcRunResult) -> tuple[str, ...]:
    lines = [f"{mark} — {NOTE_LEGENDS[mark]}" for mark in result.used_note_marks if mark in NOTE_LEGENDS]
    lines.extend(INDEX_NOTE_LINES)
    return tuple(lines)


def _stat_issue_line(row: StaticCalcRow) -> str | None:
    label = f"ИГЭ {compact_ige_label(row.ige_id)}"
    detail = str(row.detail_reason or "").strip()
    if "табличные зависимости" in detail.lower():
        return f"{label} — {detail[:1].lower() + detail[1:]}"
    reasons: list[str] = []
    if int(row.n_points or 0) < 6:
        reasons.append(f"n = {int(row.n_points or 0)} при требуемом n ≥ 6")
    if row.v_qc is not None and float(row.v_qc) > 0.30:
        reasons.append(f"V = {format_variation(row.v_qc)} при допустимом V ≤ 0,30")
    if not reasons:
        return None
    if row.phi_i_deg is None and row.c_i_kpa is None and row.phi_ii_deg is None and row.c_ii_kpa is None:
        return f"{label} — расчетные значения не приведены: {'; '.join(reasons)}"
    return f"{label} — число опытов n = {int(row.n_points or 0)}; коэффициент вариации V = {format_variation(row.v_qc)}"


def _statistics_lines(result: StaticCalcRunResult) -> tuple[str, ...]:
    return tuple(line for row in result.rows if (line := _stat_issue_line(row)))


def build_static_calc_preview(result: StaticCalcRunResult) -> StaticCalcPreviewDocument:
    return StaticCalcPreviewDocument(
        title=EXPORT_PROTOCOL_TITLE,
        intro_lines=(
            f"Объект: {result.project_name or '—'}",
            f"Опыты: {_used_experiments_text(result)}",
            "Таблица 1",
        ),
        sections=(),
        summary_headers=EXPORT_SUMMARY_HEADERS,
        summary_rows=tuple(row.export_summary_values() for row in result.rows),
        note_lines=_note_lines(result),
        statistics_lines=_statistics_lines(result),
    )


def _result_lines(row: StaticCalcRow) -> tuple[str, ...]:
    return (
        f"qcср = {export_decimal_text(format_qc(row.qc_avg_mpa))} МПа",
        f"E = {export_decimal_text(format_e(row.e_n_mpa))} МПа",
        f"φ = {export_decimal_text(format_phi(row.phi_n_deg))} град",
        f"c = {export_decimal_text(format_c(row.c_n_kpa))} кПа",
        f"φ1 = {export_decimal_text(format_phi(row.phi_i_deg))} град",
        f"c1 = {export_decimal_text(format_c(row.c_i_kpa))} кПа",
        f"φ2 = {export_decimal_text(format_phi(row.phi_ii_deg))} град",
        f"c2 = {export_decimal_text(format_c(row.c_ii_kpa))} кПа",
    )


def _detail_section(row: StaticCalcRow) -> StaticCalcPreviewSection:
    lines: list[str] = [
        "Исходные данные",
        f"В расчет включены опыты статического зондирования: {', '.join(row.sounding_labels) if row.sounding_labels else '—'}",
        f"Число опытов: n = {int(row.n_points or 0)}",
        f"Среднее значение qc: {export_decimal_text(format_qc(row.qc_avg_mpa))} МПа",
        f"Коэффициент вариации V: {format_variation(row.v_qc)}",
        "",
        "Результат",
        *_result_lines(row),
    ]
    if row.detail_reason:
        lines.extend(["", "Особенности расчета", str(row.detail_reason)])
    return StaticCalcPreviewSection(
        heading=f"ИГЭ {compact_ige_label(row.ige_id)}. {row.soil_name or '—'}",
        lines=tuple(lines),
    )


def build_static_calc_detailed_preview(result: StaticCalcRunResult) -> StaticCalcPreviewDocument:
    return StaticCalcPreviewDocument(
        title=DETAILED_PROTOCOL_TITLE,
        intro_lines=(
            f"Объект: {result.project_name or '—'}",
            f"В расчет включены опыты статического зондирования: {_used_experiments_text(result)}",
            "Нормативная база:",
            "СП 446.1325800.2019 (с Изм. № 1), приложение Ж",
            "СП 22.13330.2016, п. 5.3.17",
            "ГОСТ 20522-2012",
        ),
        sections=tuple(_detail_section(row) for row in result.rows),
        summary_headers=EXPORT_SUMMARY_HEADERS,
        summary_rows=tuple(row.export_summary_values() for row in result.rows),
        note_lines=_note_lines(result),
        statistics_lines=_statistics_lines(result),
    )
