Шаг 14 — io/geo_writer.py (сохранение K2 GEO) + roundtrip тест

Добавлено:
- src/zondeditor/io/geo_writer.py: build_k2_geo_bytes + save_k2_geo
- tools/geo_roundtrip_selftest.py: отдельный roundtrip тест
- tools/selfcheck.py: теперь включает roundtrip save->read на K2 fixture

Проверка:
  py tools\selfcheck.py
  py tools\geo_roundtrip_selftest.py

Git (dev):
  git add src\zondeditor\io\geo_writer.py tools\geo_roundtrip_selftest.py tools\selfcheck.py STEP14_README.txt
  git commit -m "refactor(io): add K2 geo writer + roundtrip tests"
  git push
