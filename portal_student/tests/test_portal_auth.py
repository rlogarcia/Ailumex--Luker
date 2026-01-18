# -*- coding: utf-8 -*-
from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestPortalStudentAuth(HttpCase):
    def _create_portal_student(self, name, code, email, document, state="active", profile_state=None, must_change=False):
        partner = self.env["res.partner"].create(
            {"name": name, "email": email, "is_company": False}
        )
        portal_group = self.env.ref("base.group_portal")
        student_group = self.env.ref("portal_student.group_benglish_student")
        user = self.env["res.users"].sudo().create(
            {
                "name": name,
                "login": email,
                "email": email,
                "partner_id": partner.id,
                "groups_id": [(6, 0, [portal_group.id, student_group.id])],
                "active": True,
                "password": document,
                "portal_must_change_password": must_change,
            }
        )
        student = self.env["benglish.student"].create(
            {
                "name": name,
                "code": code,
                "email": email,
                "student_id_number": document,
                "state": state,
                "user_id": user.id,
                "partner_id": partner.id,
                "profile_state_id": profile_state.id if profile_state else False,
            }
        )
        return student, user

    def test_login_with_document_forces_welcome(self):
        student, _user = self._create_portal_student(
            "Test Student",
            "ST-001",
            "student1@example.com",
            "123456789",
            must_change=True,
        )
        response = self.url_open(
            "/web/login",
            data={"login": student.student_id_number, "password": student.student_id_number},
            allow_redirects=False,
        )
        self.assertIn(response.status_code, (302, 303))
        self.assertIn("/my/welcome", response.headers.get("Location", ""))

    def test_login_blocked_by_state(self):
        profile_state = self.env["benglish.student.profile.state"].create(
            {
                "name": "Bloqueado Portal",
                "code": "BLOCK_PORTAL",
                "portal_visible": False,
                "can_schedule": False,
                "can_attend": False,
                "can_use_apps": False,
                "can_view_history": False,
                "can_request_freeze": False,
            }
        )
        student, _user = self._create_portal_student(
            "Blocked Student",
            "ST-002",
            "blocked@example.com",
            "987654321",
            state="active",
            profile_state=profile_state,
            must_change=False,
        )
        response = self.url_open(
            "/web/login",
            data={"login": student.student_id_number, "password": student.student_id_number},
            allow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("No es posible iniciar sesi\u00f3n", response.text)

    def test_restricted_state_limits_agenda(self):
        profile_state = self.env["benglish.student.profile.state"].create(
            {
                "name": "Suspendido Test",
                "code": "SUSP_TEST",
                "can_schedule": False,
                "can_attend": False,
                "can_use_apps": False,
                "can_view_history": True,
                "can_request_freeze": False,
                "portal_visible": True,
            }
        )
        student, _user = self._create_portal_student(
            "Limited Student",
            "ST-003",
            "limited@example.com",
            "555555555",
            state="active",
            profile_state=profile_state,
            must_change=False,
        )
        self.url_open(
            "/web/login",
            data={"login": student.student_id_number, "password": student.student_id_number},
            allow_redirects=True,
        )
        response = self.url_open("/my/student/agenda", allow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Acceso limitado", response.text)
