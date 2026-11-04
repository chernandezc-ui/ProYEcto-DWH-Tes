@echo off
chcp 65001 > nul
title ACP Platform - Iniciando...

set BASE=%~dp0
set PY=%BASE%.venv\Scripts\python.exe

:: Verificar que exista python del venv
if not exist "%PY%" (
    echo.
    echo  [ERROR] No se encontro el entorno virtual.
    echo  Ruta esperada: %PY%
    echo.
    echo  Pasos para crear el entorno:
    echo    1. Abrir una terminal en esta carpeta
    echo    2. Ejecutar:  python -m venv .venv
    echo    3. Ejecutar:  .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: Lanzar el gestor Python con la ventana visible
"%PY%" "%BASE%acp_start.py"

:: Si Python falla por alguna razon, mostrar error
if errorlevel 1 (
    echo.
    echo  [ERROR] El gestor de servicios cerro con error.
    echo  Revisa los logs en:  %BASE%backend\logs\
    pause
)
