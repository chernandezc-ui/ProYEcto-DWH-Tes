@echo off
setlocal enabledelayedexpansion

set "BASE_DIR=%~dp0"
set "PYTHON_EXE=%BASE_DIR%.venv\Scripts\python.exe"
set "ETL_DIR=%BASE_DIR%ETL"
set "PIPELINE_SCRIPT=%ETL_DIR%\pipeline.py"
set "PYTHONUTF8=1"
set "PYTHONUNBUFFERED=1"
set "EXIT_CODE=99"

:: Fecha en formato YYYYMMDD para nombre del log (wmic es independiente del idioma regional)
for /f %%a in ('wmic os get localdatetime ^| find "."') do set "LOG_DATE=%%a"
set "LOG_DATE=!LOG_DATE:~0,8!"
set "LOG_DIR=%BASE_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\etl_%LOG_DATE%.log"

title ETL ACP DWH

echo ============================================================
echo   ETL ACP DWH
echo   %date%  %time%
echo   Log: %LOG_FILE%
echo ============================================================
echo.

:: --- Validaciones previas ---
if not exist "%PYTHON_EXE%" (
    echo [ERROR] No se encontro el entorno virtual:
    echo         %PYTHON_EXE%
    set "EXIT_CODE=1"
    goto :fin
)

"%PYTHON_EXE%" --version >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [ERROR] El ejecutable Python no responde.
    set "EXIT_CODE=1"
    goto :fin
)

if not exist "%PIPELINE_SCRIPT%" (
    echo [ERROR] No se encontro el script del pipeline:
    echo         %PIPELINE_SCRIPT%
    set "EXIT_CODE=1"
    goto :fin
)

:: --- Ejecutar pipeline y guardar log simultaneamente via PowerShell Tee-Object ---
:: Captura stdout + stderr y los duplica a consola y archivo. Mantiene el exit
:: code real de Python (sin esto, tracebacks de Python y stderr se perdian).
pushd "%ETL_DIR%"

echo. >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"
echo   ETL ACP DWH - inicio %date% %time% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

powershell -NoProfile -Command ^
    "$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; & '%PYTHON_EXE%' '%PIPELINE_SCRIPT%' %* 2>&1 | Tee-Object -FilePath '%LOG_FILE%' -Append; exit $LASTEXITCODE"
set "EXIT_CODE=!ERRORLEVEL!"

popd

:: Escribir resultado en log (la salida de Python ya aparecio en consola)
echo. >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"
echo   ETL ACP DWH - %date%  %time% >> "%LOG_FILE%"
echo   Codigo de salida: !EXIT_CODE! >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

if !EXIT_CODE! neq 0 (
    echo.
    echo [ERROR] El ETL finalizo con codigo !EXIT_CODE!.
    echo [ERROR] El ETL finalizo con codigo !EXIT_CODE!. >> "%LOG_FILE%"
    goto :fin
)

echo.
echo [OK] El ETL finalizo correctamente.
echo [OK] El ETL finalizo correctamente. >> "%LOG_FILE%"

:fin
echo.
echo Presione cualquier tecla para cerrar...
pause >nul
title %COMSPEC%
exit /b !EXIT_CODE!
