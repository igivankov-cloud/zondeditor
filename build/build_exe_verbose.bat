@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"
pushd "%REPO_ROOT%"

echo === ZondEditor EXE build (verbose) ===

set "PY=py -3.11"
%PY% -V >nul 2>&1 || set "PY=py -3.10"
%PY% -V >nul 2>&1 || set "PY=py"
%PY% -V >nul 2>&1 || (
  echo ERROR: Python launcher was not found.
  popd
  exit /b 1
)

echo Using Python launcher: %PY%
%PY% -V

set "VENV=build\.venv"
if exist "%VENV%" (
  echo Removing previous venv: %VENV%
  rmdir /s /q "%VENV%"
)

echo Creating venv...
%PY% -m venv "%VENV%" || (
  echo ERROR: cannot create virtual environment.
  popd
  exit /b 1
)

call "%VENV%\Scripts\activate.bat" || (
  echo ERROR: cannot activate virtual environment.
  popd
  exit /b 1
)

python -m pip install --upgrade pip || goto :fail
python -m pip install -r requirements.txt || goto :fail
python -m pip install pyinstaller || goto :fail

echo Running selfcheck suite...
python tools\selfcheck_ui_handlers.py || goto :fail
python tools\selfcheck.py || goto :fail

if exist "dist" rmdir /s /q "dist"
if exist "pyinstaller_build" rmdir /s /q "pyinstaller_build"

set "ICON_ARG="
if exist "build\assets\app.ico" (
  set "ICON_ARG=--icon build\assets\app.ico"
  echo Icon found: build\assets\app.ico
) else (
  echo WARNING: build\assets\app.ico was not found. Building without icon.
)

echo Building one-dir windowed EXE...
python -m PyInstaller --noconfirm --clean --windowed --onedir --name "ZondEditor" --distpath "dist" --workpath "pyinstaller_build" %ICON_ARG% run_zondeditor.py || goto :fail

echo.
echo Build successful: dist\ZondEditor\ZondEditor.exe
popd
exit /b 0

:fail
echo.
echo ERROR: build failed.
popd
exit /b 1
