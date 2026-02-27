# tools/selfcheck.py
# Автопроверка проекта (без GUI).
# Запуск из корня проекта:
#   py tools\selfcheck.py
#
# Проверяет:
# - компиляцию всех .py (compileall)
# - импорт ключевых модулей src/zondeditor
# - наличие монолита и launcher'а
#
# Не открывает Tkinter и не запускает окно.

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
    # k2_reader появится на следующем шаге, добавим позже
]

def fail(msg: str, code: int = 1) -> None:
    print(f"[FAIL] {msg}")
    raise SystemExit(code)

def ok(msg: str) -> None:
    print(f"[ OK ] {msg}")

def main() -> None:
    root = Path(__file__).resolve().parents[1]

    # Files
    if not (root / MONOLITH).exists():
        fail(f"Не найден монолит: {MONOLITH}")
    ok(f"Монолит найден: {MONOLITH}")

    if not (root / LAUNCHER).exists():
        fail(f"Не найден файл запуска: {LAUNCHER}")
    ok(f"Launcher найден: {LAUNCHER}")

    # compileall
    ok("Компиляция .py (compileall) ...")
    success = compileall.compile_dir(str(root), quiet=1)
    if not success:
        fail("compileall нашёл ошибки компиляции")
    ok("compileall: без ошибок")

    # imports
    ok("Проверка импортов модулей ...")
    for m in MODULES_TO_IMPORT:
        try:
            importlib.import_module(m)
            ok(f"import {m}")
        except Exception as e:
            fail(f"Не импортируется {m}: {e}")

    ok("Автопроверка завершена успешно.")

if __name__ == "__main__":
    # Чтобы 'src.*' импортировалось даже при запуске из другой папки
    # добавим корень проекта в sys.path.
    proj_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(proj_root))
    main()
