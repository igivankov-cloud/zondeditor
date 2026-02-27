Шаг 10 — пересчёт qc/fs для K4 (scale=1000) + экспорт использует geo_kind по умолчанию

Изменено/добавлено:
- src/zondeditor/processing/calibration.py: добавлен calc_qc_fs(..., geo_kind) + дефолты K2_DEFAULT/K4_DEFAULT
- src/zondeditor/export/excel_export.py: использует calc_qc_fs и дефолты по geo_kind
- src/zondeditor/export/credo_zip.py: использует calc_qc_fs и дефолты по geo_kind
- tools/selfcheck.py: добавлен unit-check пересчёта K4 (1000 -> ~50 MPa), остальное как раньше

Проверка:
  py tools\selfcheck.py

Git (dev):
  git add src\zondeditor\processing\calibration.py src\zondeditor\export\excel_export.py src\zondeditor\export\credo_zip.py tools\selfcheck.py STEP10_README.txt
  git commit -m "refactor: add K4 calibration defaults and use in exports + tests"
  git push
