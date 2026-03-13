from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import IGECalcSample
from .normative_profiles import load_normative_profiles


def _soil_name_from_sample(sample: IGECalcSample) -> str:
    method = str(sample.method or "").upper()
    if "SAND" in method:
        return "песок"
    if "CLAY" in method:
        return "глинистый"
    return ""


def build_protocol(*, project_name: str, profile_id: str, samples: list[IGECalcSample]) -> dict[str, Any]:
    profiles = load_normative_profiles()
    prof = profiles.get(profile_id)

    not_applicable: list[dict[str, Any]] = []
    warnings: list[str] = []
    ige_results: list[dict[str, Any]] = []
    calc_trace: list[dict[str, Any]] = []
    export_ready_params: list[dict[str, Any]] = []

    for s in samples or []:
        soil_name = _soil_name_from_sample(s)
        if s.warnings:
            warnings.extend(s.warnings)

        if s.status in {"NOT_APPLICABLE", "LAB_ONLY", "NOT_IMPLEMENTED", "INVALID_INPUT"}:
            not_applicable.append(
                {
                    "ige_label": s.ige_id,
                    "soil_name": soil_name,
                    "status": s.status,
                    "reason": (s.warnings[0] if s.warnings else ""),
                    "missing_fields": list(s.missing_fields or []),
                    "errors": list(s.errors or []),
                    "required_fields": list(s.required_fields or []),
                }
            )

        row = {
            "ige_label": s.ige_id,
            "soil_name": soil_name,
            "normative_profile": profile_id,
            "method": s.method,
            "status": s.status,
            "used_soundings": list(s.used_sounding_ids or []),
            "depth_interval": s.depth_interval,
            "n_points": s.stats.n_points,
            "n_soundings": int(getattr(s, "sounding_count", 0) or 0),
            "n_lt_6_triggered": bool(getattr(s, "n_lt_6_triggered", False)),
            "n_lt_6_blocked": bool(getattr(s, "n_lt_6_blocked", False)),
            "n_lt_6_overridden": bool(getattr(s, "n_lt_6_overridden", False)),
            "excluded_points": list(s.excluded_points or []),
            "excluded_reasons": list(s.exclusions or []),
            "sample_stats": {
                "qc_avg_mpa": s.stats.qc_avg_mpa,
                "qc_min_mpa": s.stats.qc_min_mpa,
                "qc_max_mpa": s.stats.qc_max_mpa,
                "fs_avg_kpa": s.stats.fs_avg_kpa,
                "v_qc": s.stats.v_qc,
                "avg_depth_m": s.stats.avg_depth_m,
            },
            "result_params": {
                "E_MPa": s.result.E_MPa,
                "phi_deg": s.result.phi_deg,
                "c_kPa": s.result.c_kPa,
            },
            "warnings": list(s.warnings or []),
            "errors": list(s.errors or []),
            "missing_fields": list(s.missing_fields or []),
            "required_fields": list(s.required_fields or []),
            "contributing_layers": list(s.contributing_layers or []),
            "preliminary_or_not_applicable": bool(s.status in {"PRELIMINARY", "NOT_APPLICABLE", "LAB_ONLY", "NOT_IMPLEMENTED", "INVALID_INPUT"}),
        }
        ige_results.append(row)
        calc_trace.append(row)

        export_ready_params.append(
            {
                "ige_id": s.ige_id,
                "status": s.status,
                "method": s.method,
                "E_MPa": s.result.E_MPa,
                "phi_deg": s.result.phi_deg,
                "c_kPa": s.result.c_kPa,
                "warnings": list(s.warnings or []),
                "errors": list(s.errors or []),
            }
        )

    return {
        "project_name": project_name,
        "profile_id": profile_id,
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat(),
        "sections": {
            "header": {
                "object_name": project_name,
                "profile_name": (prof.profile_name if prof else profile_id),
                "documents_used": [f"{d.get('title', '')} {d.get('amendments', '')}".strip() for d in (prof.documents if prof else [])],
            },
            "ige_results": ige_results,
            "not_applicable": not_applicable,
            "warnings": warnings,
            "calculation_trace": calc_trace,
            "export_ready_params": export_ready_params,
        },
    }



def _human_method_name(method_key: str) -> str:
    key = str(method_key or '').upper()
    mapping = {
        'SP446_CPT_SAND': 'СП 446: песчаная ветка',
        'SP446_CPT_CLAY': 'СП 446: глинистая ветка',
        'LAB_ONLY': 'Лабораторный путь / неприменимо для CPT',
    }
    return mapping.get(key, method_key or '')


def _calc_path_name(sample: IGECalcSample) -> str:
    warnings_joined = ' | '.join(sample.warnings or []).lower()
    method = str(sample.method or '').upper()
    if 'старой редакции' in warnings_joined and 'CLAY' in method:
        return 'супесь по старой редакции'
    if str(sample.status or '').upper() == 'PRELIMINARY':
        return 'предварительный насыпной'
    if 'SAND' in method:
        return 'песчаная ветка'
    if 'CLAY' in method:
        return 'глинистая ветка'
    if str(sample.status or '').upper() in {'NOT_APPLICABLE', 'LAB_ONLY', 'NOT_IMPLEMENTED', 'INVALID_INPUT', 'N_LT_6_BLOCKED'}:
        return 'неприменимо / заблокировано / not implemented'
    return 'неприменимо / заблокировано / not implemented'


def build_debug_protocol_text(*, project_name: str, profile_id: str, samples: list[IGECalcSample], calc_options: dict[str, Any] | None = None) -> str:
    calc_options = dict(calc_options or {})
    lines: list[str] = []
    lines.append(f'Отладочный протокол расчёта: {project_name or "(без названия)"}')
    lines.append(f'Норматив: {profile_id}')
    lines.append('')

    if not samples:
        lines.append('Нет данных для протокола. Сначала пересоберите выборки.')
        return '\n'.join(lines)

    for idx, s in enumerate(samples, start=1):
        lines.append(f'=== ИГЭ #{idx}: {s.ige_id} ===')
        lines.append('A. Паспорт расчёта')
        lines.append(f'- ИГЭ: {s.ige_id}')
        lines.append(f'- Тип: {_soil_name_from_sample(s) or "не определён"}')
        lines.append(f'- subtype: {getattr(s, "subtype", None) or "—"}')
        lines.append(f'- Норматив расчёта по зондированию: {calc_options.get("cpt_method", "СП 446.1325800.2019, приложение Ж")}')
        lines.append(f'- Переход к нормативным/расчётным: {calc_options.get("transition_method", "СП 22.13330.2016 (п. 5.3.17)")}')
        lines.append('- Флаги:')
        lines.append(f'  * N < 6: {"вкл" if bool(calc_options.get("allow_normative_lt6")) else "выкл"}')
        lines.append(f'  * супесь по старой редакции: {"вкл" if bool(calc_options.get("use_legacy_sandy_loam_sp446")) else "выкл"}')
        lines.append(f'  * предварительный насыпной: {"вкл" if bool(calc_options.get("allow_fill_preliminary")) else "выкл"}')

        lines.append('Б. Выборка')
        lines.append(f'- Использованные опыты: {", ".join(s.used_sounding_ids or []) or "—"}')
        lines.append(f'- Число опытов (N): {int(getattr(s, "sounding_count", 0) or 0)}')
        before = int((s.stats.n_points or 0) + (s.excluded_count or 0))
        lines.append(f'- Число точек до фильтрации: {before}')
        lines.append(f'- Число точек выборки: {int(s.stats.n_points or 0)}')
        if s.excluded_points:
            lines.append('- Исключённые точки:')
            for ep in s.excluded_points[:30]:
                lines.append(f'  * {ep.get("sounding_id", "?")} @ {ep.get("depth_m", "?")} м — {ep.get("reason", "")}')
            if len(s.excluded_points) > 30:
                lines.append(f'  * ... ещё {len(s.excluded_points)-30}')
        else:
            lines.append('- Исключённые точки: нет')
        if s.depth_interval:
            lines.append(f'- Интервал глубин: {float(s.depth_interval[0]):.2f}-{float(s.depth_interval[1]):.2f} м')
        else:
            lines.append('- Интервал глубин: —')
        lines.append('В. Статистика')
        lines.append(f'- qc_min: {s.stats.qc_min_mpa}')
        lines.append(f'- qc_avg: {s.stats.qc_avg_mpa}')
        lines.append(f'- qc_max: {s.stats.qc_max_mpa}')
        lines.append(f'- V: {s.stats.v_qc}')
        lines.append(f'- fs_avg: {s.stats.fs_avg_kpa}')

        lines.append('Г. Метод')
        lines.append(f'- Внутренний ключ: {s.method}')
        lines.append(f'- Человекочитаемое имя: {_human_method_name(s.method)}')
        lines.append(f'- Выбранный путь: {_calc_path_name(s)}')

        lines.append('Д. Расчёт')
        lines.append(f'- Входные: qc_avg={s.stats.qc_avg_mpa}, n={s.stats.n_points}, avg_depth={s.stats.avg_depth_m}')
        lines.append(f'- Промежуточные: V={s.stats.v_qc}, excluded={s.excluded_count}')
        lines.append(f'- Итог E: {s.result.E_MPa}')
        lines.append(f'- Итог phi: {s.result.phi_deg}')
        if s.result.c_kPa is None and 'SAND' in str(s.method or '').upper():
            lines.append('- Итог c: c не вычисляется для данной ветки')
        else:
            lines.append(f'- Итог c: {s.result.c_kPa}')

        lines.append('Е. Результат')
        lines.append(f'- Статус: {s.status}')
        lines.append(f'- Правило N < 6 сработало: {"да" if bool(getattr(s, "n_lt_6_triggered", False)) else "нет"}')
        lines.append(f'- Расчёт заблокирован по N < 6: {"да" if bool(getattr(s, "n_lt_6_blocked", False)) else "нет"}')
        lines.append(f'- Разрешён по override N < 6: {"да" if bool(getattr(s, "n_lt_6_overridden", False)) else "нет"}')
        lines.append(f'- warnings: {"; ".join(s.warnings or []) or "—"}')
        lines.append(f'- errors: {"; ".join(s.errors or []) or "—"}')
        lines.append(f'- missing fields: {", ".join(s.missing_fields or []) or "—"}')
        lines.append(f'- Финальный вывод: {"расчёт доступен" if s.status in {"CALCULATED", "PRELIMINARY"} else "требуется внимание / блокировка"}')
        lines.append('')

    return "\n".join(lines)
