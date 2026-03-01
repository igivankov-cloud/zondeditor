@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"
pushd "%REPO_ROOT%"

if not exist "build" mkdir "build"

call build\build_exe_verbose.bat > build\build_exe.log 2>&1
set "RC=%ERRORLEVEL%"

if "%RC%"=="0" (
  echo Build successful. See build\build_exe.log
  echo Output: dist\ZondEditor\ZondEditor.exe
) else (
  echo Build failed with code %RC%. See build\build_exe.log
)

popd
exit /b %RC%
