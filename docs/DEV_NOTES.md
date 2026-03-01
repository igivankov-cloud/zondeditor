# DEV_NOTES

## Общие правила
- Не ломать запуск из исходников (`python run_zondeditor.py`).
- Изменения бизнес-логики редактора делать только при необходимости.
- Поддерживать совместимость с Windows 7/10/11 (tkinter/ttk).

## Selfcheck и тестовые скрипты
Основные проверки:
- `tools/selfcheck.py`
- `tools/selfcheck_ui_handlers.py`
- `tools/selfcheck_project_marks.py`
- `tools/k2k4_selftest.py`
- `tools/geo_roundtrip_selftest.py`

Перед релизной сборкой EXE обязательно запускать минимум:
1. `python tools/selfcheck_ui_handlers.py`
2. `python tools/selfcheck.py`

## UI/Tkinter соглашения
- Использовать ровно один `Tk()` root в приложении.
- Дополнительные окна создавать через `Toplevel`.
- Не создавать скрытые лишние root-окна в хелперах/диалогах.

## Ribbon-команды
При добавлении новой команды Ribbon:
1. Добавить обработчик в соответствующий UI-модуль.
2. Привязать команду к кнопке/элементу Ribbon.
3. Убедиться, что обработчик доступен в selfcheck `tools/selfcheck_ui_handlers.py`.
4. Проверить, что команда не ломает состояние проекта.

## Работа с .zproj
- Формат `.zproj` считается основным контейнером состояния проекта.
- Изменения модели/сериализации делать обратно-совместимо.
- При изменениях структуры `.zproj` обязательно:
  - обновить чтение/запись в `src/zondeditor/project/*`;
  - прогнать selfcheck и smoke-кейсы открытия/сохранения.

## Сборка EXE и установщика
- Скрипты сборки: `build/build_exe*.bat`.
- Inno Setup-скрипт: `installer/installer_protected.iss`.
- Не смешивать артефакты сборки с исходниками: итоги в `dist/` и `dist_installer/`.
