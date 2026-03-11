# Расчётный контур — этап 3

## Что добавлено на этапе 3
- Эталонные reference-cases для инженерной сверки (`fixtures/reference_calc_cases.json`).
- Автотест сравнения program vs expected с допусками (`tests/test_calc_reference_cases.py`).
- Первый export-ready payload в `protocol_builder`: `sections.export_ready_params` по `E_MPa`, `phi_deg`, `c_kPa`.
- Увязка с данными слоёв: `contributing_layers`, `required_fields`, `missing_fields`, причины отказа.

## Подтверждённые расчётные ветки
- `SP446_CPT_SAND`: работает, добавлены warning на пограничных qc/V.
- `SP446_CPT_CLAY`: работает, добавлены warning на пограничных qc/V и обязательность `IL|consistency`.

## Консервативная политика
Для веток SP446 пока используется инженерная упрощённая формула (явный warning в результате).
Если часть логики нормативно не подтверждена, расчёт не «догадывается»:
- `not_implemented` для неготовых методов;
- `invalid_input` при нехватке обязательных полей.

## Структура протокола
По каждому ИГЭ фиксируются:
- тип/статус/метод/профиль;
- использованные зондирования;
- глубинный интервал;
- число точек;
- исключённые точки и причины;
- статистика;
- итоговые параметры E/phi/c;
- warnings/errors/missing_fields/required_fields;
- contributing_layers (по каким слоям считалось).
