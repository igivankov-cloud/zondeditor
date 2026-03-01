# -*- coding: utf-8 -*-
"""
Patch for ZondEditor: add GeoCanvasEditor.save_geo / save_gxl aliases
to prevent AttributeError when Ribbon maps export_geo to self.save_geo.

Usage (from repo root):
  py tools\patch_save_geo_alias_v1.py

It edits: src/zondeditor/ui/editor.py (in place) and makes a .bak рядом.
Safe: if methods already exist, it won't duplicate.
"""
from __future__ import annotations
import os, re, shutil, sys

EDITOR_PATH = os.path.join('src', 'zondeditor', 'ui', 'editor.py')

ALIAS_BLOCK = '''
    # --- Compatibility aliases for Ribbon commands (safe export UX) ---
    def save_geo(self, *args, **kwargs):
        """
        Ribbon compatibility alias: export GEO using 'Save As...' flow.
        Tries a list of known handlers; does NOT overwrite the original source file silently.
        """
        for name in (
            'export_geo_as',
            'export_geo_file_as',
            'export_geo_as_file',
            'export_geo',
            'save_geo_as',
            'save_geo_file_as',
            'save_geo_file',
        ):
            fn = getattr(self, name, None)
            if callable(fn) and fn is not self.save_geo:
                return fn(*args, **kwargs)
        try:
            import tkinter.messagebox as mb
            mb.showerror('Экспорт GEO', 'Не найден обработчик экспорта GEO (export_geo_as/save_geo_as...).')
        except Exception:
            pass
        return None

    def save_gxl(self, *args, **kwargs):
        """
        Ribbon compatibility alias: export GXL using 'Save As...' flow.
        """
        for name in (
            'export_gxl_as',
            'export_gxl_file_as',
            'export_gxl_as_file',
            'export_gxl',
            'save_gxl_as',
            'save_gxl_file_as',
            'save_gxl_file',
        ):
            fn = getattr(self, name, None)
            if callable(fn) and fn is not self.save_gxl:
                return fn(*args, **kwargs)
        try:
            import tkinter.messagebox as mb
            mb.showerror('Экспорт GXL', 'Не найден обработчик экспорта GXL (export_gxl_as/save_gxl_as...).')
        except Exception:
            pass
        return None
'''

def main():
    if not os.path.exists(EDITOR_PATH):
        print(f'[ERR] Not found: {EDITOR_PATH}')
        sys.exit(1)

    with open(EDITOR_PATH, 'r', encoding='utf-8') as f:
        s = f.read()

    if re.search(r'^\s{4}def\s+save_geo\s*\(', s, flags=re.M):
        print('[OK] save_geo already exists; nothing to do.')
        return

    if not re.search(r'^class\s+GeoCanvasEditor\b.*?:\s*$', s, flags=re.M):
        print('[ERR] class GeoCanvasEditor not found.')
        sys.exit(2)

    insert_at = len(s)
    m_if = re.search(r'^if\s+__name__\s*==\s*[\"\']__main__[\"\']\s*:', s, flags=re.M)
    if m_if:
        insert_at = m_if.start()

    bak = EDITOR_PATH + '.bak'
    shutil.copy2(EDITOR_PATH, bak)

    patched = s[:insert_at].rstrip() + '\n' + ALIAS_BLOCK + '\n\n' + s[insert_at:].lstrip()
    with open(EDITOR_PATH, 'w', encoding='utf-8') as f:
        f.write(patched)

    print('[OK] Patched editor.py')
    print(f'[OK] Backup: {bak}')

if __name__ == '__main__':
    main()