# -*- coding: utf-8 -*-
"""
Patch: fix RuntimeError 'Too early to create variable: no default root window'

Причина: tk.StringVar/IntVar/... создаются без master, а default root не установлен.
Решение: передать master=self (или master=parent/Toplevel) при создании переменных.

Usage (from repo root):
  py tools\\patch_tk_vars_master_v1.py

Edits: src/zondeditor/ui/editor.py (in place), creates .bak next to it.
"""
from __future__ import annotations
import os, re, shutil, sys

EDITOR_PATH = os.path.join('src', 'zondeditor', 'ui', 'editor.py')

VAR_CTORS = ('StringVar', 'IntVar', 'DoubleVar', 'BooleanVar')

def _patch_vars(s: str) -> tuple[str, int]:
    n = 0
    # Replace tk.StringVar(value=...) -> tk.StringVar(master=self, value=...) when no master arg present
    for ctor in VAR_CTORS:
        # matches tk.StringVar(   value=... ) or tk.StringVar() etc, but not if master= present
        pat = re.compile(rf'(\btk\.{ctor}\()(?=[^\)]*\))(?![^\)]*\bmaster\s*=)', re.M)
        # We will do a more careful replace only for calls that start immediately with value= or name= or )
        # Use a callback to inspect the call head
        call_pat = re.compile(rf'(\btk\.{ctor}\()([^\)]*)\)', re.M)
        def repl(m):
            nonlocal n
            head, args = m.group(1), m.group(2)
            if re.search(r'\bmaster\s*=', args):
                return m.group(0)
            # if first arg is positional (not keyword) we assume it's master already: StringVar(self, ...)
            stripped = args.strip()
            if stripped and not stripped.startswith(('value', 'name')) and not stripped.startswith(','):
                # likely positional master present
                return m.group(0)
            # inject master=self after '(' and optional whitespace
            n += 1
            if stripped.startswith(''):
                if stripped:
                    return f"{head}master=self, {args})"
                else:
                    return f"{head}master=self)"
        s2 = call_pat.sub(repl, s)
        s = s2
    return s, n

def main():
    if not os.path.exists(EDITOR_PATH):
        print(f'[ERR] Not found: {EDITOR_PATH}')
        sys.exit(1)
    with open(EDITOR_PATH, 'r', encoding='utf-8') as f:
        s = f.read()
    patched, n = _patch_vars(s)
    if n == 0:
        print('[WARN] No tk.*Var() occurrences patched (maybe already fixed).')
        return
    bak = EDITOR_PATH + '.bak'
    shutil.copy2(EDITOR_PATH, bak)
    with open(EDITOR_PATH, 'w', encoding='utf-8') as f:
        f.write(patched)
    print(f'[OK] Patched editor.py: injected master=self into {n} tk.*Var() calls')
    print(f'[OK] Backup: {bak}')

if __name__ == '__main__':
    main()