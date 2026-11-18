@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title International Trade - Vista previa local
set "DATABASE_URL="
set "SEED_DEMO=0"
set "PYTHONUTF8=1"
echo.
echo ===================================================
echo   INTERNATIONAL TRADE - SERVIDOR LOCAL
echo ===================================================
echo.
if not exist ".venv\Scripts\python.exe" (
  echo Preparando Python para esta carpeta...
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
  if errorlevel 1 goto python_error
)
if not exist ".venv\instalado.ok" (
  echo Instalando dependencias - requiere Internet la primera vez...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto install_error
  echo ok>".venv\instalado.ok"
)
echo.
choice /C SN /M "Deseas cargar datos ficticios de ejemplo? [S/N]"
if errorlevel 2 (set "SEED_DEMO=0") else (set "SEED_DEMO=1")
echo Preparando SQLite local... (no se conecta a Neon)
".venv\Scripts\python.exe" seed.py
if errorlevel 1 goto run_error
echo.
echo Abrir: http://127.0.0.1:8000/login
echo Usuario local: admin
echo Contrasena local de demostracion: admin123
echo.
echo Para detener: pulsa Ctrl+C
start "" "http://127.0.0.1:8000/login"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 goto run_error
goto end
:python_error
echo ERROR: No se pudo iniciar Python. Instala Python 3.12 y reintenta.
goto end
:install_error
echo ERROR: No se pudieron instalar dependencias. Revisa Internet.
goto end
:run_error
echo ERROR: No se pudo iniciar. Copia el error de la consola.
:end
echo.
pause
