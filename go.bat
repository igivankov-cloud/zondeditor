@echo off
setlocal
cd /d "%~dp0"

rem Quick launcher: allows running the app by typing "go" in repo root.
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py run_zondeditor.py
    goto :eof
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python run_zondeditor.py
    goto :eof
)

echo [ERROR] Python launcher not found. Install Python or add it to PATH.
exit /b 1

