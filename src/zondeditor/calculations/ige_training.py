from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def layer_brief(layer: dict[str, Any]) -> dict[str, Any]:
    return {
        "top_m": float(layer.get("top_m", 0.0) or 0.0),
        "bot_m": float(layer.get("bot_m", 0.0) or 0.0),
        "soil_type": str(layer.get("soil_type") or ""),
        "ige_id": str(layer.get("ige_id") or ""),
        "notes": str((layer.get("params") or {}).get("notes") or layer.get("notes") or ""),
    }


def _boundaries(layers: list[dict[str, Any]]) -> list[float]:
    out = []
    for lyr in layers[:-1]:
        out.append(round(float(lyr.get("bot_m", 0.0) or 0.0), 2))
    return sorted(out)


def _find_overlap(a: dict[str, Any], b: dict[str, Any]) -> float:
    top = max(float(a.get("top_m", 0.0)), float(b.get("top_m", 0.0)))
    bot = min(float(a.get("bot_m", 0.0)), float(b.get("bot_m", 0.0)))
    return max(0.0, bot - top)


def diff_layer_models(auto_layers: list[dict[str, Any]], manual_layers: list[dict[str, Any]]) -> dict[str, Any]:
    auto_b = set(_boundaries(auto_layers))
    man_b = set(_boundaries(manual_layers))
    removed = sorted(auto_b - man_b)
    added = sorted(man_b - auto_b)

    actions: list[dict[str, Any]] = []
    for x in removed:
        near = min((abs(x - y), y) for y in added) if added else (999, None)
        if near[0] <= 0.25:
            actions.append({"kind": "boundary_shift", "from_m": x, "to_m": near[1], "delta_m": round(float(near[1] - x), 2)})
        else:
            actions.append({"kind": "boundary_removed", "depth_m": x})
    for x in added:
        near = min((abs(x - y), y) for y in removed) if removed else (999, None)
        if near[0] > 0.25:
            actions.append({"kind": "boundary_added", "depth_m": x})

    if len(manual_layers) < len(auto_layers):
        actions.append({"kind": "interval_merge", "count": len(auto_layers) - len(manual_layers)})
    elif len(manual_layers) > len(auto_layers):
        actions.append({"kind": "interval_split", "count": len(manual_layers) - len(auto_layers)})

    for ml in manual_layers:
        best = None
        best_ov = 0.0
        for al in auto_layers:
            ov = _find_overlap(al, ml)
            if ov > best_ov:
                best_ov = ov
                best = al
        if best is None:
            continue
        st_a = str(best.get("soil_type") or "")
        st_m = str(ml.get("soil_type") or "")
        if st_a and st_m and st_a != st_m:
            actions.append(
                {
                    "kind": "soil_type_changed",
                    "interval_m": [float(ml.get("top_m", 0.0)), float(ml.get("bot_m", 0.0))],
                    "from": st_a,
                    "to": st_m,
                }
            )

    return {
        "removed_boundaries": removed,
        "added_boundaries": added,
        "actions": actions,
        "auto_layers_count": len(auto_layers),
        "manual_layers_count": len(manual_layers),
    }


def make_diff_text(diff: dict[str, Any]) -> str:
    lines = ["Отличия авторазбиения и ручной правки:"]
    rb = list(diff.get("removed_boundaries") or [])
    ab = list(diff.get("added_boundaries") or [])
    lines.append(f"- Удалены границы: {', '.join(f'{x:.2f}' for x in rb) if rb else 'нет'}")
    lines.append(f"- Добавлены границы: {', '.join(f'{x:.2f}' for x in ab) if ab else 'нет'}")
    for a in (diff.get("actions") or []):
        k = a.get("kind")
        if k == "boundary_shift":
            lines.append(f"- Сдвиг границы: {a.get('from_m'):.2f} -> {a.get('to_m'):.2f} м")
        elif k == "boundary_removed":
            lines.append(f"- Удаление границы: {a.get('depth_m'):.2f} м")
        elif k == "boundary_added":
            lines.append(f"- Добавление границы: {a.get('depth_m'):.2f} м")
        elif k == "interval_merge":
            lines.append(f"- Объединение интервалов: {int(a.get('count') or 0)}")
        elif k == "interval_split":
            lines.append(f"- Деление интервалов: {int(a.get('count') or 0)}")
        elif k == "soil_type_changed":
            itv = a.get("interval_m") or [0.0, 0.0]
            lines.append(f"- Изменение типа: {itv[0]:.2f}-{itv[1]:.2f} м: {a.get('from')} -> {a.get('to')}")
    return "\n".join(lines)


@dataclass
class ProfileUpdateResult:
    updated_profile: dict[str, Any]
    stats: dict[str, Any]


@dataclass
class TrainingEligibilityResult:
    eligible: bool
    reasons: list[str]
    used_test_ids: list[str]


def _test_id(meta: dict[str, Any]) -> str:
    return str(meta.get("test_id") or "")


def evaluate_training_case_eligibility(
    *,
    interpretation_status: str,
    approved_for_training: bool,
    has_prebuild_snapshot: bool,
    test_meta: list[dict[str, Any]],
) -> TrainingEligibilityResult:
    reasons: list[str] = []
    used_ids: list[str] = []
    if not has_prebuild_snapshot:
        reasons.append("нет данных предварительного автоформирования (_last_prebuild_snapshot)")
    if str(interpretation_status or "").strip().lower() != "completed":
        reasons.append("интерпретация не завершена (требуется статус 'Завершено')")
    if not bool(approved_for_training):
        reasons.append("выключена галка «Использовать для обучения»")

    if not test_meta:
        reasons.append("нет участвующих опытов для интерпретации")
    for one in (test_meta or []):
        tid = _test_id(one)
        if tid:
            used_ids.append(tid)
        if not bool(one.get("export_on", True)):
            reasons.append(f"опыт {tid or '?'} отключён")
        if bool(one.get("is_excluded", False)):
            reasons.append(f"опыт {tid or '?'} исключён")
        if bool(one.get("is_invalid", False)):
            reasons.append(f"опыт {tid or '?'} некорректный")
        if not bool(one.get("is_real_field_data", True)):
            reasons.append(f"опыт {tid or '?'} не является реальными полевыми данными")
        if bool(one.get("is_synthetic", False)):
            reasons.append(f"опыт {tid or '?'} синтетический")
        if bool(one.get("is_copied", False)):
            reasons.append(f"опыт {tid or '?'} помечен как копия")
        if bool(one.get("has_problem_points", False)):
            reasons.append(f"опыт {tid or '?'} содержит проблемные точки")

    dedup = sorted(set(str(x) for x in reasons if str(x).strip()))
    return TrainingEligibilityResult(eligible=(len(dedup) == 0), reasons=dedup, used_test_ids=sorted(set(used_ids)))


def filter_valid_training_examples(examples: list[dict[str, Any]]) -> dict[str, Any]:
    valid: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    reason_counts: dict[str, int] = {}
    for ex in (examples or []):
        q = dict(ex.get("quality") or {})
        reasons = list(q.get("rejection_reasons") or [])
        completed = str(ex.get("interpretation_status") or "").lower() == "completed"
        approved = bool(ex.get("approved_for_training", False))
        data_valid = bool(q.get("is_valid_for_training", False))
        is_active = bool(ex.get("is_active", True))
        if completed and approved and data_valid and is_active and not reasons:
            valid.append(ex)
            continue
        if not completed:
            reasons.append("status_not_completed")
        if not approved:
            reasons.append("not_approved_for_training")
        if not data_valid:
            reasons.append("invalid_data_flags")
        if not is_active:
            reasons.append("inactive_example_version")
        one_reasons = sorted(set(str(r) for r in reasons if str(r).strip()))
        for r in one_reasons:
            reason_counts[r] = int(reason_counts.get(r, 0) or 0) + 1
        rejected.append({"example_id": ex.get("example_id"), "reasons": one_reasons})
    return {
        "valid_examples": valid,
        "rejected_examples": rejected,
        "reason_counts": reason_counts,
        "total": len(examples or []),
        "valid": len(valid),
        "rejected": len(rejected),
    }


def update_profile_from_examples(*, base_profile: dict[str, Any], examples: list[dict[str, Any]]) -> ProfileUpdateResult:
    profile = dict(base_profile or {})
    if not examples:
        return ProfileUpdateResult(updated_profile=profile, stats={"examples_used": 0, "adjusted": {}})

    removed_ratios = []
    merged_counts = []
    split_counts = []
    shifts = []
    rf_to_soil = []
    for ex in examples:
        diff = dict(ex.get("diff") or {})
        a_cnt = int(diff.get("auto_layers_count", 0) or 0)
        m_cnt = int(diff.get("manual_layers_count", 0) or 0)
        if a_cnt > 0:
            removed_ratios.append(max(0.0, float(a_cnt - m_cnt) / float(a_cnt)))
        for act in (diff.get("actions") or []):
            k = act.get("kind")
            if k == "interval_merge":
                merged_counts.append(int(act.get("count") or 0))
            elif k == "interval_split":
                split_counts.append(int(act.get("count") or 0))
            elif k == "boundary_shift":
                shifts.append(abs(float(act.get("delta_m") or 0.0)))
            elif k == "soil_type_changed":
                rf = act.get("rf_avg")
                if rf is not None:
                    rf_to_soil.append((float(rf), str(act.get("to") or "")))

    adjusted: dict[str, dict[str, Any]] = {}
    n = len(examples)
    if n >= 2:
        if removed_ratios and median(removed_ratios) > 0.25:
            old = float(profile.get("min_layer_thickness_m", 0.8) or 0.8)
            new = min(1.6, round(old + 0.1, 2))
            profile["min_layer_thickness_m"] = new
            adjusted["min_layer_thickness_m"] = {"old": old, "new": new, "reason": "часто удаляются тонкие интервалы"}
        if merged_counts and sum(merged_counts) >= n:
            old = bool(profile.get("merge_same_soil", True))
            profile["merge_same_soil"] = True
            adjusted["merge_same_soil"] = {"old": old, "new": True, "reason": "часто объединяются соседние интервалы"}
        if split_counts and sum(split_counts) >= 1:
            old = float(profile.get("boundary_q_jump", 2.0) or 2.0)
            new = max(1.2, round(old - 0.2, 2))
            profile["boundary_q_jump"] = new
            adjusted["boundary_q_jump"] = {"old": old, "new": new, "reason": "часто добавляются пропущенные границы"}
        if shifts and median(shifts) > 0.2:
            old = int(profile.get("smoothing_window", 5) or 5)
            new = min(9, old + 2)
            profile["smoothing_window"] = new
            adjusted["smoothing_window"] = {"old": old, "new": new, "reason": "границы часто сдвигаются после ручной правки"}

    profile["training_examples_count"] = n
    profile["last_updated_at"] = now_iso()
    profile.setdefault("auto_adjustments", [])
    profile["auto_adjustments"] = list(adjusted.keys())
    if n < 2:
        profile["training_confidence"] = "low"
    elif n < 5:
        profile["training_confidence"] = "medium"
    else:
        profile["training_confidence"] = "high"

    return ProfileUpdateResult(updated_profile=profile, stats={"examples_used": n, "adjusted": adjusted})
