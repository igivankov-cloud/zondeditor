# ZondEditor Release Contour (Minimal Stable Flow)

## 1) Стабильная ветка
- Рекомендуемый стабильный контур: `main` (или выделенная release-ветка, если команда использует release branching).
- Все изменения в stable идут через PR с обязательным прогоном regression-checklist.

## 2) Обязательная проверка перед релизом
1. Автотесты:
   - `PYTHONPATH=. pytest -q`
2. Core selfcheck (минимум):
   - `PYTHONPATH=. python tools/selfcheck.py`
   - `PYTHONPATH=. python tools/geo_roundtrip_selftest.py`
   - `PYTHONPATH=. python tools/selfcheck_export_selection.py`
3. Ручной regression-checklist:
   - `docs/REGRESSION_CHECKLIST.md` (K2/K4, save/reopen, diagnostics, exports).

## 3) Основной путь сборки
- Windows build scripts:
  - `build/build_exe.bat`
  - `build/build_exe_verbose.bat`
- Installer path:
  - `installer/installer_protected.iss`
  - `installer_protected_v3_autolicense.iss`

## 4) Релизные артефакты и файлы
- Основной исполняемый пакет из `build/*.bat`.
- Инсталлятор из `installer*.iss`.
- Версия: `build/version.txt`.
- Changelog: `docs/CHANGELOG.md`.

## 5) Чек перед упаковкой/выдачей
- Нет расхождений UI/status/diagnostics/export (по regression checklist).
- K2/K4 открываются и экспортируются без деградации.
- `.zproj` roundtrip сохраняет common params/view flags/step/depth.
- Экспорт GEO/GXL/Excel/CREDO использует одинаковый selection/calibration контур.
- В git нет незакоммиченных изменений.
