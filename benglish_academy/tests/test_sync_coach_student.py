# -*- coding: utf-8 -*-
"""
Tests para validar la sincronización Portal Coach → Portal Student
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class TestSyncCoachStudent(TransactionCase):
    """
    Test suite para validar la sincronización automática de asistencias
    desde Portal Coach hacia Portal Student a través del historial académico.
    """

    def setUp(self):
        super(TestSyncCoachStudent, self).setUp()

        # Crear datos de prueba
        self.program = self.env["benglish.program"].create({
            "name": "Benglish Test",
            "code": "BT",
        })

        self.level = self.env["benglish.level"].create({
            "name": "Basic 1",
            "code": "B1",
            "program_id": self.program.id,
        })

        self.subject = self.env["benglish.subject"].create({
            "name": "BCheck 1",
            "code": "BC1",
            "level_id": self.level.id,
            "subject_category": "bcheck",
        })

        self.campus = self.env["benglish.campus"].create({
            "name": "Sede Test",
            "city_name": "Test City",
        })

        self.teacher_user = self.env["res.users"].create({
            "name": "Profesor Test",
            "login": "teacher_test",
            "email": "teacher@test.com",
            "groups_id": [(4, self.env.ref("benglish_academy.group_academic_teacher").id)],
        })

        self.student = self.env["benglish.student"].create({
            "name": "Estudiante Test",
            "email": "student@test.com",
            "program_id": self.program.id,
        })

        # Crear sesión
        self.session = self.env["benglish.academic.session"].create({
            "program_id": self.program.id,
            "subject_id": self.subject.id,
            "date": datetime.now().date(),
            "time_start": 14.0,
            "time_end": 15.5,
            "campus_id": self.campus.id,
            "teacher_id": self.teacher_user.id,
            "delivery_mode": "presential",
            "max_capacity": 15,
        })

        # Crear inscripción
        self.enrollment = self.env["benglish.session.enrollment"].create({
            "session_id": self.session.id,
            "student_id": self.student.id,
            "state": "confirmed",
        })

    def test_01_mark_attended_creates_history(self):
        """
        Test 1: Marcar asistencia en Portal Coach crea registro en historial académico.
        """
        # Iniciar sesión
        self.session.state = "started"

        # Verificar que NO existe historial previo
        history_before = self.env["benglish.academic.history"].search([
            ("student_id", "=", self.student.id),
            ("session_id", "=", self.session.id),
        ])
        self.assertEqual(len(history_before), 0, "No debe existir historial antes de marcar asistencia")

        # Marcar asistencia (simula Portal Coach)
        self.enrollment.state = "attended"

        # Verificar que SE CREÓ el historial automáticamente
        history_after = self.env["benglish.academic.history"].search([
            ("student_id", "=", self.student.id),
            ("session_id", "=", self.session.id),
        ])
        self.assertEqual(len(history_after), 1, "Debe existir 1 registro de historial después de marcar asistencia")
        self.assertEqual(history_after.attendance_status, "attended", "El estado debe ser 'attended'")
        self.assertEqual(history_after.subject_id.id, self.subject.id, "La asignatura debe coincidir")

    def test_02_mark_absent_creates_history(self):
        """
        Test 2: Marcar ausencia en Portal Coach crea registro en historial académico.
        """
        # Iniciar sesión
        self.session.state = "started"

        # Marcar ausencia (simula Portal Coach)
        self.enrollment.state = "absent"

        # Verificar que SE CREÓ el historial
        history = self.env["benglish.academic.history"].search([
            ("student_id", "=", self.student.id),
            ("session_id", "=", self.session.id),
        ])
        self.assertEqual(len(history), 1, "Debe existir 1 registro de historial")
        self.assertEqual(history.attendance_status, "absent", "El estado debe ser 'absent'")

    def test_03_modify_attendance_updates_history(self):
        """
        Test 3: Modificar asistencia actualiza el registro existente (no duplica).
        """
        # Iniciar sesión
        self.session.state = "started"

        # Marcar asistencia
        self.enrollment.state = "attended"

        # Verificar historial inicial
        history = self.env["benglish.academic.history"].search([
            ("student_id", "=", self.student.id),
            ("session_id", "=", self.session.id),
        ])
        self.assertEqual(len(history), 1)
        self.assertEqual(history.attendance_status, "attended")

        # Cambiar a ausente
        self.enrollment.state = "absent"

        # Verificar que NO se duplicó el registro
        history_after = self.env["benglish.academic.history"].search([
            ("student_id", "=", self.student.id),
            ("session_id", "=", self.session.id),
        ])
        self.assertEqual(len(history_after), 1, "NO debe duplicarse el registro")
        self.assertEqual(history_after.attendance_status, "absent", "El estado debe actualizarse a 'absent'")

    def test_04_action_mark_done_idempotent(self):
        """
        Test 4: action_mark_done() respeta registros creados por Portal Coach (idempotencia).
        """
        # Iniciar sesión
        self.session.state = "started"

        # Marcar asistencia desde Portal Coach
        self.enrollment.state = "attended"

        # Verificar historial creado
        history_before = self.env["benglish.academic.history"].search([
            ("student_id", "=", self.student.id),
            ("session_id", "=", self.session.id),
        ])
        self.assertEqual(len(history_before), 1)
        self.assertEqual(history_before.attendance_status, "attended")

        # Marcar sesión como dictada (simula backend)
        self.session.action_mark_done()

        # Verificar que NO se duplicó el registro
        history_after = self.env["benglish.academic.history"].search([
            ("student_id", "=", self.student.id),
            ("session_id", "=", self.session.id),
        ])
        self.assertEqual(len(history_after), 1, "NO debe duplicarse el registro al marcar como 'done'")
        self.assertEqual(history_after.attendance_status, "attended", "Debe mantener el estado original")

    def test_05_no_sync_if_session_not_started(self):
        """
        Test 5: NO se sincroniza si la sesión no está en estado 'started' o 'done'.
        """
        # Sesión en estado 'draft' (NO iniciada)
        self.session.state = "draft"

        # Intentar marcar asistencia
        self.enrollment.state = "attended"

        # Verificar que NO se creó historial
        history = self.env["benglish.academic.history"].search([
            ("student_id", "=", self.student.id),
            ("session_id", "=", self.session.id),
        ])
        self.assertEqual(len(history), 0, "NO debe crear historial si la sesión no está 'started' o 'done'")

    def test_06_portal_student_sees_attendance(self):
        """
        Test 6: Portal Student debe ver la asistencia marcada en Portal Coach.
        """
        # Iniciar sesión y marcar asistencia
        self.session.state = "started"
        self.enrollment.state = "attended"

        # Simular consulta desde Portal Student
        History = self.env["benglish.academic.history"]
        history = History.search([
            ("student_id", "=", self.student.id)
        ])

        # Verificar que Portal Student puede ver el registro
        self.assertEqual(len(history), 1, "Portal Student debe ver 1 registro")
        self.assertEqual(history.attendance_status, "attended", "Debe ver 'attended'")
        self.assertEqual(history.student_id.id, self.student.id, "Debe ser del estudiante correcto")

        # Verificar resumen de asistencia
        summary = History.get_attendance_summary(self.student.id)
        self.assertEqual(summary["total_classes"], 1, "Total de clases debe ser 1")
        self.assertEqual(summary["attended"], 1, "Clases asistidas debe ser 1")
        self.assertEqual(summary["absent"], 0, "Clases ausentes debe ser 0")

    def test_07_multiple_sessions_sync(self):
        """
        Test 7: Múltiples sesiones con diferentes estados se sincronizan correctamente.
        """
        # Crear segunda sesión
        session2 = self.env["benglish.academic.session"].create({
            "program_id": self.program.id,
            "subject_id": self.subject.id,
            "date": datetime.now().date() + timedelta(days=1),
            "time_start": 14.0,
            "time_end": 15.5,
            "campus_id": self.campus.id,
            "teacher_id": self.teacher_user.id,
            "delivery_mode": "presential",
            "max_capacity": 15,
        })

        enrollment2 = self.env["benglish.session.enrollment"].create({
            "session_id": session2.id,
            "student_id": self.student.id,
            "state": "confirmed",
        })

        # Iniciar ambas sesiones
        self.session.state = "started"
        session2.state = "started"

        # Marcar asistencias diferentes
        self.enrollment.state = "attended"
        enrollment2.state = "absent"

        # Verificar historial
        history = self.env["benglish.academic.history"].search([
            ("student_id", "=", self.student.id)
        ])
        self.assertEqual(len(history), 2, "Deben existir 2 registros de historial")

        # Verificar resumen
        summary = self.env["benglish.academic.history"].get_attendance_summary(self.student.id)
        self.assertEqual(summary["total_classes"], 2)
        self.assertEqual(summary["attended"], 1)
        self.assertEqual(summary["absent"], 1)
        self.assertEqual(summary["attendance_rate"], 50.0, "Tasa de asistencia debe ser 50%")
