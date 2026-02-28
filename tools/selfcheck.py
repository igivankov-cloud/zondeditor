# tools/selfcheck.py (patched by Step14)
from __future__ import annotations

import compileall
import importlib
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

LAUNCHER = "run_zondeditor.py"

MODULES_TO_IMPORT = [
    "src.zondeditor.app",
    "src.zondeditor.io.k4_reader",
    "src.zondeditor.io.k2_reader",
    "src.zondeditor.io.geo_writer",
    "src.zondeditor.domain.models",
    "src.zondeditor.processing.calibration",
    "src.zondeditor.processing.fixes",
    "src.zondeditor.export.excel_export",
    "src.zondeditor.export.credo_zip",
    "src.zondeditor.export.gxl_export",
    "src.zondeditor.ui.main_window",
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

def _smoke_all(root: Path) -> None:
    from src.zondeditor.io.k4_reader import detect_geo_kind, parse_k4_geo_strict
    from src.zondeditor.io.k2_reader import parse_geo_with_blocks as parse_k2
    from src.zondeditor.domain.models import TestData, GeoBlockInfo, TestFlags
    from src.zondeditor.processing.calibration import calc_qc_fs
    from src.zondeditor.export.excel_export import export_excel
    from src.zondeditor.export.credo_zip import export_credo_zip
    from src.zondeditor.export.gxl_export import export_gxl_generated
    from src.zondeditor.processing.fixes import fix_tests_by_algorithm
    from src.zondeditor.io.geo_writer import save_k2_geo

    out_dir = root / "tools" / "_selfcheck_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    for p in out_dir.glob("*"):
        try:
            p.unlink()
        except Exception:
            pass

    # calibration sanity
    qc4, _ = calc_qc_fs(1000, 1000, geo_kind="K4")
    if abs(qc4 - 50.0) > 0.5:
        fail(f"calc_qc_fs(K4) unexpected qc={qc4}")
    ok("Calibration sanity OK")

    k2_tests = None
    k2_raw_bytes = None

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
            if incl is None or len(t0.depth) != len(incl):
                fail(f"{rel}: K4 incl invalid")

            export_excel(tests, geo_kind="K4", out_path=out_dir / "K4_test.xlsx")
            export_credo_zip(tests, geo_kind="K4", out_zip_path=out_dir / "K4_credo.zip")
            export_gxl_generated(tests, out_path=out_dir / "K4_generated.gxl", object_code="SELFTEST_K4")
            ok(f"{rel}: K4 parse+export OK (tests={len(tests)})")
        else:
            if detected != "K2":
                fail(f"{rel}: ожидали K2, получили {detected}")
            tests, meta = parse_k2(data, TestData, GeoBlockInfo)
            if not tests:
                fail(f"{rel}: K2 парсер вернул 0 опытов")

            export_excel(tests, geo_kind="K2", out_path=out_dir / "K2_test.xlsx")
            export_credo_zip(tests, geo_kind="K2", out_zip_path=out_dir / "K2_credo.zip")
            export_gxl_generated(tests, out_path=out_dir / "K2_generated.gxl", object_code="SELFTEST_K2")
            ok(f"{rel}: K2 parse+export OK (tests={len(tests)})")
            k2_tests = tests
            k2_raw_bytes = data

    if k2_tests:
        ok("Fix-by-algorithm smoke on K2 fixture ...")
        k2_flags = []
        ret = fix_tests_by_algorithm(k2_tests, k2_flags, choose_tail_k=2, min_zero_run=6, TestFlagsCls=TestFlags)
        if (not k2_flags) and ret:
            k2_flags = list(ret)
        if not k2_flags:
            fail("fix_tests_by_algorithm: flags not produced")
        ok(f"fix_by_algorithm OK (flags={len(k2_flags)})")

        ok("K2 GEO roundtrip (save->read) ...")
        out_geo = out_dir / "K2_roundtrip_saved.GEO"
        save_k2_geo(out_geo, k2_raw_bytes, k2_tests)
        if not out_geo.exists() or out_geo.stat().st_size < 1000:
            fail("roundtrip GEO not created")
        tests2, _ = parse_k2(out_geo.read_bytes(), TestData, GeoBlockInfo)
        if len(tests2) != len(k2_tests):
            fail(f"roundtrip test count mismatch {len(tests2)} != {len(k2_tests)}")
        ok("roundtrip OK")

def main() -> None:
    root = Path(__file__).resolve().parents[1]

    if not (root / LAUNCHER).exists():
        fail(f"Не найден файл запуска: {LAUNCHER}")
    ok(f"Launcher найден: {LAUNCHER}")

    legacy = root / "ZondEditor_SZ_v3_k2k4_dispatch_fix_params_step_depth_v5_nofreeze_k4fix_xlsxfix.py"
    if legacy.exists():
        ok(f"Legacy-монолит найден (опционально): {legacy.name}")
    else:
        ok("Legacy-монолит отсутствует (это допустимо для модульной версии)")

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

    ok("Smoke parse + exports + fixes + roundtrip ...")
    _smoke_all(root)

    ok("Автопроверка завершена успешно.")

if __name__ == "__main__":
    proj_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(proj_root))
    main()
