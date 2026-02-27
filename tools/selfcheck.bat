@echo off
chcp 65001 >nul
pushd "%~dp0.."
py tools\selfcheck.py
set ERR=%ERRORLEVEL%
popd
exit /b %ERR%
