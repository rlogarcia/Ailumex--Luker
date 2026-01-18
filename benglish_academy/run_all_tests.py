#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Pruebas Automatizadas - Sprint 1
Ejecuta todas las validaciones y genera un reporte.
"""

import os
import sys
import subprocess
from datetime import datetime

# Configurar encoding para Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def print_header(title):
    """Imprime un encabezado formateado."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_test(name, passed, message=""):
    """Imprime el resultado de un test."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {name}")
    if message:
        print(f"     {message}")


def run_validation_script(script_name):
    """Ejecuta un script de validación y retorna el resultado."""
    try:
        result = subprocess.run(
            [sys.executable, script_name], capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0, result.stdout
    except Exception as e:
        return False, str(e)


def check_file_exists(filepath, description):
    """Verifica que un archivo exista."""
    exists = os.path.exists(filepath)
    print_test(
        description, exists, filepath if exists else f"No encontrado: {filepath}"
    )
    return exists


def main():
    """Ejecuta todas las pruebas."""
    base_path = os.path.dirname(os.path.abspath(__file__))

    print_header("PRUEBAS AUTOMATIZADAS - SPRINT 1")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Ruta base: {base_path}")

    results = {"total": 0, "passed": 0, "failed": 0}

    # ========================================
    # PRUEBA 1: Validación de Sintaxis Python
    # ========================================
    print_header("1. VALIDACIÓN DE SINTAXIS PYTHON")

    validate_py = os.path.join(base_path, "validate_syntax.py")
    if os.path.exists(validate_py):
        passed, output = run_validation_script(validate_py)
        results["total"] += 1
        if passed:
            results["passed"] += 1
            print_test("Sintaxis Python", True, "Todos los archivos válidos")
        else:
            results["failed"] += 1
            print_test("Sintaxis Python", False, "Errores encontrados")
            print(output)
    else:
        print_test(
            "Script de validación Python", False, "validate_syntax.py no encontrado"
        )

    # ========================================
    # PRUEBA 2: Validación de Sintaxis XML
    # ========================================
    print_header("2. VALIDACIÓN DE SINTAXIS XML")

    validate_xml = os.path.join(base_path, "validate_xml.py")
    if os.path.exists(validate_xml):
        passed, output = run_validation_script(validate_xml)
        results["total"] += 1
        if passed:
            results["passed"] += 1
            print_test("Sintaxis XML", True, "Todos los archivos válidos")
        else:
            results["failed"] += 1
            print_test("Sintaxis XML", False, "Errores encontrados")
            print(output)
    else:
        print_test("Script de validación XML", False, "validate_xml.py no encontrado")

    # ========================================
    # PRUEBA 3: Verificación de Archivos Core
    # ========================================
    print_header("3. VERIFICACIÓN DE ARCHIVOS CORE")

    core_files = [
        ("models/crm_lead.py", "Modelo CRM Lead"),
        ("models/hr_employee.py", "Modelo HR Employee"),
        ("models/__init__.py", "Init de modelos"),
        ("__manifest__.py", "Manifest del módulo"),
    ]

    for filepath, description in core_files:
        full_path = os.path.join(base_path, filepath)
        results["total"] += 1
        if check_file_exists(full_path, description):
            results["passed"] += 1
        else:
            results["failed"] += 1

    # ========================================
    # PRUEBA 4: Verificación de Vistas
    # ========================================
    print_header("4. VERIFICACIÓN DE VISTAS")

    view_files = [
        ("views/hr_employee_sales_views.xml", "Vistas HR Sales"),
        ("views/crm_lead_views.xml", "Vistas CRM Lead"),
    ]

    for filepath, description in view_files:
        full_path = os.path.join(base_path, filepath)
        results["total"] += 1
        if check_file_exists(full_path, description):
            results["passed"] += 1
        else:
            results["failed"] += 1

    # ========================================
    # PRUEBA 5: Verificación de Datos
    # ========================================
    print_header("5. VERIFICACIÓN DE DATOS")

    data_files = [
        ("data/crm_pipelines_data.xml", "Pipelines CRM"),
        ("data/crm_automations_data.xml", "Automatizaciones"),
    ]

    for filepath, description in data_files:
        full_path = os.path.join(base_path, filepath)
        results["total"] += 1
        if check_file_exists(full_path, description):
            results["passed"] += 1
        else:
            results["failed"] += 1

    # ========================================
    # PRUEBA 6: Verificación de Seguridad
    # ========================================
    print_header("6. VERIFICACIÓN DE SEGURIDAD")

    security_files = [
        ("security/crm_security.xml", "Seguridad CRM"),
        ("security/ir.model.access.csv", "Access Rights"),
    ]

    for filepath, description in security_files:
        full_path = os.path.join(base_path, filepath)
        results["total"] += 1
        if check_file_exists(full_path, description):
            results["passed"] += 1
        else:
            results["failed"] += 1

    # ========================================
    # PRUEBA 7: Verificación de Documentación
    # ========================================
    print_header("7. VERIFICACIÓN DE DOCUMENTACIÓN")

    doc_files = [
        ("docs/API_REST_TECHNICAL_DOCUMENTATION.md", "Doc API REST"),
        ("docs/CONFIGURACION_ENTORNO_WEBHOOKS.md", "Doc Configuración"),
        ("docs/SPRINT_1_RESUMEN_IMPLEMENTACION.md", "Resumen Sprint 1"),
        ("docs/CHECKLIST_INSTALACION.md", "Checklist Instalación"),
        ("docs/SPRINT_1_EXECUTIVE_SUMMARY.md", "Resumen Ejecutivo"),
        ("docs/GUIA_PRUEBAS_COMPLETAS.md", "Guía de Pruebas"),
    ]

    for filepath, description in doc_files:
        full_path = os.path.join(base_path, filepath)
        results["total"] += 1
        if check_file_exists(full_path, description):
            results["passed"] += 1
        else:
            results["failed"] += 1

    # ========================================
    # PRUEBA 8: Verificación de Manifest
    # ========================================
    print_header("8. VERIFICACIÓN DE MANIFEST")

    manifest_path = os.path.join(base_path, "__manifest__.py")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            content = f.read()

        checks = [
            ('"crm"' in content, "Dependencia CRM presente"),
            ('"hr"' in content, "Dependencia HR presente"),
            ("crm_pipelines_data.xml" in content, "Datos de pipelines en manifest"),
            (
                "crm_automations_data.xml" in content,
                "Datos de automatizaciones en manifest",
            ),
            ("crm_security.xml" in content, "Seguridad CRM en manifest"),
            ("hr_employee_sales_views.xml" in content, "Vistas HR sales en manifest"),
            ("crm_lead_views.xml" in content, "Vistas CRM lead en manifest"),
        ]

        for check, description in checks:
            results["total"] += 1
            print_test(description, check)
            if check:
                results["passed"] += 1
            else:
                results["failed"] += 1
    else:
        print_test("Archivo manifest", False, "No encontrado")
        results["total"] += 1
        results["failed"] += 1

    # ========================================
    # RESUMEN FINAL
    # ========================================
    print_header("RESUMEN DE PRUEBAS")

    success_rate = (
        (results["passed"] / results["total"] * 100) if results["total"] > 0 else 0
    )

    print(f"Total de pruebas: {results['total']}")
    print(f"✅ Exitosas: {results['passed']}")
    print(f"❌ Fallidas: {results['failed']}")
    print(f"Tasa de éxito: {success_rate:.1f}%")

    print()
    if results["failed"] == 0:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
        print("✅ El módulo está listo para instalación en Odoo")
        print()
        print("Siguiente paso:")
        print(
            "  python odoo-bin -c odoo.conf -d TU_BASE_DATOS -u benglish_academy --stop-after-init"
        )
        return 0
    else:
        print("⚠️  ALGUNAS PRUEBAS FALLARON")
        print("Por favor, revisa los errores arriba antes de instalar en Odoo")
        return 1


if __name__ == "__main__":
    sys.exit(main())
