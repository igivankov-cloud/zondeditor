@echo off
chcp 65001 >nul
pushd "%~dp0.."
echo ==== ROLLBACK (hard reset to HEAD) ====
git reset --hard
echo.
py tools\selfcheck.py
set ERR=%ERRORLEVEL%
if NOT "%ERR%"=="0" (
  echo [FAIL] selfcheck failed after rollback (code=%ERR%)
  popd
  exit /b %ERR%
)
echo [OK] rolled back + selfcheck OK.
popd
