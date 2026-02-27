@echo off
chcp 65001 >nul
pushd "%~dp0.."
echo ==== CLEANUP (safe) ====
if exist tools\_selfcheck_out rmdir /s /q tools\_selfcheck_out
del /q STEP*_README.txt 2>nul
del /q STEP*_HOTFIX*.txt 2>nul
echo [OK] cleanup done.
popd
