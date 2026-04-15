"""Lookup-driven static sounding calculation engine for SP 446."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import NormalDist, mean, pstdev
from typing import Any, Iterable
import re

from src.zondeditor.domain.layers import SoilType

from .lookup_loader import LookupDataset, LookupRule, load_lookup_dataset
from .preview_model import (
    LOOKUP_RELATIVE_PATH,
    NOTE_LEGACY_SUPES,
    NOTE_PRELIM_FILL,
    NOTE_REFERENCE_ONLY,
    STATIC_CALC_ALGORITHM_VERSION,
    StaticCalcRow,
    StaticCalcRunResult,
)


@dataclass(frozen=True)
class StaticCalcOptions:
    use_legacy_sandy_loam_sp446: bool = False
    allow_fill_preliminary: bool = False
    allow_reference_on_insufficient_stats: bool = False
    alluvial_sands: bool = True
    lookup_relative_path: str = LOOKUP_RELATIVE_PATH


@dataclass(frozen=True)
class _QcPoint:
    sounding_label: str
    depth_m: float
    qc_mpa: float


def _to_float(value: Any) -> float | None:
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def convert_cohesion_mpa_to_kpa(value_mpa: float | None) -> float | None:
    """Convert cohesion from MPa to kPa after interpolation."""

    if value_mpa is None:
        return None
    return float(value_mpa) * 1000.0


def _capitalize(text: str) -> str:
    value = str(text or "").strip()
    return value[:1].upper() + value[1:] if value else ""


def _sound_label(test: Any) -> str:
    return f"ТСЗ-{int(getattr(test, 'tid', 0) or 0)}"


def _iter_points_in_layer(test: Any, layer: Any) -> Iterable[_QcPoint]:
    depths = list(getattr(test, "depth", []) or [])
    qcs = list(getattr(test, "qc", []) or [])
    top = float(getattr(layer, "top_m", 0.0) or 0.0)
    bot = float(getattr(layer, "bot_m", 0.0) or 0.0)
    limit = min(len(depths), len(qcs))
    label = _sound_label(test)
    for idx in range(limit):
        depth_m = _to_float(depths[idx])
        qc_mpa = _to_float(qcs[idx])
        if depth_m is None or qc_mpa is None or qc_mpa <= 0:
            continue
        if top <= depth_m <= bot:
            yield _QcPoint(sounding_label=label, depth_m=depth_m, qc_mpa=qc_mpa)


def _soil_name(entry: dict[str, Any]) -> str:
    return str(entry.get("soil_type") or "").strip().lower()


def _normalize_sand_kind(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if value in {"гравелистый", "крупный", "средней крупности"}:
        return "крупные и средней крупности"
    if value == "мелкий":
        return "мелкие"
    if value == "пылеватый":
        return "пылеватые"
    return "все пески"


def _normalize_water_saturation(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if value == "водонасыщенный":
        return "водонасыщенные"
    if value in {"малой степени", "влажный", "средней степени"}:
        return "малой и средней степени водонасыщения"
    return "любая"


def _normalize_fill_subtype(raw: str) -> str:
    return str(raw or "").strip().lower()


def _is_fill_debris_subtype(raw: str) -> bool:
    value = _normalize_fill_subtype(raw)
    return "10%" in value or "строит" in value


def _fill_material_kind(raw: str) -> str:
    value = _normalize_fill_subtype(raw)
    if _is_fill_debris_subtype(value):
        return "debris"
    if "песчан" in value:
        return "sand"
    if "глинист" in value:
        return "clay"
    return ""


def _fill_normative_block_reason() -> str:
    return (
        "Для насыпного грунта с содержанием строительного мусора более 10% "
        "в принятом нормативном источнике отсутствуют табличные зависимости "
        "для расчета по результатам статического зондирования"
    )


def _normalize_consistency(soil_name: str, raw: str) -> str:
    value = str(raw or "").strip().lower()
    if not value:
        return ""
    if soil_name == SoilType.LOAM.value:
        mapping = {
            "твердая": "твердый",
            "твердый": "твердый",
            "полутвердая": "полутвердый",
            "полутвердый": "полутвердый",
            "тугопластичная": "тугопластичный",
            "тугопластичный": "тугопластичный",
        }
        return mapping.get(value, value)
    if soil_name == SoilType.CLAY.value:
        mapping = {
            "твердый": "твердая",
            "твердая": "твердая",
            "полутвердый": "полутвердая",
            "полутвердая": "полутвердая",
            "тугопластичный": "тугопластичная",
            "тугопластичная": "тугопластичная",
            "мягкопластичный": "мягкопластичная",
            "мягкопластичная": "мягкопластичная",
            "текучепластичный": "текучепластичная",
            "текучепластичная": "текучепластичная",
        }
        return mapping.get(value, value)
    if soil_name == SoilType.SANDY_LOAM.value:
        mapping = {
            "твердый": "твердая",
            "твердая": "твердая",
            "полутвердый": "полутвердая",
            "полутвердая": "полутвердая",
            "тугопластичный": "тугопластичная",
            "тугопластичная": "тугопластичная",
            "мягкопластичный": "мягкопластичная",
            "мягкопластичная": "мягкопластичная",
            "текучепластичный": "текучепластичная",
            "текучепластичная": "текучепластичная",
            "пластичный": "пластичная",
            "пластичная": "пластичная",
            "текучий": "текучая",
            "текучая": "текучая",
        }
        return mapping.get(value, value)
    return value


def _manual_or_generated_soil_name(entry: dict[str, Any]) -> str:
    manual_text = str(entry.get("manual_notes") or entry.get("notes") or "").strip()
    if manual_text:
        return _capitalize(manual_text)
    soil_name = str(entry.get("soil_type") or "").strip()
    if not soil_name:
        return "—"
    if soil_name == SoilType.SAND.value:
        parts = [str(entry.get("sand_kind") or "").strip(), str(entry.get("sand_water_saturation") or "").strip(), str(entry.get("density_state") or "").strip()]
        parts = [part for part in parts if part]
        if not parts:
            return "Песок"
        return _capitalize(f"песок {parts[0]}" + (f", {', '.join(parts[1:])}" if len(parts) > 1 else ""))
    if soil_name in {SoilType.LOAM.value, SoilType.CLAY.value, SoilType.SANDY_LOAM.value}:
        consistency = _normalize_consistency(soil_name, str(entry.get("consistency") or ""))
        return _capitalize(f"{soil_name} {consistency}".strip())
    if soil_name == SoilType.FILL.value:
        subtype = str(entry.get("fill_subtype") or "").strip()
        return _capitalize(f"насыпной грунт {subtype}".strip())
    return _capitalize(soil_name)


def _ige_sort_key(ige_id: str) -> tuple[int, str]:
    text = str(ige_id or "").strip()
    match = re.search(r"(\d+)\s*([A-Za-zА-Яа-я]*)$", text)
    if not match:
        return (10**9, text.casefold())
    return (int(match.group(1)), match.group(2).casefold())


def _collect_points_for_ige(tests: list[Any], ige_id: str) -> list[_QcPoint]:
    points: list[_QcPoint] = []
    for test in tests or []:
        if not bool(getattr(test, "export_on", True)):
            continue
        for layer in list(getattr(test, "layers", []) or []):
            if str(getattr(layer, "ige_id", "") or "").strip() != ige_id:
                continue
            points.extend(list(_iter_points_in_layer(test, layer)))
    points.sort(key=lambda item: (item.sounding_label, item.depth_m, item.qc_mpa))
    return points


def _calc_stats(points: list[_QcPoint]) -> tuple[int, float | None, float | None, float | None]:
    if not points:
        return 0, None, None, None
    sounding_qc: dict[str, list[float]] = {}
    for point in points:
        sounding_qc.setdefault(point.sounding_label, []).append(point.qc_mpa)
    sounding_avgs = [float(mean(values)) for values in sounding_qc.values() if values]
    if not sounding_avgs:
        return 0, None, None, None
    # n for this module means the number of independent active soundings, not the count of depth points.
    qc_avg = float(mean(sounding_avgs))
    variation = 0.0
    if len(sounding_avgs) > 1 and qc_avg > 0:
        variation = float(pstdev(sounding_avgs) / qc_avg)
    avg_depth = float(mean([point.depth_m for point in points]))
    return len(sounding_avgs), qc_avg, variation, avg_depth


def _points_by_sounding(points: list[_QcPoint]) -> tuple[tuple[str, tuple[float, ...]], ...]:
    ordered: list[tuple[str, tuple[float, ...]]] = []
    buckets: dict[str, list[float]] = {}
    for point in points:
        buckets.setdefault(point.sounding_label, []).append(point.qc_mpa)
    for sounding_label in sorted(buckets):
        ordered.append((sounding_label, tuple(buckets[sounding_label])))
    return tuple(ordered)


def _filter_rules(rules: Iterable[LookupRule], **criteria: str) -> list[LookupRule]:
    result: list[LookupRule] = []
    for rule in rules:
        matched = True
        for field_name, expected in criteria.items():
            if expected in {"", "все", "любая"}:
                continue
            actual = str(getattr(rule, field_name) or "").strip().lower()
            if actual != str(expected or "").strip().lower():
                matched = False
                break
        if matched:
            result.append(rule)
    return sorted(result, key=lambda item: (item.priority, item.rule_id))


def _point_value(rule: LookupRule) -> tuple[float, float] | None:
    xval = rule.qc_from_mpa if rule.qc_from_mpa is not None else rule.qc_to_mpa
    if xval is None or rule.output_value_num is None:
        return None
    return float(xval), float(rule.output_value_num)


def _interpolate_point_rules(rules: list[LookupRule], qc_mpa: float) -> tuple[float | None, list[str], list[str], str]:
    points: list[tuple[float, float, str]] = []
    for rule in rules:
        parsed = _point_value(rule)
        if parsed is None:
            continue
        xval, yval = parsed
        points.append((xval, yval, rule.rule_id))
    if not points:
        return None, [], [], "табличные точки не найдены"
    points.sort(key=lambda item: item[0])
    warnings: list[str] = []
    if qc_mpa <= points[0][0]:
        value = points[0][1]
        if qc_mpa < points[0][0]:
            warnings.append(f"qc={qc_mpa:.3f} МПа ниже диапазона таблицы; использовано граничное значение {points[0][0]:.3f} МПа")
        return value, warnings, [points[0][2]], f"использовано граничное значение по qc={points[0][0]:.2f} МПа"
    if qc_mpa >= points[-1][0]:
        value = points[-1][1]
        if qc_mpa > points[-1][0]:
            warnings.append(f"qc={qc_mpa:.3f} МПа выше диапазона таблицы; использовано граничное значение {points[-1][0]:.3f} МПа")
        return value, warnings, [points[-1][2]], f"использовано граничное значение по qc={points[-1][0]:.2f} МПа"
    for index in range(1, len(points)):
        left_x, left_y, left_rule = points[index - 1]
        right_x, right_y, right_rule = points[index]
        if left_x <= qc_mpa <= right_x:
            if right_x == left_x:
                value = left_y
            else:
                part = (qc_mpa - left_x) / (right_x - left_x)
                value = left_y + ((right_y - left_y) * part)
            return value, warnings, [left_rule, right_rule], f"линейная интерполяция по qc между {left_x:.2f} и {right_x:.2f} МПа"
    return None, warnings, [], "табличный интервал не найден"


def _range_lookup(rules: list[LookupRule], qc_mpa: float) -> tuple[str, list[str], list[str], str]:
    for rule in rules:
        low = float(rule.qc_from_mpa) if rule.qc_from_mpa is not None else None
        high = float(rule.qc_to_mpa) if rule.qc_to_mpa is not None else None
        if low is not None and qc_mpa < low:
            continue
        if high is not None and qc_mpa >= high:
            continue
        label = str(rule.output_value_text or "").strip()
        if not label:
            continue
        interval = []
        if low is not None:
            interval.append(f"от {low:.2f}")
        if high is not None:
            interval.append(f"до {high:.2f}")
        return label, [], [rule.rule_id], f"диапазон qc {' '.join(interval) if interval else 'без ограничений'} МПа"
    return "—", [], [], "диапазон qc не найден"


def _j3_phi(dataset: LookupDataset, qc_mpa: float, avg_depth_m: float, warnings: list[str]) -> tuple[float | None, list[str], str]:
    base_rules = [rule for rule in dataset.rules if rule.appendix_table == "Ж.3" and rule.output_param == "phi_deg"]
    rules_lt2 = [rule for rule in base_rules if rule.depth_to_m is not None and float(rule.depth_to_m) <= 2.0]
    rules_ge5 = [rule for rule in base_rules if rule.depth_from_m is not None and float(rule.depth_from_m) >= 5.0]
    phi_2m, warn_2m, rules_2m, note_2m = _interpolate_point_rules(rules_lt2, qc_mpa)
    phi_5m, warn_5m, rules_5m, note_5m = _interpolate_point_rules(rules_ge5, qc_mpa)
    warnings.extend(warn_2m)
    warnings.extend(warn_5m)
    if avg_depth_m <= 2.0:
        return phi_2m, rules_2m, f"табл. Ж.3, колонка «2 м»; {note_2m}"
    if avg_depth_m >= 5.0:
        return phi_5m, rules_5m, f"табл. Ж.3, колонка «5 м и более»; {note_5m}"
    if phi_2m is None or phi_5m is None:
        return None, [], "табл. Ж.3: недостаточно данных для интерполяции по глубине"
    part = (avg_depth_m - 2.0) / 3.0
    phi_val = phi_2m + ((phi_5m - phi_2m) * part)
    return phi_val, list(dict.fromkeys(rules_2m + rules_5m)), (
        "табл. Ж.3: линейная интерполяция по глубине между колонками «2 м» и «5 м и более»; "
        f"{note_2m}; {note_5m}"
    )


def _select_rules(dataset: LookupDataset, *, edition_mode: str, appendix_table: str, output_param: str, soil_kind_ru: str, genetic_group: str = "все", state_or_consistency: str = "все", water_saturation: str = "все") -> list[LookupRule]:
    base = [
        rule for rule in dataset.rules
        if rule.method == "static"
        and rule.edition_mode == edition_mode
        and rule.appendix_table == appendix_table
        and rule.output_param == output_param
    ]
    return _filter_rules(
        base,
        soil_kind_ru=soil_kind_ru,
        genetic_group=genetic_group,
        state_or_consistency=state_or_consistency,
        water_saturation=water_saturation,
    )


def _sand_result(entry: dict[str, Any], dataset: LookupDataset, qc_avg: float, avg_depth: float, alluvial_sands: bool) -> tuple[dict[str, float | str | None], list[str], list[str], str]:
    warnings: list[str] = []
    rule_ids: list[str] = []
    sand_kind = _normalize_sand_kind(str(entry.get("sand_kind") or ""))
    saturation = _normalize_water_saturation(str(entry.get("sand_water_saturation") or ""))
    j1_rules = _select_rules(dataset, edition_mode="current", appendix_table="Ж.1", output_param="density_class", soil_kind_ru=sand_kind, water_saturation=saturation)
    density_class, warn_j1, ids_j1, note_j1 = _range_lookup(j1_rules, qc_avg)
    warnings.extend(warn_j1)
    rule_ids.extend(ids_j1)

    genetic_group = "аллювиальные и флювиогляциальные" if bool(alluvial_sands) else "кроме аллювиальных и флювиогляциальных"
    j2_rules = _select_rules(dataset, edition_mode="current", appendix_table="Ж.2", output_param="E_MPa", soil_kind_ru="все пески", genetic_group=genetic_group)
    e_n, warn_j2, ids_j2, note_j2 = _interpolate_point_rules(j2_rules, qc_avg)
    warnings.extend(warn_j2)
    rule_ids.extend(ids_j2)

    phi_n, ids_j3, note_j3 = _j3_phi(dataset, qc_avg, avg_depth, warnings)
    rule_ids.extend(ids_j3)

    return (
        {
            "density_class": density_class,
            "e_n_mpa": e_n,
            "phi_n_deg": phi_n,
            "c_n_kpa": None,
            "lookup_label": f"Ж.1 / Ж.2 / Ж.3 ({'аллювиальные' if alluvial_sands else 'неаллювиальные'} пески)",
            "interpolation": f"{note_j1}; {note_j2}; {note_j3}",
        },
        warnings,
        list(dict.fromkeys(rule_ids)),
        "",
    )


def _clay_like_result(dataset: LookupDataset, qc_avg: float, *, edition_mode: str, soil_kind_ru: str, state_or_consistency: str, note_suffix: str = "") -> tuple[dict[str, float | str | None], list[str], list[str], str]:
    warnings: list[str] = []
    rule_ids: list[str] = []
    payload: dict[str, float | str | None] = {
        "density_class": "",
        "lookup_label": f"Ж.4{note_suffix}",
        "interpolation": "",
    }
    notes: list[str] = []
    for output_param in ("E_MPa", "phi_deg", "c_kPa"):
        lookup_param = output_param
        rules = _select_rules(
            dataset,
            edition_mode=edition_mode,
            appendix_table="Ж.4",
            output_param=lookup_param,
            soil_kind_ru=soil_kind_ru,
            state_or_consistency=state_or_consistency,
        )
        convert_c_from_mpa = False
        if output_param == "c_kPa" and not rules:
            lookup_param = "c_MPa"
            rules = _select_rules(
                dataset,
                edition_mode=edition_mode,
                appendix_table="Ж.4",
                output_param=lookup_param,
                soil_kind_ru=soil_kind_ru,
                state_or_consistency=state_or_consistency,
            )
            convert_c_from_mpa = True
        value, param_warnings, param_rule_ids, note = _interpolate_point_rules(rules, qc_avg)
        if output_param == "c_kPa" and convert_c_from_mpa:
            # In SP 446 table Ж.4 cohesion may be given in MPa; convert to kPa only after interpolation.
            value = convert_cohesion_mpa_to_kpa(value)
            if value is not None:
                note += "; после интерполяции выполнен перевод c из МПа в кПа"
        warnings.extend(param_warnings)
        rule_ids.extend(param_rule_ids)
        notes.append(f"{lookup_param}: {note}")
        if output_param == "E_MPa":
            payload["e_n_mpa"] = value
        elif output_param == "phi_deg":
            payload["phi_n_deg"] = value
        else:
            payload["c_n_kpa"] = value
    payload["interpolation"] = "; ".join(notes)
    if payload.get("e_n_mpa") is None and payload.get("phi_n_deg") is None and payload.get("c_n_kpa") is None:
        return payload, warnings, rule_ids, "По выбранному состоянию в lookup нет нормативных значений"
    return payload, warnings, list(dict.fromkeys(rule_ids)), ""


def _fill_preliminary_result(entry: dict[str, Any], dataset: LookupDataset, qc_avg: float, avg_depth: float, alluvial_sands: bool) -> tuple[dict[str, float | str | None], list[str], list[str], str]:
    subtype = _normalize_fill_subtype(entry.get("fill_subtype"))
    if not subtype:
        return {}, [], [], "Для предварительного расчёта насыпного требуется выбрать материал заполнителя"
    material_kind = _fill_material_kind(subtype)
    if material_kind == "debris":
        return {}, [], [], _fill_normative_block_reason()
    if material_kind == "sand":
        return _sand_result(entry, dataset, qc_avg, avg_depth, alluvial_sands)
    if material_kind == "clay":
        # For preliminary fill-by-material calculations, clayey fill is mapped
        # to the clay branch with a representative consistency from table Ж.4.
        return _clay_like_result(
            dataset,
            qc_avg,
            edition_mode="current",
            soil_kind_ru="глина",
            state_or_consistency="тугопластичная",
            note_suffix=" (предварительно по материалу)",
        )
    return {}, [], [], "Для предварительного расчёта насыпного требуется выбрать поддерживаемый материал заполнителя"


def _blocked_row(ige_id: str, soil_name: str, qc_avg: float | None, n_points: int, v_qc: float | None, avg_depth: float | None, reason: str) -> StaticCalcRow:
    return StaticCalcRow(
        ige_id=ige_id,
        soil_name=soil_name,
        qc_avg_mpa=qc_avg,
        e_n_mpa=None,
        phi_n_deg=None,
        c_n_kpa=None,
        phi_i_deg=None,
        c_i_kpa=None,
        phi_ii_deg=None,
        c_ii_kpa=None,
        n_points=n_points,
        v_qc=v_qc,
        avg_depth_m=avg_depth,
        blocked=True,
        status_text="Не рассчитывается",
        detail_reason=reason,
    )


def _design_qc(qc_avg: float | None, v_qc: float | None, n_points: int, confidence: float) -> float | None:
    if qc_avg is None or v_qc is None or n_points <= 0:
        return None
    z_factor = NormalDist().inv_cdf(confidence)
    reduced = float(qc_avg) * (1.0 - (z_factor * float(v_qc) / sqrt(float(n_points))))
    return max(reduced, 0.0)


def _apply_design_values(dataset: LookupDataset, entry: dict[str, Any], soil_name: str, qc_design: float | None, avg_depth: float | None, alluvial_sands: bool, *, use_legacy_supes: bool) -> tuple[float | None, float | None]:
    if qc_design is None:
        return None, None
    if soil_name == SoilType.SAND.value:
        phi_val, _ids, _note = _j3_phi(dataset, qc_design, float(avg_depth or 0.0), [])
        return phi_val, None
    if soil_name in {SoilType.LOAM.value, SoilType.CLAY.value}:
        state = _normalize_consistency(soil_name, str(entry.get("consistency") or ""))
        result, _warnings, _rule_ids, _reason = _clay_like_result(dataset, qc_design, edition_mode="current", soil_kind_ru=soil_name, state_or_consistency=state)
        return result.get("phi_n_deg"), result.get("c_n_kpa")
    if soil_name == SoilType.SANDY_LOAM.value and use_legacy_supes:
        result, _warnings, _rule_ids, _reason = _clay_like_result(dataset, qc_design, edition_mode="legacy_supes_pre_izm1", soil_kind_ru="супесь", state_or_consistency="пластичная/твердая по выделенному ИГЭ", note_suffix=" (legacy)")
        return result.get("phi_n_deg"), result.get("c_n_kpa")
    if soil_name == SoilType.FILL.value:
        material_kind = _fill_material_kind(entry.get("fill_subtype"))
        if material_kind == "sand":
            phi_val, _ids, _note = _j3_phi(dataset, qc_design, float(avg_depth or 0.0), [])
            return phi_val, None
        if material_kind == "clay":
            result, _warnings, _rule_ids, _reason = _clay_like_result(
                dataset,
                qc_design,
                edition_mode="current",
                soil_kind_ru="глина",
                state_or_consistency="тугопластичная",
                note_suffix=" (предварительно по материалу)",
            )
            return result.get("phi_n_deg"), result.get("c_n_kpa")
    return None, None


def _build_row_for_ige(ige_id: str, entry: dict[str, Any], points: list[_QcPoint], dataset: LookupDataset, options: StaticCalcOptions) -> StaticCalcRow:
    n_points, qc_avg, v_qc, avg_depth = _calc_stats(points)
    soil_name = _soil_name(entry)
    soil_display_name = _manual_or_generated_soil_name(entry)
    if n_points <= 0 or qc_avg is None or avg_depth is None:
        return _blocked_row(ige_id, soil_display_name, qc_avg, n_points, v_qc, avg_depth, "Нет данных qc в интервалах выбранного ИГЭ")

    note_marks: list[str] = []
    warnings: list[str] = []
    rule_ids: list[str] = []
    detail_reason = ""
    payload: dict[str, float | str | None]

    if soil_name == SoilType.SAND.value:
        alluvial = bool(entry.get("sand_is_alluvial", entry.get("is_alluvial", options.alluvial_sands))) or bool(options.alluvial_sands)
        payload, calc_warnings, calc_rule_ids, detail_reason = _sand_result(entry, dataset, qc_avg, avg_depth, alluvial)
        warnings.extend(calc_warnings)
        rule_ids.extend(calc_rule_ids)
    elif soil_name in {SoilType.LOAM.value, SoilType.CLAY.value}:
        state = _normalize_consistency(soil_name, str(entry.get("consistency") or ""))
        if not state:
            return _blocked_row(ige_id, soil_display_name, qc_avg, n_points, v_qc, avg_depth, "Для расчёта по Ж.4 требуется выбрать состояние грунта")
        payload, calc_warnings, calc_rule_ids, detail_reason = _clay_like_result(dataset, qc_avg, edition_mode="current", soil_kind_ru=soil_name, state_or_consistency=state)
        warnings.extend(calc_warnings)
        rule_ids.extend(calc_rule_ids)
    elif soil_name == SoilType.SANDY_LOAM.value:
        if not options.use_legacy_sandy_loam_sp446:
            return _blocked_row(ige_id, soil_display_name, qc_avg, n_points, v_qc, avg_depth, "Супеси по действующей редакции СП 446 в этой реализации не рассчитываются")
        payload, calc_warnings, calc_rule_ids, detail_reason = _clay_like_result(
            dataset,
            qc_avg,
            edition_mode="legacy_supes_pre_izm1",
            soil_kind_ru="супесь",
            state_or_consistency="пластичная/твердая по выделенному ИГЭ",
            note_suffix=" (редакция до Изм. №1)",
        )
        warnings.extend(calc_warnings)
        rule_ids.extend(calc_rule_ids)
        note_marks.append(NOTE_LEGACY_SUPES)
    elif soil_name == SoilType.FILL.value:
        if not options.allow_fill_preliminary:
            return _blocked_row(ige_id, soil_display_name, qc_avg, n_points, v_qc, avg_depth, "Насыпной грунт не рассчитывается без режима предварительного расчёта по материалу")
        payload, calc_warnings, calc_rule_ids, detail_reason = _fill_preliminary_result(entry, dataset, qc_avg, avg_depth, bool(options.alluvial_sands))
        warnings.extend(calc_warnings)
        rule_ids.extend(calc_rule_ids)
        note_marks.append(NOTE_PRELIM_FILL)
    else:
        return _blocked_row(
            ige_id,
            soil_display_name,
            qc_avg,
            n_points,
            v_qc,
            avg_depth,
            "Для данного типа грунта в приложении Ж СП 446.1325800.2019 отсутствуют табличные зависимости для расчета по результатам статического зондирования",
        )

    if detail_reason:
        return _blocked_row(ige_id, soil_display_name, qc_avg, n_points, v_qc, avg_depth, detail_reason)

    stats_reasons: list[str] = []
    if n_points < 6:
        stats_reasons.append(f"число опытов n = {n_points}, требуется не менее 6")
    if v_qc is not None and v_qc > 0.30:
        stats_reasons.append(f"коэффициент вариации V = {f'{v_qc:.2f}'.replace('.', ',')} превышает допустимое значение 0,30")
    reference_only = bool(stats_reasons)
    allow_reference = bool(options.allow_reference_on_insufficient_stats)
    if reference_only and allow_reference:
        note_marks.append(NOTE_REFERENCE_ONLY)

    if reference_only and not allow_reference:
        qc_design_i = None
        qc_design_ii = None
        phi_i = None
        c_i = None
        phi_ii = None
        c_ii = None
    else:
        qc_design_i = _design_qc(qc_avg, v_qc, n_points, 0.95)
        qc_design_ii = _design_qc(qc_avg, v_qc, n_points, 0.85)
        phi_i, c_i = _apply_design_values(dataset, entry, soil_name, qc_design_i, avg_depth, bool(options.alluvial_sands), use_legacy_supes=bool(options.use_legacy_sandy_loam_sp446))
        phi_ii, c_ii = _apply_design_values(dataset, entry, soil_name, qc_design_ii, avg_depth, bool(options.alluvial_sands), use_legacy_supes=bool(options.use_legacy_sandy_loam_sp446))

    return StaticCalcRow(
        ige_id=ige_id,
        soil_name=soil_display_name,
        qc_avg_mpa=qc_avg,
        e_n_mpa=float(payload.get("e_n_mpa")) if payload.get("e_n_mpa") is not None else None,
        phi_n_deg=float(payload.get("phi_n_deg")) if payload.get("phi_n_deg") is not None else None,
        c_n_kpa=float(payload.get("c_n_kpa")) if payload.get("c_n_kpa") is not None else None,
        phi_i_deg=phi_i,
        c_i_kpa=c_i,
        phi_ii_deg=phi_ii,
        c_ii_kpa=c_ii,
        note_marks=tuple(note_marks),
        n_points=n_points,
        v_qc=v_qc,
        avg_depth_m=avg_depth,
        reference_only=reference_only,
        blocked=False,
        status_text="Справочный" if (reference_only and allow_reference) else ("Нормативный" if reference_only else "Расчётный"),
        detail_reason=("Расчётные значения приведены в справочном режиме" if (reference_only and allow_reference) else ("Расчётные значения не выведены: " + "; ".join(stats_reasons) if reference_only else "Условия статистической обеспеченности выполнены")),
        lookup_label=str(payload.get("lookup_label") or ""),
        interpolation_summary=str(payload.get("interpolation") or ""),
        density_class=str(payload.get("density_class") or ""),
        selected_lookup_rules=tuple(rule_ids),
        sounding_labels=tuple(sorted({point.sounding_label for point in points})),
        qc_by_sounding=_points_by_sounding(points),
        qc_design_i_mpa=qc_design_i,
        qc_design_ii_mpa=qc_design_ii,
        warning_lines=tuple(dict.fromkeys(warnings)),
    )


def run_static_sounding_calculation(*, tests: list[Any], ige_registry: dict[str, dict[str, Any]], project_name: str, options: StaticCalcOptions | None = None, calculation_date: str | None = None) -> StaticCalcRunResult:
    opts = options or StaticCalcOptions()
    dataset = load_lookup_dataset(opts.lookup_relative_path)
    rows: list[StaticCalcRow] = []
    for ige_id in sorted((ige_registry or {}).keys(), key=_ige_sort_key):
        entry = dict(ige_registry.get(ige_id) or {})
        points = _collect_points_for_ige(list(tests or []), ige_id)
        rows.append(_build_row_for_ige(ige_id, entry, points, dataset, opts))

    used_note_marks = tuple(mark for mark in (NOTE_LEGACY_SUPES, NOTE_PRELIM_FILL, NOTE_REFERENCE_ONLY) if any(mark in row.note_marks for row in rows))
    calc_date = str(calculation_date or "").strip() or __import__("datetime").datetime.now().strftime("%d.%m.%Y %H:%M")
    global_warnings = tuple(dict.fromkeys(warning for row in rows for warning in row.warning_lines))
    return StaticCalcRunResult(
        title="Расчёт по результатам статического зондирования",
        project_name=str(project_name or "").strip() or "—",
        calculation_date=calc_date,
        algorithm_version=STATIC_CALC_ALGORITHM_VERSION,
        lookup_path=str(dataset.source_path),
        rows=tuple(rows),
        used_note_marks=used_note_marks,
        global_warnings=global_warnings,
    )
