@echo off
REM ===============================================
REM Script de Actualización del Módulo CRM
REM ===============================================

echo ==========================================
echo   ACTUALIZACION MODULO CRM IMPORT LEADS
echo ==========================================
echo.

set ODOO_PATH=c:\Program Files\Odoo 18.0.20251128
set PYTHON_EXE=%ODOO_PATH%\python\python.exe
set ODOO_BIN=%ODOO_PATH%\server\odoo-bin
set ODOO_CONF=%ODOO_PATH%\server\odoo.conf
set DATABASE=ailumex_be_crm
set MODULE=crm_import_leads

echo Configuracion:
echo   Base de datos: %DATABASE%
echo   Modulo: %MODULE%
echo.

echo PASO 1: Deteniendo procesos Python...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM python3.13.exe >nul 2>&1
timeout /t 3 >nul

echo PASO 2: Actualizando modulo %MODULE%...
echo.

"%PYTHON_EXE%" "%ODOO_BIN%" -c "%ODOO_CONF%" -d %DATABASE% -u %MODULE% --stop-after-init

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =========================================
    echo   ACTUALIZACION COMPLETADA CON EXITO
    echo =========================================
    echo.
    echo Los campos de evaluacion ya estan disponibles.
    echo Reinicie Odoo y recargue la pagina en el navegador.
) else (
    echo.
    echo =========================================
    echo   ERROR EN LA ACTUALIZACION
    echo =========================================
    echo.
    echo Revise el log de Odoo para mas detalles.
)

echo.
pause
