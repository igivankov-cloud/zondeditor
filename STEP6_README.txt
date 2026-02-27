Шаг 6 — processing/calibration + export (excel/credo) + тесты в selfcheck

Добавлено:
- src/zondeditor/processing/calibration.py: calc_qc_fs_from_del (qc_MPa, fs_kPa)
- src/zondeditor/export/excel_export.py: экспорт xlsx без UI
- src/zondeditor/export/credo_zip.py: экспорт ZIP (лоб/бок csv) без UI
- tools/selfcheck.py: теперь дополнительно делает экспорт на fixtures и проверяет файлы/инварианты

Проверка:
  py tools\selfcheck.py

Git (dev):
  git add src\zondeditor\processing src\zondeditor\export tools\selfcheck.py STEP6_README.txt
  git commit -m "refactor: add calibration+export modules and selfcheck export tests"
  git push
