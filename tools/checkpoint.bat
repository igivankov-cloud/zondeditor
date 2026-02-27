@echo off
chcp 65001 >nul
pushd "%~dp0.."
echo ==== CHECKPOINT ====
git status
echo.
set /p MSG=Commit message (leave empty for default): 
if "%MSG%"=="" set MSG=checkpoint
git add .
git commit -m "%MSG%"
git push
echo.
echo [OK] checkpoint pushed.
popd
