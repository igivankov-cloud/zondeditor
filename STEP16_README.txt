Шаг 16 — UI-экспорты через модули (автопатч монолита)

Что добавлено:
- tools/patch_step16_ui_exports.py: патчит монолит, добавляет импорты и заменяет вызовы export-функций
  (Excel/CREDO/GXL) на модульные:
    export_excel / export_credo_zip / export_gxl_generated

Как применить:
1) Распаковать в корень C:\ZondEditor
2) Запустить патчер:
   py tools\patch_step16_ui_exports.py
3) Проверить:
   py tools\selfcheck.py
4) В GUI проверить кнопки экспортов (Excel, CREDO ZIP, GXL).

Git:
  git add tools\patch_step16_ui_exports.py ZondEditor_...py
  git commit -m "refactor(ui): route exports through modules (step16)"
  git push

Если патчер пишет WARN (не нашёл шаблоны) — пришли мне куски обработчиков кнопок экспортов из монолита.
