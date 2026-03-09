# ZondEditor Architecture Notes (SoT)

Краткие правила для безопасной доработки после унификации.

## Source of Truth

### 1) Common params
- **SoT:** runtime `GeoCanvasEditor._common_params`.
- **Чтение:** через `GeoCanvasEditor._current_common_params()`.
- **Сериализация:** `Project.state["common_params"]` (+ fallback из `Project.settings` для старых проектов).
- **UI vars (`scale_var`, `fcone_var`, ...):** только отражение, не первичный источник.

### 2) Диагностика ошибок
- **SoT:** `processing.diagnostics.evaluate_diagnostics(...)`.
- **UI должен читать только report:** footer/header/protocol.
- Нельзя заново считать invalid/missing разными формулами в разных UI местах.

### 3) qc/fs расчёт
- **SoT:** `processing.calibration` (`calibration_from_common_params`, `calc_qc_fs_from_del`, `calc_qc_fs`).
- Графики, статусы, Excel/CREDO и ручной пересчёт должны использовать один calibration snapshot (`_current_calibration`).

### 4) Состояние проекта
- **SoT runtime:** `Project.state` + runtime-модель editor (`tests`, `flags`, `depth0_by_tid`, `step_by_tid`, view-flags).
- **`Project.settings`:** сериализация/совместимость и fallback при отсутствии state-ключей.
- **Порядок open/restore:** модель/state -> синхронизация UI (никогда наоборот).

## Что считается моделью
- `tests`, `flags`, `depth0_by_tid`, `step_by_tid`, `gwl_by_tid`, `project_ops`, `ige_registry`, `cpt_calc_settings`, `common_params`, `geo_kind`.

## Что считается UI-отражением
- `StringVar/BooleanVar`, ribbon controls, status labels, легенда, цвета.

## Инварианты согласованности
Обязано совпадать между UI/статусом/графиком/расчётами/экспортом:
1. состав экспортируемых опытов (`select_export_tests`);
2. calibration params (scale/Fкон/Fмуф/areas);
3. rule invalid (`>5` нулей подряд) и missing;
4. шаг и глубины для конкретного опыта.

## Антипаттерны (запрещено)
- Читать calibration напрямую из UI vars в экспорт/расчётах.
- Считать diagnostics вручную в нескольких местах UI.
- После `_restore(...)` перезаписывать модель значениями из старых UI vars/settings.
- Использовать параллельные фильтры опытов вместо `select_export_tests`.
