# ===============================================
# Script de Actualización del Módulo CRM
# ===============================================
# Este script actualiza el módulo crm_import_leads
# en la base de datos de Odoo
# ===============================================

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  ACTUALIZACIÓN MÓDULO CRM IMPORT LEADS  " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Configuración
$ODOO_PATH = "c:\Program Files\Odoo 18.0.20251128"
$PYTHON_EXE = "$ODOO_PATH\python\python.exe"
$ODOO_BIN = "$ODOO_PATH\server\odoo-bin"
$ODOO_CONF = "$ODOO_PATH\server\odoo.conf"
$DATABASE = "ailumex_be_crm"
$MODULE = "crm_import_leads"

Write-Host "Configuración:" -ForegroundColor Yellow
Write-Host "  Base de datos: $DATABASE" -ForegroundColor White
Write-Host "  Módulo: $MODULE" -ForegroundColor White
Write-Host ""

# Verificar que los archivos existan
if (-not (Test-Path $PYTHON_EXE)) {
    Write-Host "ERROR: No se encuentra el ejecutable de Python en: $PYTHON_EXE" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $ODOO_BIN)) {
    Write-Host "ERROR: No se encuentra odoo-bin en: $ODOO_BIN" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $ODOO_CONF)) {
    Write-Host "ERROR: No se encuentra odoo.conf en: $ODOO_CONF" -ForegroundColor Red
    exit 1
}

Write-Host "PASO 1: Deteniendo servicios de Odoo (si existen)..." -ForegroundColor Yellow
Get-Process | Where-Object {$_.ProcessName -like "*odoo*"} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

Write-Host "PASO 2: Actualizando módulo $MODULE..." -ForegroundColor Yellow
Write-Host ""

$arguments = @(
    $ODOO_BIN,
    "-c", $ODOO_CONF,
    "-d", $DATABASE,
    "-u", $MODULE,
    "--stop-after-init",
    "--log-level=info"
)

Write-Host "Ejecutando comando:" -ForegroundColor Cyan
Write-Host "  $PYTHON_EXE $($arguments -join ' ')" -ForegroundColor Gray
Write-Host ""

# Ejecutar actualización
& $PYTHON_EXE $arguments

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host "  ✓ ACTUALIZACIÓN COMPLETADA CON ÉXITO  " -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Cambios aplicados:" -ForegroundColor Yellow
    Write-Host "  ✓ HU-CRM-01: Campos HR jerárquicos (es_asesor_comercial, etc.)" -ForegroundColor White
    Write-Host "  ✓ HU-CRM-03/04: Pipelines Marketing y Comercial" -ForegroundColor White
    Write-Host "  ✓ HU-CRM-05: Campos personalizados corregidos" -ForegroundColor White
    Write-Host "  ✓ HU-CRM-06: Bloqueo de fuente/campaña implementado" -ForegroundColor White
    Write-Host "  ✓ HU-CRM-07: Agenda de evaluación completa" -ForegroundColor White
    Write-Host "  ✓ HU-CRM-08: Actividades automáticas configuradas" -ForegroundColor White
    Write-Host "  ✓ HU-CRM-09: Seguridad operativa (record rules)" -ForegroundColor White
    Write-Host "  ✓ HU-CRM-10: Vistas filtradas implementadas" -ForegroundColor White
    Write-Host ""
    Write-Host "PRÓXIMOS PASOS:" -ForegroundColor Cyan
    Write-Host "1. Reiniciar el servicio de Odoo" -ForegroundColor White
    Write-Host "2. Ingresar a Odoo y verificar el módulo" -ForegroundColor White
    Write-Host "3. Configurar roles comerciales en HR > Empleados" -ForegroundColor White
    Write-Host "4. Asignar grupos de seguridad a usuarios" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Red
    Write-Host "  ✗ ERROR EN LA ACTUALIZACIÓN           " -ForegroundColor Red
    Write-Host "=========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Revise el log anterior para identificar el problema." -ForegroundColor Yellow
    Write-Host "Errores comunes:" -ForegroundColor Yellow
    Write-Host "  - Módulo ox_res_partner_ext_co no instalado" -ForegroundColor White
    Write-Host "  - Base de datos bloqueada por otro proceso" -ForegroundColor White
    Write-Host "  - Permisos insuficientes" -ForegroundColor White
    Write-Host ""
}

Write-Host "Presione cualquier tecla para continuar..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
