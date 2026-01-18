# -*- coding: utf-8 -*-
"""
Script para reconstruir correctamente el session_tracking.
Elimina registros incorrectos y crea solo los del plan del estudiante.

Uso desde Odoo shell:
    cd "C:\Program Files\Odoo 18.0.20251128\python"
    .\python.exe ..\server\odoo-bin shell -c ..\server\odoo.conf -d benglish_db

    exec(open('d:/AiLumex/Ailumex--Be/benglish_academy/scripts/rebuild_session_tracking.py').read())
"""


def rebuild_session_tracking():
    """Reconstruye el tracking eliminando registros incorrectos"""

    Student = env["benglish.student"]
    Tracking = env["benglish.subject.session.tracking"]

    # Buscar todos los estudiantes con plan
    students = Student.search([("plan_id", "!=", False)])

    print(f"\n{'='*60}")
    print(f"Encontrados {len(students)} estudiantes con plan asignado")
    print(f"{'='*60}\n")

    total_deleted = 0
    total_created = 0

    for student in students:
        print(f"\n{'─'*60}")
        print(f"Estudiante: {student.name}")
        print(f"Programa: {student.program_id.name if student.program_id else 'N/A'}")
        print(f"Plan: {student.plan_id.name if student.plan_id else 'N/A'}")
        print(f"{'─'*60}")

        # Obtener asignaturas correctas del estudiante
        correct_subject_ids = student.subject_ids.ids
        print(f"Asignaturas correctas del plan: {len(correct_subject_ids)}")

        # Buscar tracking actual del estudiante
        current_tracking = Tracking.search([("student_id", "=", student.id)])
        current_subject_ids = current_tracking.mapped("subject_id").ids
        print(f"Tracking actual: {len(current_tracking)} registros")

        # Identificar registros incorrectos (de asignaturas que no están en su plan)
        incorrect_ids = set(current_subject_ids) - set(correct_subject_ids)
        if incorrect_ids:
            incorrect_tracking = Tracking.search(
                [
                    ("student_id", "=", student.id),
                    ("subject_id", "in", list(incorrect_ids)),
                ]
            )
            print(f"  ❌ Eliminando {len(incorrect_tracking)} registros incorrectos...")
            incorrect_tracking.unlink()
            total_deleted += len(incorrect_tracking)

        # Identificar asignaturas faltantes
        missing_ids = set(correct_subject_ids) - set(current_subject_ids)
        if missing_ids:
            print(f"  ➕ Creando {len(missing_ids)} registros faltantes...")
            for subject_id in missing_ids:
                subject = env["benglish.subject"].browse(subject_id)
                Tracking.create(
                    {
                        "student_id": student.id,
                        "subject_id": subject_id,
                        "phase_id": subject.phase_id.id,
                        "level_id": subject.level_id.id,
                        "state": "pending",
                    }
                )
                total_created += 1

        # Verificar distribución por fase
        final_tracking = Tracking.search([("student_id", "=", student.id)])
        basic_count = len(final_tracking.filtered(lambda t: t.phase_id.name == "Basic"))
        inter_count = len(
            final_tracking.filtered(lambda t: t.phase_id.name == "Intermediate")
        )
        adv_count = len(
            final_tracking.filtered(lambda t: t.phase_id.name == "Advanced")
        )

        print(f"\n  Distribución por fase:")
        print(f"    📘 Basic: {basic_count}")
        print(f"    📗 Intermediate: {inter_count}")
        print(f"    📕 Advanced: {adv_count}")
        print(f"    Total: {len(final_tracking)}")

    print(f"\n{'='*60}")
    print(f"RESUMEN:")
    print(f"  Eliminados: {total_deleted} registros incorrectos")
    print(f"  Creados: {total_created} registros faltantes")
    print(f"{'='*60}\n")

    return total_deleted, total_created


if __name__ == "__main__":
    deleted, created = rebuild_session_tracking()
