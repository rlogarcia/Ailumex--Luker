# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
import base64
import logging
import traceback
import pytz

from odoo import fields, http, _
from odoo.exceptions import ValidationError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from . import portal_utils

_logger = logging.getLogger(__name__)


class PortalStudentController(CustomerPortal):
    """Controlador del Portal del Estudiante (frontend y datos)."""

    @http.route(['/my', '/my/home'], type="http", auth="user", website=True)
    def portal_my_redirect(self, **kwargs):
        """
        Redirige el home de portal genérico según el rol del usuario.
        
        Prioridad de redirección:
        1. Coach → /my/coach
        2. Student → /my/student  
        3. Coach + Student (ambos roles) → /my/coach (prioridad a coach)
        4. Usuario portal sin rol específico → /my (portal estándar Odoo)
        5. Usuarios internos (empleados/admin) → /my (portal estándar Odoo)
        """
        user = request.env.user
        
        _logger.info(f"=== PORTAL REDIRECT START === User: {user.login} (ID: {user.id})")

        if portal_utils.must_change_password(user):
            return request.redirect("/my/welcome")
        
        # Detectar roles PRIMERO
        is_coach = portal_utils.is_coach(user)
        is_student = portal_utils.is_student(user)
        _logger.info(f"User {user.login} - is_coach: {is_coach}, is_student: {is_student}")
        
        # Usuarios internos (base.group_user) que NO son coach ni student → comportamiento estándar
        is_internal = user.has_group('base.group_user')
        if is_internal and not is_coach and not is_student:
            _logger.info(f"User {user.login} is internal user (not coach/student), using standard portal")
            return super(PortalStudentController, self).portal_my_home(**kwargs)
        
        # Si es coach o student, continuar con la lógica de portal personalizado
        
        # Obtener URL de home según rol
        home_url = portal_utils.get_portal_home_url(user)
        role = portal_utils.get_user_role(user)
        
        _logger.info(f"User {user.login} - role: {role}, redirect URL: {home_url}")
        _logger.info(f"=== PORTAL REDIRECT END ===")
        
        return request.redirect(home_url)

    def _get_portal_access_rules(self, student):
        return portal_utils.get_student_portal_access_rules(student=student)

    def _prepare_portal_values(self, student, values=None, access=None):
        if values is None:
            values = {}
        if access is None:
            access = self._get_portal_access_rules(student)
        values.setdefault("student", student)
        values["portal_access"] = access
        values["portal_access_message"] = access.get("message")
        values["portal_access_level"] = access.get("level")
        return values

    def _prepare_access_response(self, student, access, capability=None):
        values = self._prepare_portal_values(
            student,
            {
                "page_name": "access_restricted",
                "required_capability": capability,
            },
            access=access,
        )
        return request.render("portal_student.portal_student_access_restricted", values)

    def _ensure_portal_access(self, student, capability=None):
        if portal_utils.must_change_password(request.env.user):
            return request.redirect("/my/welcome"), None
        access = self._get_portal_access_rules(student)
        if not access.get("allow_login", True):
            values = self._prepare_portal_values(
                student,
                {"page_name": "access_blocked"},
                access=access,
            )
            return request.render("portal_student.portal_student_access_blocked", values), access
        if capability:
            capabilities = access.get("capabilities", {})
            if isinstance(capability, (list, tuple, set)):
                allowed = any(capabilities.get(item, True) for item in capability)
            else:
                allowed = capabilities.get(capability, True)
            if not allowed:
                return self._prepare_access_response(student, access, capability=capability), access
        return None, access

    def _get_student(self):
        """Obtiene el estudiante vinculado al usuario portal actual."""
        return (
            request.env["benglish.student"]
            .sudo()
            .search([("user_id", "=", request.env.user.id)], limit=1)
        )

    def _error_message(self, exc, fallback=None):
        """Devuelve un mensaje seguro desde una excepción Odoo."""
        msg = getattr(exc, "name", None) or ""
        if not msg and getattr(exc, "args", None):
            msg = exc.args[0]
        if not msg:
            msg = str(exc)
        if msg:
            return msg
        return fallback or _("Ocurrió un error.")

    def _get_student_subjects(self, student):
        Subject = request.env["benglish.subject"].sudo()
        if not student:
            return Subject.browse()
        program, plan = self._get_student_program_plan(student)
        
        if program:
            subjects = Subject.search([
                ("program_id", "=", program.id),
                ("active", "=", True),
            ])
        else:
            subjects = student.enrollment_ids.sudo().mapped("subject_id")
        
        if plan and subjects:
            filtered = subjects.filtered(lambda s: plan in (s.plan_ids or []))
            if filtered:
                subjects = filtered
        
        return subjects

    def _get_student_program_plan(self, student):
        if not student:
            return False, False
        
        # 1. Buscar en matrículas activas
        active_enrollment = student.enrollment_ids.sudo().filtered(
            lambda e: e.state in ["draft", "pending", "enrolled", "in_progress", "active"]
        ).sorted("enrollment_date", reverse=True)[:1]
        if active_enrollment:
            program = active_enrollment.program_id or active_enrollment.plan_id.program_id
            plan = active_enrollment.plan_id
            _logger.info("[PROGRAM DEBUG] Found program from active enrollment: %s, plan: %s", 
                        program.name if program else 'N/A', plan.name if plan else 'N/A')
            return program, plan
        
        # 2. Buscar en campos directos del estudiante
        if student.program_id and student.plan_id:
            _logger.info("[PROGRAM DEBUG] Found program from student fields: %s, plan: %s",
                        student.program_id.name, student.plan_id.name)
            return student.program_id, student.plan_id
        
        # 3. Buscar en TODAS las matrículas (incluyendo completadas)
        all_enrollments = student.enrollment_ids.sudo().filtered(
            lambda e: e.state in ["draft", "pending", "enrolled", "in_progress", "active", "completed"]
        ).sorted("enrollment_date", reverse=True)[:1]
        if all_enrollments:
            program = all_enrollments.program_id or all_enrollments.plan_id.program_id
            plan = all_enrollments.plan_id
            _logger.info("[PROGRAM DEBUG] Found program from any enrollment: %s, plan: %s",
                        program.name if program else 'N/A', plan.name if plan else 'N/A')
            return program, plan
        
        # 4. Buscar si el estudiante tiene nivel/fase asignado y deducir el programa
        if hasattr(student, 'current_level_id') and student.current_level_id:
            level = student.current_level_id
            if level.phase_id and level.phase_id.program_id:
                program = level.phase_id.program_id
                # Buscar plan por defecto del programa
                plan = request.env['benglish.plan'].sudo().search([
                    ('program_id', '=', program.id)
                ], limit=1)
                _logger.info("[PROGRAM DEBUG] Found program from current_level: %s, plan: %s",
                            program.name, plan.name if plan else 'N/A')
                return program, plan
        
        _logger.info("[PROGRAM DEBUG] No program found for student: %s", student.name)
        return False, False

    def _get_student_current_unit(self, student):
        """
        Obtiene la unidad actual del estudiante para filtrar sesiones por audiencia.
        
        LÓGICA CORRECTA:
        - Si una unidad está completamente terminada (B-check + 4 Skills), avanzar a la siguiente
        - Si una unidad está parcialmente completada, permanecer en esa unidad
        - NO avanzar solo por completar el B-check
        
        Returns:
            int: Unidad actual del estudiante (1-24)
        """
        if not student:
            return 1
        
        # Obtener historial académico del estudiante
        History = request.env['benglish.academic.history'].sudo()
        completed_history = History.search([
            ('student_id', '=', student.id),
            ('attendance_status', '=', 'attended'),
            ('subject_id', '!=', False)
        ])
        
        if not completed_history:
            # Sin historial, empezar desde unidad 1
            return 1
        
        # Agrupar asignaturas completadas por unidad
        units_progress = {}
        for history in completed_history:
            subject = history.subject_id
            unit_num = subject.unit_number
            if not unit_num:
                continue
                
            if unit_num not in units_progress:
                units_progress[unit_num] = {
                    'bcheck': False,
                    'skills': 0,
                    'total_subjects': 0
                }
            
            units_progress[unit_num]['total_subjects'] += 1
            
            if subject.subject_category == 'bcheck':
                units_progress[unit_num]['bcheck'] = True
            elif subject.subject_category == 'bskills':
                # Contar CUALQUIER bskill completada, sin importar el número
                # Las skills son intercambiables en el catálogo
                units_progress[unit_num]['skills'] += 1
        
        # Determinar la unidad actual:
        # La unidad más alta que el estudiante ha comenzado (tiene al menos 1 clase)
        # PERO si completó todas las clases obligatorias, avanza a la siguiente
        if units_progress:
            highest_unit_started = max(units_progress.keys())
            
            # Verificar si la unidad más alta está COMPLETAMENTE terminada
            progress = units_progress[highest_unit_started]
            
            # Una unidad está completa si tiene B-check + 4 Skills (mínimo 5 clases)
            # O si tiene todas las clases requeridas según el plan
            is_unit_complete = progress['bcheck'] and progress['skills'] >= 4
            
            if is_unit_complete:
                # Unidad completa, avanzar a la siguiente
                return highest_unit_started + 1
            else:
                # Unidad incompleta, quedarse en esta
                return highest_unit_started
        
        # Fallback: usar el nivel actual
        if hasattr(student, 'current_level_id') and student.current_level_id:
            level = student.current_level_id
            if hasattr(level, 'min_unit') and level.min_unit:
                return level.min_unit
        
        # Default: unidad 1
        return 1

    def _get_effective_subject(self, session, student, check_completed=True, check_prereq=True):
        """
        Obtiene el subject efectivo para una sesión y estudiante.
        
        LÓGICA ESPECIAL PARA B-CHECKS CON INASISTENCIA:
        Si el estudiante tiene un B-check con 'absent' (no asistió), el sistema
        debe permitir agendar un NUEVO B-check de la MISMA unidad, no avanzar.
        """
        if not session or not student:
            return False
        
        # Verificar si es B-check
        base_subject = session.subject_id
        is_bcheck = self._is_prerequisite_subject(base_subject) if base_subject else False
        
        if is_bcheck and check_completed:
            # Para B-checks: Verificar si hay registro con 'absent' sin 'attended'
            History = request.env['benglish.academic.history'].sudo()
            Subject = request.env['benglish.subject'].sudo()
            
            # Buscar B-checks del mismo programa ordenados por unit_number
            program_id = base_subject.program_id.id if base_subject.program_id else False
            if program_id:
                bcheck_subjects = Subject.search([
                    ('subject_category', '=', 'bcheck'),
                    ('program_id', '=', program_id),
                ], order='unit_number asc')
                
                # Buscar la primera unidad donde tiene 'absent' pero NO 'attended'
                for bcheck_subj in bcheck_subjects:
                    has_attended = History.search_count([
                        ('student_id', '=', student.id),
                        ('subject_id', '=', bcheck_subj.id),
                        ('attendance_status', '=', 'attended')
                    ]) > 0
                    
                    has_absent = History.search_count([
                        ('student_id', '=', student.id),
                        ('subject_id', '=', bcheck_subj.id),
                        ('attendance_status', '=', 'absent')
                    ]) > 0
                    
                    # Si tiene 'absent' pero NO 'attended', debe agendar este B-check
                    if has_absent and not has_attended:
                        _logger.info(f"[BCHECK RECOVERY] Estudiante {student.id} tiene B-check Unidad {bcheck_subj.unit_number} con 'absent'. Forzando resolución a esta unidad.")
                        return bcheck_subj
                    
                    # Si NO tiene ni 'attended' ni 'absent', esta es la siguiente unidad pendiente
                    if not has_attended and not has_absent:
                        _logger.info(f"[BCHECK NEXT] Estudiante {student.id} siguiente B-check pendiente: Unidad {bcheck_subj.unit_number}")
                        return bcheck_subj
        
        # Lógica original para otros casos
        if hasattr(session, "resolve_effective_subject"):
            subject = session.resolve_effective_subject(
                student,
                check_completed=check_completed,
                raise_on_error=False,
                check_prereq=check_prereq,
            )
            return subject or session.subject_id
        return session.subject_id

    def _get_session_alias(self, session):
        if not session:
            return "Clase"
        if getattr(session, "student_alias", False):
            return session.student_alias
        subject = session.subject_id
        return subject.alias if subject and subject.alias else (subject.name if subject else "Clase")

    def _is_bcheck_session(self, session):
        """
        Verifica si una sesión es B-check u Oral Test.
        REGLA ESPECIAL: B-checks y Oral Tests SIEMPRE son virtuales, 
        independientemente de la modalidad del estudiante.
        """
        if not session:
            return False
        
        # Verificar por template
        if getattr(session, "template_id", False):
            if session.template_id.subject_category in ["bcheck", "oral_test"]:
                return True
        
        # Verificar por subject
        subject = session.subject_id
        return bool(subject and subject.subject_category in ["bcheck", "oral_test"])

    def _get_default_campus(self, student):
        if not student:
            return False, False
        if student.preferred_campus_id:
            return student.preferred_campus_id.sudo(), "preferred"
        active_enrollments = student.enrollment_ids.sudo().filtered(
            lambda e: e.state in ["draft", "pending", "enrolled", "in_progress", "active"]
        ).sorted("enrollment_date", reverse=True)
        if active_enrollments and active_enrollments[0].campus_id:
            return active_enrollments[0].campus_id.sudo(), "enrollment"
        return False, False

    def _get_latest_published_agenda(self, student, subjects=None, campus=None):
        Agenda = request.env["benglish.academic.agenda"].sudo()
        domain = [("state", "=", "published"), ("active", "=", True)]
        program, _plan = self._get_student_program_plan(student)
        if program:
            domain.append(("session_ids.program_id", "=", program.id))
        if subjects:
            domain += [
                "|",
                ("session_ids.template_id", "!=", False),
                ("session_ids.subject_id", "in", subjects.ids),
            ]
        if campus:
            domain_with_campus = list(domain) + [("campus_id", "=", campus.id)]
            agenda = Agenda.search(
                domain_with_campus,
                order="date_start desc, write_date desc, id desc",
                limit=1,
            )
            if agenda or campus.campus_type != "online":
                return agenda
        return Agenda.search(
            domain, order="date_start desc, write_date desc, id desc", limit=1
        )

    def _get_latest_published_agendas(self, student, subjects=None):
        Agenda = request.env["benglish.academic.agenda"].sudo()
        domain = [("state", "=", "published"), ("active", "=", True)]
        program, _plan = self._get_student_program_plan(student)
        if program:
            domain.append(("session_ids.program_id", "=", program.id))
        if subjects:
            domain += [
                "|",
                ("session_ids.template_id", "!=", False),
                ("session_ids.subject_id", "in", subjects.ids),
            ]
        agendas = Agenda.search(domain, order="campus_id asc, date_start desc, write_date desc, id desc")
        latest_by_campus = {}
        for agenda in agendas:
            campus_id = agenda.campus_id.id
            if campus_id and campus_id not in latest_by_campus:
                latest_by_campus[campus_id] = agenda.id
        return Agenda.browse(list(latest_by_campus.values()))

    def _get_published_agendas_for_range(self, student, start_date, end_date, subjects=None, campus=None):
        Agenda = request.env["benglish.academic.agenda"].sudo()
        domain = [("state", "=", "published"), ("active", "=", True)]
        program, _plan = self._get_student_program_plan(student)
        if program:
            domain.append(("session_ids.program_id", "=", program.id))
        if subjects:
            domain += [
                "|",
                ("session_ids.template_id", "!=", False),
                ("session_ids.subject_id", "in", subjects.ids),
            ]
        if start_date:
            domain.append(("date_end", ">=", start_date))
        if end_date:
            domain.append(("date_start", "<=", end_date))
        if campus:
            domain.append(("campus_id", "=", campus.id))
        return Agenda.search(domain, order="campus_id asc, date_start desc, write_date desc, id desc")

    def _base_session_domain(self, campus=None):
        """
        Dominio base para sesiones visibles en el portal (agenda publicada actual).
        
        ACTUALIZACIÓN CRÍTICA:
        - Las sesiones en estado 'done' (dictadas) NO aparecen en la agenda
        - Las sesiones en estado 'cancelled' (canceladas) NO aparecen en la agenda
        - Solo se muestran sesiones activas: 'active' o 'with_enrollment'
        
        Esto garantiza que las clases que ya fueron dictadas desaparezcan
        automáticamente de la agenda del estudiante.
        """
        Subject = request.env["benglish.subject"].sudo()
        student = self._get_student()
        if not student:
            return [("id", "=", 0)], False, Subject.browse()
        subjects = self._get_student_subjects(student)
        if campus is None:
            campus, _source = self._get_default_campus(student)
        agenda = self._get_latest_published_agenda(student, subjects, campus=campus)
        if not agenda:
            return [("id", "=", 0)], False, subjects
        if campus and campus.campus_type == "online" and agenda.campus_id and agenda.campus_id != campus:
            campus = agenda.campus_id
        domain = [
            ("is_published", "=", True),
            ("active", "=", True),
            ("agenda_id", "=", agenda.id),
            # FILTRO CRÍTICO: Solo sesiones activas, NO dictadas ni canceladas
            ("state", "in", ["active", "with_enrollment"]),
        ]
        program, _plan = self._get_student_program_plan(student)
        if program:
            domain.append(("program_id", "=", program.id))
        if subjects:
            domain += [
                "|",
                ("template_id", "!=", False),
                ("subject_id", "in", subjects.ids),
            ]
        if campus:
            domain.append(("campus_id", "=", campus.id))
        return domain, agenda, subjects

    def _is_optional_bskill(self, subject):
        return (
            subject
            and subject.subject_category == "bskills"
            and (subject.bskill_number or 0) > 4
        )

    def _is_join_allowed(self, session):
        if not session or not session.datetime_start:
            return False
        tz = pytz.timezone("America/Bogota")
        now_utc = fields.Datetime.now()
        now_utc = pytz.UTC.localize(now_utc) if now_utc.tzinfo is None else now_utc.astimezone(pytz.UTC)
        start_utc = fields.Datetime.to_datetime(session.datetime_start)
        start_utc = (
            pytz.UTC.localize(start_utc)
            if start_utc and start_utc.tzinfo is None
            else start_utc.astimezone(pytz.UTC)
        )
        now_local = now_utc.astimezone(tz)
        start_local = start_utc.astimezone(tz)
        delta = start_local - now_local
        return timedelta(minutes=-5) <= delta <= timedelta(minutes=5)

    def _format_session_label(self, session):
        if not session:
            return ""
        label = self._get_session_alias(session)
        date_label = session.date.strftime("%Y-%m-%d") if session.date else ""
        time_label = ""
        if session.time_start is not False:
            hours = int(session.time_start)
            minutes = int(round((session.time_start % 1) * 60))
            if minutes >= 60:
                hours += 1
                minutes = 0
            time_label = f"{hours:02d}:{minutes:02d}"
        parts = [p for p in [label, date_label, time_label] if p]
        return " | ".join(parts)

    def _is_prerequisite_subject(self, subject):
        """Determina si una asignatura es prerrequisito (BCheck)."""
        if not subject:
            return False
        name = (subject.name or "").lower()
        return (
            subject.subject_category == "bcheck"
            or subject.subject_classification == "prerequisite"
            or ("bcheck" in name or "b check" in name)
        )

    def _get_class_booking_policy(self, company_id=None):
        """Configuración centralizada en Benglish Academic para reglas de portal."""
        return request.env["benglish.academic.settings"].sudo().get_class_booking_policy(company_id=company_id)

    def _can_cancel_line(self, line):
        if not line or not line.start_datetime:
            return True
        policy = self._get_class_booking_policy()
        minutos_cancelar = max(0, int(policy.get("minutos_anticipacion_cancelar", 0) or 0))
        now_local = fields.Datetime.context_timestamp(request.env.user, fields.Datetime.now())
        start_local = fields.Datetime.context_timestamp(
            request.env.user,
            fields.Datetime.to_datetime(line.start_datetime),
        )
        return (start_local - now_local) >= timedelta(minutes=minutos_cancelar)

    def _ensure_session_enrollment(self, session, student):
        """
        Crea o actualiza el enrollment de un estudiante en una sesión.
        
        LÓGICA ESPECIAL PARA B-CHECKS CON INASISTENCIA:
        Si el estudiante tiene un B-check con 'absent', se debe forzar
        que el effective_subject_id sea de la unidad con 'absent', no la siguiente.
        """
        SessionEnrollment = request.env["benglish.session.enrollment"].sudo()
        
        # Obtener el effective_subject correcto usando nuestra lógica de recuperación
        effective_subject = self._get_effective_subject(
            session, student, check_completed=True, check_prereq=False
        )
        
        enrollment = SessionEnrollment.search(
            [("session_id", "=", session.id), ("student_id", "=", student.id)],
            limit=1,
        )
        if enrollment:
            # Actualizar effective_subject_id si es diferente
            if effective_subject and enrollment.effective_subject_id != effective_subject:
                _logger.info(f"[ENROLLMENT DEBUG] Actualizando effective_subject_id de {enrollment.effective_subject_id.name if enrollment.effective_subject_id else 'None'} a {effective_subject.name}")
                enrollment.write({'effective_subject_id': effective_subject.id})
            
            if enrollment.state == "pending":
                enrollment.action_confirm()
            elif enrollment.state == "cancelled":
                enrollment.write({"state": "pending"})
                if effective_subject:
                    enrollment.write({'effective_subject_id': effective_subject.id})
                enrollment.action_confirm()
            return enrollment

        # Crear nuevo enrollment con effective_subject_id explícito
        vals = {
            "session_id": session.id,
            "student_id": student.id,
            "state": "pending",
        }
        if effective_subject:
            vals['effective_subject_id'] = effective_subject.id
            _logger.info(f"[ENROLLMENT DEBUG] Creando enrollment con effective_subject_id={effective_subject.name} (Unit {effective_subject.unit_number})")
        
        enrollment = SessionEnrollment.create(vals)
        enrollment.action_confirm()
        return enrollment

    def _cancel_session_enrollment(self, session, student, target_state="cancelled"):
        """
        Cancela la inscripción de un estudiante en una sesión.
        Esto libera el cupo para que otro estudiante pueda agendarlo.
        
        Args:
            session: Sesión académica
            student: Estudiante
            target_state: Estado objetivo ('cancelled' o 'absent')
        
        Returns:
            enrollment o False
        """
        SessionEnrollment = request.env["benglish.session.enrollment"].sudo()
        enrollment = SessionEnrollment.search(
            [("session_id", "=", session.id), ("student_id", "=", student.id)],
            limit=1,
        )
        if not enrollment:
            _logger.info(f"[CANCEL ENROLLMENT] No enrollment found for session {session.id}, student {student.id}")
            return False
        
        _logger.info(f"[CANCEL ENROLLMENT] Processing enrollment {enrollment.id} - Session: {session.display_name}, Student: {student.name}, Current state: {enrollment.state}, Target: {target_state}")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # CRÍTICO: LIBERAR CUPO
        # ═══════════════════════════════════════════════════════════════════════════════
        # El enrolled_count se calcula solo con state="confirmed"
        # Al cambiar a cualquier otro estado (cancelled, absent), el cupo se libera
        # ═══════════════════════════════════════════════════════════════════════════════
        
        old_state = enrollment.state
        
        if target_state == "absent":
            if enrollment.state not in ["attended", "absent"]:
                enrollment.write({"state": "absent"})
                enrollment.flush_recordset()  # Forzar persistencia
                _logger.info(f"[CANCEL ENROLLMENT] ✅ Changed state from {old_state} to absent")
            return enrollment
        
        # Para target_state = "cancelled"
        if enrollment.state == "attended":
            _logger.info(f"[CANCEL ENROLLMENT] ⚠️ Cannot cancel - student already attended")
            return enrollment
        
        if enrollment.state == "cancelled":
            _logger.info(f"[CANCEL ENROLLMENT] Already cancelled")
            return enrollment
        
        # Cancelar y forzar liberación de cupo
        try:
            enrollment.action_cancel()
            _logger.info(f"[CANCEL ENROLLMENT] ✅ Successfully cancelled enrollment {enrollment.id} (was {old_state})")
        except Exception as e:
            _logger.warning(f"[CANCEL ENROLLMENT] action_cancel() failed: {e}, forcing state to cancelled")
            enrollment.write({"state": "cancelled"})
            enrollment.flush_recordset()  # Forzar persistencia
        
        # Invalidar caché de la sesión para forzar recálculo de available_spots
        session.invalidate_recordset(['enrolled_count', 'available_spots', 'is_full', 'occupancy_rate'])
        
        return enrollment

    def _apply_late_cancel_failure(self, student, session):
        """Registra falla por intento de cancelación fuera de tiempo."""
        if not student or not session:
            return False
        SessionEnrollment = request.env["benglish.session.enrollment"].sudo()
        existing = SessionEnrollment.search(
            [("session_id", "=", session.id), ("student_id", "=", student.id)],
            limit=1,
        )
        note = "Late cancel from portal"
        if existing:
            vals = {}
            if existing.state != "absent":
                vals["state"] = "absent"
            if "notes" in existing._fields:
                vals["notes"] = note
            if vals:
                existing.write(vals)
            return existing
        create_vals = {
            "session_id": session.id,
            "student_id": student.id,
            "state": "absent",
        }
        if "notes" in SessionEnrollment._fields:
            create_vals["notes"] = note
        return SessionEnrollment.create(create_vals)

    def _compute_stats(self, student, enrollments):
        """Calcula indicadores de estado académico usando datos reales."""
        completed = enrollments.filtered(lambda e: e.state == "completed")
        graded = [e.final_grade for e in completed if e.final_grade]
        avg_grade = sum(graded) / len(graded) if graded else 0
        progress = 0
        if student.total_enrollments:
            progress = int((student.completed_enrollments / student.total_enrollments) * 100)

        return {
            "total_enrollments": student.total_enrollments,
            "active_enrollments": student.active_enrollments,
            "completed_enrollments": student.completed_enrollments,
            "failed_enrollments": student.failed_enrollments,
            "avg_grade": round(avg_grade, 2) if avg_grade else False,
            "progress": progress,
        }

    def _prepare_profile_data(self, student):
        partner = student.partner_id.sudo() if student.partner_id else False
        return {
            "name": student.name,
            "document": student.student_id_number or "",
            "email": student.email or (partner.email if partner else ""),
            "phone": student.phone or student.mobile or (partner.phone if partner else ""),
            "mobile": student.mobile or (partner.mobile if partner else ""),
            "address": student.address or (partner.street if partner else ""),
            "city": student.city or (partner.city if partner else ""),
            "country": student.country_id.name if student.country_id else (partner.country_id.name if partner and partner.country_id else ""),
            "program": student.program_id.name if student.program_id else "",
            "plan": student.plan_id.name if student.plan_id else "",
            "current_phase": student.current_phase_id.name if student.current_phase_id else "",
            "current_level": student.current_level_id.name if student.current_level_id else "",
            "state": student.state,
            "profile_state": student.profile_state_id.name if student.profile_state_id else "",
            "profile_state_message": student.profile_state_id.student_message if student.profile_state_id else "",
        }

    def _prepare_materials(self, subject):
        """Recupera recursos/links asociados a la asignatura de forma segura."""
        materials = []
        urls_field = getattr(subject.sudo(), "resource_urls", False)
        if urls_field and isinstance(urls_field, str):
            for idx, raw in enumerate([u.strip() for u in urls_field.splitlines() if u.strip()]):
                materials.append({"name": f"Recurso {idx + 1}", "url": raw})

        resource_links = getattr(subject.sudo(), "resource_link_ids", False)
        if resource_links:
            for link in resource_links.sudo():
                materials.append(
                    {
                        "name": getattr(link, "name", False) or getattr(link, "display_name", ""),
                        "url": getattr(link, "url", False) or getattr(link, "link_url", False),
                    }
                )

        try:
            Attachment = request.env["ir.attachment"].sudo()
            attachments = Attachment.search(
                [("res_model", "=", subject._name), ("res_id", "=", subject.id), ("type", "=", "url")]
            )
            for att in attachments:
                materials.append({"name": att.name, "url": att.url})
        except Exception:
            pass

        seen = set()
        unique = []
        for item in materials:
            url = item.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            unique.append(item)
        return unique

    def _prepare_resources(self, active_enrollments):
        """Prepara enlaces y recursos de clases virtuales."""
        Session = request.env["benglish.academic.session"].sudo()
        now = fields.Datetime.now()
        window_start = now - timedelta(minutes=5)
        base_domain, agenda, subjects = self._base_session_domain()
        resources = []
        for enrollment in active_enrollments.sudo():
            group = enrollment.group_id.sudo()
            next_session = Session.sudo().search(
                base_domain + [
                    ("subject_id", "=", enrollment.subject_id.id),
                    ("campus_id", "=", enrollment.campus_id.id),
                    ("datetime_start", ">=", window_start),
                ],
                order="datetime_start asc",
                limit=1,
            )
            meeting_link = (
                (next_session.teacher_meeting_link if next_session else False)
                or (next_session.meeting_link if next_session else False)
            )
            meeting_platform = (
                getattr(next_session, "meeting_platform", False)
                or (group and group.meeting_platform)
                or (group and group.subcampus_id and group.subcampus_id.sudo().meeting_platform)
            )
            subject = enrollment.subject_id.sudo()
            subject_alias = subject.alias if subject and subject.alias else (subject.name if subject else "")
            join_allowed = self._is_join_allowed(next_session) if next_session else False
            # Obtener modalidad de la sesión o del grupo
            delivery_mode = (
                next_session.delivery_mode if next_session
                else (group.delivery_mode if group else "presential")
            )
            resources.append(
                {
                    "enrollment": enrollment,
                    "group": group,
                    "subject": subject,
                    "subject_alias": subject_alias,
                    "next_session": next_session,
                    "meeting_link": meeting_link,
                    "meeting_platform": meeting_platform,
                    "campus": enrollment.campus_id.sudo(),
                    "materials": self._prepare_materials(subject),
                    "join_allowed": join_allowed,
                    "delivery_mode": delivery_mode,
                }
            )
        return resources

    def _prepare_dashboard_data(self, student, fallback_to_published=True):
        """Prepara datos del dashboard tomando prioridad de la agenda planificada.

        Si fallback_to_published es False, solo se consideran clases agendadas por el estudiante.
        """
        enrollments = student.enrollment_ids.sudo()
        active_enrollments = enrollments.filtered(lambda e: e.state in ["enrolled", "in_progress"])
        Session = request.env["benglish.academic.session"].sudo()
        Plan = request.env["portal.student.weekly.plan"].sudo()
        now = fields.Datetime.now()
        window_start = now - timedelta(minutes=5)
        today = fields.Date.context_today(request.env.user)
        base_domain, agenda, subjects = self._base_session_domain()

        plan = Plan.get_or_create_for_student(student, today)
        scheduled_lines = plan.line_ids.sudo().sorted(key=lambda l: l.start_datetime or now)

        next_scheduled = False
        for line in scheduled_lines:
            if line.start_datetime and line.start_datetime >= window_start:
                next_scheduled = line
                break
        if not next_scheduled and scheduled_lines:
            next_scheduled = scheduled_lines[0]

        today_scheduled_sessions = scheduled_lines.filtered(lambda ln: ln.date == today).mapped("session_id")

        published_next = False
        published_today = Session.browse()

        if fallback_to_published:
            published_next = Session.search(
                base_domain + [("datetime_start", ">=", window_start)],
                order="datetime_start asc",
                limit=1,
            )
            published_today = Session.search(
                base_domain + [("date", "=", today)],
                order="datetime_start asc",
            )

        programs = active_enrollments.mapped("program_id")
        if not programs and student.program_id:
            programs = student.program_id

        next_session = next_scheduled.session_id if next_scheduled else (published_next if fallback_to_published else False)

        return {
            "enrollments": enrollments,
            "active_enrollments": active_enrollments,
            "plan": plan,
            "scheduled_lines": scheduled_lines,
            "next_session": next_session,
            "next_session_source": "agenda" if next_scheduled else ("publicada" if published_next else False),
            "today_sessions": today_scheduled_sessions or (published_today if fallback_to_published else Session.browse()),
            "today_sessions_source": "agenda" if today_scheduled_sessions else ("publicada" if (fallback_to_published and published_today) else False),
            "programs": programs,
            "next_session_join_allowed": self._is_join_allowed(next_session) if next_session else False,
        }

    def _prepare_week(self, start_param=None, filter_student_subjects=True, campus=None, agendas=None):
        """Devuelve rango semanal y sesiones publicadas.
        
        Args:
            start_param: Fecha de inicio (string o date)
            filter_student_subjects: Si True, filtra por asignaturas del estudiante.
                                    Si False, muestra TODAS las sesiones publicadas.
            campus: Sede seleccionada (para agenda publicada mas reciente por sede).
            agendas: Recordset de agendas publicadas a usar (p. ej., por ciudad).
        """
        Session = request.env["benglish.academic.session"].sudo()
        try:
            start_date = (
                fields.Date.from_string(start_param) if start_param else fields.Date.today()
            )
        except Exception:
            start_date = fields.Date.today()

        # Normalizar al lunes de la semana
        if isinstance(start_date, str):
            start_date = fields.Date.from_string(start_date)
        monday = start_date - timedelta(days=start_date.weekday())
        start_dt = datetime.combine(monday, datetime.min.time())
        end_dt = start_dt + timedelta(days=7)

        # Construir dominio base
        if filter_student_subjects:
            student = self._get_student()
            if not student:
                domain = [("id", "=", 0)]
            else:
                subjects = self._get_student_subjects(student)
                program, _plan = self._get_student_program_plan(student)
                if agendas is None:
                    agendas = self._get_published_agendas_for_range(
                        student,
                        monday,
                        monday + timedelta(days=6),
                        subjects=subjects,
                        campus=campus,
                    )
                domain = [
                    ("is_published", "=", True),
                    ("active", "=", True),
                ]
                if program:
                    domain.append(("program_id", "=", program.id))
                if subjects:
                    domain += [
                        "|",
                        ("template_id", "!=", False),
                        ("subject_id", "in", subjects.ids),
                    ]
                if campus:
                    domain.append(("campus_id", "=", campus.id))
                if agendas is not None:
                    if agendas:
                        domain.append(("agenda_id", "in", agendas.ids))
                    else:
                        domain.append(("id", "=", 0))
        else:
            domain = [
                ("is_published", "=", True),
                ("active", "=", True),
            ]

        sessions = Session.sudo().search(
            domain + [
                ("datetime_start", ">=", fields.Datetime.to_string(start_dt)),
                ("datetime_start", "<", fields.Datetime.to_string(end_dt)),
                ("state", "in", ["active", "with_enrollment"]),  # Solo sesiones activas
            ],
            order="datetime_start asc",
        )

        agenda = []
        for offset in range(7):
            day = monday + timedelta(days=offset)
            day_sessions = sessions.filtered(lambda s, d=day: s.date == d)
            agenda.append(
                {
                    "date": day,
                    "sessions": day_sessions,
                }
            )
        return {
            "monday": monday,
            "sunday": monday + timedelta(days=6),
            "sessions": sessions,
            "agenda_by_day": agenda,
        }

    def _prepare_program_structure(self, student):
        """Construye jerarquía Programa -> Plan -> Fase -> Nivel -> Asignaturas con detalle de docente y sede."""
        enrollments = student.enrollment_ids.sudo().filtered(
            lambda e: e.state in ["draft", "pending", "enrolled", "in_progress", "active", "completed"]
        )
        subjects = enrollments.mapped("subject_id")
        levels = subjects.mapped("level_id")
        phases = levels.mapped("phase_id")
        programs = phases.mapped("program_id")
        
        # Obtener SOLO los planes en los que el estudiante está matriculado
        plans = enrollments.mapped("plan_id")

        structure = []
        
        # Si hay matrículas activas, construir estructura basada en matrículas
        if enrollments:
            for program in programs.sorted(key=lambda p: p.sequence or 0):
                program_plans = plans.filtered(lambda p: p.program_id == program).sorted(
                    key=lambda p: p.sequence or 0
                )
                plan_items = []
                for plan in program_plans:
                    # Las fases están relacionadas con el programa, no con el plan directamente
                    # Filtrar fases del programa que tengan niveles con asignaturas del estudiante
                    plan_phases = phases.filtered(lambda ph: ph.program_id == program).sorted(
                        key=lambda ph: ph.sequence or 0
                    )
                    phase_items = []
                    for phase in plan_phases:
                        phase_levels = levels.filtered(lambda lv: lv.phase_id == phase).sorted(
                            key=lambda lv: lv.sequence or 0
                        )
                        level_items = []
                        for level in phase_levels:
                            level_subjects = subjects.filtered(lambda sb: sb.level_id == level).sorted(
                                key=lambda sb: sb.sequence or 0
                            )
                            # TPE14: Preparar información de cada asignatura con docente y sede
                            subject_details = []
                            for subject in level_subjects:
                                # Buscar matrícula(s) activa(s) para esta asignatura
                                subject_enrollments = enrollments.filtered(
                                    lambda e: e.subject_id.id == subject.id
                                ).sorted(key=lambda e: e.enrollment_date or datetime.min, reverse=True)
                                
                                # Obtener la matrícula más reciente (solo si existe)
                                enrollment = subject_enrollments[:1] if subject_enrollments else request.env['benglish.enrollment'].sudo().browse()
                                
                                subject_info = {
                                    "subject": subject,
                                    "enrollment": enrollment if enrollment else False,
                                    "campus": enrollment.campus_id if enrollment else None,
                                    "subcampus": enrollment.subcampus_id if enrollment else None,
                                    "group": enrollment.group_id if enrollment else None,
                                    "delivery_mode": enrollment.delivery_mode if enrollment else False,
                                    "state": enrollment.state if enrollment else False,
                                }
                                subject_details.append(subject_info)
                            
                            level_items.append(
                                {
                                    "level": level,
                                    "subjects": level_subjects,  # Mantenemos por compatibilidad
                                    "subject_details": subject_details,  # Nueva estructura con detalles
                                }
                            )
                        phase_items.append({"phase": phase, "levels": level_items})
                    plan_items.append({"plan": plan, "phases": phase_items})
                structure.append({"program": program, "plans": plan_items})
        else:
            # Si no hay matrículas, mostrar estructura básica del programa/plan asignado al estudiante
            _logger.info("[PROGRAM DEBUG] No enrollments found, trying to get program from student fields")
            student_program, student_plan = self._get_student_program_plan(student)
            _logger.info("[PROGRAM DEBUG] student_program: %s, student_plan: %s", 
                        student_program.name if student_program else 'N/A',
                        student_plan.name if student_plan else 'N/A')
            
            if student_program and student_plan:
                # Obtener modalidad preferida del estudiante
                delivery_mode = student.preferred_delivery_mode or 'presencial'
                
                # Crear estructura básica - mostrar solo el nivel actual del estudiante
                phase_items = []
                
                # Intentar obtener la fase del estudiante
                student_phase = None
                student_level = None
                
                if hasattr(student, 'current_phase_id') and student.current_phase_id:
                    student_phase = student.current_phase_id
                if hasattr(student, 'current_level_id') and student.current_level_id:
                    student_level = student.current_level_id
                    if not student_phase and student_level.phase_id:
                        student_phase = student_level.phase_id
                
                # Si tiene fase/nivel, mostrar solo eso
                if student_phase and student_level:
                    level_items = [{
                        "level": student_level,
                        "subjects": request.env['benglish.subject'].sudo().browse(),
                        "subject_details": [{
                            "subject": None,
                            "enrollment": False,
                            "campus": None,
                            "subcampus": None,
                            "group": None,
                            "delivery_mode": delivery_mode,
                            "state": False,
                        }],
                    }]
                    phase_items = [{"phase": student_phase, "levels": level_items}]
                else:
                    # Buscar todas las fases del programa
                    phases = request.env['benglish.phase'].sudo().search([
                        ('program_id', '=', student_program.id)
                    ], order='sequence')
                    
                    for phase in phases:
                        levels = request.env['benglish.level'].sudo().search([
                            ('phase_id', '=', phase.id)
                        ], order='sequence')
                        
                        level_items = []
                        for level in levels:
                            # Preparar información básica del nivel
                            subject_details = [{
                                "subject": None,
                                "enrollment": False,
                                "campus": None,
                                "subcampus": None,
                                "group": None,
                                "delivery_mode": delivery_mode,
                                "state": False,
                            }]
                            
                            level_items.append({
                                "level": level,
                                "subjects": request.env['benglish.subject'].sudo().browse(),
                                "subject_details": subject_details,
                            })
                        
                        phase_items.append({"phase": phase, "levels": level_items})
                
                plan_items = [{"plan": student_plan, "phases": phase_items}]
                structure.append({"program": student_program, "plans": plan_items})
                _logger.info("[PROGRAM DEBUG] Built structure with %d programs", len(structure))
            else:
                _logger.info("[PROGRAM DEBUG] No program/plan found for student, structure will be empty")
        
        return structure

    def _serialize_student(self, student):
        """Serializa datos personales y académicos básicos."""
        summary = {}
        if hasattr(student, "get_profile_permissions_summary"):
            summary = student.sudo().get_profile_permissions_summary() or {}

        return {
            "id": student.id,
            "name": student.name,
            "code": student.code,
            "email": student.email,
            "phone": student.phone or student.mobile,
            "mobile": student.mobile,
            "gender": student.gender,
            "birth_date": fields.Date.to_string(student.birth_date) if student.birth_date else False,
            "city": student.city,
            "country": student.country_id.name if student.country_id else "",
            "preferred_delivery_mode": student.preferred_delivery_mode,
            "preferred_campus": student.preferred_campus_id.name if student.preferred_campus_id else "",
            "program": student.program_id.name if student.program_id else "",
            "plan": student.plan_id.name if student.plan_id else "",
            "current_phase": student.current_phase_id.name if student.current_phase_id else "",
            "current_level": student.current_level_id.name if student.current_level_id else "",
            "profile_state": summary,
            "al_dia_en_pagos": student.al_dia_en_pagos,
            "monto_pendiente": student.monto_pendiente,
            "facturas_vencidas": student.facturas_vencidas_count,
            "tiene_congelamiento_activo": student.tiene_congelamiento_activo,
            "dias_congelamiento_disponibles": student.dias_congelamiento_disponibles,
        }

    def _serialize_enrollment(self, enrollment):
        """Serializa matrículas para consumo en el portal/API."""
        subject = enrollment.subject_id
        subject_label = subject.alias if subject and subject.alias else (subject.name if subject else "Matrícula")
        return {
            "id": enrollment.id,
            "name": subject_label,
            "state": enrollment.state,
            "enrollment_date": fields.Date.to_string(enrollment.enrollment_date) if enrollment.enrollment_date else False,
            "start_date": fields.Date.to_string(enrollment.start_date) if enrollment.start_date else False,
            "end_date": fields.Date.to_string(enrollment.end_date) if enrollment.end_date else False,
            "program": enrollment.program_id.name if enrollment.program_id else "",
            "plan": enrollment.plan_id.name if enrollment.plan_id else "",
            "phase": enrollment.phase_id.name if enrollment.phase_id else "",
            "level": enrollment.level_id.name if enrollment.level_id else "",
            "subject": subject_label if subject_label else "",
            "group": enrollment.group_id.name if enrollment.group_id else "",
            "campus": enrollment.campus_id.name if enrollment.campus_id else "",
            "delivery_mode": enrollment.delivery_mode,
            "coach": "",
            "final_grade": enrollment.final_grade,
        }

    def _serialize_session(self, session):
        """Serializa sesiones publicadas para agenda/horarios."""
        student = self._get_student()
        subject = self._get_effective_subject(session, student, check_completed=False, check_prereq=False) if student else session.subject_id
        subject_alias = self._get_session_alias(session)
        is_prerequisite = False
        if subject:
            is_prerequisite = (
                subject.subject_category == "bcheck"
                or subject.subject_classification == "prerequisite"
                or (subject.name and ("bcheck" in subject.name.lower() or "b check" in subject.name.lower()))
            )
        return {
            "id": session.id,
            "name": self._format_session_label(session),
            "subject": subject_alias,
            "subject_name": subject_alias,
            "start": fields.Datetime.to_string(session.datetime_start) if session.datetime_start else False,
            "end": fields.Datetime.to_string(session.datetime_end) if session.datetime_end else False,
            "date": fields.Date.to_string(session.date) if session.date else False,
            "delivery_mode": session.delivery_mode,
            "campus": session.campus_id.name if session.campus_id else "",
            "subcampus": session.subcampus_id.name if session.subcampus_id else "",
            "meeting_link": session.teacher_meeting_link or session.meeting_link,
            "meeting_platform": getattr(session, "meeting_platform", False),
            "is_published": session.is_published,
            "state": session.state,
            "is_prerequisite": is_prerequisite,
        }

    def _serialize_resource(self, resource):
        """Serializa recursos preparados a partir de matr?culas activas."""
        enrollment = resource.get("enrollment")
        session = resource.get("next_session")
        subject_alias = resource.get("subject_alias") or (resource.get("subject").name if resource.get("subject") else "")
        return {
            "enrollment": enrollment.id if enrollment else False,
            "group": resource.get("group").name if resource.get("group") else "",
            "subject": subject_alias,
            "subject_name": resource.get("subject").name if resource.get("subject") else "",
            "next_session": session and self._serialize_session(session) or False,
            "meeting_link": resource.get("meeting_link"),
            "meeting_platform": resource.get("meeting_platform"),
            "campus": resource.get("campus").name if resource.get("campus") else "",
            "materials": resource.get("materials") or [],
            "join_allowed": resource.get("join_allowed", False),
        }

    def _serialize_campus(self, campus):
        """Serializa sedes de forma segura para el portal."""
        return {
            "id": campus.id,
            "name": campus.name,
            "city": campus.city_name or "",
            "country": campus.country_id.name if campus.country_id else "",
        }

    def _serialize_group(self, group):
        """Serializa grupos sin exponer datos sensibles (solo lectura)."""
        return {
            "id": group.id,
            "name": group.name,
            "code": getattr(group, "code", "") or "",
            "delivery_mode": getattr(group, "delivery_mode", "") or "",
            "campus": group.campus_id.name if getattr(group, "campus_id", False) else "",
            "subcampus": group.subcampus_id.name if getattr(group, "subcampus_id", False) else "",
            "meeting_link": getattr(group, "meeting_link", False),
            "meeting_platform": getattr(group, "meeting_platform", False),
        }

    def _gather_overview(self, student):
        """Compone datasets reutilizables para vistas y APIs."""
        enrollments = student.enrollment_ids.sudo()
        active_enrollments = enrollments.filtered(lambda e: e.state in ["enrolled", "in_progress"]).sorted(
            key=lambda e: e.enrollment_date or date.min, reverse=True
        )
        Session = request.env["benglish.academic.session"].sudo()
        now = fields.Datetime.now()
        today = fields.Date.context_today(request.env.user)
        base_domain, agenda, subjects = self._base_session_domain()

        next_sessions = Session.search(
            base_domain + [("datetime_start", ">=", now)],
            order="datetime_start asc",
            limit=5,
        )
        today_sessions = Session.search(
            base_domain + [("date", "=", today)],
            order="datetime_start asc",
        )

        profile_state = {}
        if hasattr(student, "get_profile_permissions_summary"):
            profile_state = student.sudo().get_profile_permissions_summary() or {}

        return {
            "student": student,
            "enrollments": enrollments,
            "active_enrollment": active_enrollments[:1],
            "active_enrollments": active_enrollments,
            "stats": self._compute_stats(student, enrollments),
            "next_sessions": next_sessions,
            "today_sessions": today_sessions,
            "resources": self._prepare_resources(active_enrollments),
            "profile_state": profile_state,
        }

    @http.route("/my/student", type="http", auth="user", website=True)
    def portal_student_home(self, **kwargs):
        """
        Home del portal del estudiante.
        Valida que el usuario sea estudiante antes de mostrar contenido.
        """
        user = request.env.user
        _logger.info(f"=== /my/student accessed by user: {user.login} (ID: {user.id}) ===")
        
        student = self._get_student()
        _logger.info(f"Student found for user {user.login}: {bool(student)}")
        
        if not student:
            # Verificar si el usuario es coach (para redirigir correctamente)
            is_coach = portal_utils.is_coach(user)
            _logger.info(f"User {user.login} is coach: {is_coach}")
            
            if is_coach:
                _logger.info(f"Redirecting coach {user.login} to /my/coach")
                return request.redirect('/my/coach')
            
            # Usuario portal sin rol: mostrar página de error
            _logger.info(f"User {user.login} has no student/coach record, showing error page")
            return request.render(
                "portal_student.portal_student_missing",
                {"page_name": "student_missing"},
            )

        guard_response, access = self._ensure_portal_access(student, capability="can_use_apps")
        if guard_response:
            return guard_response

        dashboard = self._prepare_dashboard_data(student, fallback_to_published=False)
        enrollments = dashboard.get("enrollments") or student.enrollment_ids.sudo()
        active_enrollments = dashboard.get("active_enrollments") or request.env["benglish.enrollment"].sudo()


        values = {
            "page_name": "home",
            "student": student,
            "active_enrollments": active_enrollments,
            "next_session": dashboard.get("next_session"),
            "next_session_source": dashboard.get("next_session_source"),
            "next_session_join_allowed": dashboard.get("next_session_join_allowed"),
            "today_sessions": dashboard.get("today_sessions"),
            "today_sessions_source": dashboard.get("today_sessions_source"),
            "programs": dashboard.get("programs"),
            "stats": self._compute_stats(student, enrollments),
            "plan": dashboard.get("plan"),
            "scheduled_lines": dashboard.get("scheduled_lines"),
            "resources": self._prepare_resources(active_enrollments)[:4],
        }
        values = self._prepare_portal_values(student, values, access=access)
        return request.render("portal_student.portal_student_home", values)

    @http.route("/my/student/agenda", type="http", auth="user", website=True)
    def portal_student_agenda(self, **kwargs):
        student = self._get_student()
        if not student:
            if portal_utils.is_coach():
                return request.redirect('/my/coach')
            return request.redirect("/my")

        guard_response, access = self._ensure_portal_access(student, capability="can_schedule")
        if guard_response:
            return guard_response
        
        # HU-E9: Obtener filtros desde parámetros
        filter_campus_id = kwargs.get("filter_campus_id")
        filter_city = kwargs.get("filter_city")
        filter_mode = kwargs.get("filter_mode")  # presential, virtual, hybrid
        if filter_mode == "presencial":
            filter_mode = "presential"
        clear_filter = kwargs.get("clear_filter")  # 1 para limpiar
        
        # SIEMPRE filtrar por asignaturas del plan del estudiante
        filter_by_student_subjects = True
        
        # Obtener plan de la semana
        plan_model = request.env["portal.student.weekly.plan"].sudo()
        
        # Determinar fecha de inicio
        start_param = kwargs.get("start")
        try:
            start_date = (
                fields.Date.from_string(start_param) if start_param else fields.Date.today()
            )
        except Exception:
            start_date = fields.Date.today()
        
        if isinstance(start_date, str):
            start_date = fields.Date.from_string(start_date)
        monday = start_date - timedelta(days=start_date.weekday())
        
        plan = plan_model.get_or_create_for_student(student, monday)

        student_is_virtual = student.preferred_delivery_mode == "virtual"

        # HU-E9: Actualizar filtros en el plan
        selected_campus = False
        selected_city = False
        using_default_campus = False
        default_campus_source = False
        if clear_filter == "1":
            # Limpiar filtros persistidos
            plan.sudo().write({"filter_campus_id": False, "filter_city": False})
        elif filter_campus_id:
            try:
                campus_id_int = int(filter_campus_id)
                campus = request.env["benglish.campus"].sudo().browse(campus_id_int)
                if campus.exists():
                    selected_campus = campus
                    selected_city = campus.city_name or False
                    plan.sudo().write(
                        {"filter_campus_id": campus_id_int, "filter_city": selected_city}
                    )
            except (ValueError, TypeError):
                pass
        elif filter_city:
            selected_city = filter_city
            plan.sudo().write({"filter_campus_id": False, "filter_city": filter_city})
        else:
            # Si no vienen filtros en la request, usar los guardados en el plan (si existen)
            if plan.filter_campus_id:
                selected_campus = plan.filter_campus_id
                selected_city = plan.filter_city or selected_campus.city_name
            elif plan.filter_city:
                selected_city = plan.filter_city

        # Si no hay filtros seleccionados, usar la sede preferida o la de la matrícula activa
        if not selected_campus and not selected_city:
            default_campus, default_campus_source = self._get_default_campus(student)
            if default_campus:
                selected_campus = default_campus
                selected_city = selected_campus.city_name or False
                using_default_campus = True

        Campus = request.env["benglish.campus"].sudo()
        Session = request.env["benglish.academic.session"].sudo()

        student_subjects = self._get_student_subjects(student)
        program, _plan = self._get_student_program_plan(student)
        agendas = self._get_published_agendas_for_range(
            student,
            monday,
            monday + timedelta(days=6),
            subjects=student_subjects,
        )
        if not agendas:
            agendas = self._get_latest_published_agendas(student, student_subjects)

        # DEBUG: Log para diagnóstico
        _logger.info("DEBUG SEDES - Estudiante: %s (ID: %s)", student.name, student.id)

        campus_domain = [
            ("is_published", "=", True),
            ("active", "=", True),
        ]
        if student_subjects:
            campus_domain += [
                "|",
                ("template_id", "!=", False),
                ("subject_id", "in", student_subjects.ids),
            ]
        if program:
            campus_domain.append(("program_id", "=", program.id))
        if agendas:
            campus_domain.append(("agenda_id", "in", agendas.ids))
        else:
            campus_domain.append(("id", "=", 0))

        available_sessions_for_campuses = Session.search(campus_domain)
        _logger.info("DEBUG SEDES - Sesiones publicadas encontradas: %s", len(available_sessions_for_campuses))

        campus_ids = available_sessions_for_campuses.mapped("campus_id").ids
        unique_campus_ids = list(set(campus_ids))
        _logger.info("DEBUG SEDES - Campus IDs unicos: %s - %s", len(unique_campus_ids), unique_campus_ids)

        # Verificar si hay B-checks o Oral Tests en sedes virtuales (SIEMPRE accesibles para todos)
        has_bcheck_or_oral = any(
            self._is_bcheck_session(s) and s.campus_id.campus_type == "online"
            for s in available_sessions_for_campuses
            if s.campus_id
        )
        
        available_campuses_domain = [
            ("id", "in", campus_ids),
            ("active", "=", True),
        ]
        
        # Filtrar sedes según modalidad del estudiante
        # EXCEPCIÓN: Si hay B-checks/Oral Tests en sedes virtuales, NO filtrar (mostrar todo)
        if student_is_virtual and not has_bcheck_or_oral:
            # NUEVO: Estudiantes virtuales ven TODAS las sedes que tengan sesiones virtuales o híbridas
            # No limitamos solo a campus_type="online", sino a sedes con horarios virtuales disponibles
            virtual_campus_ids = set()
            for session in available_sessions_for_campuses:
                if session.delivery_mode in ['virtual', 'hybrid'] and session.campus_id:
                    virtual_campus_ids.add(session.campus_id.id)
            
            if virtual_campus_ids:
                available_campuses_domain.append(("id", "in", list(virtual_campus_ids)))
            else:
                # Fallback: si no hay sesiones virtuales/híbridas, mostrar sedes tipo "online"
                available_campuses_domain.append(("campus_type", "=", "online"))
        elif not student_is_virtual and student.preferred_delivery_mode == "presential" and not has_bcheck_or_oral:
            # Estudiantes presenciales puros solo ven sedes físicas (NO virtuales)
            # EXCEPTO cuando hay B-checks/Oral Tests virtuales disponibles
            available_campuses_domain.append(("campus_type", "!=", "online"))
        # Híbridos y casos con B-checks/Oral Tests ven todas las sedes
        
        available_campuses = Campus.search(
            [
                *available_campuses_domain,
            ],
            order="city_name, name",
        )
        if not available_campuses and program and agendas:
            fallback_domain = [
                ("is_published", "=", True),
                ("active", "=", True),
                ("program_id", "=", program.id),
                ("agenda_id", "in", agendas.ids),
            ]
            fallback_sessions = Session.search(fallback_domain)
            
            # Verificar si hay B-checks o Oral Tests en sedes virtuales en el fallback
            has_bcheck_or_oral_fallback = any(
                self._is_bcheck_session(s) and s.campus_id.campus_type == "online"
                for s in fallback_sessions
                if s.campus_id
            )
            
            fallback_campus_ids = fallback_sessions.mapped("campus_id").ids
            fallback_campus_domain = [
                ("id", "in", fallback_campus_ids),
                ("active", "=", True),
            ]
            
            # Aplicar mismo filtro que arriba
            if student_is_virtual and not has_bcheck_or_oral_fallback:
                # Fallback: estudiantes virtuales ven sedes que tengan sesiones virtuales/híbridas
                virtual_fallback_campus_ids = set()
                for session in fallback_sessions:
                    if session.delivery_mode in ['virtual', 'hybrid'] and session.campus_id:
                        virtual_fallback_campus_ids.add(session.campus_id.id)
                
                if virtual_fallback_campus_ids:
                    fallback_campus_domain.append(("id", "in", list(virtual_fallback_campus_ids)))
                else:
                    fallback_campus_domain.append(("campus_type", "=", "online"))
            elif not student_is_virtual and student.preferred_delivery_mode == "presential" and not has_bcheck_or_oral_fallback:
                fallback_campus_domain.append(("campus_type", "!=", "online"))
            
            available_campuses = Campus.search(fallback_campus_domain, order="city_name, name")
        _logger.info("DEBUG SEDES - Sedes disponibles (activas): %s", len(available_campuses))
        for camp in available_campuses:
            _logger.info("DEBUG SEDES -    - %s (ID: %s, Ciudad: %s)", camp.name, camp.id, camp.city_name)

        # Agrupar sedes por ciudad
        cities = {}
        for campus in available_campuses:
            city = campus.city_name or 'Virtual'
            # Normalizar "Sin ciudad" a "Virtual"
            if city.lower() == 'sin ciudad':
                city = 'Virtual'
            if city not in cities:
                cities[city] = []
            cities[city].append(campus)

        # Fallback: si no hay sede definida, usar la primera sede disponible
        if not selected_campus and not selected_city and not using_default_campus and available_campuses:
            selected_campus = available_campuses[0]
            selected_city = selected_campus.city_name or False
            using_default_campus = True
            default_campus_source = "agenda"

        # NUEVO: Solo asignar sede virtual automáticamente si NO hay filtro manual
        if student_is_virtual and not filter_campus_id and not filter_city and not selected_campus:
            _logger.info("[SEDE DEBUG] Estudiante virtual sin filtro manual - aplicando sede virtual automática")
            virtual_campus = Campus.search([("campus_type", "=", "online"), ("active", "=", True)], limit=1)
            if virtual_campus:
                selected_campus = virtual_campus
                selected_city = virtual_campus.city_name or False
                using_default_campus = True
                default_campus_source = "virtual"
                filter_mode = "virtual"
                plan.sudo().write({"filter_campus_id": virtual_campus.id, "filter_city": selected_city})
                _logger.info(f"[SEDE DEBUG] Sede virtual automática asignada: {virtual_campus.name}")
        elif student_is_virtual and (filter_campus_id or filter_city or selected_campus):
            _logger.info(f"[SEDE DEBUG] Estudiante virtual con filtro manual - respetando selección: campus_id={filter_campus_id}, city={filter_city}, selected={selected_campus.name if selected_campus else 'None'}")

        agendas_for_city = None
        if selected_city and not selected_campus:
            agendas_for_city = agendas.filtered(
                lambda a: a.campus_id.city_name == selected_city
            )
        agendas_for_week = agendas
        if selected_campus:
            agendas_for_week = agendas.filtered(lambda a: a.campus_id == selected_campus)
        elif agendas_for_city is not None:
            agendas_for_week = agendas_for_city

        # Cargar semana y sesiones siempre (mostrar agenda publicada completa del plan)
        week = self._prepare_week(
            start_param,
            filter_student_subjects=filter_by_student_subjects,
            campus=selected_campus,
            agendas=agendas_for_week,
        )
        try:
            week_number = week.get("monday").isocalendar()[1] if week.get("monday") else False
        except Exception:
            week_number = False

        scheduled_lines = plan.line_ids.sudo().sorted(key=lambda l: l.start_datetime or fields.Datetime.now())
        scheduled_lines_all = scheduled_lines
        now = fields.Datetime.now()
        scheduled_lines_visible = scheduled_lines_all.filtered(
            lambda l: l.session_id
            and l.session_id.state not in ["done", "cancelled"]
            and l.start_datetime
            and l.start_datetime > now
        )
        join_allowed_session_ids = [
            line.session_id.id
            for line in scheduled_lines_visible
            if self._is_join_allowed(line.session_id)
        ]
        scheduled_session_ids = scheduled_lines_visible.mapped("session_id").ids

        # Aplicar filtros a sesiones disponibles
        all_sessions = week.get("sessions") or request.env["benglish.academic.session"].sudo()

        # Solo mostrar sesiones cuando hay un filtro de sede/ciudad activo
        filtered_sessions = request.env["benglish.academic.session"].sudo().browse()
        if selected_campus:
            filtered_sessions = all_sessions.filtered(lambda s: s.campus_id.id == selected_campus.id)
        elif selected_city:
            filtered_sessions = all_sessions.filtered(lambda s: s.campus_id.city_name == selected_city)

        # Filtrar por modalidad según preferencia del estudiante
        # REGLA: 
        # - Virtual solo ve virtual/híbrido
        # - Presencial solo ve presencial/híbrido
        # - Híbrido ve todas
        # ⭐ EXCEPCIÓN 1: B-checks y Oral Tests SIEMPRE son virtuales (se muestran a TODOS independientemente de modalidad/sede)
        # ⭐ EXCEPCIÓN 2: Sesiones en sede VIRTUAL solo se muestran a estudiantes virtual/híbrido (NO presencial)
        if filter_mode and filter_mode in ['presential', 'virtual', 'hybrid']:
            # Si hay filtro manual, aplicar ese filtro específico
            filtered_sessions = filtered_sessions.filtered(
                lambda s: s.delivery_mode == filter_mode or self._is_bcheck_session(s)
            )
        else:
            # Filtro automático según modalidad del estudiante
            student_mode = student.preferred_delivery_mode or 'presential'
            
            def _is_virtual_campus(session):
                """Verifica si la sesión está en sede VIRTUAL"""
                return session.campus_id and (
                    session.campus_id.code == 'VIRTUAL' or 
                    session.campus_id.campus_type == 'online'
                )
            
            if student_mode == 'virtual':
                # Estudiantes virtuales: solo ven sesiones virtuales e híbridas + B-checks/Oral Tests (siempre virtuales)
                filtered_sessions = filtered_sessions.filtered(
                    lambda s: s.delivery_mode in ['virtual', 'hybrid'] or self._is_bcheck_session(s)
                )
            elif student_mode == 'presential':
                # Estudiantes presenciales: 
                # - Ven sesiones presenciales e híbridas
                # - Ven B-checks/Oral Tests (siempre virtuales, en cualquier sede)
                # - NO ven sesiones publicadas en sede VIRTUAL (excepto B-checks/Oral Tests)
                filtered_sessions = filtered_sessions.filtered(
                    lambda s: (
                        # Skills presenciales o híbridas (excepto las de sede VIRTUAL)
                        (s.delivery_mode in ['presential', 'hybrid'] and not _is_virtual_campus(s)) or
                        # B-checks y Oral Tests SIEMPRE (en cualquier sede, incluso VIRTUAL)
                        self._is_bcheck_session(s)
                    )
                )
            else:
                # Estudiantes híbridos: ven todas las modalidades (incluyendo B-checks/Oral Tests virtuales)
                pass

        effective_subject_by_session = {}
        eligible_sessions = request.env["benglish.academic.session"].sudo().browse()
        
        # Obtener la unidad actual del estudiante para filtrar por audiencia
        student_current_unit = self._get_student_current_unit(student)
        
        for session in filtered_sessions:
            # ⭐ FILTRO DE AUDIENCIA: Verificar que el estudiante esté en el rango de audiencia de la sesión
            if session.template_id and session.audience_unit_from and session.audience_unit_to:
                # EXCEPCIÓN: Oral Tests se publican para UNA sola unidad (ej: Unit 4 para bloque 1-4)
                # El estudiante debe estar EN esa unidad o haberla completado (estar en la siguiente)
                is_oral_test = (
                    session.template_id.subject_category == 'oral_test' or
                    (session.subject_id and session.subject_id.subject_category == 'oral_test')
                )
                
                if is_oral_test:
                    # Oral Test publicado para Unit X: mostrar a estudiantes en Unit X o X+1
                    # Ejemplo: Oral Test Unit 4 → visible para estudiantes en Unit 4 o 5
                    target_unit = session.audience_unit_to  # La unidad objetivo del Oral Test
                    if not (target_unit <= student_current_unit <= target_unit + 1):
                        _logger.info(
                            "[FILTRO AUDIENCIA] Oral Test (ID: %s) descartado para estudiante %s: "
                            "publicado para Unit %s, estudiante en Unit %s",
                            session.id, student.name, target_unit, student_current_unit
                        )
                        continue
                else:
                    # Para otras sesiones (Skills, B-checks): lógica normal de audiencia
                    if not (session.audience_unit_from <= student_current_unit <= session.audience_unit_to):
                        _logger.info(
                            "[FILTRO AUDIENCIA] Sesión %s (ID: %s) descartada para estudiante %s: "
                            "audiencia %s-%s, estudiante en unidad %s",
                            session.display_name, session.id, student.name,
                            session.audience_unit_from, session.audience_unit_to, student_current_unit
                        )
                        continue  # Saltar esta sesión, no está en el rango
            
            effective_subject = self._get_effective_subject(
                session,
                student,
                check_completed=True,
                check_prereq=False,  # NO verificar prerrequisitos al cargar - solo al agendar
            )
            if effective_subject:
                effective_subject_by_session[session.id] = effective_subject
                eligible_sessions |= session

        if not eligible_sessions and all_sessions:
            _logger.info(
                "[AGENDA DEBUG] Sesiones sin match tras filtros. total=%s campus_ids=%s modes=%s subjects=%s selected_campus=%s selected_city=%s student_virtual=%s",
                len(all_sessions),
                sorted(set(all_sessions.mapped("campus_id").ids)),
                sorted(set([m for m in all_sessions.mapped("delivery_mode") if m])),
                sorted(set(all_sessions.mapped("subject_id").ids)),
                selected_campus.id if selected_campus else False,
                selected_city,
                student_is_virtual,
            )

        # Sesiones disponibles para seleccionar (publicadas, no canceladas, elegibles por homologación)
        available_sessions = eligible_sessions.filtered(
            lambda s: s.id not in scheduled_session_ids
            and s.datetime_start and s.datetime_start > now
        )
        agenda_sessions = eligible_sessions.filtered(
            lambda s: s.datetime_start and s.datetime_start > now
        )
        bookable_session_ids = set(available_sessions.ids)

        # Agrupar sesiones disponibles por asignatura efectiva
        subjects_with_sessions = {}
        for session in available_sessions:
            subject = effective_subject_by_session.get(session.id)
            if not subject:
                continue
            if subject.id not in subjects_with_sessions:
                subjects_with_sessions[subject.id] = {
                    "subject": subject,
                    "sessions": request.env["benglish.academic.session"].sudo(),
                    "total_horarios": 0,
                }
            subjects_with_sessions[subject.id]["sessions"] |= session
            subjects_with_sessions[subject.id]["total_horarios"] += 1

        subjects_grouped = sorted(
            subjects_with_sessions.values(),
            key=lambda x: x["subject"].sequence or 0,
        )

        agenda_by_day = []
        for offset in range(7):
            day = monday + timedelta(days=offset)
            agenda_by_day.append(
                {
                    "date": day,
                    "lines": scheduled_lines_visible.filtered(lambda ln, d=day: ln.date == d),
                    "sessions": agenda_sessions.filtered(lambda ss, d=day: ss.date == d),
                }
            )

        effective_subjects_available = request.env["benglish.subject"].sudo().browse(
            list({s.id for s in effective_subject_by_session.values() if s})
        )
        effective_subjects_scheduled = request.env["benglish.subject"].sudo().browse()
        for line in scheduled_lines:
            subj = self._get_effective_subject(
                line.session_id, student, check_completed=False, check_prereq=False
            )
            if subj:
                effective_subjects_scheduled |= subj
        subjects_for_prereq = (effective_subjects_available | effective_subjects_scheduled).sudo()
        prereq_status = {}

        def _summarize_missing(missing_records):
            missing_bchecks = missing_records.filtered(lambda s: s.subject_category == "bcheck")
            missing_bskills = missing_records.filtered(lambda s: s.subject_category == "bskills")
            parts = []
            if missing_bchecks:
                units = sorted({(s.unit_number or s.code or s.name) for s in missing_bchecks})
                parts.append(_("BCheck unidades: %s") % ", ".join(map(str, units)))
            if missing_bskills:
                units = sorted({(s.unit_number or s.code or s.name) for s in missing_bskills})
                parts.append(_("Bskills unidades: %s") % ", ".join(map(str, units)))
            return " | ".join(parts) if parts else ", ".join(missing_records.mapped("name"))

        for subject in subjects_for_prereq:
            result = subject.sudo().check_prerequisites_completed(student)
            missing = result.get("missing_prerequisites") or request.env["benglish.subject"].sudo()
            missing_summary = _summarize_missing(missing)
            message = result.get("message") or (missing_summary and _("Faltan prerrequisitos: %s") % missing_summary)
            prereq_status[subject.id] = {
                "ok": bool(result.get("completed")),
                "missing": missing_summary,
                "message": message,
            }
        prereq_status_by_session = {}
        for session in eligible_sessions:
            subject = effective_subject_by_session.get(session.id)
            if subject:
                prereq_status_by_session[session.id] = prereq_status.get(subject.id)
        
        # Detectar prerrequisitos
        has_prerequisite_scheduled = False
        for line in scheduled_lines_all:
            line_subject = self._get_effective_subject(
                line.session_id,
                student,
                check_completed=False,
                check_prereq=False,
            )
            if line_subject and self._is_prerequisite_subject(line_subject):
                has_prerequisite_scheduled = True
                break
        available_prerequisites = available_sessions.filtered(
            lambda s: self._is_prerequisite_subject(
                effective_subject_by_session.get(s.id) or s.subject_id
            )
        )
        needs_prerequisite_warning = not has_prerequisite_scheduled and len(scheduled_lines_all) == 0

        dependency_map = {}
        for line in scheduled_lines_visible:
            dependents = plan.sudo().compute_dependent_lines(line)
            dependency_map[line.id] = [self._format_session_label(dep.session_id) for dep in dependents]

        student_level_name_ctx = ""
        student_max_unit_ctx = 0
        if student:
            active_enrollments = student.enrollment_ids.sudo().filtered(
                lambda e: e.state in ["enrolled", "in_progress"]
            ).sorted("enrollment_date", reverse=True)
            if active_enrollments and active_enrollments[0].level_id:
                level = active_enrollments[0].level_id
                student_level_name_ctx = level.name or ""
                student_max_unit_ctx = level.max_unit or 0

        week.update({
            "week_number": week_number,
            "total_sessions": len(week.get("sessions") or []),
            "scheduled_total": len(scheduled_lines_visible),
        })
        
        # Determinar filtro actual (solo si el usuario lo envió en la request)
        current_filter = {
            'type': 'none',
            'label': 'Selecciona una sede',
            'campus_id': False,
            'city': False,
            'mode': filter_mode or False
        }
        
        if selected_campus and using_default_campus:
            current_filter = {
                'type': 'default',
                'label': selected_campus.name,
                'campus_id': selected_campus.id,
                'city': selected_campus.city_name,
                'mode': filter_mode or False,
                'default_source': default_campus_source,
            }
        elif selected_campus:
            current_filter = {
                'type': 'campus',
                'label': selected_campus.name,
                'campus_id': selected_campus.id,
                'city': selected_campus.city_name,
                'mode': filter_mode or False
            }
        elif selected_city:
            current_filter = {
                'type': 'city',
                'label': f'Ciudad: {selected_city}',
                'campus_id': False,
                'city': selected_city,
                'mode': filter_mode or False
            }
        
        # Mostrar agenda solo cuando hay filtro de sede/ciudad
        has_filter = bool(selected_campus or selected_city)
        
        values = {
            "page_name": "agenda",
            "week": week,
            "plan": plan,
            "scheduled_lines": scheduled_lines_visible,
            "available_sessions": available_sessions,
            "agenda_sessions": agenda_sessions,
            "subjects_grouped": subjects_grouped,
            "agenda_by_day": agenda_by_day,
            "bookable_session_ids": list(bookable_session_ids),
            "prereq_status": prereq_status,
            "prereq_status_by_session": prereq_status_by_session,
            "dependency_map": dependency_map,
            "week_start_str": fields.Date.to_string(monday),
            "available_campuses": available_campuses,
            "cities_data": cities,
            "current_filter": current_filter,
            "has_filter": has_filter,  # NUEVO: Indicador de si hay filtro activo
            "has_prerequisite_scheduled": has_prerequisite_scheduled,
            "available_prerequisites": available_prerequisites,
            "needs_prerequisite_warning": needs_prerequisite_warning,
            "join_allowed_session_ids": join_allowed_session_ids,
            "student_level_name_ctx": student_level_name_ctx,
            "student_max_unit_ctx": student_max_unit_ctx,
        }
        values = self._prepare_portal_values(student, values, access=access)
        return request.render("portal_student.portal_student_agenda", values)

    @http.route("/my/student/agenda/mine", type="http", auth="user", website=True)
    def portal_student_my_agenda(self, **kwargs):
        student = self._get_student()
        if not student:
            if portal_utils.is_coach():
                return request.redirect('/my/coach')
            return request.redirect("/my")

        guard_response, access = self._ensure_portal_access(
            student, capability=["can_attend", "can_schedule"]
        )
        if guard_response:
            return guard_response

        plan_model = request.env["portal.student.weekly.plan"].sudo()
        start_param = kwargs.get("start")
        try:
            start_date = (
                fields.Date.from_string(start_param) if start_param else fields.Date.today()
            )
        except Exception:
            start_date = fields.Date.today()

        if isinstance(start_date, str):
            start_date = fields.Date.from_string(start_date)
        monday = start_date - timedelta(days=start_date.weekday())

        plan = plan_model.get_or_create_for_student(student, monday)
        scheduled_lines = plan.line_ids.sudo().sorted(key=lambda l: l.start_datetime or fields.Datetime.now())
        scheduled_lines_all = scheduled_lines
        now = fields.Datetime.now()
        scheduled_lines_visible = scheduled_lines_all.filtered(
            lambda l: l.session_id
            and l.session_id.state not in ["done", "cancelled"]
            and l.start_datetime
            and l.start_datetime > now
        )
        join_allowed_session_ids = [
            line.session_id.id
            for line in scheduled_lines_visible
            if self._is_join_allowed(line.session_id)
        ]

        agenda_by_day = []
        for offset in range(7):
            day = monday + timedelta(days=offset)
            agenda_by_day.append(
                {
                    "date": day,
                    "lines": scheduled_lines_visible.filtered(lambda ln, d=day: ln.date == d),
                }
            )

        dependency_map = {}
        for line in scheduled_lines_visible:
            dependents = plan.sudo().compute_dependent_lines(line)
            dependency_map[line.id] = [self._format_session_label(dep.session_id) for dep in dependents]

        try:
            week_number = monday.isocalendar()[1] if monday else False
        except Exception:
            week_number = False

        week = {
            "monday": monday,
            "sunday": monday + timedelta(days=6),
            "week_number": week_number,
            "scheduled_total": len(scheduled_lines_visible),
        }

        values = {
            "page_name": "my_agenda",
            "week": week,
            "plan": plan,
            "scheduled_lines": scheduled_lines_visible,
            "agenda_by_day": agenda_by_day,
            "dependency_map": dependency_map,
            "week_start_str": fields.Date.to_string(monday),
            "join_allowed_session_ids": join_allowed_session_ids,
        }
        values = self._prepare_portal_values(student, values, access=access)
        return request.render("portal_student.portal_student_my_agenda", values)

    @http.route("/my/student/program", type="http", auth="user", website=True)
    def portal_student_program(self, **kwargs):
        student = self._get_student()
        if not student:
            if portal_utils.is_coach():
                return request.redirect('/my/coach')
            return request.redirect("/my")
        guard_response, access = self._ensure_portal_access(student, capability="can_view_history")
        if guard_response:
            return guard_response
        structure = self._prepare_program_structure(student)
        values = {
            "page_name": "program",
            "student": student,
            "structure": structure,
        }
        values = self._prepare_portal_values(student, values, access=access)
        return request.render("portal_student.portal_student_program", values)

    @http.route("/my/student/agenda/add", type="json", auth="user", website=True, methods=["POST"], csrf=True)
    def portal_student_add_session(self, session_id=None, week_start=None, **kwargs):
        """
        HU-PE-CUPO-01: Programar una clase validando disponibilidad de cupos sin mostrar números exactos.
        """
        student = self._get_student()
        if not student:
            return {"status": "error", "message": _("No encontramos tu ficha de estudiante.")}
        if portal_utils.must_change_password(request.env.user):
            return {
                "status": "error",
                "message": _("Debes cambiar tu contraseña antes de continuar."),
                "code": "password_change_required",
            }
        access = self._get_portal_access_rules(student)
        if not access.get("allow_login", True):
            return {
                "status": "error",
                "message": _("Tu cuenta no tiene acceso al portal en este momento."),
                "code": "access_blocked",
            }
        if not access.get("capabilities", {}).get("can_schedule", True):
            return {
                "status": "error",
                "message": _("No tienes permiso para programar clases en tu estado actual."),
                "code": "access_restricted",
            }
        try:
            session_id = int(session_id)
        except Exception:
            return {"status": "error", "message": _("Clase no valida.")}

        Session = request.env["benglish.academic.session"].sudo()
        session = Session.browse(session_id)
        if not session or not session.exists():
            return {"status": "error", "message": _("No se encontro la clase seleccionada.")}
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # HU-PE-CUPO-01 & T-PE-CUPO-01: VALIDACIÓN DE CUPOS
        # ═══════════════════════════════════════════════════════════════════════════════
        # Contar estudiantes ACTUALMENTE agendados (excluyendo al estudiante actual)
        # Las líneas eliminadas (canceladas) NO se cuentan - esto garantiza que
        # al cancelar, el cupo queda disponible inmediatamente.
        Line = request.env["portal.student.weekly.plan.line"].sudo()
        students_scheduled_count = Line.search_count(
            [("session_id", "=", session.id), ("plan_id.student_id", "!=", student.id)]
        )
        max_capacity = session.max_capacity or 0
        is_full = bool(getattr(session, "is_full", False))
        available_spots = getattr(session, "available_spots", 0)
        
        # Log para debug de cupos
        _logger.info(f"[CUPOS DEBUG] Session {session.id} ({session.display_name})")
        _logger.info(f"[CUPOS DEBUG] - Estudiantes agendados (otros): {students_scheduled_count}")
        _logger.info(f"[CUPOS DEBUG] - Capacidad máxima: {max_capacity}")
        _logger.info(f"[CUPOS DEBUG] - is_full: {is_full}, available_spots: {available_spots}")
        
        if is_full or (max_capacity and students_scheduled_count >= max_capacity) or (available_spots is not False and available_spots <= 0):
            _logger.info(f"[CUPOS DEBUG] ❌ Sin cupos disponibles para sesión {session.id}")
            return {
                "status": "error",
                "message": _(
                    "Esta clase ya no tiene cupos disponibles. "
                    "Por favor, elige otro horario para esta asignatura. "
                    "Puedes consultar otras opciones en la agenda publicada."
                ),
                "no_capacity": True,
            }
        
        _logger.info(f"[CUPOS DEBUG] ✅ Cupos disponibles: {max_capacity - students_scheduled_count if max_capacity else 'ilimitado'}")

        plan_model = request.env["portal.student.weekly.plan"].sudo()
        plan = plan_model.get_or_create_for_student(student, week_start or session.date)

        # Validaciones académicas y de negocio (prerrequisitos, Bcheck, Oral Test, solapes)
        validation = Line._evaluate_session_for_plan(
            plan, session, student=student, raise_on_error=False
        )

        # IMPORTANTE: Usar check_completed=True para forzar recálculo y evitar cache stale
        # Cuando validamos para scheduling, necesitamos el subject actualizado basado en
        # el progreso ACTUAL del estudiante, no el valor cacheado de enrollment anterior
        effective_subject = self._get_effective_subject(
            session,
            student,
            check_completed=True,  # Forzar recálculo - no usar cache de enrollment
            check_prereq=False,
        )
        is_prereq = self._is_prerequisite_subject(effective_subject or session.subject_id)

        # Log detallado para depuración
        _logger.info("="*80)
        _logger.info(f"[AGENDA DEBUG] Validación de sesión {session.id} - {session.display_name}")
        _logger.info(f"[AGENDA DEBUG] Estudiante: {student.id} - {student.name}")
        _logger.info(f"[AGENDA DEBUG] Validation result: {validation}")
        _logger.info(f"[AGENDA DEBUG] Session is_prerequisite: {is_prereq}")
        _logger.info(
            f"[AGENDA DEBUG] Session subject: {effective_subject.name if effective_subject else (session.subject_id.name if session.subject_id else 'N/A')}"
        )
        _logger.info(
            f"[AGENDA DEBUG] Session subject_category: {effective_subject.subject_category if effective_subject else (session.subject_id.subject_category if session.subject_id else 'N/A')}"
        )
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # LOG ESPECIAL PARA POOLS DE ELECTIVAS
        # ═══════════════════════════════════════════════════════════════════════════════
        if session.elective_pool_id:
            _logger.info(f"🟢 [ELECTIVE-POOL] Sesión {session.id} tiene pool de electivas:")
            _logger.info(f"🟢 [ELECTIVE-POOL]   - Pool ID: {session.elective_pool_id.id}")
            _logger.info(f"🟢 [ELECTIVE-POOL]   - Pool nombre: {session.elective_pool_id.display_name}")
            _logger.info(f"🟢 [ELECTIVE-POOL]   - Asignaturas en pool: {len(session.elective_pool_id.subject_ids)}")
            _logger.info(f"🟢 [ELECTIVE-POOL]   - Nivel estudiante: {student.current_level_id.name if student.current_level_id else 'N/A'}")
            _logger.info(f"🟢 [ELECTIVE-POOL]   - Asignatura efectiva resuelta: {effective_subject.name if effective_subject else 'NINGUNA'}")
        
        # Verificar matrículas del estudiante
        enrollments = student.enrollment_ids.filtered(lambda e: e.state in ["enrolled", "in_progress"])
        _logger.info(f"[AGENDA DEBUG] Matrículas activas: {len(enrollments)}")
        for enr in enrollments:
            _logger.info(
                f"  - {(enr.subject_id.alias or enr.subject_id.name) if enr.subject_id else 'N/A'} (estado: {enr.state})"
            )
        _logger.info("="*80)
        
        if not validation.get("ok", True):
            return {
                "status": "error",
                "message": validation.get("blocked_reason") or _("No puedes programar esta clase."),
                "prerequisites_ok": validation.get("prerequisites_ok"),
                "missing_prerequisites": validation.get("missing_prerequisites"),
                "blocked_reason": validation.get("blocked_reason"),
                "errors": validation.get("errors"),
                "prerequisite_subjects": validation.get("prerequisite_subjects"),
                "oral_test": validation.get("oral_test"),
            }
        
        # Evitar crear duplicados: si ya existe, devolver OK con la linea existente
        existing = Line.search([("plan_id", "=", plan.id), ("session_id", "=", session.id)], limit=1)
        if existing:
            try:
                self._ensure_session_enrollment(session, student)
            except (ValidationError, UserError) as e:
                return {"status": "error", "message": self._error_message(e)}
            except Exception as e:
                return {"status": "error", "message": str(e)}
            return {
                "status": "ok",
                "message": _("La clase ya está en tu agenda."),
                "line": existing.to_portal_dict(),
            }

        try:
            with request.env.cr.savepoint():
                line = Line.create({
                    "plan_id": plan.id,
                    "session_id": session.id,
                })
                
                # ═══════════════════════════════════════════════════════════════════════════════
                # CRÍTICO: Forzar cálculo inmediato del effective_subject_id para B-Checks
                # ═══════════════════════════════════════════════════════════════════════════════
                # Esto es especialmente importante para B-Checks que usan resolve_effective_subject
                # para determinar la unidad específica del estudiante
                # ═══════════════════════════════════════════════════════════════════════════════
                if line.session_id and not line.effective_subject_id:
                    _logger.info(f"[AGENDA DEBUG] Forzando cálculo de effective_subject_id para línea {line.id}")
                    line._compute_effective_subject()
                    line.flush_recordset()  # Forzar persistencia inmediata
                    
                    calculated_subject = line.effective_subject_id
                    _logger.info(f"[AGENDA DEBUG] effective_subject_id calculado: {calculated_subject.name if calculated_subject else 'None'}")
                    _logger.info(f"[AGENDA DEBUG] unit_number: {calculated_subject.unit_number if calculated_subject else 'None'}")
                    _logger.info(f"[AGENDA DEBUG] subject_category: {calculated_subject.subject_category if calculated_subject else 'None'}")
        except ValidationError as e:
            return {"status": "error", "message": self._error_message(e)}
        except Exception as e:
            # Manejar posible race-condition por constraint único en BD
            msg = str(e)
            if "unique" in msg.lower() or "duplicat" in msg.lower():
                # Buscar la línea de nuevo y devolver OK si existe
                existing = Line.search([("plan_id", "=", plan.id), ("session_id", "=", session.id)], limit=1)
                if existing:
                    return {
                        "status": "ok",
                        "message": _("La clase ya está en tu agenda."),
                        "line": existing.to_portal_dict(),
                    }
            return {"status": "error", "message": msg}

        try:
            self._ensure_session_enrollment(session, student)
        except (ValidationError, UserError) as e:
            line.unlink()
            return {"status": "error", "message": self._error_message(e)}
        except Exception as e:
            line.unlink()
            return {"status": "error", "message": str(e)}

        # HU-PE-CUPO-01: Mensaje de éxito genérico (sin mencionar cupos)
        return {
            "status": "ok",
            "message": _("Clase agregada exitosamente a tu agenda."),
            "line": line.to_portal_dict(),
        }

    @http.route("/my/student/agenda/remove", type="json", auth="user", website=True, methods=["POST"], csrf=True)
    def portal_student_remove_session(self, line_id=None, **kwargs):
        student = self._get_student()
        if not student:
            return {"status": "error", "message": _("No encontramos tu ficha de estudiante.")}
        if portal_utils.must_change_password(request.env.user):
            return {
                "status": "error",
                "message": _("Debes cambiar tu contraseña antes de continuar."),
                "code": "password_change_required",
            }
        access = self._get_portal_access_rules(student)
        if not access.get("allow_login", True):
            return {
                "status": "error",
                "message": _("Tu cuenta no tiene acceso al portal en este momento."),
                "code": "access_blocked",
            }
        can_manage_agenda = any(
            access.get("capabilities", {}).get(flag, True)
            for flag in ["can_schedule", "can_attend"]
        )
        if not can_manage_agenda:
            return {
                "status": "error",
                "message": _("No tienes permiso para modificar tu agenda en tu estado actual."),
                "code": "access_restricted",
            }
        try:
            line_id = int(line_id)
        except Exception:
            return {"status": "error", "message": _("Registro no valido.")}

        Line = request.env["portal.student.weekly.plan.line"].sudo()
        line = Line.search(
            [("id", "=", line_id), ("plan_id.student_id", "=", student.id)],
            limit=1,
        )
        if not line:
            return {"status": "error", "message": _("No encontramos esa clase en tu agenda.")}

        session = line.session_id
        session_state = session.state if session else False
        skip_penalty = session_state in ["cancelled", "done"]
        late_cancel = not self._can_cancel_line(line)
        apply_failure = late_cancel and not skip_penalty
        late_message = ""

        if apply_failure:
            self._apply_late_cancel_failure(student, session)
            late_message = _(
                "Cancelacion fuera de tiempo. Se registro una falla en tu historial."
            )

        plan = line.plan_id.sudo()
        
        # HU-E8 (nuevo): calcular dependencias reales por prerequisite_ids
        line_subject = self._get_effective_subject(
            line.session_id,
            student,
            check_completed=False,
            check_prereq=False,
        )
        is_prerequisite = self._is_prerequisite_subject(line_subject or line.session_id.subject_id)
        dependents = plan.compute_dependent_lines(line)
        to_remove = (dependents | line).sorted(key=lambda l: l.start_datetime or fields.Datetime.now())
        removed_names = [self._format_session_label(ln.session_id) for ln in to_remove]

        # Log de cancelación
        _logger.info(f"[CANCEL DEBUG] Cancelando línea {line_id} - Session: {line.session_id.display_name}")
        _logger.info(f"[CANCEL DEBUG] Es prerrequisito: {is_prerequisite}")
        _logger.info(f"[CANCEL DEBUG] Dependencias encontradas: {len(dependents)}")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # CRÍTICO: LIBERAR CUPOS DE TODAS LAS SESIONES
        # ═══════════════════════════════════════════════════════════════════════════════
        # SIEMPRE cancelamos el enrollment para liberar el cupo, sin importar:
        # - Si es cancelación tardía (apply_failure): El estudiante recibe falla pero el cupo se libera
        # - Si la sesión ya terminó (state="done"): El enrollment puede seguir activo, cancelarlo
        # 
        # La ÚNICA excepción es si el estudiante ya asistió (state="attended"), 
        # en cuyo caso no se puede cancelar
        # ═══════════════════════════════════════════════════════════════════════════════
        for rem_line in to_remove:
            if not rem_line.session_id:
                continue
            
            # Determinar el estado objetivo según el caso
            if apply_failure and rem_line.id == line.id:
                # Cancelación tardía: marcar como ausente pero IGUAL liberar cupo
                target = "absent"
                _logger.info(f"[CANCEL DEBUG] ⚠️ Cancelación tardía - marcando como ausente: {rem_line.session_id.display_name}")
            else:
                target = "cancelled"
            
            _logger.info(f"[CANCEL DEBUG] Liberando cupo - Session: {rem_line.session_id.display_name}, target_state={target}")
            result = self._cancel_session_enrollment(rem_line.session_id, student, target_state=target)
            _logger.info(f"[CANCEL DEBUG] Resultado cancelación: {result}")

        message = _("✅ Clase eliminada de tu agenda. El cupo ha sido liberado.")
        warning_type = "success"

        if dependents:
            warning_type = "warning"
            # Obtener unidad del B-Check cancelado para mensaje más claro
            line_unit = line_subject.unit_number if line_subject and hasattr(line_subject, 'unit_number') else 0
            if is_prerequisite and line_unit:
                message = _("✅ Se eliminó el B-Check Unidad {} y {} Skills de la misma unidad.\n"
                           "Los cupos han sido liberados.").format(line_unit, len(dependents))
            else:
                message = _("✅ Se eliminaron {} clases dependientes.\n"
                           "Los cupos han sido liberados.").format(len(to_remove))
        elif is_prerequisite:
            line_unit = line_subject.unit_number if line_subject and hasattr(line_subject, 'unit_number') else 0
            if line_unit:
                message = _("✅ Se eliminó el B-Check Unidad {}.\n"
                           "El cupo ha sido liberado.").format(line_unit)
            else:
                message = _("✅ Se eliminó el prerrequisito.\nEl cupo ha sido liberado.")

        if skip_penalty:
            warning_type = "info"
            message = _("La clase ya estaba cancelada o finalizada. Se removió de tu agenda.")
            if dependents:
                message = _("La clase ya estaba cancelada o finalizada. Se removieron %s clases dependientes.") % len(to_remove)

        if apply_failure:
            warning_type = "warning"
            message = late_message
            if dependents:
                message = _(
                    "Cancelacion fuera de tiempo. Se registro una falla en tu historial y se eliminaron %s clases dependientes."
                ) % len(to_remove)

        to_remove.unlink()

        return {
            "status": "ok",
            "message": message,
            "removed": removed_names,
            "warning_type": warning_type,
            "is_prerequisite_removed": is_prerequisite,
            "dependent_line_ids": dependents.ids,
            "late_cancel": apply_failure,
            "failure_applied": apply_failure,
        }

    @http.route("/my/profile", type="http", auth="user", website=True)
    def portal_student_profile(self, **kwargs):
        student = self._get_student()
        if not student:
            if portal_utils.is_coach():
                return request.redirect('/my/coach')
            return request.redirect("/my")
        guard_response, access = self._ensure_portal_access(student)
        if guard_response:
            return guard_response

        profile = self._prepare_profile_data(student)
        values = {
            "page_name": "profile",
            "profile": profile,
        }
        values = self._prepare_portal_values(student, values, access=access)
        return request.render("portal_student.portal_student_profile", values)

    @http.route("/my/student/info", type="http", auth="user", website=True, methods=["GET", "POST"], csrf=True)
    def portal_student_info(self, **kwargs):
        student = self._get_student()
        if not student:
            if portal_utils.is_coach():
                return request.redirect('/my/coach')
            return request.redirect("/my")
        guard_response, access = self._ensure_portal_access(student)
        if guard_response:
            return guard_response

        values = {
            "page_name": "info",
            "countries": request.env["res.country"].sudo().search([]),
            "campuses": request.env["benglish.campus"].sudo().search([]),
            "message": None,
            "error": None,
        }
        values = self._prepare_portal_values(student, values, access=access)

        if request.httprequest.method == "POST":
            params = kwargs
            vals = {
                "name": params.get("name"),
                "student_id_number": params.get("student_id_number"),
                "gender": params.get("gender") or False,
                "birth_date": params.get("birth_date") or False,
                "email": params.get("email"),
                "phone": params.get("phone"),
                "mobile": params.get("mobile"),
                "address": params.get("address"),
                "city": params.get("city"),
                "preferred_delivery_mode": params.get("preferred_delivery_mode") or False,
            }
            country_id = params.get("country_id")
            campus_id = params.get("preferred_campus_id")
            if country_id:
                vals["country_id"] = int(country_id)
            else:
                vals["country_id"] = False
            if campus_id:
                vals["preferred_campus_id"] = int(campus_id)
            else:
                vals["preferred_campus_id"] = False
            try:
                student.sudo().write(vals)
                values["message"] = _("Información actualizada correctamente.")
            except Exception as e:
                values["error"] = _("No se pudo actualizar: %s") % e

        return request.render("portal_student.portal_student_info", values)

    @http.route("/my/student/resources", type="http", auth="user", website=True)
    def portal_student_resources(self, **kwargs):
        student = self._get_student()
        if not student:
            if portal_utils.is_coach():
                return request.redirect('/my/coach')
            return request.redirect("/my")
        guard_response, access = self._ensure_portal_access(student, capability="can_use_apps")
        if guard_response:
            return guard_response
        active_enrollments = student.enrollment_ids.sudo().filtered(
            lambda e: e.state in ["enrolled", "in_progress"]
        )
        values = {
            "page_name": "resources",
            "resources": self._prepare_resources(active_enrollments),
        }
        values = self._prepare_portal_values(student, values, access=access)
        return request.render("portal_student.portal_student_resources", values)

    @http.route("/my/student/summary", type="http", auth="user", website=True)
    def portal_student_summary(self, **kwargs):
        """
        Resumen académico basado en clases individuales del historial académico.
        Muestra progreso real de clases completadas vs pendientes.
        """
        student = self._get_student()
        if not student:
            if portal_utils.is_coach():
                return request.redirect('/my/coach')
            return request.redirect("/my")
        guard_response, access = self._ensure_portal_access(student, capability="can_use_apps")
        if guard_response:
            return guard_response

        # Obtener historial académico del estudiante (excluir Placement Test)
        History = request.env["benglish.academic.history"].sudo()
        history_domain = [
            ('student_id', '=', student.id),
            ('subject_id.subject_category', '!=', 'placement_test')
        ]
        history_records = History.search(history_domain, order='session_date desc')
        
        # Obtener resumen de asistencia
        attendance_summary = {
            'total_classes': len(history_records),
            'attended': len(history_records.filtered(lambda h: h.attendance_status == 'attended')),
            'absent': len(history_records.filtered(lambda h: h.attendance_status == 'absent')),
            'pending': len(history_records.filtered(lambda h: h.attendance_status == 'pending')),
        }
        if attendance_summary['total_classes'] > 0:
            attendance_summary['attendance_rate'] = round(
                (attendance_summary['attended'] / attendance_summary['total_classes']) * 100, 1
            )
        else:
            attendance_summary['attendance_rate'] = 0
        
        # Obtener todas las asignaturas del plan del estudiante
        Subject = request.env["benglish.subject"].sudo()
        
        # Obtener plan y programa desde la matrícula activa (no desde el estudiante)
        active_enrollments = student.enrollment_ids.filtered(
            lambda e: e.state in ['enrolled', 'in_progress']
        ).sorted('enrollment_date', reverse=True)
        
        if active_enrollments:
            enrollment = active_enrollments[0]
            program = enrollment.program_id
            plan = enrollment.plan_id
        else:
            program = student.program_id
            plan = student.plan_id
        
        # Buscar asignaturas del programa y plan del estudiante
        subject_domain = []
        if program:
            subject_domain.append(('program_id', '=', program.id))
        if plan:
            subject_domain.append(('plan_ids', 'in', [plan.id]))
        # ⭐ ORDEN CORRECTO: level_id, unit_number, sequence, name
        # Esto asegura que UNIT 9 aparezca antes de UNIT 10, UNIT 11, etc.
        all_subjects = Subject.search(subject_domain, order='level_id, unit_number, sequence, name')
        enrollment_subject_ids = set(
            student.enrollment_ids.filtered(
                lambda e: e.state in ['enrolled', 'in_progress', 'completed', 'active']
            ).mapped('subject_id').ids
        )
        history_subject_ids = set(history_records.mapped('subject_id').ids)
        visible_optional_ids = enrollment_subject_ids | history_subject_ids
        all_subjects = all_subjects.filtered(
            lambda s: (not self._is_optional_bskill(s)) or s.id in visible_optional_ids
        )
        
        # Clasificar asignaturas: completadas vs pendientes vs ausente
        # Un estudiante completa una asignatura si tiene AL MENOS UNA clase attended
        completed_subject_ids = set(history_records.filtered(
            lambda h: h.attendance_status == 'attended'
        ).mapped('subject_id').ids)
        
        # Asignaturas donde el estudiante no asistió
        absent_subject_ids = set(history_records.filtered(
            lambda h: h.attendance_status == 'absent'
        ).mapped('subject_id').ids)
        
        subjects_data = []
        for subject in all_subjects:
            is_completed = subject.id in completed_subject_ids
            is_absent = subject.id in absent_subject_ids and not is_completed
            is_pending = not is_completed and not is_absent  # Solo si NUNCA ha visto la clase
            
            # Obtener última clase de esta asignatura (attended o absent)
            last_class = history_records.filtered(
                lambda h: h.subject_id.id == subject.id
            ).sorted('session_date', reverse=True)[:1]
            
            # Determinar el estado
            if is_completed:
                status = 'attended'
            elif is_absent:
                status = 'absent'
            else:
                status = 'pending'
            
            subjects_data.append({
                'subject': subject,
                'name': subject.alias or subject.name,
                'code': subject.code,
                'completed': is_completed,
                'absent': is_absent,
                'pending': is_pending,
                'status': status,
                'last_class_date': last_class.session_date if last_class else False,
                'attendance_status': last_class.attendance_status if last_class else None,
                'notes': last_class.notes if last_class and last_class.notes else False,
                'grade': last_class.grade if last_class and last_class.grade else False,  # ⭐ NUEVO: Agregar nota
                'level': subject.level_id.name if subject.level_id else '',
                'phase': subject.phase_id.name if subject.phase_id else '',
            })
        
        # Calcular progreso general
        total_subjects = len(subjects_data)
        completed_subjects = len([s for s in subjects_data if s['completed']])
        pending_subjects = len([s for s in subjects_data if s['pending']])  # Solo las que NUNCA ha visto
        progress_percentage = round((completed_subjects / total_subjects * 100), 1) if total_subjects > 0 else 0
        
        # Agrupar por fase y nivel
        subjects_by_phase = {}
        for subject_data in subjects_data:
            phase_name = subject_data['phase'] or 'Sin fase'
            if phase_name not in subjects_by_phase:
                subjects_by_phase[phase_name] = {
                    'name': phase_name,
                    'levels': {}
                }
            
            level_name = subject_data['level'] or 'Sin nivel'
            if level_name not in subjects_by_phase[phase_name]['levels']:
                subjects_by_phase[phase_name]['levels'][level_name] = {
                    'name': level_name,
                    'subjects': []
                }
            
            subjects_by_phase[phase_name]['levels'][level_name]['subjects'].append(subject_data)
        
        dashboard = self._prepare_dashboard_data(student, fallback_to_published=False)
        
        values = {
            "page_name": "summary",
            "history_records": history_records[:10],  # Últimas 10 clases
            "attendance_summary": attendance_summary,
            "subjects_data": subjects_data,
            "subjects_by_phase": subjects_by_phase,
            "total_subjects": total_subjects,
            "completed_subjects": completed_subjects,
            "pending_subjects": pending_subjects,  # Solo clases que NUNCA ha visto
            "progress_percentage": progress_percentage,
            "next_session": dashboard.get("next_session"),
            "program": program,
            "plan": plan,
        }
        values = self._prepare_portal_values(student, values, access=access)
        return request.render("portal_student.portal_student_summary_v2", values)

    @http.route("/my/student/status", type="http", auth="user", website=True)
    def portal_student_status(self, **kwargs):
        student = self._get_student()
        if not student:
            if portal_utils.is_coach():
                return request.redirect('/my/coach')
            return request.redirect("/my")
        guard_response, access = self._ensure_portal_access(student, capability="can_view_history")
        if guard_response:
            return guard_response
        enrollments = student.enrollment_ids.sudo().sorted(key=lambda e: e.enrollment_date or date.min)
        active_enrollments = enrollments.filtered(lambda e: e.state in ["enrolled", "in_progress"])
        Session = request.env["benglish.academic.session"].sudo()
        now = fields.Datetime.now()
        today = fields.Date.context_today(request.env.user)
        base_domain, agenda, subjects = self._base_session_domain()

        next_session = Session.search(
            base_domain + [("datetime_start", ">=", now)],
            order="datetime_start asc",
            limit=1,
        )
        today_sessions = Session.search(
            base_domain + [("date", "=", today)],
            order="datetime_start asc",
        )
        programs = active_enrollments.mapped("program_id")
        if not programs and student.program_id:
            programs = student.program_id

        values = {
            "page_name": "status",
            "enrollments": enrollments,
            "stats": self._compute_stats(student, enrollments),
            "next_session": next_session,
            "today_sessions": today_sessions,
            "programs": programs,
            "resources": self._prepare_resources(active_enrollments)[:4],
        }
        values = self._prepare_portal_values(student, values, access=access)
        return request.render("portal_student.portal_student_status", values)

    @http.route("/my/student/academic", type="http", auth="user", website=True)
    def portal_student_academic(self, **kwargs):
        """Estado académico básico por asignatura (asistencias y notas)."""
        student = self._get_student()
        if not student:
            if portal_utils.is_coach():
                return request.redirect('/my/coach')
            return request.redirect("/my")
        guard_response, access = self._ensure_portal_access(student, capability="can_view_history")
        if guard_response:
            return guard_response

        enrollments = student.enrollment_ids.sudo().filtered(
            lambda e: e.state in ["enrolled", "in_progress", "completed"]
        ).sorted(key=lambda e: e.enrollment_date or date.min, reverse=True)

        enrollments_data = []
        for e in enrollments:
            attendance = getattr(e, "attendance_percentage", False) or getattr(e, "attendance_rate", False)
            absences = getattr(e, "absences_count", False) or getattr(e, "absences", False)
            subject = e.subject_id
            subject_label = subject.alias if subject and subject.alias else (subject.name if subject else "Asignatura")
            enrollments_data.append(
                {
                    "enrollment": e,
                    "subject": e.subject_id,
                    "subject_label": subject_label,
                    "program": e.program_id,
                    "phase": e.phase_id,
                    "level": e.level_id,
                    "campus": e.campus_id,
                    "delivery_mode": e.delivery_mode,
                    "state": e.state,
                    "start_date": e.start_date,
                    "end_date": e.end_date,
                    "final_grade": e.final_grade,
                    "attendance": attendance,
                    "absences": absences,
                }
            )

        values = {
            "page_name": "academic",
            "enrollments_data": enrollments_data,
            "stats": self._compute_stats(student, enrollments),
        }
        values = self._prepare_portal_values(student, values, access=access)
        return request.render("portal_student.portal_student_academic", values)

    @http.route("/my/student/data", type="http", auth="user", website=True)
    def portal_student_data(self, **kwargs):
        """Vista de datos generales: perfil, matrícula, horarios y enlaces."""
        student = self._get_student()
        if not student:
            return request.redirect("/my")
        guard_response, access = self._ensure_portal_access(
            student, capability=["can_view_history", "can_use_apps"]
        )
        if guard_response:
            return guard_response

        overview = self._gather_overview(student)
        values = {
            "page_name": "data",
            "active_enrollment": overview.get("active_enrollment"),
            "enrollments": overview.get("enrollments"),
            "stats": overview.get("stats"),
            "next_sessions": overview.get("next_sessions"),
            "today_sessions": overview.get("today_sessions"),
            "resources": overview.get("resources"),
            "profile_state": overview.get("profile_state"),
        }
        values = self._prepare_portal_values(student, values, access=access)
        return request.render("portal_student.portal_student_data", values)

    @http.route(
        "/my/student/api/overview",
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_student_api_overview(self, **kwargs):
        """Endpoint JSON con datos generales (HU-E1 a HU-E6)."""
        student = self._get_student()
        if not student:
            return request.make_json_response({"error": "student_not_found"})
        if portal_utils.must_change_password(request.env.user):
            return request.make_json_response({"error": "password_change_required"})
        access = self._get_portal_access_rules(student)
        if not access.get("allow_login", True):
            return request.make_json_response({"error": "access_blocked"})
        if not access.get("capabilities", {}).get("can_use_apps", True):
            return request.make_json_response({"error": "access_restricted"})

        overview = self._gather_overview(student)
        active_enrollment = overview.get("active_enrollment")[:1] if overview.get("active_enrollment") else []
        payload = {
            "student": self._serialize_student(student),
            "profile_state": overview.get("profile_state"),
            "stats": overview.get("stats"),
            "active_enrollment": active_enrollment and self._serialize_enrollment(active_enrollment[0]) or False,
            "enrollments": [self._serialize_enrollment(e) for e in overview.get("enrollments")],
            "next_sessions": [self._serialize_session(s) for s in overview.get("next_sessions")],
            "today_sessions": [self._serialize_session(s) for s in overview.get("today_sessions")],
            "resources": [self._serialize_resource(r) for r in overview.get("resources")],
        }
        return request.make_json_response(payload)

    @http.route(
        "/my/student/api/progress",
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_student_api_progress(self, **kwargs):
        """Resumen estructurado de avance por unidad/bloque (HU-E2/HU-E7/HU-E8)."""
        student = self._get_student()
        if not student:
            return request.make_json_response({"error": "student_not_found"})
        if portal_utils.must_change_password(request.env.user):
            return request.make_json_response({"error": "password_change_required"})
        access = self._get_portal_access_rules(student)
        if not access.get("allow_login", True):
            return request.make_json_response({"error": "access_blocked"})
        if not access.get("capabilities", {}).get("can_view_history", True):
            return request.make_json_response({"error": "access_restricted"})

        Plan = request.env["portal.student.weekly.plan"].sudo()
        progress = Plan.get_progress_overview(student)
        return request.make_json_response(progress)

    @http.route(
        "/my/student/api/oral-tests",
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_student_api_oral_tests(self, **kwargs):
        """Disponibilidad de Oral Tests por bloque para el estudiante autenticado."""
        student = self._get_student()
        if not student:
            return request.make_json_response({"error": "student_not_found"})
        if portal_utils.must_change_password(request.env.user):
            return request.make_json_response({"error": "password_change_required"})
        access = self._get_portal_access_rules(student)
        if not access.get("allow_login", True):
            return request.make_json_response({"error": "access_blocked"})
        if not access.get("capabilities", {}).get("can_schedule", True):
            return request.make_json_response({"error": "access_restricted"})

        Plan = request.env["portal.student.weekly.plan"].sudo()
        availability = Plan.get_oral_test_availability(student)
        return request.make_json_response({"oral_tests": availability})

    @http.route(
        "/my/student/api/available-groups",
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_student_api_available_groups(self, subject_id=None, campus_id=None, start=None, end=None, **kwargs):
        """
        TPE06: Endpoint de grupos y horarios disponibles por asignatura para el estudiante autenticado.
        Solo lectura sobre datos de matrícula y clases publicadas.
        """
        student = self._get_student()
        if not student:
            return request.make_json_response({"error": "student_not_found"})
        if portal_utils.must_change_password(request.env.user):
            return request.make_json_response({"error": "password_change_required"})
        access = self._get_portal_access_rules(student)
        if not access.get("allow_login", True):
            return request.make_json_response({"error": "access_blocked"})
        if not access.get("capabilities", {}).get("can_schedule", True):
            return request.make_json_response({"error": "access_restricted"})

        Enrollment = request.env["benglish.enrollment"].sudo()
        Session = request.env["benglish.academic.session"].sudo()

        enrollment_domain = [("student_id", "=", student.id), ("state", "in", ["enrolled", "in_progress"])]
        if subject_id:
            try:
                enrollment_domain.append(("subject_id", "=", int(subject_id)))
            except Exception:
                pass

        enrollments = Enrollment.search(enrollment_domain)
        if not enrollments:
            return request.make_json_response({"enrollments": []})

        today = fields.Date.context_today(request.env.user)
        try:
            start_date = fields.Date.from_string(start) if start else today
        except Exception:
            start_date = today
        try:
            end_date = fields.Date.from_string(end) if end else False
        except Exception:
            end_date = False

        campus_filter = False
        if campus_id:
            try:
                campus_filter = request.env["benglish.campus"].sudo().browse(int(campus_id))
                if not campus_filter.exists():
                    campus_filter = False
            except Exception:
                campus_filter = False

        payload = []
        for enrollment in enrollments:
            session_domain = [
                ("subject_id", "=", enrollment.subject_id.id),
                ("is_published", "=", True),
                (
                    "datetime_start",
                    ">=",
                    fields.Datetime.to_string(datetime.combine(start_date, datetime.min.time())),
                ),
            ]

            # Respetar rango solicitado
            if end_date:
                session_domain.append(
                    (
                        "datetime_start",
                        "<=",
                        fields.Datetime.to_string(datetime.combine(end_date, datetime.max.time())),
                    )
                )

            # Respetar rango de la matrícula activa
            if enrollment.start_date:
                session_domain.append(
                    (
                        "datetime_start",
                        ">=",
                        fields.Datetime.to_string(datetime.combine(enrollment.start_date, datetime.min.time())),
                    )
                )
            if enrollment.end_date:
                session_domain.append(
                    (
                        "datetime_start",
                        "<=",
                        fields.Datetime.to_string(datetime.combine(enrollment.end_date, datetime.max.time())),
                    )
                )

            # Filtrar por sede: prioridad al filtro explícito, luego sede de la matrícula
            if campus_filter:
                session_domain.append(("campus_id", "=", campus_filter.id))
            elif enrollment.campus_id:
                session_domain.append(("campus_id", "=", enrollment.campus_id.id))

            subject_sessions = Session.search(session_domain, order="datetime_start asc")

            payload.append(
                {
                    "enrollment_id": enrollment.id,
                    "subject_id": enrollment.subject_id.id,
                    "subject": enrollment.subject_id.alias or enrollment.subject_id.name,
                    "group": enrollment.group_id and self._serialize_group(enrollment.group_id.sudo()) or False,
                    "campus": enrollment.campus_id.name if enrollment.campus_id else "",
                    "sessions": [self._serialize_session(s) for s in subject_sessions],
                    "total_sessions": len(subject_sessions),
                }
            )

        return request.make_json_response({"enrollments": payload})

    @http.route(
        "/my/student/api/available-campuses",
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_student_api_available_campuses(self, **kwargs):
        """
        TPE20: Endpoint de sedes disponibles para el estudiante.
        Devuelve solo sedes que tengan sesiones publicadas de asignaturas del plan del estudiante.
        """
        student = self._get_student()
        if not student:
            return request.make_json_response({"error": "student_not_found"})
        if portal_utils.must_change_password(request.env.user):
            return request.make_json_response({"error": "password_change_required"})
        access = self._get_portal_access_rules(student)
        if not access.get("allow_login", True):
            return request.make_json_response({"error": "access_blocked"})
        if not access.get("capabilities", {}).get("can_schedule", True):
            return request.make_json_response({"error": "access_restricted"})

        Session = request.env["benglish.academic.session"].sudo()
        Campus = request.env["benglish.campus"].sudo()

        # Obtener asignaturas del programa/plan vigente
        subjects = self._get_student_subjects(student)
        if not subjects:
            return request.make_json_response({"campuses": []})

        agendas = self._get_latest_published_agendas(student, subjects)
        if not agendas:
            return request.make_json_response({"campuses": []})

        # Buscar sedes con sesiones publicadas y vigentes para esas asignaturas
        sessions = Session.search(
            [
                ("subject_id", "in", subjects.ids),
                ("is_published", "=", True),
                ("active", "=", True),
                ("agenda_id", "in", agendas.ids),
            ]
        )
        campus_ids = sessions.mapped("campus_id").ids
        campuses = Campus.search(
            [("id", "in", campus_ids), ("active", "=", True)], order="city_name, name"
        )

        payload = [self._serialize_campus(c) for c in campuses]
        return request.make_json_response({"campuses": payload})

    @http.route(
        "/my/student/api/published-sessions",
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_student_api_published_sessions(self, start=None, **kwargs):
        """Endpoint JSON para horarios publicados filtrados por semana."""
        student = self._get_student()
        if not student:
            return request.make_json_response({"error": "student_not_found"})
        if portal_utils.must_change_password(request.env.user):
            return request.make_json_response({"error": "password_change_required"})
        access = self._get_portal_access_rules(student)
        if not access.get("allow_login", True):
            return request.make_json_response({"error": "access_blocked"})
        if not access.get("capabilities", {}).get("can_schedule", True):
            return request.make_json_response({"error": "access_restricted"})

        week = self._prepare_week(start)
        payload = {
            "week_start": fields.Date.to_string(week.get("monday")) if week.get("monday") else False,
            "week_end": fields.Date.to_string(week.get("sunday")) if week.get("sunday") else False,
            "sessions": [self._serialize_session(s) for s in week.get("sessions")],
            "agenda": [
                {
                    "date": fields.Date.to_string(day.get("date")) if day.get("date") else False,
                    "sessions": [self._serialize_session(ss) for ss in day.get("sessions")],
                }
                for day in week.get("agenda_by_day") or []
            ],
        }
        return request.make_json_response(payload)
    
    @http.route("/my/student/debug/sedes", type="http", auth="user", website=True, methods=["GET"])
    def portal_student_debug_sedes(self, **kwargs):
        """Endpoint temporal de debug para verificar sedes disponibles."""
        student = self._get_student()
        if not student:
            return request.make_response("<h1>Estudiante no encontrado</h1>", headers=[('Content-Type', 'text/html')])
        if portal_utils.must_change_password(request.env.user):
            return request.make_response("<h1>Acceso restringido</h1>", headers=[('Content-Type', 'text/html')])
        access = self._get_portal_access_rules(student)
        if not access.get("allow_login", True) or not access.get("capabilities", {}).get("can_schedule", True):
            return request.make_response("<h1>Acceso restringido</h1>", headers=[('Content-Type', 'text/html')])
        
        Session = request.env["benglish.academic.session"].sudo()
        Campus = request.env["benglish.campus"].sudo()
        
        # Obtener asignaturas del programa/plan vigente
        subjects = self._get_student_subjects(student)
        agendas = self._get_latest_published_agendas(student, subjects)

        # Buscar sesiones
        sessions = Session.search([
            ("subject_id", "in", subjects.ids),
            ("is_published", "=", True),
            ("active", "=", True),
            ("agenda_id", "in", agendas.ids) if agendas else ("id", "=", 0),
        ])
        
        # Obtener campus IDs
        campus_ids = sessions.mapped("campus_id").ids
        unique_campus_ids = list(set(campus_ids))
        
        # Buscar campuses
        campuses = Campus.search([
            ("id", "in", campus_ids),
            ("active", "=", True),
        ], order="city_name, name")
        
        # Agrupar por ciudad
        cities_data = {}
        for campus in campuses:
            city = campus.city_name or "Virtual"
            if city not in cities_data:
                cities_data[city] = []
            campus_sessions = sessions.filtered(lambda s: s.campus_id.id == campus.id)
            cities_data[city].append({
                "campus": campus,
                "sessions_count": len(campus_sessions),
                "subjects_count": len(campus_sessions.mapped("subject_id"))
            })
        
        # Generar HTML
        html = "<html><head><title>Debug Sedes</title><style>"
        html += "body { font-family: Arial; padding: 20px; } "
        html += "table { border-collapse: collapse; width: 100%; margin: 20px 0; } "
        html += "th, td { border: 1px solid #ddd; padding: 12px; text-align: left; } "
        html += "th { background: #4CAF50; color: white; } "
        html += ".city-header { background: #2196F3; color: white; font-weight: bold; } "
        html += "</style></head><body>"
        
        html += f"<h1>DEBUG - Sedes Disponibles</h1>"
        html += f"<h2>Estudiante: {student.name} (ID: {student.id})</h2>"
        html += f"<p><strong>Plan:</strong> {student.plan_id.name if student.plan_id else 'SIN PLAN'}</p>"
        
        html += "<h3>Resumen:</h3>"
        html += "<table>"
        html += "<tr><th>Descripción</th><th>Cantidad</th></tr>"
        html += f"<tr><td>Total asignaturas</td><td>{len(subjects)}</td></tr>"
        html += f"<tr><td>Sesiones publicadas encontradas</td><td>{len(sessions)}</td></tr>"
        html += f"<tr><td>Campus IDs únicos</td><td>{len(unique_campus_ids)}</td></tr>"
        html += f"<tr><td>Sedes activas disponibles</td><td>{len(campuses)}</td></tr>"
        html += f"<tr><td>Ciudades con sedes</td><td>{len(cities_data)}</td></tr>"
        html += "</table>"
        
        html += "<h3>Detalle por Ciudad y Sede:</h3>"
        html += "<table>"
        html += "<tr><th>Ciudad</th><th>Sede</th><th>ID</th><th>Activa</th><th>Sesiones</th><th>Asignaturas</th></tr>"
        
        for city in sorted(cities_data.keys()):
            first = True
            for campus_data in cities_data[city]:
                campus = campus_data["campus"]
                if first:
                    html += f"<tr><td rowspan='{len(cities_data[city])}' class='city-header'>{city}</td>"
                    first = False
                else:
                    html += "<tr>"
                html += f"<td>{campus.name}</td>"
                html += f"<td>{campus.id}</td>"
                html += f"<td>{'Sí' if campus.active else 'No'}</td>"
                html += f"<td>{campus_data['sessions_count']}</td>"
                html += f"<td>{campus_data['subjects_count']}</td>"
                html += "</tr>"
        
        html += "</table>"
        
        html += "<h3>Campus IDs en sesiones (raw):</h3>"
        html += f"<p>{unique_campus_ids}</p>"
        
        html += "</body></html>"
        
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])
    
    # ==================== CONGELAMIENTO (HU-PE-CONG-01) ====================
    
    @http.route("/my/student/freeze", type="http", auth="user", website=True, methods=["GET"])
    def portal_student_freeze(self, **kwargs):
        """Vista principal de solicitud de congelamiento."""
        student = self._get_student()
        if not student:
            return request.redirect("/my")
        guard_response, access = self._ensure_portal_access(student, capability="can_request_freeze")
        if guard_response:
            return guard_response
        
        # Obtener matrículas activas
        active_enrollments = student.enrollment_ids.sudo().filtered(
            lambda e: e.state in ["enrolled", "in_progress"]
        )
        
        # Obtener solicitudes previas del estudiante
        FreezeRequest = request.env['portal.student.freeze.request'].sudo()
        previous_requests = FreezeRequest.search([
            ('student_id', '=', student.id)
        ], order='create_date desc', limit=10)
        
        # Obtener periodos de congelamiento del backend
        FreezePeriod = request.env['benglish.student.freeze.period'].sudo()
        freeze_periods = FreezePeriod.search([
            ('student_id', '=', student.id),
            ('visible_portal', '=', True)
        ], order='fecha_inicio desc')
        
        # HU-PE-CONG-02: Obtener congelamiento activo actual
        today = fields.Date.context_today(request.env.user)
        active_freeze_period = FreezePeriod.search([
            ('student_id', '=', student.id),
            ('estado', '=', 'aprobado'),
            ('fecha_inicio', '<=', today),
            ('fecha_fin', '>=', today)
        ], limit=1)
        
        # Calcular fecha de retorno (día siguiente al fin del congelamiento)
        return_date = False
        if active_freeze_period:
            return_date = active_freeze_period.fecha_fin + timedelta(days=1)
        
        # Obtener motivos disponibles
        FreezeReason = request.env['benglish.freeze.reason'].sudo()
        freeze_reasons = FreezeReason.search([
            ('active', '=', True),
            ('es_especial', '=', False)
        ], order='sequence, name')
        
        # Preparar información de cada matrícula
        enrollment_info = []
        for enrollment in active_enrollments:
            FreezeConfig = request.env['benglish.plan.freeze.config'].sudo()
            config = FreezeConfig.get_config_for_plan(enrollment.plan_id) if enrollment.plan_id else False
            
            # Calcular días usados
            dias_usados = 0
            if config:
                congelamientos = FreezePeriod.search([
                    ('enrollment_id', '=', enrollment.id),
                    ('estado', 'in', ('aprobado', 'finalizado')),
                    ('es_especial', '=', False)
                ])
                dias_usados = sum(congelamientos.mapped('dias'))
            
            # Calcular días disponibles
            dias_disponibles = 0
            permite_congelamiento = False
            if config:
                permite_congelamiento = config.permite_congelamiento
                if permite_congelamiento:
                    dias_disponibles = max(0, config.max_dias_acumulados - dias_usados)
            
            enrollment_info.append({
                'enrollment': enrollment,
                'config': config,
                'dias_usados': dias_usados,
                'dias_disponibles': dias_disponibles,
                'permite_congelamiento': permite_congelamiento,
                'puede_solicitar': permite_congelamiento and dias_disponibles >= (config.min_dias_congelamiento if config else 0),
            })
        
        values = {
            'page_name': 'freeze',
            'active_enrollments': active_enrollments,
            'enrollment_info': enrollment_info,
            'previous_requests': previous_requests,
            'freeze_periods': freeze_periods,
            'freeze_reasons': freeze_reasons,
            'active_freeze_period': active_freeze_period,
            'return_date': return_date,
            'message': kwargs.get('message'),
            'error': kwargs.get('error'),
        }
        values = self._prepare_portal_values(student, values, access=access)
        return request.render("portal_student.portal_student_freeze", values)
    
    @http.route("/my/student/freeze/request", type="http", auth="user", website=True, methods=["GET", "POST"], csrf=True)
    def portal_student_freeze_request(self, **kwargs):
        """Formulario y procesamiento de solicitud de congelamiento."""
        student = self._get_student()
        if not student:
            return request.redirect("/my")
        guard_response, _access = self._ensure_portal_access(student, capability="can_request_freeze")
        if guard_response:
            return guard_response
        
        # Si es GET, redirigir a la vista principal con el enrollment seleccionado
        if request.httprequest.method == "GET":
            enrollment_id = kwargs.get('enrollment_id')
            if enrollment_id:
                try:
                    enrollment_id = int(enrollment_id)
                    enrollment = request.env['benglish.enrollment'].sudo().browse(enrollment_id)
                    if enrollment.exists() and enrollment.student_id == student:
                        # Preparar datos para prellenar el formulario
                        kwargs['enrollment_id'] = enrollment_id
                except (ValueError, TypeError):
                    pass
            return self.portal_student_freeze(**kwargs)
        
        # Si es POST, procesar la solicitud
        try:
            # Validar datos requeridos
            enrollment_id = int(kwargs.get('enrollment_id', 0))
            fecha_inicio = kwargs.get('fecha_inicio')
            fecha_fin = kwargs.get('fecha_fin')
            freeze_reason_id = int(kwargs.get('freeze_reason_id', 0))
            motivo_detalle = kwargs.get('motivo_detalle', '')
            
            # T-PE-CONG-02: Validar aceptación de términos financieros
            aceptacion_terminos = kwargs.get('aceptacion_terminos')
            if not aceptacion_terminos or aceptacion_terminos != 'on':
                raise ValidationError(
                    "Debes aceptar las condiciones financieras para continuar. "
                    "El congelamiento es únicamente académico y tu plan de pagos continúa sin cambios."
                )
            
            if not all([enrollment_id, fecha_inicio, fecha_fin, freeze_reason_id]):
                raise ValidationError("Todos los campos son obligatorios")
            
            # Validar que la matrícula pertenece al estudiante
            enrollment = request.env['benglish.enrollment'].sudo().browse(enrollment_id)
            if not enrollment.exists() or enrollment.student_id.id != student.id:
                raise ValidationError("Matrícula no válida")
            
            if enrollment.state not in ['enrolled', 'in_progress']:
                raise ValidationError("Solo puedes solicitar congelamiento para matrículas activas")
            
            # Convertir fechas
            fecha_inicio = fields.Date.from_string(fecha_inicio)
            fecha_fin = fields.Date.from_string(fecha_fin)
            
            # Validar que las fechas sean futuras
            today = fields.Date.context_today(request.env.user)
            if fecha_inicio < today:
                raise ValidationError("La fecha de inicio debe ser igual o posterior a hoy")
            
            # Crear la solicitud directamente en el backend (benglish.student.freeze.period)
            FreezePeriod = request.env['benglish.student.freeze.period'].sudo()
            freeze_period = FreezePeriod.create({
                'student_id': student.id,
                'enrollment_id': enrollment_id,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'freeze_reason_id': freeze_reason_id,
                'motivo_detalle': motivo_detalle,
                'estado': 'borrador',
            })
            
            # T-PE-CONG-02: Registrar aceptación de términos financieros en el chatter
            freeze_period.message_post(
                body=f"""
                <div style="padding: 12px; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 6px;">
                    <strong style="color: #92400e;">✓ Términos Financieros Aceptados</strong><br/>
                    <p style="margin: 8px 0 0; color: #78350f;">
                        El estudiante <strong>{student.name}</strong> ha leído y aceptado que:
                    </p>
                    <ul style="margin: 8px 0; padding-left: 20px; color: #78350f;">
                        <li>El congelamiento es únicamente académico</li>
                        <li>El plan de pagos continúa sin cambios</li>
                        <li>Debe mantener sus cuotas al día durante el congelamiento</li>
                    </ul>
                    <p style="margin: 8px 0 0; font-size: 12px; color: #92400e;">
                        <em>Fecha de aceptación: {fields.Datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</em>
                    </p>
                </div>
                """,
                subject="Aceptación de Términos Financieros"
            )
            
            # Manejar archivos adjuntos si hay
            if 'documento_soporte' in request.httprequest.files:
                files = request.httprequest.files.getlist('documento_soporte')
                Attachment = request.env['ir.attachment'].sudo()
                for file in files:
                    if file.filename:
                        attachment = Attachment.create({
                            'name': file.filename,
                            'datas': base64.b64encode(file.read()),
                            'res_model': 'benglish.student.freeze.period',
                            'res_id': freeze_period.id,
                            'type': 'binary',
                        })
                        freeze_period.documento_soporte_ids = [(4, attachment.id)]
            
            # Enviar la solicitud a aprobación
            freeze_period.action_enviar_aprobacion()
            
            return request.redirect('/my/student/freeze?message=Solicitud enviada correctamente para aprobación')
            
        except ValidationError as e:
            return request.redirect(f'/my/student/freeze?error={str(e)}')
        except Exception as e:
            error_detail = traceback.format_exc()
            request.env['ir.logging'].sudo().create({
                'name': 'Portal Student Freeze Request Error',
                'type': 'server',
                'level': 'error',
                'message': f'Error al procesar solicitud de congelamiento: {str(e)}\n\n{error_detail}',
                'path': 'portal_student.freeze_request',
                'func': 'portal_student_freeze_request',
                'line': 0,
            })
            return request.redirect(f'/my/student/freeze?error=Error al procesar la solicitud. Por favor contacta al administrador.')

    @http.route('/my/student/mark_notifications_viewed', type='json', auth='user', website=True, methods=['POST'])
    def mark_notifications_viewed(self, session_ids=None, **kwargs):
        """Marca notificaciones como vistas cuando el estudiante abre el dropdown."""
        try:
            _logger.info(f"=== MARK NOTIFICATIONS VIEWED START ===")
            _logger.info(f"Session IDs recibidos: {session_ids}")

            if not session_ids:
                _logger.warning("No session IDs provided")
                return {'success': False, 'error': 'No session IDs provided'}

            user = request.env.user
            if portal_utils.must_change_password(user):
                return {'success': False, 'error': 'password_change_required'}

            student = self._get_student()
            if not student:
                return {'success': False, 'error': 'student_not_found'}

            access = self._get_portal_access_rules(student)
            if not access.get("allow_login", True):
                return {'success': False, 'error': 'access_blocked'}
            if not access.get("capabilities", {}).get("can_use_apps", True):
                return {'success': False, 'error': 'access_restricted'}
            _logger.info(f"Usuario: {user.name} (ID: {user.id})")
            
            NotificationView = request.env['portal.notification.view'].sudo()
            created_count = 0
            
            for session_id in session_ids:
                # Verificar que la sesión existe
                session = request.env['benglish.academic.session'].sudo().browse(session_id)
                if not session.exists():
                    _logger.warning(f"Sesión {session_id} no existe")
                    continue
                
                session_label = session.student_alias or (
                    session.subject_id.alias if session.subject_id else False
                ) or (session.subject_id.name if session.subject_id else "Sin asignatura")
                _logger.info(f"Procesando sesión {session_id}: {session_label}")
                
                # Crear registro de vista si no existe
                existing = NotificationView.search([
                    ('user_id', '=', user.id),
                    ('session_id', '=', session_id)
                ], limit=1)
                
                if existing:
                    _logger.info(f"  - Ya existe registro de vista para sesión {session_id}")
                else:
                    new_view = NotificationView.create({
                        'user_id': user.id,
                        'session_id': session_id,
                    })
                    created_count += 1
                    _logger.info(f"  - Creado nuevo registro de vista {new_view.id} para sesión {session_id}")
            
            _logger.info(f"Total registros creados: {created_count}")
            _logger.info(f"=== MARK NOTIFICATIONS VIEWED END ===")
            
            return {'success': True, 'viewed_count': len(session_ids), 'created': created_count}
        except Exception as e:
            _logger.error(f"Error marking notifications as viewed: {str(e)}")
            _logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}

    @http.route('/my/student/notifications_count', type='json', auth='user', website=True)
    def get_notifications_count(self, **kwargs):
        """Obtiene el contador de notificaciones no vistas para el estudiante actual."""
        try:
            user = request.env.user
            if portal_utils.must_change_password(user):
                return {'success': False, 'error': 'password_change_required', 'unseen_count': 0}

            student = self._get_student()
            if not student:
                return {'success': False, 'error': 'student_not_found', 'unseen_count': 0}

            access = self._get_portal_access_rules(student)
            if not access.get("allow_login", True):
                return {'success': False, 'error': 'access_blocked', 'unseen_count': 0}
            if not access.get("capabilities", {}).get("can_use_apps", True):
                return {'success': False, 'error': 'access_restricted', 'unseen_count': 0}
            
            # Obtener programa y modalidad del estudiante
            program, plan = self._get_student_program_and_plan(student)
            student_mode = student.preferred_delivery_mode or 'presential'
            
            # Construir dominio para notificaciones relevantes
            notif_domain = [
                ('is_published', '=', True),
                ('datetime_start', '>', fields.Datetime.now()),  # Solo futuras
            ]
            
            # Filtrar por programa si existe
            if program:
                notif_domain.append(('program_id', '=', program.id))
            
            # Filtrar por modalidad compatible
            if student_mode == 'virtual':
                notif_domain.append(('delivery_mode', 'in', ['virtual', 'hybrid']))
            elif student_mode == 'presential':
                notif_domain.append(('delivery_mode', 'in', ['presential', 'hybrid']))
            # Si es hybrid, mostrar todas
            
            # Obtener notificaciones (sesiones publicadas relevantes para el estudiante)
            notif_list = request.env['benglish.academic.session'].sudo().search(
                notif_domain, 
                order='datetime_start asc',  # Más próximas primero
                limit=10
            )
            
            # Obtener IDs de las notificaciones que el usuario ya ha visto
            viewed_ids = request.env['portal.notification.view'].sudo().search([
                ('user_id','=',user.id)
            ]).mapped('session_id').ids
            
            # Calcular notificaciones no vistas
            unseen_count = len([n for n in notif_list if n.id not in viewed_ids])
            
            return {
                'success': True,
                'unseen_count': unseen_count,
                'total_notifications': len(notif_list)
            }
        except Exception as e:
            _logger.error(f"Error getting notifications count: {str(e)}")
            return {'success': False, 'error': str(e), 'unseen_count': 0}

    @http.route('/my/student/notifications_debug', type='json', auth='user', website=True)
    def notifications_debug(self, **kwargs):
        """Endpoint de diagnóstico para verificar estado de notificaciones."""
        try:
            user = request.env.user
            if portal_utils.must_change_password(user):
                return {'success': False, 'error': 'password_change_required'}

            student = self._get_student()
            if not student:
                return {'success': False, 'error': 'student_not_found'}

            access = self._get_portal_access_rules(student)
            if not access.get("allow_login", True):
                return {'success': False, 'error': 'access_blocked'}
            if not access.get("capabilities", {}).get("can_use_apps", True):
                return {'success': False, 'error': 'access_restricted'}
            
            # Obtener notificaciones
            notif_list = request.env['benglish.academic.session'].sudo().search(
                [('is_published','=',True)], 
                order='create_date desc', 
                limit=10
            )
            
            # Obtener vistas
            viewed_records = request.env['portal.notification.view'].sudo().search([
                ('user_id','=',user.id)
            ])
            
            viewed_ids = viewed_records.mapped('session_id').ids
            
            notifications = []
            for n in notif_list:
                subject_label = n.student_alias or (
                    n.subject_id.alias if n.subject_id else False
                ) or (n.subject_id.name if n.subject_id else "Sin asignatura")
                notifications.append({
                    'id': n.id,
                    'subject': subject_label,
                    'datetime': str(n.datetime_start),
                    'created': str(n.create_date),
                    'is_viewed': n.id in viewed_ids
                })
            
            return {
                'success': True,
                'user': user.name,
                'student_id': student.id,
                'notifications': notifications,
                'viewed_count': len(viewed_ids),
                'total_notifications': len(notif_list)
            }
        except Exception as e:
            _logger.error(f"Error in notifications_debug: {str(e)}")
            return {'success': False, 'error': str(e)}

    # ===================================================================
    # NUEVO: HISTORIAL ACADÉMICO
    # Endpoints para consultar el historial de clases dictadas
    # ===================================================================

    @http.route('/my/student/academic_history', type='http', auth='user', website=True)
    def portal_academic_history(self, **kwargs):
        """
        Vista del historial académico del estudiante.
        Muestra todas las clases dictadas con su asistencia.
        """
        user = request.env.user
        
        # Validaciones de acceso
        if portal_utils.must_change_password(user):
            return request.redirect("/my/welcome")
        
        student = self._get_student()
        if not student:
            return request.redirect("/my")
        
        # Verificar acceso
        access_response, access = self._ensure_portal_access(student, capability="can_view_history")
        if access_response:
            return access_response
        
        # Obtener historial académico
        History = request.env["benglish.academic.history"].sudo()
        domain = [("student_id", "=", student.id)]
        history = History.search(domain, order="session_date desc, session_time_start desc", limit=100)
        
        # Obtener resumen de asistencia
        total = len(history)
        attended = len(history.filtered(lambda h: h.attendance_status == "attended"))
        absent = len(history.filtered(lambda h: h.attendance_status == "absent"))
        pending = len(history.filtered(lambda h: h.attendance_status == "pending"))
        attendance_summary = {
            "total_classes": total,
            "attended": attended,
            "absent": absent,
            "pending": pending,
            "attendance_rate": round((attended / total * 100), 2) if total > 0 else 0,
        }
        
        # Preparar valores para la vista
        values = self._prepare_portal_values(student, access=access)
        values.update({
            "page_name": "academic_history",
            "history": history,
            "attendance_summary": attendance_summary,
        })
        
        return request.render("portal_student.portal_student_academic_history", values)
    
    @http.route('/my/student/api/academic_history', type='json', auth='user', website=True)
    def api_get_academic_history(self, filters=None, **kwargs):
        """
        API JSON para obtener el historial académico del estudiante.
        
        Args:
            filters (dict): Filtros opcionales
                - program_id: Filtrar por programa
                - subject_id: Filtrar por asignatura
                - attendance_status: Filtrar por estado de asistencia
                - date_from: Fecha desde
                - date_to: Fecha hasta
                - limit: Límite de registros (default: 100)
        
        Returns:
            dict: {
                'success': bool,
                'history': list,
                'summary': dict,
                'total': int
            }
        """
        try:
            user = request.env.user
            
            # Validaciones
            if portal_utils.must_change_password(user):
                return {"success": False, "error": "password_change_required"}
            
            student = self._get_student()
            if not student:
                return {"success": False, "error": "student_not_found"}
            
            access = self._get_portal_access_rules(student)
            if not access.get("allow_login", True):
                return {"success": False, "error": "access_blocked"}
            
            # Obtener historial con filtros
            History = request.env["benglish.academic.history"].sudo()
            if filters is None:
                filters = {}
            limit = int(filters.get("limit", 100))

            domain = [("student_id", "=", student.id)]
            if filters.get("program_id"):
                domain.append(("program_id", "=", filters["program_id"]))
            if filters.get("subject_id"):
                domain.append(("subject_id", "=", filters["subject_id"]))
            if filters.get("attendance_status"):
                domain.append(("attendance_status", "=", filters["attendance_status"]))
            if filters.get("date_from"):
                domain.append(("session_date", ">=", filters["date_from"]))
            if filters.get("date_to"):
                domain.append(("session_date", "<=", filters["date_to"]))

            history = History.search(domain, order="session_date desc, session_time_start desc")
            if limit > 0:
                history = history[:limit]
            
            # Serializar historial
            history_data = []
            for record in history:
                subject_label = ""
                if record.session_id and getattr(record.session_id, "student_alias", False):
                    subject_label = record.session_id.student_alias
                elif record.subject_id:
                    subject_label = record.subject_id.alias or record.subject_id.name or ""
                history_data.append({
                    "id": record.id,
                    "date": fields.Date.to_string(record.session_date) if record.session_date else False,
                    "subject": subject_label,
                    "subject_code": record.subject_id.alias if record.subject_id else "",
                    "program": record.program_id.name if record.program_id else "",
                    "level": record.level_id.name if record.level_id else "",
                    "campus": record.campus_id.name if record.campus_id else "",
                    "teacher": record.teacher_id.name if record.teacher_id else "",
                    "delivery_mode": record.delivery_mode,
                    "attendance_status": record.attendance_status,
                    "time_start": record.session_time_start,
                    "time_end": record.session_time_end,
                })
            
            # Obtener resumen de asistencia
            total = len(history)
            attended = len(history.filtered(lambda h: h.attendance_status == "attended"))
            absent = len(history.filtered(lambda h: h.attendance_status == "absent"))
            pending = len(history.filtered(lambda h: h.attendance_status == "pending"))
            summary = {
                "total_classes": total,
                "attended": attended,
                "absent": absent,
                "pending": pending,
                "attendance_rate": round((attended / total * 100), 2) if total > 0 else 0,
            }
            
            return {
                "success": True,
                "history": history_data,
                "summary": summary,
                "total": len(history_data)
            }
            
        except Exception as e:
            _logger.error(f"Error getting academic history: {str(e)}\n{traceback.format_exc()}")
            return {"success": False, "error": str(e)}
    
    @http.route('/my/student/api/attendance_summary', type='json', auth='user', website=True)
    def api_get_attendance_summary(self, program_id=None, **kwargs):
        """
        API JSON para obtener resumen de asistencia del estudiante.
        
        Returns:
            dict: {
                'success': bool,
                'total_classes': int,
                'attended': int,
                'absent': int,
                'pending': int,
                'attendance_rate': float
            }
        """
        try:
            user = request.env.user
            
            # Validaciones
            if portal_utils.must_change_password(user):
                return {"success": False, "error": "password_change_required"}
            
            student = self._get_student()
            if not student:
                return {"success": False, "error": "student_not_found"}
            
            access = self._get_portal_access_rules(student)
            if not access.get("allow_login", True):
                return {"success": False, "error": "access_blocked"}
            
            # Obtener resumen
            History = request.env["benglish.academic.history"].sudo()
            summary = History.get_attendance_summary(student.id, program_id=program_id)
            
            return {
                "success": True,
                **summary
            }
            
        except Exception as e:
            _logger.error(f"Error getting attendance summary: {str(e)}")
            return {"success": False, "error": str(e)}
