from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Operation:
    op_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    mark: dict[str, Any] = field(default_factory=dict)
    ts: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "opType": self.op_type,
            "payload": self.payload,
            "mark": self.mark,
            "ts": self.ts or datetime.now(timezone.utc).isoformat(),
        }


def op_cell_set(*, test_id: int, row: int, field: str, before: str, after: str, reason: str = "manual_edit", color: str = "purple") -> dict[str, Any]:
    return Operation(
        op_type="cell_set",
        payload={"testId": int(test_id), "row": int(row), "field": field, "before": before, "after": after},
        mark={"reason": reason, "color": color},
    ).to_dict()


def op_meta_change(*, object_name_before: str, object_name_after: str) -> dict[str, Any]:
    return Operation(
        op_type="meta_change",
        payload={"objectNameBefore": object_name_before, "objectNameAfter": object_name_after},
        mark={"reason": "meta_change", "color": "purple"},
    ).to_dict()


def op_algo_fix_applied(*, changes: list[dict[str, Any]]) -> dict[str, Any]:
    return Operation(
        op_type="algo_fix_applied",
        payload={"changes": changes},
        mark={"reason": "algo_fix", "color": "green"},
    ).to_dict()
