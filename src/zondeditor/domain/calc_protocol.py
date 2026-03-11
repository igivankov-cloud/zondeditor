from __future__ import annotations

from typing import Any


def build_calc_protocol(*, object_name: str, profile_id: str, profile_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    excluded = [r for r in (rows or []) if r.get("status") in {"LAB_ONLY", "NOT_APPLICABLE"}]
    warnings = [r for r in (rows or []) if str(r.get("warning") or "").strip()]
    return {
        "header": {"object_name": object_name, "profile_id": profile_id, "profile_name": profile_name},
        "ige_list": [str(r.get("ige_id") or "") for r in (rows or [])],
        "calc_table": rows,
        "warnings": [{"ige_id": r.get("ige_id"), "warning": r.get("warning")} for r in warnings],
        "excluded_ige": [{"ige_id": r.get("ige_id"), "status": r.get("status"), "reason": r.get("warning")} for r in excluded],
        "aggregated_samples": [
            {
                "ige_id": r.get("ige_id"),
                "n_points": r.get("n_points"),
                "qc_avg": r.get("qc_avg"),
                "qc_min": r.get("qc_min"),
                "qc_max": r.get("qc_max"),
                "V_qc": r.get("V_qc"),
            }
            for r in (rows or [])
        ],
    }
