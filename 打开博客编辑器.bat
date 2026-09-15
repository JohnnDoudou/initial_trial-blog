@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Starting local blog editor...
echo Browser will open http://127.0.0.1:8766/
echo Close this window (or press Ctrl+C) to stop the editor.
echo.

start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8766/"
python admin_server.py
if errorlevel 1 (
  echo.
  echo Failed to start. Is Python installed and on PATH?
  pause
)
