#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Diagnóstico: Problema de Matrículas Activas no Visibles
Estudiante: Julian Noreña (MAT-2026-00002)

PROBLEMA DETECTADO:
===================
El campo active_enrollment_ids en benglish.student tenía un dominio incorrecto:
    domain=[("state", "in", ["enrolled", "in_progress"])]

Este dominio NO incluía el estado "active", que es el estado principal actual
para matrículas en curso según enrollment.py líneas 403-404:
    ("active", "Activa"),  # Estado principal de matrícula en curso

SOLUCIÓN APLICADA:
==================
Se actualizó el dominio para incluir "active":
    domain=[("state", "in", ["active", "enrolled", "in_progress"])]

Este script verifica que la corrección funcione correctamente.
"""

import logging
import sys

_logger = logging.getLogger(__name__)


def diagnose_student_enrollments(env, student_code="Julian Noreña"):
    """
    Diagnostica las matrículas de un estudiante específico.

    Args:
        env: Odoo environment
        student_code: Código o nombre del estudiante a diagnosticar
    """
    Student = env["benglish.student"]
    Enrollment = env["benglish.enrollment"]

    print("\n" + "=" * 80)
    print(f"🔍 DIAGNÓSTICO DE MATRÍCULAS - {student_code}")
    print("=" * 80)

    # Buscar estudiante por código o nombre
    student = Student.search(
        ["|", ("code", "=", student_code), ("name", "ilike", student_code)], limit=1
    )

    if not student:
        print(f"❌ ERROR: No se encontró estudiante con código/nombre '{student_code}'")
        return False

    print(
        f"\n✅ Estudiante encontrado: {student.name} (ID: {student.id}, Código: {student.code})"
    )

    # 1. Obtener TODAS las matrículas del estudiante
    all_enrollments = Enrollment.search([("student_id", "=", student.id)])

    print(f"\n📋 TODAS LAS MATRÍCULAS ({len(all_enrollments)}):")
    print("-" * 80)
    for enrollment in all_enrollments:
        print(
            f"  • {enrollment.code} | Estado: {enrollment.state} | "
            f"Fecha: {enrollment.enrollment_date} | "
            f"Plan: {enrollment.plan_id.name if enrollment.plan_id else 'N/A'}"
        )

    # 2. Verificar matrículas con cada estado posible
    print(f"\n🔎 ANÁLISIS POR ESTADO:")
    print("-" * 80)

    states_to_check = [
        "active",
        "enrolled",
        "in_progress",
        "draft",
        "pending",
        "suspended",
        "completed",
        "finished",
        "withdrawn",
        "cancelled",
    ]

    for state in states_to_check:
        count = Enrollment.search_count(
            [("student_id", "=", student.id), ("state", "=", state)]
        )
        icon = "✅" if count > 0 else "⚪"
        print(f"  {icon} {state:15s}: {count} matrícula(s)")

    # 3. Verificar el campo active_enrollment_ids (DESPUÉS de la corrección)
    active_enrollments_field = student.active_enrollment_ids

    print(f"\n🎯 CAMPO active_enrollment_ids (con corrección):")
    print("-" * 80)
    print(f"  • Total: {len(active_enrollments_field)} matrícula(s)")
    for enrollment in active_enrollments_field:
        print(f"    ✓ {enrollment.code} | Estado: {enrollment.state}")

    # 4. Comparar con búsqueda manual usando SOLO estados legacy
    legacy_enrollments = Enrollment.search(
        [("student_id", "=", student.id), ("state", "in", ["enrolled", "in_progress"])]
    )

    print(f"\n⚠️  BÚSQUEDA CON ESTADOS LEGACY SOLAMENTE (enrolled, in_progress):")
    print("-" * 80)
    print(f"  • Total: {len(legacy_enrollments)} matrícula(s)")
    if legacy_enrollments:
        for enrollment in legacy_enrollments:
            print(f"    ✓ {enrollment.code} | Estado: {enrollment.state}")
    else:
        print("    ❌ NO SE ENCONTRARON MATRÍCULAS (este era el problema)")

    # 5. Comparar con búsqueda incluyendo "active"
    fixed_enrollments = Enrollment.search(
        [
            ("student_id", "=", student.id),
            ("state", "in", ["active", "enrolled", "in_progress"]),
        ]
    )

    print(f"\n✅ BÚSQUEDA CON CORRECCIÓN (active, enrolled, in_progress):")
    print("-" * 80)
    print(f"  • Total: {len(fixed_enrollments)} matrícula(s)")
    for enrollment in fixed_enrollments:
        print(f"    ✓ {enrollment.code} | Estado: {enrollment.state}")

    # 6. Verificar información académica actual
    print(f"\n📚 INFORMACIÓN ACADÉMICA ACTUAL:")
    print("-" * 80)
    print(f"  • Programa: {student.program_id.name if student.program_id else 'N/A'}")
    print(f"  • Plan: {student.plan_id.name if student.plan_id else 'N/A'}")
    print(
        f"  • Fase actual: {student.current_phase_id.name if student.current_phase_id else 'N/A'}"
    )
    print(
        f"  • Nivel actual: {student.current_level_id.name if student.current_level_id else 'N/A'}"
    )
    print(
        f"  • Asignatura actual: {student.current_subject_id.name if student.current_subject_id else 'N/A'}"
    )

    # 7. Resumen del problema
    print(f"\n" + "=" * 80)
    print("📊 RESUMEN DEL DIAGNÓSTICO:")
    print("=" * 80)

    has_active_state = (
        Enrollment.search_count(
            [("student_id", "=", student.id), ("state", "=", "active")]
        )
        > 0
    )

    has_legacy_states = len(legacy_enrollments) > 0

    if has_active_state and not has_legacy_states:
        print("✅ PROBLEMA CONFIRMADO Y CORREGIDO:")
        print("   • El estudiante tiene matrícula(s) con estado 'active'")
        print("   • El dominio anterior (enrolled, in_progress) NO las encontraba")
        print(
            "   • El dominio corregido (active, enrolled, in_progress) SÍ las encuentra"
        )
        print("   • El historial académico ahora debería mostrarse correctamente")
    elif has_legacy_states:
        print("ℹ️  Este estudiante usa estados legacy (enrolled/in_progress)")
        print("   • La corrección es compatible con ambos esquemas")
    else:
        print("⚠️  No se encontraron matrículas activas con ningún estado")

    print("\n" + "=" * 80 + "\n")

    return True


if __name__ == "__main__":
    # Este script debe ejecutarse desde Odoo shell:
    # python odoo-bin shell -d nombre_db -c odoo.conf
    # >>> exec(open('benglish_academy/diagnose_julian_enrollment.py').read())
    # >>> diagnose_student_enrollments(env, "Julian Noreña")

    print(
        """
    ⚠️  Este script debe ejecutarse desde Odoo shell:
    
    Opción 1 - Desde el directorio de Odoo:
        python odoo-bin shell -d nombre_db -c odoo.conf
        >>> exec(open('addons/benglish_academy/diagnose_julian_enrollment.py').read())
        >>> diagnose_student_enrollments(env, "Julian Noreña")
    
    Opción 2 - Buscar por código de estudiante:
        >>> diagnose_student_enrollments(env, "EST-2026-001")
    """
    )
