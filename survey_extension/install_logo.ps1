# Script para verificar el logo de Fundacion Luker
# Ejecutar en PowerShell desde la carpeta del modulo

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host " Verificador de Logo Fundacion Luker" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

$logoPath = ".\static\description\fundacion_luker_logo.png"
$svgPath = ".\static\description\fundacion_luker_logo.svg"

Write-Host "Verificando archivos del logo..." -ForegroundColor White
Write-Host ""

# Verificar PNG
if (Test-Path $logoPath) {
    $fileSize = (Get-Item $logoPath).Length / 1KB
    Write-Host "[OK] Logo PNG encontrado" -ForegroundColor Green
    Write-Host "    Ubicacion: $logoPath" -ForegroundColor Gray
    Write-Host "    Tamano: $([math]::Round($fileSize, 2)) KB" -ForegroundColor Gray
    
    if ($fileSize -gt 500) {
        Write-Host "    [!] Advertencia: El logo es grande. Considera optimizarlo." -ForegroundColor Yellow
    } else {
        Write-Host "    [OK] Tamano optimo para PDF" -ForegroundColor Green
    }
} else {
    Write-Host "[X] Logo PNG no encontrado" -ForegroundColor Red
}

Write-Host ""

# Verificar SVG
if (Test-Path $svgPath) {
    $fileSizeSvg = (Get-Item $svgPath).Length / 1KB
    Write-Host "[OK] Logo SVG encontrado" -ForegroundColor Green
    Write-Host "    Ubicacion: $svgPath" -ForegroundColor Gray
    Write-Host "    Tamano: $([math]::Round($fileSizeSvg, 2)) KB" -ForegroundColor Gray
} else {
    Write-Host "[X] Logo SVG no encontrado" -ForegroundColor Red
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan

# Resumen
if ((Test-Path $logoPath) -and (Test-Path $svgPath)) {
    Write-Host "Estado: OK - AMBOS LOGOS DISPONIBLES" -ForegroundColor Green
    Write-Host "Los reportes usaran el PNG para mejor calidad" -ForegroundColor Green
} elseif (Test-Path $logoPath) {
    Write-Host "Estado: OK - LOGO PNG DISPONIBLE" -ForegroundColor Green
} elseif (Test-Path $svgPath) {
    Write-Host "Estado: ADVERTENCIA - SOLO SVG DISPONIBLE" -ForegroundColor Yellow
} else {
    Write-Host "Estado: ERROR - SIN LOGOS" -ForegroundColor Red
}

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
