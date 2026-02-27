# tools/selfcheck.py
# Автопроверка проекта (без GUI).
#
# Запуск из корня проекта:
#   py tools\selfcheck.py
#
# Проверяет:
# - компиляцию всех .py (compileall)
# - импорт ключевых модулей src/zondeditor
# - наличие монолита и launcher'а
# - smoke-парсинг эталонных файлов в fixtures/ (K2 и K4)

from __future__ import annotations

import compileall
import importlib
import sys
from pathlib import Path

MONOLITH = "ZondEditor_SZ_v3_k2k4_dispatch_fix_params_step_depth_v5_nofreeze_k4fix_xlsxfix.py"
LAUNCHER = "run_zondeditor.py"

MODULES_TO_IMPORT = [
    "src.zondeditor.app",
    "src.zondeditor.io.k4_reader",
    "src.zondeditor.io.k2_reader",
    "src.zondeditor.domain.models",
]

FIXTURES = [
    ("K2", "fixtures/K2_260205A1.GEO"),
    ("K4", "fixtures/К4_260218O1.GEO"),
]

def fail(msg: str, code: int = 1) -> None:
    print(f"[FAIL] {msg}")
    raise SystemExit(code)

def ok(msg: str) -> None:
    print(f"[ OK ] {msg}")

def _smoke_parse_fixtures(root: Path) -> None:
    from src.zondeditor.io.k4_reader import detect_geo_kind, parse_k4_geo_strict
    from src.zondeditor.io.k2_reader import parse_geo_with_blocks as parse_k2
    from src.zondeditor.domain.models import TestData, GeoBlockInfo

    for kind, rel in FIXTURES:
        p = root / rel
        if not p.exists():
            ok(f"Фикстура отсутствует (пропуск): {rel}")
            continue

        data = p.read_bytes()
        detected = detect_geo_kind(data)
        ok(f"{rel}: detect_geo_kind -> {detected}")

        if kind == "K4":
            if detected != "K4":
                fail(f"{rel}: ожидали K4, получили {detected}")
            tests = parse_k4_geo_strict(data, TestData)
            if not tests:
                fail(f"{rel}: K4 парсер вернул 0 опытов")
            t0 = tests[0]
            incl = getattr(t0, "incl", None)
            if incl is None:
                fail(f"{rel}: у K4 нет колонки U (.incl)")
            if len(t0.depth) != len(incl):
                fail(f"{rel}: depth и incl разной длины ({len(t0.depth)} != {len(incl)})")
            ok(f"{rel}: K4 parse OK (tests={len(tests)})")
        else:
            if detected != "K2":
                fail(f"{rel}: ожидали K2, получили {detected}")
            tests, meta_rows = parse_k2(data, TestData, GeoBlockInfo)
            if not tests:
                fail(f"{rel}: K2 парсер вернул 0 опытов")
            t0 = tests[0]
            if hasattr(t0, "incl") and getattr(t0, "incl"):
                fail(f"{rel}: у K2 неожиданно есть U (.incl)")
            ok(f"{rel}: K2 parse OK (tests={len(tests)}, meta_rows={len(meta_rows)})")

def main() -> None:
    root = Path(__file__).resolve().parents[1]

    if not (root / MONOLITH).exists():
        fail(f"Не найден монолит: {MONOLITH}")
    ok(f"Монолит найден: {MONOLITH}")

    if not (root / LAUNCHER).exists():
        fail(f"Не найден файл запуска: {LAUNCHER}")
    ok(f"Launcher найден: {LAUNCHER}")

    ok("Компиляция .py (compileall) ...")
    success = compileall.compile_dir(str(root), quiet=1)
    if not success:
        fail("compileall нашёл ошибки компиляции")
    ok("compileall: без ошибок")

    ok("Проверка импортов модулей ...")
    for m in MODULES_TO_IMPORT:
        try:
            importlib.import_module(m)
            ok(f"import {m}")
        except Exception as e:
            fail(f"Не импортируется {m}: {e}")

    ok("Smoke-парсинг fixtures/ ...")
    _smoke_parse_fixtures(root)

    ok("Автопроверка завершена успешно.")

if __name__ == "__main__":
    proj_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(proj_root))
    main()
