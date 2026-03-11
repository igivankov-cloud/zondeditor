# Расчётный контур — этап 2

## Реестр и справочники
- `data/normative_profiles.json` — профили нормативной базы с документами и изменениями.
- `data/soil_catalog.json` — типы грунтов, семейства, subtype и validation profile.
- `data/applicability_rules.json` — матрица применимости методов к грунтам и статусам.
- `data/method_catalog.json` — описание методов (`applicable_soils`, `required_fields`, `optional_fields`, `blocking_conditions`, `warning_conditions`, `output_params`, `implemented`).

## Модуль расчётов
`src/zondeditor/calculations/`:
- `normative_profiles.py`
- `soil_catalog.py`
- `applicability.py`
- `validation.py`
- `sample_builder.py`
- `statistics.py`
- `calc_methods.py`
- `protocol_builder.py`
- `models.py`

## Статусы и ограничения
- Статусы: `CALCULATED`, `PRELIMINARY`, `LAB_ONLY`, `NOT_APPLICABLE`, `NOT_IMPLEMENTED`.
- Если данных недостаточно, расчёт не выполняется: `result.status=invalid_input`, с `missing_fields`.
- Для неготовых методов: `result.status=not_implemented`, без фиктивных параметров.

## Трассировка
В `protocol_builder` добавлена `sections.calculation_trace`, где фиксируются:
- профиль,
- метод,
- использованные зондирования,
- диапазон глубин,
- число точек,
- исключённые точки и причины,
- warnings/errors/missing_fields.
