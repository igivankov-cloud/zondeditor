Шаг 5 — domain/models + selfcheck использует реальные модели

Что добавлено:
- src/zondeditor/domain/models.py (TestData, GeoBlockInfo, TestFlags)
- src/zondeditor/domain/__init__.py
- tools/selfcheck.py теперь парсит fixtures используя эти модели

Проверка:
  py tools\selfcheck.py

Git:
  git add src\zondeditor\domain tools\selfcheck.py STEP5_README.txt
  git commit -m "refactor(domain): add models and use in selfcheck"
  git push
