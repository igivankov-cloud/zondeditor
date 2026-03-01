# -*- coding: utf-8 -*-
"""
Patch for ZondEditor: fix ttk.Button font setting in Ribbon (QAT).

Problem:
  _tkinter.TclError: unknown option '-font'
Cause:
  ttk.Button doesn't support configure(font=...). Use ttk.Style instead.

Usage (from repo root):
  py tools\\patch_ribbon_ttk_font_v1.py

Edits: src/zondeditor/ui/ribbon.py (in place), creates .bak next to it.
"""
from __future__ import annotations
import os, re, shutil, sys

RIBBON_PATH = os.path.join('src', 'zondeditor', 'ui', 'ribbon.py')

def main():
    if not os.path.exists(RIBBON_PATH):
        print(f'[ERR] Not found: {RIBBON_PATH}')
        sys.exit(1)

    with open(RIBBON_PATH, 'r', encoding='utf-8') as f:
        s = f.read()

    # If already patched (style is used), exit.
    if 'Zond.QAT.TButton' in s and 'style.configure' in s:
        print('[OK] Already patched.')
        return

    # Ensure ttk is imported
    if not re.search(r'^\s*from\s+tkinter\s+import\s+.*ttk', s, flags=re.M) and not re.search(r'^\s*import\s+tkinter\.ttk\s+as\s+ttk', s, flags=re.M):
        # Try to inject 'from tkinter import ttk' after first 'import tkinter as tk' or similar
        m = re.search(r'^(\s*import\s+tkinter\s+as\s+tk\s*\n)', s, flags=re.M)
        if m:
            s = s[:m.end()] + 'from tkinter import ttk\n' + s[m.end():]
        else:
            # Fallback: add at top after docstring if present
            m2 = re.search(r'\n\n', s, flags=re.M)
            insert_at = m2.end() if m2 else 0
            s = s[:insert_at] + 'from tkinter import ttk\n' + s[insert_at:]

    # Patch the QAT button font line: replace btn.configure(font=self.icon_font) with Style-based approach.
    # We'll look for a line containing configure(font=self.icon_font) (allow spaces).
    pat = re.compile(r'^(\s*)btn\.configure\(\s*font\s*=\s*self\.icon_font\s*\)\s*$', re.M)
    m = pat.search(s)
    if not m:
        print('[ERR] Could not find line: btn.configure(font=self.icon_font)')
        sys.exit(2)

    indent = m.group(1)
    repl = '\n'.join([
        f"{indent}# ttk.Button does not support configure(font=...). Use a style.",
        f"{indent}if self.icon_font:",
        f"{indent}    try:",
        f"{indent}        style = ttk.Style(btn)",
        f"{indent}        style.configure('Zond.QAT.TButton', font=self.icon_font)",
        f"{indent}        btn.configure(style='Zond.QAT.TButton')",
        f"{indent}    except Exception:",
        f"{indent}        pass",
    ])

    s = pat.sub(repl, s, count=1)

    bak = RIBBON_PATH + '.bak'
    shutil.copy2(RIBBON_PATH, bak)
    with open(RIBBON_PATH, 'w', encoding='utf-8') as f:
        f.write(s)

    print('[OK] Patched ribbon.py (ttk font via style).')
    print(f'[OK] Backup: {bak}')

if __name__ == '__main__':
    main()