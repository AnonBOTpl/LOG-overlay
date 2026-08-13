@echo off
setlocal
cd /d "%~dp0"

if not exist "tools\python37\python.exe" (
  echo [ERROR] Brak tools\python37\python.exe
  echo Pobierz Python 3.7.9 embeddable do tools\python37
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Brak .venv
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m tools.package_mod package
if errorlevel 1 (
  echo [ERROR] Pakowanie nie powiodlo sie
  pause
  exit /b 1
)

echo.
echo [OK] dist\LogOverlay.ts4script
pause
