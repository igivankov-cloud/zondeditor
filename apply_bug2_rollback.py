# -*- coding: utf-8 -*-
"""
Патч для ZondEditor: откат нестабильного bug-2 фикса окна выбора ИГЭ
и скрытие hover-подсказки "Выбрать ИГЭ".

Запускать из корня репозитория:
    py apply_bug2_rollback.py
"""
from pathlib import Path
import re
import shutil
import sys

ROOT = Path.cwd()
TARGET = ROOT / "src" / "zondeditor" / "ui" / "editor.py"

if not TARGET.exists():
    print(f"[ERR] Не найден файл: {TARGET}")
    sys.exit(1)

text = TARGET.read_text(encoding="utf-8")
original = text

# 1) Удалить helper deferred focus-out, если есть
text = re.sub(
    r'\n[ \t]*def _maybe_hide_layer_ige_picker_on_focus_out\(self, _event=None\):\n'
    r'(?:(?:[ \t].*\n)|\n)*?'
    r'(?=[ \t]*def _show_ige_picker_at_click\(self, event, ti: int, depth: float\):)',
    '\n',
    text,
    flags=re.MULTILINE
)

# 2) Удалить нестабильные строки внутри picker-а
for needle in [
    '        win.transient(self)\n',
    '        win.lift(self)\n',
    '        win.bind("<FocusOut>", self._maybe_hide_layer_ige_picker_on_focus_out)\n',
    '        win.grab_set()\n',
]:
    text = text.replace(needle, '')

# 3) Скрыть tooltip "Выбрать ИГЭ"
text = text.replace(
    '            elif kind == "layer_interval":\n                tip_text = "Выбрать ИГЭ"\n',
    '            elif kind == "layer_interval":\n                tip_text = None\n'
)

# 4) Обернуть показ tooltip в if tip_text:, если ещё не обёрнуто
old = (
    '            self._schedule_canvas_tip(tip_text, event.x_root, event.y_root, delay_ms=700)\n'
    '            self.canvas.configure(cursor="hand2")\n'
)
new = (
    '            if tip_text:\n'
    '                self._schedule_canvas_tip(tip_text, event.x_root, event.y_root, delay_ms=700)\n'
    '            self.canvas.configure(cursor="hand2")\n'
)
if old in text:
    text = text.replace(old, new, 1)

if text == original:
    print("[OK] Изменений не потребовалось: файл уже в нужном состоянии.")
    sys.exit(0)

backup = TARGET.with_suffix(TARGET.suffix + ".bak_bug2")
shutil.copy2(TARGET, backup)
TARGET.write_text(text, encoding="utf-8")

print("[OK] Патч применён.")
print(f"[OK] Резервная копия: {backup}")

# Простейшая самопроверка
checks = {
    "_maybe_hide_layer_ige_picker_on_focus_out": "_maybe_hide_layer_ige_picker_on_focus_out" not in text,
    'win.transient(self)': 'win.transient(self)' not in text,
    'win.lift(self)': 'win.lift(self)' not in text,
    'win.grab_set()': 'win.grab_set()' not in text,
    '"Выбрать ИГЭ"': '"Выбрать ИГЭ"' not in text or 'tip_text = "Выбрать ИГЭ"' not in text,
}
for name, ok in checks.items():
    print(f"[CHK] {name}: {'OK' if ok else 'WARN'}")
