#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para verificar la conexión entre sesiones y historial académico.
Ejecutar desde Odoo shell o como script independiente.
"""


def diagnose_session_history_connection(env):
    """
    Diagnóstico de la conexión entre sesiones académicas y historial.
    """
    print("\n" + "=" * 80)
    print("DIAGNÓSTICO: SESIONES → HISTORIAL ACADÉMICO")
    print("=" * 80 + "\n")

    # 1. Verificar sesiones en estado 'done'
    Session = env["benglish.academic.session"].sudo()
    done_sessions = Session.search(
        [("state", "=", "done")], limit=10, order="date desc"
    )

    print(f"1️⃣  SESIONES EN ESTADO 'DONE' (últimas 10):")
    print(f"   Total encontradas: {len(done_sessions)}")

    if done_sessions:
        for session in done_sessions:
            print(f"\n   📅 Sesión ID: {session.id}")
            print(
                f"      - Asignatura: {session.subject_id.name if session.subject_id else 'N/A'}"
            )
            print(f"      - Fecha: {session.date}")
            print(f"      - Estado: {session.state}")
            print(f"      - Inscripciones: {len(session.enrollment_ids)}")

            # Buscar historial para esta sesión
            History = env["benglish.academic.history"].sudo()
            history_records = History.search([("session_id", "=", session.id)])
            print(f"      - Registros en historial: {len(history_records)}")

            if history_records:
                attended = len(
                    history_records.filtered(
                        lambda h: h.attendance_status == "attended"
                    )
                )
                absent = len(
                    history_records.filtered(lambda h: h.attendance_status == "absent")
                )
                pending = len(
                    history_records.filtered(lambda h: h.attendance_status == "pending")
                )
                print(f"        ✓ Asistieron: {attended}")
                print(f"        ✗ Ausentes: {absent}")
                print(f"        ⏳ Pendientes: {pending}")
            else:
                print(f"        ⚠️  NO HAY REGISTROS EN HISTORIAL (ERROR)")
    else:
        print("   ⚠️  No se encontraron sesiones en estado 'done'")

    # 2. Verificar inscripciones con asistencia marcada
    print(f"\n\n2️⃣  INSCRIPCIONES CON ASISTENCIA MARCADA:")
    Enrollment = env["benglish.session.enrollment"].sudo()
    marked_enrollments = Enrollment.search(
        [("state", "in", ["attended", "absent"])], limit=10, order="write_date desc"
    )

    print(f"   Total encontradas (últimas 10): {len(marked_enrollments)}")

    if marked_enrollments:
        for enroll in marked_enrollments:
            print(f"\n   📝 Enrollment ID: {enroll.id}")
            print(
                f"      - Estudiante: {enroll.student_id.name if enroll.student_id else 'N/A'}"
            )
            print(
                f"      - Sesión ID: {enroll.session_id.id if enroll.session_id else 'N/A'}"
            )
            print(
                f"      - Estado sesión: {enroll.session_id.state if enroll.session_id else 'N/A'}"
            )
            print(f"      - Estado enrollment: {enroll.state}")

            # Buscar historial
            History = env["benglish.academic.history"].sudo()
            history = History.search(
                [
                    ("student_id", "=", enroll.student_id.id),
                    ("session_id", "=", enroll.session_id.id),
                ],
                limit=1,
            )

            if history:
                print(f"      - ✅ Historial encontrado: ID {history.id}")
                print(f"        - Attendance status: {history.attendance_status}")
            else:
                print(f"      - ❌ NO HAY HISTORIAL (Problema de sincronización)")
    else:
        print("   ℹ️  No se encontraron inscripciones con asistencia marcada")

    # 3. Verificar líneas de agenda del portal que referencian sesiones 'done'
    print(f"\n\n3️⃣  LÍNEAS DE AGENDA DEL PORTAL (sesiones dictadas):")
    PlanLine = env["portal.student.weekly.plan.line"].sudo()

    if done_sessions:
        lines_with_done_sessions = PlanLine.search(
            [("session_id", "in", done_sessions.ids)]
        )

        print(f"   Total líneas encontradas: {len(lines_with_done_sessions)}")

        if lines_with_done_sessions:
            print(
                f"   ⚠️  PROBLEMA ENCONTRADO: Hay {len(lines_with_done_sessions)} líneas de agenda"
            )
            print(
                f"       que referencian sesiones ya dictadas (deberían haberse eliminado)"
            )

            for line in lines_with_done_sessions[:5]:  # Mostrar solo las primeras 5
                print(f"\n      - Línea ID: {line.id}")
                print(
                    f"        - Estudiante: {line.plan_id.student_id.name if line.plan_id and line.plan_id.student_id else 'N/A'}"
                )
                print(
                    f"        - Sesión: {line.session_id.id} (estado: {line.session_id.state})"
                )
                print(f"        - Fecha: {line.date}")
        else:
            print(f"   ✅ Correcto: No hay líneas de agenda con sesiones dictadas")

    # 4. Estadísticas generales de historial
    print(f"\n\n4️⃣  ESTADÍSTICAS GENERALES DEL HISTORIAL ACADÉMICO:")
    History = env["benglish.academic.history"].sudo()

    total_history = History.search_count([])
    attended_count = History.search_count([("attendance_status", "=", "attended")])
    absent_count = History.search_count([("attendance_status", "=", "absent")])
    pending_count = History.search_count([("attendance_status", "=", "pending")])

    print(f"   Total registros: {total_history}")
    print(f"   - Asistieron: {attended_count}")
    print(f"   - Ausentes: {absent_count}")
    print(f"   - Pendientes: {pending_count}")

    # 5. Verificar estudiantes con historial
    print(f"\n\n5️⃣  ESTUDIANTES CON HISTORIAL (últimos 5):")
    students_with_history = History.search([]).mapped("student_id")[:5]

    for student in students_with_history:
        student_history = History.search([("student_id", "=", student.id)])
        print(f"\n   👤 {student.name} (ID: {student.id})")
        print(f"      - Total clases en historial: {len(student_history)}")
        print(
            f"      - Asistidas: {len(student_history.filtered(lambda h: h.attendance_status == 'attended'))}"
        )
        print(
            f"      - Ausentes: {len(student_history.filtered(lambda h: h.attendance_status == 'absent'))}"
        )
        print(
            f"      - Pendientes: {len(student_history.filtered(lambda h: h.attendance_status == 'pending'))}"
        )

    print("\n" + "=" * 80)
    print("FIN DEL DIAGNÓSTICO")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    # Para ejecutar desde Odoo shell
    import odoo
    from odoo import api, SUPERUSER_ID

    # Configurar la base de datos
    db_name = "AiLumex"  # Cambiar por el nombre de tu base de datos

    with api.Environment.manage():
        registry = odoo.registry(db_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            diagnose_session_history_connection(env)
