# -*- coding: utf-8 -*-
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestAgendaHomologation(TransactionCase):
    def setUp(self):
        super().setUp()
        self.program = self._create_program("Program A", "benglish")
        self.phase = self._create_phase(self.program, "Phase A", 1)
        self.level = self._create_level(self.phase, "Level A", 1, max_unit=24)

        self.program_b = self._create_program("Program B", "bteens")
        self.phase_b = self._create_phase(self.program_b, "Phase B", 1)
        self.level_b = self._create_level(self.phase_b, "Level B", 1, max_unit=24)

        self.campus = self.env["benglish.campus"].create(
            {
                "name": "Test Campus",
                "code": "CAMP-01",
                "city_name": "Test City",
            }
        )
        today = fields.Date.today()
        self.agenda = self.env["benglish.academic.agenda"].create(
            {
                "location_city": "Test City",
                "campus_id": self.campus.id,
                "date_start": today,
                "date_end": today,
                "time_start": 8.0,
                "time_end": 18.0,
            }
        )
        self.teacher = self.env["hr.employee"].create(
            {
                "name": "Teacher Test",
                "is_teacher": True,
                "meeting_link": "https://meet.test/teacher",
                "meeting_id": "ROOM-001",
            }
        )

    def _create_program(self, name, program_type):
        return self.env["benglish.program"].create(
            {
                "name": name,
                "code": "/",
                "program_type": program_type,
            }
        )

    def _create_phase(self, program, name, sequence):
        return self.env["benglish.phase"].create(
            {
                "name": name,
                "code": "/",
                "sequence": sequence,
                "program_id": program.id,
            }
        )

    def _create_level(self, phase, name, sequence, max_unit=0):
        return self.env["benglish.level"].create(
            {
                "name": name,
                "code": "/",
                "sequence": sequence,
                "phase_id": phase.id,
                "max_unit": max_unit,
            }
        )

    def _create_subject(
        self,
        level,
        name,
        category,
        alias=None,
        unit_number=None,
        bskill_number=None,
        unit_block_start=None,
        unit_block_end=None,
    ):
        vals = {
            "name": name,
            "alias": alias or name,
            "level_id": level.id,
            "subject_category": category,
        }
        if unit_number is not None:
            vals["unit_number"] = unit_number
        if bskill_number is not None:
            vals["bskill_number"] = bskill_number
        if unit_block_start is not None:
            vals["unit_block_start"] = unit_block_start
        if unit_block_end is not None:
            vals["unit_block_end"] = unit_block_end
        return self.env["benglish.subject"].create(vals)

    def _create_template(
        self,
        program,
        code,
        category,
        mapping_mode,
        alias_student,
        skill_number=None,
    ):
        vals = {
            "name": "%s %s" % (code, program.name),
            "code": code,
            "program_id": program.id,
            "subject_category": category,
            "mapping_mode": mapping_mode,
            "alias_student": alias_student,
        }
        if skill_number is not None:
            vals["skill_number"] = skill_number
        return self.env["benglish.agenda.template"].create(vals)

    def _create_session(self, program, template, audience_from=None, audience_to=None):
        vals = {
            "agenda_id": self.agenda.id,
            "program_id": program.id,
            "template_id": template.id,
            "date": fields.Date.today(),
            "time_start": 9.0,
            "time_end": 10.0,
            "teacher_id": self.teacher.id,
            "delivery_mode": "presential",
            "max_capacity": 10,
        }
        if audience_from is not None:
            vals["audience_unit_from"] = audience_from
        if audience_to is not None:
            vals["audience_unit_to"] = audience_to
        session = self.env["benglish.academic.session"].create(vals)
        session.write({"is_published": True, "state": "active"})
        return session

    def _create_student(self, code, first_name):
        return self.env["benglish.student"].create(
            {
                "code": code,
                "first_name": first_name,
                "email": "%s@test.com" % code.lower(),
            }
        )

    def _create_history(self, student, subject):
        self.env["benglish.academic.history"].create(
            {
                "student_id": student.id,
                "session_date": fields.Date.today(),
                "program_id": subject.program_id.id,
                "subject_id": subject.id,
                "attendance_status": "attended",
                "session_time_start": 8.0,
                "session_time_end": 9.0,
            }
        )
        student.invalidate_cache(fnames=["max_unit_completed"])

    def _confirm_enrollment(self, session, student):
        enrollment = self.env["benglish.session.enrollment"].create(
            {
                "session_id": session.id,
                "student_id": student.id,
                "state": "pending",
            }
        )
        enrollment.action_confirm()
        return enrollment

    def test_skill_per_unit_assigns_distinct_effective_subjects(self):
        template = self._create_template(
            self.program,
            "SKILL_2",
            "bskills",
            "per_unit",
            "Skill 2",
            skill_number=2,
        )
        skill_u1 = self._create_subject(
            self.level, "Skill2 U1", "bskills", alias="Skill 2", unit_number=1, bskill_number=2
        )
        skill_u8 = self._create_subject(
            self.level, "Skill2 U8", "bskills", alias="Skill 2", unit_number=8, bskill_number=2
        )
        subject_u7 = self._create_subject(
            self.level, "Skill1 U7", "bskills", alias="Skill 1", unit_number=7, bskill_number=1
        )
        session = self._create_session(self.program, template, audience_from=1, audience_to=8)

        student_a = self._create_student("STU-A", "Student A")
        student_b = self._create_student("STU-B", "Student B")
        self._create_history(student_b, subject_u7)

        enrollment_a = self._confirm_enrollment(session, student_a)
        enrollment_b = self._confirm_enrollment(session, student_b)

        self.assertEqual(enrollment_a.effective_subject_id.id, skill_u1.id)
        self.assertEqual(enrollment_b.effective_subject_id.id, skill_u8.id)

    def test_bcheck_pair_assigns_by_unit(self):
        template = self._create_template(
            self.program,
            "BCHECK",
            "bcheck",
            "pair",
            "B-check",
        )
        bcheck_u1 = self._create_subject(
            self.level, "BCheck U1", "bcheck", alias="B-check", unit_number=1
        )
        bcheck_u2 = self._create_subject(
            self.level, "BCheck U2", "bcheck", alias="B-check", unit_number=2
        )
        session = self._create_session(self.program, template, audience_from=1, audience_to=2)

        student_u1 = self._create_student("STU-C", "Student C")
        student_u2 = self._create_student("STU-D", "Student D")
        self._create_history(student_u2, bcheck_u1)

        enrollment_u1 = self._confirm_enrollment(session, student_u1)
        enrollment_u2 = self._confirm_enrollment(session, student_u2)

        self.assertEqual(enrollment_u1.effective_subject_id.id, bcheck_u1.id)
        self.assertEqual(enrollment_u2.effective_subject_id.id, bcheck_u2.id)

    def test_oral_test_block_mapping(self):
        template = self._create_template(
            self.program,
            "ORAL",
            "oral_test",
            "block",
            "Oral Test",
        )
        oral_1 = self._create_subject(
            self.level, "Oral 1-4", "oral_test", alias="Oral Test", unit_block_start=1, unit_block_end=4
        )
        oral_2 = self._create_subject(
            self.level, "Oral 5-8", "oral_test", alias="Oral Test", unit_block_start=5, unit_block_end=8
        )
        session_block_1 = self._create_session(self.program, template, audience_from=1, audience_to=4)
        session_block_2 = self._create_session(self.program, template, audience_from=5, audience_to=8)

        student_a = self._create_student("STU-E", "Student E")
        student_b = self._create_student("STU-F", "Student F")
        subject_u7 = self._create_subject(
            self.level, "Skill1 U7", "bskills", alias="Skill 1", unit_number=7, bskill_number=1
        )
        self._create_history(student_b, subject_u7)

        resolved_a = session_block_1.resolve_effective_subject(
            student_a, check_completed=False, check_prereq=False, raise_on_error=True
        )
        resolved_b = session_block_2.resolve_effective_subject(
            student_b, check_completed=False, check_prereq=False, raise_on_error=True
        )

        self.assertEqual(resolved_a.id, oral_1.id)
        self.assertEqual(resolved_b.id, oral_2.id)

    def test_no_repetition_blocks_confirmation(self):
        template = self._create_template(
            self.program,
            "ORAL-REP",
            "oral_test",
            "block",
            "Oral Test",
        )
        oral_1 = self._create_subject(
            self.level, "Oral 1-4 R", "oral_test", alias="Oral Test", unit_block_start=1, unit_block_end=4
        )
        subject_u4 = self._create_subject(
            self.level, "Skill1 U4", "bskills", alias="Skill 1", unit_number=4, bskill_number=1
        )
        session = self._create_session(self.program, template, audience_from=1, audience_to=4)

        student = self._create_student("STU-G", "Student G")
        self._create_history(student, oral_1)
        self._create_history(student, subject_u4)

        enrollment = self.env["benglish.session.enrollment"].create(
            {
                "session_id": session.id,
                "student_id": student.id,
                "state": "pending",
            }
        )
        with self.assertRaises(UserError):
            enrollment.action_confirm()

    def test_multi_program_uses_program_specific_subjects(self):
        template_a = self._create_template(
            self.program,
            "SKILL_MULTI",
            "bskills",
            "per_unit",
            "Skill 1",
            skill_number=1,
        )
        template_b = self._create_template(
            self.program_b,
            "SKILL_MULTI",
            "bskills",
            "per_unit",
            "Skill 1",
            skill_number=1,
        )
        subject_a = self._create_subject(
            self.level, "Skill1 U1 A", "bskills", alias="Skill 1", unit_number=1, bskill_number=1
        )
        subject_b = self._create_subject(
            self.level_b, "Skill1 U1 B", "bskills", alias="Skill 1", unit_number=1, bskill_number=1
        )

        session_b = self._create_session(self.program_b, template_b, audience_from=1, audience_to=8)
        student_b = self._create_student("STU-H", "Student H")

        enrollment = self._confirm_enrollment(session_b, student_b)
        self.assertEqual(enrollment.effective_subject_id.id, subject_b.id)
        self.assertNotEqual(enrollment.effective_subject_id.id, subject_a.id)
