# tools/k2k4_selftest.py
# Quick unit tests for src.zondeditor.processing.k2k4
# Run:
#   py tools\k2k4_selftest.py

from __future__ import annotations

from src.zondeditor.processing.k2k4 import convert_k2_raw_to_k4_raw

def assert_close(a, b, tol=1e-6, msg=""):
    if abs(a-b) > tol:
        raise SystemExit(f"[FAIL] {msg} {a} != {b}")

def main():
    # saturated K2
    r30 = convert_k2_raw_to_k4_raw(250, mode="K4_30MPA")
    if r30.k4_raw != 1000 or not r30.censored:
        raise SystemExit(f"[FAIL] 250->K4_30 expected (1000,censored) got {r30}")
    r50 = convert_k2_raw_to_k4_raw(250, mode="K4_50MPA")
    if r50.k4_raw != 600 or not r50.censored:
        raise SystemExit(f"[FAIL] 250->K4_50 expected (600,censored) got {r50}")

    # mid-scale
    r30 = convert_k2_raw_to_k4_raw(125, mode="K4_30MPA")
    if r30.k4_raw != 500 or r30.censored:
        raise SystemExit(f"[FAIL] 125->K4_30 expected 500 not censored got {r30}")
    r50 = convert_k2_raw_to_k4_raw(125, mode="K4_50MPA")
    if r50.k4_raw != 300 or r50.censored:
        raise SystemExit(f"[FAIL] 125->K4_50 expected 300 not censored got {r50}")

    print("[ OK ] k2k4 conversion unit tests passed.")

if __name__ == "__main__":
    main()
