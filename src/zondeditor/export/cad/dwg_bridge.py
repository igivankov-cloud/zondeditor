from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .logging import get_cad_logger
from .schema import DwgConversionResult

_log = get_cad_logger()

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
    _log.info("convert_dxf_to_dwg start dxf=%s dwg=%s converter_path=%s", dxf_path, dwg_path, converter_path or "")
    dxf = Path(dxf_path)
    dwg = Path(dwg_path)
    converter = find_oda_converter(converter_path)
    if converter is None:
        _log.warning("convert_dxf_to_dwg skipped: ODA converter not found")
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
        _log.exception("convert_dxf_to_dwg OS error")
        return DwgConversionResult(requested=True, success=False, dwg_path=None, message=f"DWG conversion failed: {exc}")

    produced = out_dir / dxf.with_suffix(".dwg").name
    if completed.returncode != 0 or not produced.exists():
        msg = (completed.stderr or completed.stdout or "unknown converter error").strip()
        _log.error("convert_dxf_to_dwg failed rc=%s msg=%s", completed.returncode, msg)
        return DwgConversionResult(requested=True, success=False, dwg_path=None, message=f"DWG conversion failed: {msg}")

    if produced.resolve() != dwg.resolve():
        produced.replace(dwg)
    _log.info("convert_dxf_to_dwg done dwg=%s", dwg)
    return DwgConversionResult(requested=True, success=True, dwg_path=dwg, message="DWG conversion completed.")
