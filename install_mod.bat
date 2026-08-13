@echo off
setlocal
cd /d "%~dp0"

set "MODS=%USERPROFILE%\Documents\Electronic Arts\The Sims 4\Mods"
if not exist "%MODS%" (
  set "MODS=%USERPROFILE%\OneDrive\Documents\Electronic Arts\The Sims 4\Mods"
)
if not exist "%MODS%" (
  echo [ERROR] Nie znaleziono folderu Mods Sims 4
  pause
  exit /b 1
)

if not exist "tools\python37\python.exe" (
  echo [ERROR] Brak tools\python37\python.exe
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Brak .venv
  pause
  exit /b 1
)

echo [INFO] Buduje LogOverlay.ts4script ^(Python 3.7 .pyc^)...
".venv\Scripts\python.exe" -m tools.package_mod package
if errorlevel 1 (
  echo [ERROR] Pakowanie nie powiodlo sie
  pause
  exit /b 1
)

REM Avoid double-loading with Scripts folder
if exist "%MODS%\LogOverlay\Scripts" (
  echo [INFO] Usuwam stary Mods\LogOverlay\Scripts ^(kolizja z ts4script^)
  rmdir /S /Q "%MODS%\LogOverlay\Scripts"
)

copy /Y "dist\LogOverlay.ts4script" "%MODS%\LogOverlay.ts4script" >nul
if errorlevel 1 (
  echo [ERROR] Kopiowanie do Mods nie powiodlo sie
  pause
  exit /b 1
)

echo.
echo [OK] Zainstalowano: %MODS%\LogOverlay.ts4script
echo.
echo Test:
echo  1. run_overlay.bat
echo  2. Wejdz do menu Sims 4
echo  3. Sprawdz mod_logs\LogOverlay_self.log
echo.
pause
