#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para poblar el tracking de sesiones para estudiantes existentes con planes asignados.
Ejecutar desde Odoo shell:
    python odoo-bin shell -c odoo.conf -d odoo18
    >>> exec(open('d:/AiLumex/Ailumex--Be/benglish_academy/scripts/populate_session_tracking.py').read())
"""


def populate_tracking():
    """Crea registros de tracking para todos los estudiantes con plan asignado"""

    Student = env["benglish.student"]
    Tracking = env["benglish.subject.session.tracking"]

    # Buscar estudiantes con plan asignado
    students = Student.search([("plan_id", "!=", False)])

    print(f"\n{'='*80}")
    print(f"POBLANDO TRACKING DE SESIONES")
    print(f"{'='*80}\n")
    print(f"Estudiantes con plan asignado: {len(students)}")

    total_created = 0

    for student in students:
        print(f"\n📚 Procesando: {student.name} (Plan: {student.plan_id.name})")

        # Verificar si ya tiene tracking
        existing = Tracking.search([("student_id", "=", student.id)])
        if existing:
            print(f"   ✓ Ya tiene {len(existing)} registros de tracking")
            continue

        # Crear tracking para todas las asignaturas del plan
        created = Tracking.create_tracking_for_student(student.id)
        total_created += len(created)

        print(f"   ✅ Creados {len(created)} registros de tracking")

        # Mostrar resumen por fase
        for phase_name in ["Basic", "Intermediate", "Advanced"]:
            count = len(created.filtered(lambda t: t.phase_id.name == phase_name))
            if count > 0:
                print(f"      - {phase_name}: {count} asignaturas")

    print(f"\n{'='*80}")
    print(f"RESUMEN")
    print(f"{'='*80}")
    print(f"Total de registros creados: {total_created}")
    print(f"Estudiantes procesados: {len(students)}")
    print(f"\n✅ Proceso completado exitosamente\n")


# Ejecutar si se carga el script
if __name__ == "__main__" or "env" in dir():
    populate_tracking()
