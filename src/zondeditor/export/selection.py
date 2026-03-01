from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass
class ExportSelection:
    total_tests: int
    exported_tests: list[int]
    skipped_hidden: list[int]
    skipped_deleted: list[int]
    tests: list[Any]


def _test_id(test: Any, fallback: int) -> int:
    try:
        return int(getattr(test, "tid", fallback) or fallback)
    except Exception:
        return fallback


def _is_deleted(test: Any) -> bool:
    for name in ("deleted", "is_deleted", "_deleted"):
        if hasattr(test, name) and bool(getattr(test, name, False)):
            return True
    return False


def _is_hidden(test: Any) -> bool:
    if hasattr(test, "export_on") and not bool(getattr(test, "export_on", True)):
        return True
    if hasattr(test, "hidden") and bool(getattr(test, "hidden", False)):
        return True
    if hasattr(test, "visible") and not bool(getattr(test, "visible", True)):
        return True
    if hasattr(test, "enabled") and not bool(getattr(test, "enabled", True)):
        return True
    if hasattr(test, "disabled") and bool(getattr(test, "disabled", False)):
        return True
    return False


def select_export_tests(tests: Iterable[Any]) -> ExportSelection:
    selected: list[Any] = []
    exported_ids: list[int] = []
    skipped_hidden: list[int] = []
    skipped_deleted: list[int] = []
    total = 0

    for idx, test in enumerate(list(tests or []), start=1):
        total += 1
        tid = _test_id(test, idx)
        if _is_deleted(test):
            skipped_deleted.append(tid)
            continue
        if _is_hidden(test):
            skipped_hidden.append(tid)
            continue
        selected.append(test)
        exported_ids.append(tid)

    return ExportSelection(
        total_tests=total,
        exported_tests=exported_ids,
        skipped_hidden=skipped_hidden,
        skipped_deleted=skipped_deleted,
        tests=selected,
    )
