# -*- coding: utf-8 -*-
"""
Utilitarios centralizados para detección de roles de portal.
Este módulo provee funciones para determinar si un usuario autenticado
es Student, Coach, ambos, o ninguno.
"""

from odoo.http import request


def is_student(user=None):
    """
    Verifica si el usuario autenticado es un estudiante.

    Args:
        user: objeto res.users (opcional). Si no se provee, usa request.env.user

    Returns:
        bool: True si el usuario tiene registro en benglish.student
    """
    if user is None:
        user = request.env.user

    # MÉTODO 1: Verificar directamente si existe el registro de estudiante vinculado
    # (funciona incluso si el grupo no existe o no está asignado)
    student = (
        request.env["benglish.student"]
        .sudo()
        .search([("user_id", "=", user.id)], limit=1)
    )

    if student:
        return True

    # MÉTODO 2 (fallback): Verificar si tiene el grupo de estudiante
    student_group = request.env.ref(
        "portal_student.group_benglish_student", raise_if_not_found=False
    )
    if student_group and student_group in user.groups_id:
        return True

    return False


def is_coach(user=None):
    """
    Verifica si el usuario autenticado es un coach.

    Args:
        user: objeto res.users (opcional). Si no se provee, usa request.env.user

    Returns:
        bool: True si el usuario tiene registro en benglish.coach O es empleado con is_teacher=True
    """
    if user is None:
        user = request.env.user

    # MÉTODO 1: Verificar directamente si existe el registro de coach vinculado
    coach = (
        request.env["benglish.coach"]
        .sudo()
        .search([("user_id", "=", user.id)], limit=1)
    )

    if coach:
        return True

    # MÉTODO 1B: Verificar si es un empleado con acceso al portal docente (is_teacher=True y active)
    employee = (
        request.env["hr.employee"]
        .sudo()
        .search([("user_id", "=", user.id), ("is_teacher", "=", True), ("active", "=", True)], limit=1)
    )

    if employee:
        return True

    # MÉTODO 2 (fallback): Verificar si tiene el grupo de coach
    coach_group = request.env.ref(
        "portal_coach.group_portal_coach", raise_if_not_found=False
    )
    if coach_group and coach_group in user.groups_id:
        return True

    return False


def get_user_role(user=None):
    """
    Determina el rol principal del usuario autenticado.

    Prioridad (en caso de roles múltiples):
    1. Coach (si es coach y student, se prioriza coach)
    2. Student
    3. None (usuario portal estándar sin rol específico)

    Args:
        user: objeto res.users (opcional). Si no se provee, usa request.env.user

    Returns:
        str: 'coach', 'student', 'both', o None
    """
    if user is None:
        user = request.env.user

    is_coach_user = is_coach(user)
    is_student_user = is_student(user)

    if is_coach_user and is_student_user:
        return "both"
    elif is_coach_user:
        return "coach"
    elif is_student_user:
        return "student"
    else:
        return None


def get_portal_home_url(user=None):
    """
    Obtiene la URL de home/landing del portal según el rol del usuario.

    Prioridad en caso de roles múltiples:
    - Coach primero (si es coach y student, va a portal coach)
    - Student segundo
    - Portal estándar /my si no tiene rol específico

    Args:
        user: objeto res.users (opcional). Si no se provee, usa request.env.user

    Returns:
        str: URL de la home del portal correspondiente
    """
    role = get_user_role(user)

    if role == "both":
        # Usuario con ambos roles: prioridad a coach
        return "/my/coach"
    elif role == "coach":
        return "/my/coach"
    elif role == "student":
        return "/my/student"
    else:
        # Usuario portal sin rol específico: portal estándar de Odoo
        return "/my"


def get_student(user=None):
    """Obtiene el estudiante vinculado al usuario autenticado."""
    if user is None:
        user = request.env.user
    return (
        request.env["benglish.student"]
        .sudo()
        .search([("user_id", "=", user.id)], limit=1)
    )


def get_student_portal_access_rules(user=None, student=None):
    """Retorna reglas de acceso del portal para el estudiante."""
    if student is None:
        student = get_student(user=user)
    if not student:
        return {
            "allow_login": True,
            "level": "full",
            "message": "",
            "state": "",
            "profile_state": {},
            "capabilities": {
                "can_schedule": True,
                "can_attend": True,
                "can_use_apps": True,
                "can_view_history": True,
                "can_request_freeze": True,
                "blocks_enrollment": False,
            },
        }
    return student.portal_get_access_rules()


def must_change_password(user=None):
    """Indica si el usuario debe cambiar contraseña al ingresar al portal."""
    if user is None:
        user = request.env.user
    return bool(getattr(user, "portal_must_change_password", False))
