# src/zondeditor/processing/fixes.py
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Mapping

def _parse_cell_int(v: Any) -> Optional[int]:
    try:
        s = str(v).strip()
        if s == "":
            return None
        return int(float(s.replace(",", ".")))
    except Exception:
        return None

def _parse_depth_float(v: Any) -> Optional[float]:
    try:
        s = str(v).strip().replace(",", ".")
        return float(s) if s else None
    except Exception:
        return None

def _max_zero_run(arr: list[int]) -> int:
    best = cur = 0
    for x in arr:
        if x == 0:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best

def _noise_around(x: int) -> int:
    # gentle noise ~ +-3%
    if x <= 0:
        return 1
    k = 1.0 + random.uniform(-0.03, 0.03)
    return max(1, int(round(x * k)))

def _interp_with_noise(a: int, b: int, t: float) -> int:
    a = max(1, int(a))
    b = max(1, int(b))
    v = a + (b - a) * float(t)
    v = int(round(v))
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
        algo_cells: set[tuple[int, str]] = set()

        if not hasattr(t, "qc") or not hasattr(t, "fs"):
            out.append(TestFlagsCls(False, set(), set(), _prev_user_cells, algo_cells))
            continue

        n = len(t.qc)
        if n == 0:
            out.append(TestFlagsCls(False, set(), set(), _prev_user_cells, algo_cells))
            continue

        qc = [(_parse_cell_int(v) or 0) for v in t.qc]
        fs = [(_parse_cell_int(v) or 0) for v in t.fs]

        invalid = (_max_zero_run(qc) > 5) or (_max_zero_run(fs) > 5)

        interp_cells: set[tuple[int, str]] = set(getattr(prev_flags, "interp_cells", set()) or set())
        force_cells: set[tuple[int, str]] = set(getattr(prev_flags, "force_cells", set()) or set())

        if invalid:
            out.append(TestFlagsCls(True, interp_cells, force_cells, _prev_user_cells, algo_cells))
            continue

        def interp_in_place(arr: list[int], kind: str) -> None:
            nonlocal n
            i = 0
            while i < n:
                if arr[i] != 0:
                    i += 1
                    continue
                j = i
                while j < n and arr[j] == 0:
                    j += 1
                gap_len = j - i
                if gap_len <= 5:
                    left = i - 1
                    right = j
                    if left >= 0 and right < n and arr[left] != 0 and arr[right] != 0:
                        a = arr[left]
                        b = arr[right]
                        for k in range(gap_len):
                            tt = (k + 1) / (gap_len + 1)
                            if (i + k, kind) not in _prev_user_cells and (i + k, kind) not in interp_cells and (i + k, kind) not in force_cells:
                                arr[i + k] = _interp_with_noise(a, b, tt)
                                interp_cells.add((i + k, kind))
                    elif left >= 0 and arr[left] != 0:
                        a = arr[left]
                        for k in range(gap_len):
                            if (i + k, kind) not in _prev_user_cells:
                                arr[i + k] = _noise_around(a)
                                interp_cells.add((i + k, kind))
                    elif right < n and arr[right] != 0:
                        b = arr[right]
                        for k in range(gap_len):
                            if (i + k, kind) not in _prev_user_cells:
                                arr[i + k] = _noise_around(b)
                                interp_cells.add((i + k, kind))
                i = j

        interp_in_place(qc, "qc")
        interp_in_place(fs, "fs")

        for arr, kind in ((qc, "qc"), (fs, "fs")):
            for i in range(n):
                if arr[i] != 0:
                    continue
                left = i - 1
                while left >= 0 and arr[left] == 0:
                    left -= 1
                right = i + 1
                while right < n and arr[right] == 0:
                    right += 1
                if left >= 0 and right < n:
                    arr[i] = _interp_with_noise(arr[left], arr[right], 0.5)
                elif left >= 0:
                    arr[i] = _noise_around(arr[left])
                elif right < n:
                    arr[i] = _noise_around(arr[right])
                else:
                    arr[i] = 1
                interp_cells.add((i, kind))

        for i in range(n):
            qv = max(1, int(qc[i]))
            fv = max(1, int(fs[i]))
            while i >= len(t.qc):
                t.qc.append("")
            while i >= len(t.fs):
                t.fs.append("")
            t.qc[i] = str(qv)
            t.fs[i] = str(fv)

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
            if len(t.qc) > len(_orig_qc):
                for i2 in range(len(_orig_qc), len(t.qc)):
                    if (i2, "qc") not in _prev_user_cells:
                        algo_cells.add((i2, "qc"))
                    if (i2, "fs") not in _prev_user_cells:
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
