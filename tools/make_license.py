# tools/make_license.py
# Generate/install a license token for this PC.
#
# Usage:
#   py tools\make_license.py --print
#   py tools\make_license.py --install
#
from __future__ import annotations

import argparse
from src.zondeditor.licensing.license import machine_id, expected_license_token, write_license, LICENSE_PATH

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", help="Print machine id and license token")
    ap.add_argument("--install", action="store_true", help="Write license.dat to ProgramData (may require admin)")
    args = ap.parse_args()

    mid = machine_id()
    token = expected_license_token(mid)

    if args.print or (not args.install):
        print("MachineId:", mid)
        print("LicenseToken:", token)
        print("LicensePath:", LICENSE_PATH)

    if args.install:
        write_license(token, LICENSE_PATH)
        print("OK: installed to", LICENSE_PATH)

if __name__ == "__main__":
    main()
