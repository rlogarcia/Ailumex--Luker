# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    """Asigna el grupo de portal de estudiante a usuarios ya vinculados.

    Esto garantiza que los estudiantes existentes con usuario de portal reciban
    las reglas de seguridad y menús del portal sin modificar el backend.
    """
    student_group = env.ref("portal_student.group_benglish_student", raise_if_not_found=False)
    portal_group = env.ref("base.group_portal")

    if not student_group:
        return

    students_with_user = env["benglish.student"].sudo().search([("user_id", "!=", False)])
    for student in students_with_user:
        user = student.user_id
        new_groups = set(user.groups_id.ids)
        new_groups.add(portal_group.id)
        new_groups.add(student_group.id)
        user.sudo().write({"groups_id": [(6, 0, list(new_groups))]})
