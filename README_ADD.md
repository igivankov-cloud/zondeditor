# zondeditor

## Состав проекта
- `src/zondeditor/` — основной модульный код приложения (UI, парсеры, обработка, экспорт).
- `run_zondeditor.py` — точка входа для запуска приложения.
- `tools/selfcheck.py` — базовая автопроверка модулей, парсинга и экспортов.
- `fixtures/` — тестовые GEO-файлы для smoke-проверок.
- `ZondEditor_SZ_v3_k2k4_dispatch_fix_params_step_depth_v5_nofreeze_k4fix_xlsxfix.py` — legacy-монолит (оставлен как архивный источник логики).

## Запуск
В корне проекта:

```bat
py run_zondeditor.py
```

## Проверка после изменений

```bat
py tools\selfcheck.py
py tools\k2k4_selftest.py
py tools\geo_roundtrip_selftest.py
```

## Текущий статус миграции
- Запуск и UI уже работают через `src/zondeditor/ui/...`.
- Экспорт и ключевые блоки обработки вынесены в модульную структуру.
- Legacy-монолит больше не является обязательным для старта и selfcheck.
