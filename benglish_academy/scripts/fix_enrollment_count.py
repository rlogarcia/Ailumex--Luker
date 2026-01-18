#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para recalcular el contador de matrículas activas
Ejecutar desde Odoo shell:
    odoo-bin shell -d nombre_db -c odoo.conf
    exec(open('scripts/fix_enrollment_count.py').read())
"""

# Obtener todos los estudiantes
students = env["benglish.student"].search([])

print(f"Recalculando contador de matrículas para {len(students)} estudiantes...")

fixed = 0
for student in students:
    # Forzar recálculo del campo computado
    student._compute_enrollment_statistics()

    # Verificar
    enrollments = student.enrollment_ids
    active_count = len(
        enrollments.filtered(lambda e: e.state in ["enrolled", "in_progress"])
    )

    if student.active_enrollments != active_count:
        print(
            f"INCONSISTENCIA - {student.code}: DB={student.active_enrollments}, Real={active_count}"
        )
        student.active_enrollments = active_count
        fixed += 1
    elif active_count > 0:
        print(f"OK - {student.code}: {active_count} matrícula(s) activa(s)")

print(f"\n✅ Proceso completado: {fixed} estudiantes corregidos")
