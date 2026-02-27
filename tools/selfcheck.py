# tools/selfcheck.py
from __future__ import annotations

import compileall
import importlib
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

MONOLITH = "ZondEditor_SZ_v3_k2k4_dispatch_fix_params_step_depth_v5_nofreeze_k4fix_xlsxfix.py"
LAUNCHER = "run_zondeditor.py"

MODULES_TO_IMPORT = [
    "src.zondeditor.app",
    "src.zondeditor.io.k4_reader",
    "src.zondeditor.io.k2_reader",
    "src.zondeditor.domain.models",
    "src.zondeditor.processing.calibration",
    "src.zondeditor.export.excel_export",
    "src.zondeditor.export.credo_zip",
    "src.zondeditor.export.gxl_export",
]

FIXTURES = [
    ("K2", "fixtures/K2_260205A1.GEO"),
    ("K4", "fixtures/К4_260218O1.GEO"),
]

SCALE_DIV = 250
FCONE_KN = 30.0
FSLEEVE_KN = 10.0

def fail(msg: str, code: int = 1) -> None:
    print(f"[FAIL] {msg}")
    raise SystemExit(code)

def ok(msg: str) -> None:
    print(f"[ OK ] {msg}")

def _smoke_parse_and_export(root: Path) -> None:
    from src.zondeditor.io.k4_reader import detect_geo_kind, parse_k4_geo_strict
    from src.zondeditor.io.k2_reader import parse_geo_with_blocks as parse_k2
    from src.zondeditor.domain.models import TestData, GeoBlockInfo
    from src.zondeditor.processing.calibration import calc_qc_fs_from_del
    from src.zondeditor.export.excel_export import export_excel
    from src.zondeditor.export.credo_zip import export_credo_zip
    from src.zondeditor.export.gxl_export import export_gxl_generated

    out_dir = root / "tools" / "_selfcheck_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    for p in out_dir.glob("*"):
        try:
            p.unlink()
        except Exception:
            pass

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

            xlsx = out_dir / "K4_test.xlsx"
            zpath = out_dir / "K4_credo.zip"
            gxl = out_dir / "K4_generated.gxl"
            export_excel(tests, geo_kind="K4", out_path=xlsx, scale_div=SCALE_DIV, fcone_kn=FCONE_KN, fsleeve_kn=FSLEEVE_KN)
            export_credo_zip(tests, out_zip_path=zpath, scale_div=SCALE_DIV, fcone_kn=FCONE_KN, fsleeve_kn=FSLEEVE_KN)
            export_gxl_generated(tests, out_path=gxl, object_code="SELFTEST_K4")

            if not xlsx.exists() or xlsx.stat().st_size < 1000:
                fail(f"{rel}: Excel не создан/слишком мал")
            if not zpath.exists() or zpath.stat().st_size < 100:
                fail(f"{rel}: ZIP не создан/слишком мал")
            if not gxl.exists() or gxl.stat().st_size < 200:
                fail(f"{rel}: GXL не создан/слишком мал")

            try:
                ET.fromstring(gxl.read_bytes())
            except Exception as e:
                fail(f"{rel}: GXL не парсится как XML: {e}")

            q0 = int(float(str((t0.qc[0] if t0.qc else 0)).replace(",", ".")))
            f0 = int(float(str((t0.fs[0] if t0.fs else 0)).replace(",", ".")))
            qc_mpa, fs_kpa = calc_qc_fs_from_del(q0, f0, scale_div=SCALE_DIV, fcone_kn=FCONE_KN, fsleeve_kn=FSLEEVE_KN)
            if qc_mpa < 0 or fs_kpa < 0:
                fail(f"{rel}: пересчёт дал отрицательные значения")
            ok(f"{rel}: K4 parse+export OK (tests={len(tests)})")
        else:
            if detected != "K2":
                fail(f"{rel}: ожидали K2, получили {detected}")
            tests, meta_rows = parse_k2(data, TestData, GeoBlockInfo)
            if not tests:
                fail(f"{rel}: K2 парсер вернул 0 опытов")
            t0 = tests[0]
            if hasattr(t0, "incl") and getattr(t0, "incl"):
                fail(f"{rel}: у K2 неожиданно есть U (.incl)")

            xlsx = out_dir / "K2_test.xlsx"
            zpath = out_dir / "K2_credo.zip"
            gxl = out_dir / "K2_generated.gxl"
            export_excel(tests, geo_kind="K2", out_path=xlsx, scale_div=SCALE_DIV, fcone_kn=FCONE_KN, fsleeve_kn=FSLEEVE_KN)
            export_credo_zip(tests, out_zip_path=zpath, scale_div=SCALE_DIV, fcone_kn=FCONE_KN, fsleeve_kn=FSLEEVE_KN)
            export_gxl_generated(tests, out_path=gxl, object_code="SELFTEST_K2")

            if not xlsx.exists() or xlsx.stat().st_size < 1000:
                fail(f"{rel}: Excel не создан/слишком мал")
            if not zpath.exists() or zpath.stat().st_size < 100:
                fail(f"{rel}: ZIP не создан/слишком мал")
            if not gxl.exists() or gxl.stat().st_size < 200:
                fail(f"{rel}: GXL не создан/слишком мал")

            with zipfile.ZipFile(zpath, "r") as z:
                names = z.namelist()
                if not any(n.endswith("лоб.csv") for n in names) or not any(n.endswith("бок.csv") for n in names):
                    fail(f"{rel}: в ZIP нет ожидаемых CSV (лоб/бок)")

            try:
                ET.fromstring(gxl.read_bytes())
            except Exception as e:
                fail(f"{rel}: GXL не парсится как XML: {e}")

            ok(f"{rel}: K2 parse+export OK (tests={len(tests)}, meta_rows={len(meta_rows)})")

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

    ok("Smoke parse + exports (fixtures) ...")
    _smoke_parse_and_export(root)

    ok("Автопроверка завершена успешно.")

if __name__ == "__main__":
    proj_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(proj_root))
    main()
