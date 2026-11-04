@echo off
chcp 65001 > nul
title ACP Platform - Iniciando...

:: El lanzador selecciona .venv o conserva el Python virtual activo.
python "%~dp0acp_start.py" %*
set "EXIT_CODE=%ERRORLEVEL%"

:: Si Python falla por alguna razon, mostrar error
if not "%EXIT_CODE%"=="0" (
    echo.
    echo  [ERROR] El gestor de servicios cerro con error.
    echo  Primero instala con: python instalar.py
    echo  Revisa los logs en:  %~dp0backend\logs\
    pause
)
exit /b %EXIT_CODE%
