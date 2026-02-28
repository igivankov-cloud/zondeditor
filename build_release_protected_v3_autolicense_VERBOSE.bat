@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

rem ==========================================================
rem ZondEditor build (protected installer) v3 + auto-license
rem VERBOSE edition (shows pip/pyinstaller output)
rem Requires app supports: --init-license
rem ==========================================================

pushd "%~dp0"

echo ==== ZondEditor protected build v3 (auto-license) [VERBOSE] ====
echo Folder: %CD%
echo.

set "PY=py -3.10"
%PY% -V >nul 2>&1
if errorlevel 1 set "PY=py"
%PY% -V >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python launcher not found.
  popd
  exit /b 1
)

echo Using: %PY%
%PY% -V
echo.

set "VENV=.venv_build"
if exist "%VENV%" (
  echo Removing old venv: %VENV%
  rmdir /s /q "%VENV%"
)

echo Creating venv...
%PY% -m venv "%VENV%"
if errorlevel 1 (
  echo ERROR: cannot create venv.
  popd
  exit /b 1
)

call "%VENV%\Scripts\activate.bat"
if errorlevel 1 (
  echo ERROR: cannot activate venv.
  popd
  exit /b 1
)

echo Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
  echo ERROR: pip upgrade failed.
  popd
  exit /b 1
)

echo Installing requirements...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: requirements install failed.
  popd
  exit /b 1
)

echo Installing pyinstaller...
python -m pip install pyinstaller
if errorlevel 1 (
  echo ERROR: pyinstaller install failed.
  popd
  exit /b 1
)

echo Cleaning previous build...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

set "ICON=SZ_icon_transparent_bg_only_adaptive.ico"
if exist "%ICON%" (
  echo Building with icon: %ICON%
  python -m PyInstaller --noconfirm --clean --windowed --name "ZondEditor" --icon "%ICON%" run_zondeditor.py
) else (
  echo WARNING: icon not found: %ICON%
  echo Building without icon.
  python -m PyInstaller --noconfirm --clean --windowed --name "ZondEditor" run_zondeditor.py
)

if errorlevel 1 (
  echo ERROR: PyInstaller build failed.
  popd
  exit /b 1
)

echo.
echo Build OK. Output:
echo   dist\ZondEditor\
echo.

where ISCC.exe >nul 2>&1
if errorlevel 1 (
  echo WARNING: ISCC.exe not found in PATH. Skipping installer.
  echo You can still use dist\ZondEditor folder as a portable build.
  popd
  exit /b 0
)

echo Building installer with Inno Setup...
ISCC.exe "installer_protected_v3_autolicense.iss"
if errorlevel 1 (
  echo ERROR: Inno Setup compilation failed.
  popd
  exit /b 1
)

echo.
echo OK: installer built in dist_installer\
echo.

popd
endlocal
