# Раздельный экспорт GEO для K2 и K4 (split export)

## Зачем
Общий экспорт `save_geo_as(...)` периодически ломался и для K2, и для K4 (типичная ошибка: `Payload size mismatch for template replacement`).
Чтобы исключить взаимное влияние и регрессии, экспорт разделён на два независимых модуля.

## Итоговое решение

### 1) Два независимых экспортёра

#### K2 — `src/zondeditor/io/geo_writer_k2.py`
- Rebuild на базе шаблона, **без** inplace template-replacement.
- Пишет **только prepared/exported tests**.
- **Новые (скопированные) опыты** добавляются (клонирование базового 22-байтного header, замена id в маркере).
- **Отключённые/удалённые** не попадают.
- **Хвосты/дотяжки** сохраняются (payload переменной длины).
- Маркер: `FF FF <id> 1E 0A` (принимаем также `1E 14` как fallback).
- Payload: 2 байта/строка `[qc_byte, fs_byte]`.

#### K4 — `src/zondeditor/io/geo_writer_k4.py`
- Rebuild на базе шаблона, **без** inplace template-replacement.
- Пишет **только prepared/exported tests**.
- **Новые (скопированные) опыты** добавляются (клонирование базового 22-байтного header, замена id).
- **Отключённые/удалённые** не попадают.
- **Хвосты/дотяжки** сохраняются (payload переменной длины).
- Маркер: `FF FF <id> 1E 14` (fallback `1E 0A`).
- Payload: 9 байт/строка `qh ql 00 00 fh fl ul uh 00` (hi/lo в проектной конвенции `value = hi*100 + lo`).

### 2) Диспетчер в UI (точка вызова экспорта)
В `src/zondeditor/ui/editor.py` внутри `export_geo_as()` общий вызов `save_geo_as(...)` заменён на диспетчер:
- если `self.geo_kind == "K4"` → `geo_writer_k4.save_k4_geo_as(...)`
- иначе → `geo_writer_k2.save_k2_geo_as(...)`

Так K2 и K4 не зависят друг от друга и не могут «сломать» экспорт соседнего формата.

### 3) Патчер для безопасного применения
`tools/patch_split_geo_export_k2k4.py` — однократный патч, который автоматически вносит замену в `editor.py` по стабильному шаблону вызова `save_geo_as(...)`.

## Файлы, которые должны быть в репозитории
- `src/zondeditor/io/geo_writer_k2.py`
- `src/zondeditor/io/geo_writer_k4.py`
- `tools/patch_split_geo_export_k2k4.py`
- (изменён) `src/zondeditor/ui/editor.py`
