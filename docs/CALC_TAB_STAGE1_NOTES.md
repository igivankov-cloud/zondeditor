# Расчётный контур — этап 1 (исправленный)

## Реестр и справочники
- `data/normative_profiles.json`
- `data/soil_catalog.json`
- `data/applicability_rules.json`
- `data/method_catalog.json`

## Модуль расчётов
`src/zondeditor/calculations/`:
- `normative_profiles.py`
- `soil_catalog.py`
- `applicability.py`
- `sample_builder.py`
- `statistics.py`
- `calc_methods.py`
- `protocol_builder.py`
- `models.py` (IGEModel, IGECalcPoint, IGECalcStats, IGECalcResult, IGECalcSample, CalculationTabState)

## Геоэксплорер
- Используется как источник UX/структуры workflow.
- Актуальная формульная база закреплена через профиль `DEFAULT_CURRENT`.
- `GEOEXPLORER_SP446` и `LEGACY_SP11_105` оставлены как режимы совместимости/сравнения.
