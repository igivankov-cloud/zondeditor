# ZondEditor

Продуктизированная версия ZondEditor с поддержкой запуска из исходников, сборки EXE (PyInstaller), установщика (Inno Setup) и базовой лицензии через `ProgramData`.

## Требования
- Windows 7/10/11
- Python 3.10+ (рекомендуется 3.11)
- (для установщика) Inno Setup 6

## Запуск из исходников
```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run_zondeditor.py
```

Альтернативный entrypoint:
```bat
python -m src.zondeditor.app
```

## Проверки (selfcheck)
```bat
python tools\selfcheck.py
python tools\selfcheck_ui_handlers.py
python tools\selfcheck_fixtures.py
python tools\selfcheck_project_marks.py
python tools\k2k4_selftest.py
python tools\geo_roundtrip_selftest.py
```

## Сборка EXE
Скрипты лежат в `build/`:
- `build/build_exe.bat` — обычный режим
- `build/build_exe_verbose.bat` — подробный лог установки и PyInstaller

Запуск:
```bat
build\build_exe.bat
```

Что делает скрипт:
1. Создает отдельный venv (`build\.venv`).
2. Устанавливает зависимости из `requirements.txt` и `pyinstaller`.
3. Запускает selfcheck перед сборкой.
4. Собирает one-dir, windowed EXE с именем `ZondEditor`.

Результат:
- `dist\ZondEditor\ZondEditor.exe`

### Иконка приложения
По умолчанию скрипт пытается взять иконку `build/assets/app.ico`.
Если файл отсутствует, сборка не падает и продолжается без иконки.
Чтобы добавить иконку:
1. Подготовьте `.ico` файл.
2. Положите его в `build/assets/app.ico`.
3. Перезапустите сборку.

## Установщик (Inno Setup)
- Скрипт: `installer/installer_protected.iss`
- Краткая инструкция: `installer/README_INSTALL.txt`

Сборка установщика (после сборки EXE):
```bat
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\installer_protected.iss
```

## Лицензия и ProgramData
Приложение использует каталог:
- `C:\ProgramData\ZondEditor\license.dat`
- `C:\ProgramData\ZondEditor\logs\`

Режим инициализации лицензии:
```bat
ZondEditor.exe --init-license
```
Команда создает `license.dat` (если отсутствует) и папку `logs`.
При обычном старте приложение проверяет наличие валидной лицензии и при ее отсутствии показывает понятное сообщение и блокирует запуск UI.

## CI
Workflow: `.github/workflows/ci.yml`
- Триггеры: `push`/`pull_request` в `dev`
- Проверки: `compileall`, `tools/selfcheck_ui_handlers.py`, `tools/selfcheck_fixtures.py`
- EXE в CI пока не собирается.

## Дополнительная документация
- `docs/DEV_NOTES.md`
- `docs/CHANGELOG.md`
