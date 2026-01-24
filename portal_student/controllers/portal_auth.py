# -*- coding: utf-8 -*-
import logging
import re

import odoo
from odoo import fields, http, tools, _
from odoo.exceptions import AccessDenied
from odoo.http import request
from odoo.addons.web.controllers.home import ensure_db, SIGN_UP_REQUEST_PARAMS
from odoo.addons.benglish_academy.utils.normalizers import normalize_documento

try:
    from odoo.addons.auth_signup.controllers.main import AuthSignupHome as BaseLoginHome
except Exception:  # pragma: no cover - fallback when auth_signup is not installed
    from odoo.addons.web.controllers.home import Home as BaseLoginHome

_logger = logging.getLogger(__name__)


class PortalStudentAuthController(BaseLoginHome):
    """Auth y seguridad del portal estudiante (login y contrase\u00f1as)."""

    _SPECIAL_PATTERN = re.compile(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]")

    def _normalize_document(self, document):
        doc_value = (document or "").strip()
        if not doc_value:
            return ""
        if re.search(r"[A-Za-z]", doc_value):
            return re.sub(r"[^0-9A-Za-z]", "", doc_value)
        return normalize_documento(doc_value) or ""

    def _find_student_by_document(self, document):
        Student = request.env["benglish.student"].sudo()
        raw_doc = (document or "").strip()
        if not raw_doc:
            return Student.browse()

        normalized = self._normalize_document(raw_doc)
        student = Student.search([("student_id_number", "=", raw_doc)], limit=1)
        if not student and normalized and normalized != raw_doc:
            student = Student.search([("student_id_number", "=", normalized)], limit=1)
        if not student:
            student = Student.search([("student_id_number", "=ilike", raw_doc)], limit=1)
        if not student and normalized:
            student = Student.search([("student_id_number", "=ilike", normalized)], limit=1)

        if not student and normalized and len(normalized) >= 4:
            pattern = "%".join(normalized)
            candidates = Student.search([("student_id_number", "ilike", pattern)], limit=10)
            for candidate in candidates:
                if self._normalize_document(candidate.student_id_number) == normalized:
                    student = candidate
                    break

        return student

    def _resolve_login(self, login):
        login = (login or "").strip()
        if not login:
            return login

        Student = request.env["benglish.student"].sudo()

        if "@" in login:
            student = Student.search([("email", "=ilike", login)], limit=1)
            if not student:
                student = Student.search([("partner_id.email", "=ilike", login)], limit=1)
            if student and student.user_id and student.user_id.active:
                return student.user_id.login
            return login

        student = self._find_student_by_document(login)
        if student and student.user_id and student.user_id.active:
            return student.user_id.login
        return login

    def _build_login_values(self, original_login=None, error=None):
        values = {k: v for k, v in request.params.items() if k in SIGN_UP_REQUEST_PARAMS}
        if original_login:
            values["login"] = original_login
        if error:
            values["error"] = error
        try:
            values["databases"] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values["databases"] = None
        if not tools.config["list_db"]:
            values["disable_database_manager"] = True
        return values

    def _render_login(self, values):
        response = request.render("web.login", values)
        if hasattr(self, "get_auth_signup_config"):
            response.qcontext.update(self.get_auth_signup_config())
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'self'"
        return response

    def _log_blocked_login(self, user, student, reason):
        ip = request.httprequest.remote_addr if request.httprequest else "n/a"
        message = (
            "Portal login blocked for user=%s student=%s reason=%s ip=%s"
            % (user.login, student.id if student else "n/a", reason, ip)
        )
        request.env["ir.logging"].sudo().create(
            {
                "name": "Portal Student Login Blocked",
                "type": "server",
                "level": "warning",
                "message": message,
                "path": "portal_student.web_login",
                "func": "web_login",
                "line": 0,
            }
        )

    def _ensure_student_groups(self, user):
        student_group = request.env.ref("portal_student.group_benglish_student", raise_if_not_found=False)
        portal_group = request.env.ref("base.group_portal", raise_if_not_found=False)
        updates = []
        if portal_group and portal_group not in user.groups_id:
            updates.append((4, portal_group.id))
        if student_group and student_group not in user.groups_id:
            updates.append((4, student_group.id))
        if updates:
            user.sudo().write({"groups_id": updates})
    
    def _ensure_coach_groups(self, user):
        """Asegura que el usuario coach tenga los grupos necesarios."""
        coach_group = request.env.ref("portal_coach.group_benglish_coach", raise_if_not_found=False)
        portal_group = request.env.ref("base.group_portal", raise_if_not_found=False)
        internal_group = request.env.ref("base.group_user", raise_if_not_found=False)
        
        updates = []
        
        # Si es usuario INTERNO (base.group_user), NO agregar base.group_portal
        is_internal_user = internal_group and internal_group in user.groups_id
        
        if not is_internal_user:
            # Solo agregar base.group_portal si NO es usuario interno
            if portal_group and portal_group not in user.groups_id:
                updates.append((4, portal_group.id))
        
        # SIEMPRE agregar el grupo de coach
        if coach_group and coach_group not in user.groups_id:
            updates.append((4, coach_group.id))
        
        if updates:
            user.sudo().write({"groups_id": updates})

    def _find_user_for_reset(self, login):
        login = (login or "").strip()
        if not login:
            return None, None

        Student = request.env["benglish.student"].sudo()
        Coach = request.env["benglish.coach"].sudo()
        Users = request.env["res.users"].sudo()

        if "@" in login:
            student = Student.search([("email", "=ilike", login)], limit=1)
            if not student:
                student = Student.search([("partner_id.email", "=ilike", login)], limit=1)
            if student and student.user_id and student.user_id.active:
                return student.user_id, "student"

            coach = Coach.search([("email", "=ilike", login)], limit=1)
            if coach and coach.user_id and coach.user_id.active:
                return coach.user_id, "coach"

            user = Users.search(
                ["|", ("login", "=ilike", login), ("email", "=ilike", login)],
                limit=1,
            )
            if user and user.active:
                if user.sudo()._has_group("benglish_academy.group_academic_manager"):
                    return user, "manager"
                return user, "user"
            return None, None

        document = re.sub(r"\s+", "", login)
        if document:
            student = self._find_student_by_document(login)
            if student and student.user_id and student.user_id.active:
                return student.user_id, "student"

            coach = Coach.search([("identification_number", "=", document)], limit=1)
            if not coach:
                coach = Coach.search([("identification_number", "=ilike", login)], limit=1)
            if coach and coach.user_id and coach.user_id.active:
                return coach.user_id, "coach"

            user = Users.search([("login", "=", document)], limit=1)
            if user and user.active:
                if user.sudo()._has_group("benglish_academy.group_academic_manager"):
                    return user, "manager"
                return user, "user"

        return None, None

    @http.route("/web/login", type="http", auth="none", readonly=False)
    def web_login(self, redirect=None, **kw):
        ensure_db()
        request.params["login_success"] = False

        original_login = request.params.get("login")
        if request.httprequest.method == "POST" and original_login:
            resolved_login = self._resolve_login(original_login)
            request.params["login"] = resolved_login

        response = super().web_login(redirect=redirect, **kw)

        if request.httprequest.method == "POST" and original_login and hasattr(response, "qcontext"):
            response.qcontext["login"] = original_login

        if request.httprequest.method == "POST" and request.session.uid:
            user = request.env["res.users"].sudo().browse(request.session.uid)
            
            # Manejar coach
            coach = request.env["benglish.coach"].sudo().search(
                [("user_id", "=", user.id)], limit=1
            )
            if coach:
                self._ensure_coach_groups(user)
                return request.redirect("/my/coach")
            
            # Manejar estudiante
            student = request.env["benglish.student"].sudo().search(
                [("user_id", "=", user.id)], limit=1
            )
            if student:
                self._ensure_student_groups(user)
                access = student.portal_get_access_rules()
                if not access.get("allow_login", True):
                    reason = (
                        access.get("profile_state", {}).get("code")
                        or access.get("state")
                        or "blocked"
                    )
                    self._log_blocked_login(user, student, reason)
                    request.session.logout(keep_db=True)
                    error_msg = _("No es posible iniciar sesi\u00f3n. Contacta al administrador.")
                    params = {"error": error_msg}
                    if original_login:
                        params["login"] = original_login
                    return request.redirect_query("/web/login", params)
                if user.portal_must_change_password:
                    return request.redirect("/my/welcome")
                return request.redirect("/my/student")

        return response

    def _get_password_policy(self):
        params = request.env["ir.config_parameter"].sudo()

        def _get_bool(key, default):
            raw = params.get_param(key, default)
            return str(raw).lower() in ("1", "true", "yes", "y", "on")

        try:
            min_length = int(params.get_param("portal_student.password_min_length", 10))
        except (TypeError, ValueError):
            min_length = 10

        return {
            "min_length": min_length,
            "require_upper": _get_bool("portal_student.password_require_upper", True),
            "require_number": _get_bool("portal_student.password_require_number", True),
            "require_special": _get_bool("portal_student.password_require_special", True),
            "disallow_reuse": _get_bool("portal_student.password_disallow_reuse", True),
        }

    def _validate_new_password(self, user, password, confirm):
        errors = []
        password = (password or "").strip()
        confirm = (confirm or "").strip()

        if not password or not confirm:
            errors.append(_("Contrase\u00f1a y confirmaci\u00f3n son obligatorias."))
            return errors

        if password != confirm:
            errors.append(_("Las contrase\u00f1as no coinciden."))

        policy = self._get_password_policy()
        if len(password) < policy["min_length"]:
            errors.append(
                _("La contrase\u00f1a debe tener al menos %s caracteres.") % policy["min_length"]
            )
        if policy["require_upper"] and not any(ch.isupper() for ch in password):
            errors.append(_("La contrase\u00f1a debe incluir al menos una may\u00fascula."))
        if policy["require_number"] and not any(ch.isdigit() for ch in password):
            errors.append(_("La contrase\u00f1a debe incluir al menos un n\u00famero."))
        if policy["require_special"] and not self._SPECIAL_PATTERN.search(password):
            errors.append(_("La contrase\u00f1a debe incluir al menos un car\u00e1cter especial."))

        if policy["disallow_reuse"]:
            try:
                user._check_credentials({"type": "password", "password": password}, {"interactive": True})
                errors.append(_("La nueva contrase\u00f1a debe ser diferente a la actual."))
            except AccessDenied:
                pass

        return errors

    def _log_password_change(self, user, change_type):
        ip = request.httprequest.remote_addr if request.httprequest else "n/a"
        message = "Portal password change type=%s user=%s ip=%s" % (change_type, user.login, ip)
        request.env["ir.logging"].sudo().create(
            {
                "name": "Portal Student Password Change",
                "type": "server",
                "level": "info",
                "message": message,
                "path": "portal_student.password_change",
                "func": "change_password",
                "line": 0,
            }
        )

    def _refresh_session_token(self, user):
        """Refresca el token de sesión después del cambio de contraseña.
        
        IMPORTANTE: Después de cambiar la contraseña, el hash cambia y el token
        de sesión debe actualizarse para evitar que el usuario sea deslogueado.
        """
        if request.session and request.session.uid == user.id:
            # Forzar commit de la transacción actual para persistir el cambio de contraseña
            request.env.cr.commit()
            # Limpiar caché para que Odoo recargue el usuario con la nueva contraseña
            request.env.flush_all()
            request.env.registry.clear_cache()
            # Actualizar el token de sesión solo si el método existe
            if hasattr(user, '_compute_session_token'):
                try:
                    request.session.session_token = user._compute_session_token(request.session.sid)
                except Exception as e:
                    _logger.warning("Error al refrescar token de sesión: %s", e)

    @http.route("/my/welcome", type="http", auth="user", website=True, methods=["GET", "POST"], csrf=True)
    def portal_student_welcome(self, **kwargs):
        user = request.env.user
        student = request.env["benglish.student"].sudo().search([("user_id", "=", user.id)], limit=1)
        if not student:
            return request.redirect("/my")

        if not user.portal_must_change_password:
            return request.redirect("/my/student")

        error = None
        message = None

        if request.httprequest.method == "POST":
            password = kwargs.get("password") or ""
            confirm = kwargs.get("confirm_password") or ""
            errors = self._validate_new_password(user, password, confirm)
            if errors:
                error = " ".join(errors)
            else:
                try:
                    # Cambiar contraseña usando sudo para evitar problemas de permisos
                    user.sudo().write({'password': password})
                    # Marcar que ya no necesita cambiar la contraseña
                    user.sudo().write(
                        {
                            "portal_must_change_password": False,
                            "portal_password_changed_at": fields.Datetime.now(),
                        }
                    )
                    # Forzar commit para persistir los cambios
                    request.env.cr.commit()
                    # Refrescar el token de sesión
                    self._refresh_session_token(user)
                    # Log del cambio
                    self._log_password_change(user, "forced")
                    message = _("Contraseña actualizada correctamente.")
                    return request.redirect("/my/student")
                except Exception as e:
                    _logger.error("Error al cambiar contraseña en welcome: %s", e)
                    error = _("Error al cambiar la contraseña. Intenta nuevamente.")

        values = {
            "page_name": "welcome",
            "student": student,
            "error": error,
            "message": message,
        }
        return request.render("portal_student.portal_student_welcome", values)

    @http.route("/my/change-password", type="http", auth="user", website=True, methods=["GET", "POST"], csrf=True)
    def portal_student_change_password(self, **kwargs):
        user = request.env.user
        student = request.env["benglish.student"].sudo().search([("user_id", "=", user.id)], limit=1)
        if not student:
            return request.redirect("/my")

        if user.portal_must_change_password:
            return request.redirect("/my/welcome")

        error = None
        message = None

        if request.httprequest.method == "POST":
            current = kwargs.get("current_password") or ""
            password = kwargs.get("password") or ""
            confirm = kwargs.get("confirm_password") or ""
            errors = self._validate_new_password(user, password, confirm)
            if errors:
                error = " ".join(errors)
            else:
                try:
                    credential = {"login": user.login, "password": current, "type": "password"}
                    user._check_credentials(credential, {"interactive": True})
                    # Cambiar contraseña usando sudo para evitar problemas de permisos
                    user.sudo().write({'password': password})
                    # Actualizar campos de control
                    user.sudo().write(
                        {
                            "portal_must_change_password": False,
                            "portal_password_changed_at": fields.Datetime.now(),
                        }
                    )
                    # Forzar commit para persistir los cambios
                    request.env.cr.commit()
                    # Refrescar el token de sesión
                    self._refresh_session_token(user)
                    # Log del cambio
                    self._log_password_change(user, "voluntary")
                    message = _("Contraseña actualizada correctamente.")
                except AccessDenied:
                    error = _("La contraseña actual no es válida.")
                except Exception as e:
                    _logger.error("Error al cambiar contraseña: %s", e)
                    error = _("Error al cambiar la contraseña. Intenta nuevamente.")

        access = student.portal_get_access_rules()
        values = {
            "page_name": "change_password",
            "student": student,
            "portal_access": access,
            "portal_access_message": access.get("message"),
            "portal_access_level": access.get("level"),
            "error": error,
            "message": message,
        }
        return request.render("portal_student.portal_student_change_password", values)

