@echo off
setlocal
cd /d "%~dp0"

REM Dev fallback: Sims 4 loads .py from Mods\Name\Scripts\
REM Do NOT keep LogOverlay.ts4script at the same time.

set "MODS=%USERPROFILE%\Documents\Electronic Arts\The Sims 4\Mods"
if not exist "%MODS%" (
  set "MODS=%USERPROFILE%\OneDrive\Documents\Electronic Arts\The Sims 4\Mods"
)

if exist "%MODS%\LogOverlay.ts4script" (
  echo [INFO] Usuwam LogOverlay.ts4script ^(kolizja z Scripts^)
  del /F /Q "%MODS%\LogOverlay.ts4script"
)

".venv\Scripts\python.exe" -m tools.package_mod dev
if errorlevel 1 (
  echo [ERROR] Instalacja Scripts nie powiodla sie
  pause
  exit /b 1
)

echo [OK] Dev Scripts zainstalowane.
pause
