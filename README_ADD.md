# zondeditor (modular branch)

Рабочая ветка миграции: `codex/refactor-project-structure-and-clean-up`.

## Что считается завершённой миграцией
- UI запускается через единый модульный entrypoint (`src/zondeditor/app.py`).
- Основные подсистемы разделены по пакетам: `ui`, `io`, `processing`, `export`, `domain`.
- Selfcheck проверяет импорт entrypoint/UI и smoke-сценарии парсинга/экспорта.
- Legacy-монолит опционален и не блокирует selfcheck при отсутствии.

## Клонирование
```bash
git clone https://github.com/igivankov-cloud/zondeditor.git
cd zondeditor
git checkout codex/refactor-project-structure-and-clean-up
```

## Установка зависимостей
```bash
python -m venv .venv
. .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Запуск UI
Основной способ:
```bash
PYTHONPATH=. python -m src.zondeditor.app
```

Альтернативно (добавлен пакетный entrypoint):
```bash
PYTHONPATH=. python -m src.zondeditor
```

## Проверки
Быстрая общая проверка:
```bash
PYTHONPATH=. python tools/selfcheck.py
```

Дополнительные selftests:
```bash
PYTHONPATH=. python tools/k2k4_selftest.py
PYTHONPATH=. python tools/geo_roundtrip_selftest.py
```

Примечание: если `openpyxl` не установлен, selfcheck пропускает только Excel-часть, остальные проверки выполняются.
