# src/zondeditor/processing/fixes.py
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Mapping

from src.zondeditor.processing.value_semantics import (
    is_effective_zero,
    max_zero_run,
    parse_measurement,
)
from src.zondeditor.processing.interpolation_precision import normalize_interpolated_value


def _parse_cell_float(v: Any) -> Optional[float]:
    return parse_measurement(v)

def _parse_depth_float(v: Any) -> Optional[float]:
    try:
        s = str(v).strip().replace(",", ".")
        return float(s) if s else None
    except Exception:
        return None

def _noise_around(x: float) -> float:
    # gentle noise ~ +-3%
    if x <= 0:
        return 0.0
    k = 1.0 + random.uniform(-0.03, 0.03)
    return max(0.0, float(x) * k)

def _interp_with_noise(a: float, b: float, t: float) -> float:
    a = max(0.0, float(a))
    b = max(0.0, float(b))
    v = a + (b - a) * float(t)
    return _noise_around(v)

def fix_tests_by_algorithm(
    tests: Iterable[Any],
    flags_out: Optional[Any] = None,
    prev_flags_by_tid: Optional[Mapping[int, Any]] = None,
    *args,
    step_m: Optional[float] = None,
    depth_start: Optional[float] = None,
    seed: int = 42,
    TestFlagsCls: Any = None,
    **_ignored_kwargs,
) -> list[Any]:
    """
    Real logic for the "Fix (algorithm)" action (tkinter-free).

    Behavior mirrors the monolith GeoCanvasEditor.fix_by_algorithm:
    - invalid if >5 zeros in a row in qc or fs (test is left unchanged)
    - interpolate short zero runs (<=5) with noise
    - fill remaining zeros
    - build interp_cells, force_cells, algo_cells; preserve user_cells from previous flags

    Compatibility: accepts extra args/kwargs; can fill flags_out list-like object.
    Returns list of flags (one per test).
    """
    if TestFlagsCls is None:
        @dataclass
        class _TF:
            invalid: bool
            interp_cells: set
            force_cells: set
            user_cells: set
            algo_cells: set
        TestFlagsCls = _TF

    random.seed(seed)
    out: list[Any] = []
    prev_flags_by_tid = prev_flags_by_tid or {}

    for t in tests:
        tid = int(getattr(t, "tid", 0) or 0)
        prev_flags = prev_flags_by_tid.get(tid)
        _prev_user_cells = set(getattr(prev_flags, "user_cells", set()) or set())

        _orig_qc = list(getattr(t, "qc", []) or [])
        _orig_fs = list(getattr(t, "fs", []) or [])
        _series_src = {"qc": list(_orig_qc), "fs": list(_orig_fs)}
        algo_cells: set[tuple[int, str]] = set()

        if not hasattr(t, "qc") or not hasattr(t, "fs"):
            out.append(TestFlagsCls(False, set(), set(), _prev_user_cells, algo_cells))
            continue

        # Never extend probing length in algorithm mode: process only
        # rows that already have both qc and fs cells.
        n = min(len(getattr(t, "qc", []) or []), len(getattr(t, "fs", []) or []))
        if n == 0:
            out.append(TestFlagsCls(False, set(), set(), _prev_user_cells, algo_cells))
            continue

        qc = [(pv if pv is not None else 0.0) for pv in (_parse_cell_float(v) for v in t.qc)]
        fs = [(pv if pv is not None else 0.0) for pv in (_parse_cell_float(v) for v in t.fs)]

        invalid = (max_zero_run(qc) > 5) or (max_zero_run(fs) > 5)

        interp_cells: set[tuple[int, str]] = set(getattr(prev_flags, "interp_cells", set()) or set())
        force_cells: set[tuple[int, str]] = set(getattr(prev_flags, "force_cells", set()) or set())

        if invalid:
            out.append(TestFlagsCls(True, interp_cells, force_cells, _prev_user_cells, algo_cells))
            continue

        def interp_in_place(arr: list[float], kind: str) -> None:
            nonlocal n
            i = 0
            while i < n:
                if not is_effective_zero(arr[i]):
                    i += 1
                    continue
                j = i
                while j < n and is_effective_zero(arr[j]):
                    j += 1
                gap_len = j - i
                if gap_len <= 5:
                    left = i - 1
                    right = j
                    if left >= 0 and right < n and (not is_effective_zero(arr[left])) and (not is_effective_zero(arr[right])):
                        a = arr[left]
                        b = arr[right]
                        for k in range(gap_len):
                            tt = (k + 1) / (gap_len + 1)
                            if (i + k, kind) not in _prev_user_cells and (i + k, kind) not in interp_cells and (i + k, kind) not in force_cells:
                                arr[i + k] = normalize_interpolated_value(
                                    _interp_with_noise(a, b, tt),
                                    local_samples=[a, b],
                                    series_samples=_series_src.get(kind, []),
                                    field_name=kind,
                                )
                                interp_cells.add((i + k, kind))
                    elif left >= 0 and (not is_effective_zero(arr[left])):
                        a = arr[left]
                        for k in range(gap_len):
                            if (i + k, kind) not in _prev_user_cells:
                                arr[i + k] = normalize_interpolated_value(
                                    _noise_around(a),
                                    local_samples=[a],
                                    series_samples=_series_src.get(kind, []),
                                    field_name=kind,
                                )
                                interp_cells.add((i + k, kind))
                    elif right < n and (not is_effective_zero(arr[right])):
                        b = arr[right]
                        for k in range(gap_len):
                            if (i + k, kind) not in _prev_user_cells:
                                arr[i + k] = normalize_interpolated_value(
                                    _noise_around(b),
                                    local_samples=[b],
                                    series_samples=_series_src.get(kind, []),
                                    field_name=kind,
                                )
                                interp_cells.add((i + k, kind))
                i = j

        interp_in_place(qc, "qc")
        interp_in_place(fs, "fs")

        for arr, kind in ((qc, "qc"), (fs, "fs")):
            for i in range(n):
                if not is_effective_zero(arr[i]):
                    continue
                left = i - 1
                while left >= 0 and is_effective_zero(arr[left]):
                    left -= 1
                right = i + 1
                while right < n and is_effective_zero(arr[right]):
                    right += 1
                if left >= 0 and right < n:
                    arr[i] = normalize_interpolated_value(
                        _interp_with_noise(arr[left], arr[right], 0.5),
                        local_samples=[arr[left], arr[right]],
                        series_samples=_series_src.get(kind, []),
                        field_name=kind,
                    )
                elif left >= 0:
                    arr[i] = normalize_interpolated_value(
                        _noise_around(arr[left]),
                        local_samples=[arr[left]],
                        series_samples=_series_src.get(kind, []),
                        field_name=kind,
                    )
                elif right < n:
                    arr[i] = normalize_interpolated_value(
                        _noise_around(arr[right]),
                        local_samples=[arr[right]],
                        series_samples=_series_src.get(kind, []),
                        field_name=kind,
                    )
                else:
                    arr[i] = 0.0
                interp_cells.add((i, kind))

        for i in range(n):
            t.qc[i] = f"{float(qc[i]):g}"
            t.fs[i] = f"{float(fs[i]):g}"

        try:
            for i2 in range(len(t.qc)):
                new_q = str(t.qc[i2]).strip()
                new_f = str(t.fs[i2]).strip()
                old_q = str(_orig_qc[i2]).strip() if i2 < len(_orig_qc) else ""
                old_f = str(_orig_fs[i2]).strip() if i2 < len(_orig_fs) else ""
                if (i2, "qc") not in _prev_user_cells and new_q != old_q:
                    algo_cells.add((i2, "qc"))
                if (i2, "fs") not in _prev_user_cells and new_f != old_f:
                    algo_cells.add((i2, "fs"))
        except Exception:
            pass

        out.append(TestFlagsCls(False, interp_cells, force_cells, _prev_user_cells, algo_cells))

    if flags_out is not None:
        try:
            if hasattr(flags_out, "clear"):
                flags_out.clear()
            if hasattr(flags_out, "extend"):
                flags_out.extend(out)
            else:
                for x in out:
                    flags_out.append(x)
        except Exception:
            pass

    return out
