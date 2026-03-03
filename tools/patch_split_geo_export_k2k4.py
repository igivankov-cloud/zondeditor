# -*- coding: utf-8 -*-
"""
tools/patch_split_geo_export_k2k4.py

Applies a safe patch to src/zondeditor/ui/editor.py:
- Replaces the direct call to geo_writer.save_geo_as(...) inside export_geo_as()
  with a dispatch:
    if self.geo_kind == "K4": use geo_writer_k4.save_k4_geo_as(...)
    else: use geo_writer_k2.save_k2_geo_as(...)

This makes K2/K4 exports independent from each other and avoids accidental breakage.
"""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "src" / "zondeditor" / "ui" / "editor.py"

PATTERN = re.compile(
    r"\n\s*save_geo_as\(\s*\n\s*out_file,\s*\n\s*prepared,\s*\n\s*source_bytes=self\.original_bytes,\s*\n\s*blocks_info=blocks_info,\s*\n\s*\)\s*\n",
    re.MULTILINE
)

REPL = (
    "\n"
    "            # --- GEO EXPORT DISPATCH (split K2/K4, independent) ---\n"
    "            if getattr(self, \"geo_kind\", \"K2\") == \"K4\":\n"
    "                from src.zondeditor.io.geo_writer_k4 import save_k4_geo_as\n"
    "                save_k4_geo_as(\n"
    "                    out_file,\n"
    "                    prepared,\n"
    "                    source_bytes=self.original_bytes,\n"
    "                )\n"
    "            else:\n"
    "                from src.zondeditor.io.geo_writer_k2 import save_k2_geo_as\n"
    "                save_k2_geo_as(\n"
    "                    out_file,\n"
    "                    prepared,\n"
    "                    source_bytes=self.original_bytes,\n"
    "                )\n"
)

def main() -> None:
    if not EDITOR.exists():
        raise SystemExit(f"[ERR] editor.py not found: {EDITOR}")
    s = EDITOR.read_text(encoding="utf-8", errors="replace")
    n = len(PATTERN.findall(s))
    if n == 0:
        raise SystemExit("[ERR] pattern not found (save_geo_as call). editor.py may differ.")
    s2, cnt = PATTERN.subn(REPL, s, count=1)
    if cnt != 1:
        raise SystemExit(f"[ERR] expected 1 replacement, got {cnt}")
    EDITOR.write_text(s2, encoding="utf-8")
    print("[OK] patched editor.py: split K2/K4 GEO export")

if __name__ == "__main__":
    main()
