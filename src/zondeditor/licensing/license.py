"""
Simple license gate for ZondEditor (Windows).
- Stores license in: C:\ProgramData\ZondEditor\license.dat
- License binds to PC (MachineGuid).
This is a basic protection layer (not cryptographically strong), but good for preventing casual copying.

License format (license.dat):
  LIC=<sha256(MachineGuid + SECRET_SALT)>

To generate license on a machine:
  py tools\make_license.py --print
  py tools\make_license.py --install   (writes to ProgramData, may need admin)
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

APP_NAME = "ZondEditor"
PROGRAMDATA_DIR = os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), APP_NAME)
LICENSE_PATH = os.path.join(PROGRAMDATA_DIR, "license.dat")

# NOTE: this is a "shared secret" embedded in code (basic protection).
# You can change it any time to invalidate old licenses.
SECRET_SALT = "ZondEditor::v1::SALT::9f2b0d8a"

@dataclass
class LicenseStatus:
    ok: bool
    reason: str = ""
    machine_id: str = ""

def _read_machine_guid() -> str:
    """Windows MachineGuid from registry; fallback to hostname if unavailable."""
    try:
        import winreg  # type: ignore
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
        val, _typ = winreg.QueryValueEx(key, "MachineGuid")
        if isinstance(val, str) and val.strip():
            return val.strip()
    except Exception:
        pass
    # fallback (weaker)
    try:
        import uuid
        return f"uuid:{uuid.getnode()}"
    except Exception:
        return "unknown"

def machine_id() -> str:
    return _read_machine_guid()

def expected_license_token(mid: str | None = None) -> str:
    mid = (mid or machine_id()).strip()
    raw = (mid + SECRET_SALT).encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()

def read_license_file(path: str = LICENSE_PATH) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("LIC="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        return ""
    return ""

def ensure_dirs() -> None:
    os.makedirs(PROGRAMDATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(PROGRAMDATA_DIR, "logs"), exist_ok=True)

def check_license() -> LicenseStatus:
    ensure_dirs()
    mid = machine_id()
    token = read_license_file(LICENSE_PATH)
    if not token:
        return LicenseStatus(False, f"Лицензия не найдена: {LICENSE_PATH}", mid)

    exp = expected_license_token(mid)
    if token.lower() != exp.lower():
        return LicenseStatus(False, "Лицензия не подходит к этому ПК.", mid)

    return LicenseStatus(True, "", mid)

def write_license(token: str, path: str = LICENSE_PATH) -> None:
    ensure_dirs()
    with open(path, "w", encoding="utf-8") as f:
        f.write("LIC=" + token.strip() + "\n")
