@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Brak .venv. Najpierw uruchom run_overlay.bat
  pause
  exit /b 1
)

echo [INFO] Demo sender ^(venv^) — upewnij sie, ze overlay juz dziala.
".venv\Scripts\python.exe" -m tools.demo_sender %*
echo.
pause
