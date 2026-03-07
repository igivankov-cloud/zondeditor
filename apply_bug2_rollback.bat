@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === ZondEditor bug-2 rollback patch ===
py apply_bug2_rollback.py
echo.
pause
