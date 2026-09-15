@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PATH=C:\Program Files\Git\cmd;%PATH%"

echo === Local blog: commit + push to GitHub ===
echo.

git status -sb
echo.

set /p MSG=Commit message (Enter for default): 
if "%MSG%"=="" set "MSG=Update posts and site"

git add -A
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "%MSG%"
) else (
  echo No new changes to commit. Will try push anyway.
)

echo.
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\push-github.ps1"
echo.
pause
