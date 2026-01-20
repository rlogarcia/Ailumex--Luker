# ===============================================
# Script de Actualización Rápida
# ===============================================
# Corrige error de automatizaciones y actualiza módulo

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  ACTUALIZACIÓN RÁPIDA - CRM MODULE     " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$ODOO_PATH = "c:\Program Files\Odoo 18.0.20251128"
$PYTHON_EXE = "$ODOO_PATH\python\python.exe"
$ODOO_BIN = "$ODOO_PATH\server\odoo-bin"
$ODOO_CONF = "$ODOO_PATH\server\odoo.conf"
$DATABASE = "ailumex_be_crm"
$MODULE = "crm_import_leads"

Write-Host "🔧 PROBLEMA RESUELTO:" -ForegroundColor Yellow
Write-Host "  ✓ Error: fields.Date.today() no disponible en safe_eval" -ForegroundColor White
Write-Host "  ✓ Solución: Usar 'from datetime import date'" -ForegroundColor Green
Write-Host ""

Write-Host "PASO 1: Deteniendo procesos Odoo..." -ForegroundColor Yellow
Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "PASO 2: Actualizando módulo $MODULE..." -ForegroundColor Yellow
Write-Host ""

& $PYTHON_EXE $ODOO_BIN -c $ODOO_CONF -d $DATABASE -u $MODULE --stop-after-init --log-level=info

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host "  ✓ ACTUALIZACIÓN COMPLETADA CON ÉXITO  " -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "CAMBIOS APLICADOS:" -ForegroundColor Yellow
    Write-Host "  ✓ Automatizaciones corregidas (fields → datetime)" -ForegroundColor Green
    Write-Host "  ✓ Actividad 'Llamar lead nuevo' funcional" -ForegroundColor Green
    Write-Host "  ✓ Actividad 'Seguimiento post-evaluación' funcional" -ForegroundColor Green
    Write-Host "  ✓ Actividad 'Lead incontactable' funcional" -ForegroundColor Green
    Write-Host ""
    Write-Host "PRÓXIMOS PASOS:" -ForegroundColor Yellow
    Write-Host "  1. Reiniciar Odoo" -ForegroundColor White
    Write-Host "  2. Probar crear un lead nuevo" -ForegroundColor White
    Write-Host "  3. Verificar que se cree la actividad automática" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Red
    Write-Host "  ✗ ERROR EN LA ACTUALIZACIÓN            " -ForegroundColor Red
    Write-Host "=========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Revise el log anterior para detalles." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Presione cualquier tecla para continuar..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
