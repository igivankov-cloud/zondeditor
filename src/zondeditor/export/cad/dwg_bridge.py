from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .schema import DwgConversionResult


def find_oda_converter(explicit_path: str | None = None) -> Path | None:
    if explicit_path:
        p = Path(explicit_path)
        if p.exists() and p.is_file():
            return p
    env = os.environ.get("ZE_ODA_CONVERTER", "").strip()
    if env:
        p = Path(env)
        if p.exists() and p.is_file():
            return p

    candidates = [
        "ODAFileConverter",
        "ODAFileConverter.exe",
        "TeighaFileConverter",
        "TeighaFileConverter.exe",
    ]
    for name in candidates:
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def convert_dxf_to_dwg(
    *,
    dxf_path: str | Path,
    dwg_path: str | Path,
    converter_path: str | None = None,
) -> DwgConversionResult:
    dxf = Path(dxf_path)
    dwg = Path(dwg_path)
    converter = find_oda_converter(converter_path)
    if converter is None:
        return DwgConversionResult(
            requested=True,
            success=False,
            dwg_path=None,
            message="ODA File Converter not found; DXF export completed.",
        )

    out_dir = dwg.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    in_dir = dxf.parent
    in_name = dxf.name

    # ODA CLI: <in_folder> <out_folder> <in_ver> <out_ver> <recurse> <audit> [<input_file_filter>]
    cmd = [
        str(converter),
        str(in_dir),
        str(out_dir),
        "ACAD2018",
        "ACAD2018",
        "0",
        "1",
        in_name,
    ]
    try:
        completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except OSError as exc:
        return DwgConversionResult(requested=True, success=False, dwg_path=None, message=f"DWG conversion failed: {exc}")

    produced = out_dir / dxf.with_suffix(".dwg").name
    if completed.returncode != 0 or not produced.exists():
        msg = (completed.stderr or completed.stdout or "unknown converter error").strip()
        return DwgConversionResult(requested=True, success=False, dwg_path=None, message=f"DWG conversion failed: {msg}")

    if produced.resolve() != dwg.resolve():
        produced.replace(dwg)
    return DwgConversionResult(requested=True, success=True, dwg_path=dwg, message="DWG conversion completed.")
