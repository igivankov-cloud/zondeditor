from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class ProtocolEntry:
    test_id: int
    row: int
    type: str
    field: str = ""
    row_end: int = -1


@dataclass(frozen=True)
class TestDiagnostics:
    test_id: int
    export_on: bool
    invalid: bool
    invalid_zero_run: bool
    missing_rows: tuple[tuple[int, str], ...]
    interp_cells: int
    force_cells: int
    user_cells: int
    algo_cells: int


@dataclass(frozen=True)
class DiagnosticsReport:
    tests_total: int
    tests_invalid: int
    cells_missing: int
    cells_interp: int
    by_test: dict[int, TestDiagnostics]
    protocol_entries: tuple[ProtocolEntry, ...]


def _parse_cell_int(value: Any) -> int:
    try:
        text = str(value).strip()
        if text == "":
            return 0
        return int(float(text.replace(",", ".")))
    except Exception:
        return 0


def _max_zero_run(values: list[int]) -> int:
    best = 0
    cur = 0
    for value in values:
        if int(value or 0) == 0:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


def _scan_runs(values: list[int], *, min_len: int = 6) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    i = 0
    n = len(values)
    while i < n:
        if values[i] != 0:
            i += 1
            continue
        j = i
        while j < n and values[j] == 0:
            j += 1
        if (j - i) >= min_len:
            out.append((i, j - 1))
        i = j
    return out


def evaluate_diagnostics(
    tests: Iterable[Any],
    flags_by_tid: Mapping[int, Any] | None,
) -> DiagnosticsReport:
    tests_list = list(tests or [])
    flags_map = dict(flags_by_tid or {})

    tests_total = 0
    tests_invalid = 0
    cells_missing = 0
    cells_interp = 0
    by_test: dict[int, TestDiagnostics] = {}
    protocol_entries: list[ProtocolEntry] = []

    for t in tests_list:
        tid = int(getattr(t, "tid", 0) or 0)
        export_on = bool(getattr(t, "export_on", True))
        if export_on:
            tests_total += 1

        fl = flags_map.get(tid)
        user_cells = set(getattr(fl, "user_cells", set()) or set()) if fl is not None else set()
        interp_cells = set(getattr(fl, "interp_cells", set()) or set()) if fl is not None else set()
        force_cells = set(getattr(fl, "force_cells", set()) or set()) if fl is not None else set()
        algo_cells = set(getattr(fl, "algo_cells", set()) or set()) if fl is not None else set()

        qc = [(_parse_cell_int(v) or 0) for v in (getattr(t, "qc", []) or [])]
        fs = [(_parse_cell_int(v) or 0) for v in (getattr(t, "fs", []) or [])]

        zero_runs = _scan_runs(qc, min_len=6) + _scan_runs(fs, min_len=6)
        invalid_zero_run = bool(zero_runs)
        invalid_flag = bool(getattr(fl, "invalid", False)) if fl is not None else False
        invalid = bool(invalid_zero_run or invalid_flag)

        missing_rows: list[tuple[int, str]] = []
        for i0 in range(min(len(qc), len(fs))):
            if qc[i0] == 0 and (i0, "qc") not in user_cells:
                missing_rows.append((i0, "qc"))
            if fs[i0] == 0 and (i0, "fs") not in user_cells:
                missing_rows.append((i0, "fs"))

        if export_on:
            cells_interp += len(interp_cells)
            if invalid:
                tests_invalid += 1
            else:
                cells_missing += len(missing_rows)

        if invalid_zero_run:
            r0 = min(rr[0] for rr in zero_runs)
            r1 = max(rr[1] for rr in zero_runs)
            protocol_entries.append(ProtocolEntry(test_id=tid, row=r0, row_end=r1, type="invalid_zero_run"))
        else:
            for row, field in missing_rows:
                protocol_entries.append(ProtocolEntry(test_id=tid, row=row, field=field, type=f"missing_{field}"))
            if invalid_flag:
                protocol_entries.append(ProtocolEntry(test_id=tid, row=-1, type="invalid_other"))

        by_test[tid] = TestDiagnostics(
            test_id=tid,
            export_on=export_on,
            invalid=invalid,
            invalid_zero_run=invalid_zero_run,
            missing_rows=tuple(missing_rows),
            interp_cells=len(interp_cells),
            force_cells=len(force_cells),
            user_cells=len(user_cells),
            algo_cells=len(algo_cells),
        )

    protocol_entries.sort(key=lambda x: (x.test_id, x.row, x.type))
    return DiagnosticsReport(
        tests_total=tests_total,
        tests_invalid=tests_invalid,
        cells_missing=cells_missing,
        cells_interp=cells_interp,
        by_test=by_test,
        protocol_entries=tuple(protocol_entries),
    )
