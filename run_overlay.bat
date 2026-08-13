@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Brak .venv — tworze srodowisko...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Nie udalo sie utworzyc .venv
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -c "import PySide6" 1>nul 2>nul
if errorlevel 1 (
  echo [INFO] Instaluje zaleznosci overlay do .venv...
  ".venv\Scripts\python.exe" -m pip install -r requirements-overlay.txt
  if errorlevel 1 (
    echo [ERROR] pip install nie powiodl sie
    pause
    exit /b 1
  )
)

echo [INFO] Start overlay ^(venv^)...
".venv\Scripts\python.exe" -m overlay.main %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo [ERROR] Overlay zakonczyl sie kodem %EXITCODE%
  pause
)
exit /b %EXITCODE%
