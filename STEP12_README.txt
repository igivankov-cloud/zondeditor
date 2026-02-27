Шаг 12 — processing/k2k4.py (конвертация K2->K4 + цензура насыщения)

Добавлено:
- src/zondeditor/processing/k2k4.py
  - convert_k2_raw_to_k4_raw(k2_raw, mode=K4_30MPA|K4_50MPA) -> (k4_raw, censored, qc_mpa)
  - convert_test_k2_to_k4(test, mode=...) -> (series, mask)
- src/zondeditor/processing/__init__.py обновлён (экспорты)
- tools/k2k4_selftest.py: unit тесты конвертации

Проверка:
  py tools\selfcheck.py
  py tools\k2k4_selftest.py

Git (dev):
  git add src\zondeditor\processing\k2k4.py src\zondeditor\processing\__init__.py tools\k2k4_selftest.py STEP12_README.txt
  git commit -m "refactor(processing): add k2->k4 conversion module + unit tests"
  git push
