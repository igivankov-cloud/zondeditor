Шаг 7 — экспорт GXL (генерация) + selfcheck проверяет создание .gxl

Добавлено:
- src/zondeditor/export/gxl_export.py: export_gxl_generated(...)
- src/zondeditor/export/__init__.py обновлён
- tools/selfcheck.py: генерирует K2_generated.gxl и K4_generated.gxl и проверяет валидность XML

Проверка:
  py tools\selfcheck.py

Git (dev):
  git add src\zondeditor\export\gxl_export.py src\zondeditor\export\__init__.py tools\selfcheck.py STEP7_README.txt
  git commit -m "refactor(export): add gxl generator + selfcheck gxl tests"
  git push
