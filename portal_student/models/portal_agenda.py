# -*- coding: utf-8 -*-
"""Modelos de horario semanal para el portal (no alteran la matrícula)."""

import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class PortalStudentWeeklyPlan(models.Model):
    _name = "portal.student.weekly.plan"
    _description = "Plan semanal de portal"
    _order = "week_start desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        required=True,
        ondelete="cascade",
    )
    week_start = fields.Date(string="Inicio de semana (lunes)", required=True)
    week_end = fields.Date(compute="_compute_week_end", store=True)
    
    # HU-E9: Filtro de sede temporal (no modifica matrícula)
    filter_campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Filtro de Sede",
        help="Sede temporal para filtrar horario publicado (no afecta matrícula académica)"
    )
    filter_city = fields.Char(
        string="Filtro de Ciudad",
        help="Ciudad temporal para filtrar horario publicado"
    )
    
    line_ids = fields.One2many(
        comodel_name="portal.student.weekly.plan.line",
        inverse_name="plan_id",
        string="Clases programadas",
    )
    total_sessions = fields.Integer(compute="_compute_total_sessions", store=True)

    _sql_constraints = [
        (
            "plan_unique_student_week",
            "unique(student_id, week_start)",
            "Ya existe un plan semanal para este estudiante.",
        )
    ]

    @api.depends("week_start")
    def _compute_week_end(self):
        for plan in self:
            plan.week_end = plan.week_start + timedelta(days=6) if plan.week_start else False

    @api.depends("week_start")
    def _compute_name(self):
        for plan in self:
            if plan.week_start:
                week_number = plan.week_start.isocalendar()[1]
                plan.name = _("Semana %s - %s") % (week_number, plan.week_start)
            else:
                plan.name = _("Plan semanal")

    @api.depends("line_ids")
    def _compute_total_sessions(self):
        for plan in self:
            plan.total_sessions = len(plan.line_ids)

    @api.model
    def normalize_week_start(self, value):
        """Devuelve siempre el lunes de la semana del valor recibido."""
        base_date = value or fields.Date.context_today(self)
        if isinstance(base_date, str):
            base_date = fields.Date.from_string(base_date)
        return base_date - timedelta(days=base_date.weekday())

    @api.model
    def get_or_create_for_student(self, student, week_start):
        """Obtiene (o crea) el plan de una semana para el estudiante."""
        student_id = student.id if hasattr(student, "id") else int(student)
        monday = self.normalize_week_start(week_start)
        plan = self.search(
            [("student_id", "=", student_id), ("week_start", "=", monday)], limit=1
        )
        if not plan:
            plan = self.create({"student_id": student_id, "week_start": monday})
        return plan

    def compute_dependent_lines(self, base_line):
        """
        Devuelve las líneas dependientes que deben desagendarse
        si se elimina la línea base (dependencias transitivas).
        
        HU-E8: Si la línea es una sesión prerrequisito (BCheck) y tiene enforce_prerequisite_first,
        entonces TODAS las demás sesiones de la semana deben eliminarse.
        """
        self.ensure_one()
        lines_to_unlink = self.env["portal.student.weekly.plan.line"]
        
        # HU-E8: Lógica especial para prerrequisito BCheck
        # Si es BCheck (prerrequisito), no eliminar otras líneas automáticamente
        # (la lógica de enforce_prerequisite_first ya no aplica sin class_type_id)
        base_subject = base_line.effective_subject_id or base_line._get_effective_subject(
            check_completed=False,
            check_prereq=False,
        )
        if not base_subject:
            return lines_to_unlink

        if base_line._is_prerequisite_subject(base_subject):
            # Los BCheck no eliminan otras sesiones automáticamente
            pass
        
        # Lógica original para otras dependencias (prerrequisitos de asignaturas)
        processed_subjects = set()
        pending = {base_subject.id}

        while pending:
            subject_id = pending.pop()
            processed_subjects.add(subject_id)
            dependents = self.env["portal.student.weekly.plan.line"]
            for line in self.line_ids:
                line_subject = line.effective_subject_id or line._get_effective_subject(
                    check_completed=False,
                    check_prereq=False,
                )
                if line_subject and subject_id in (line_subject.prerequisite_ids.ids or []):
                    dependents |= line
            lines_to_unlink |= dependents
            new_subject_ids = set(dependents.mapped("effective_subject_id").ids) - processed_subjects
            pending.update(new_subject_ids)
        return lines_to_unlink


class PortalStudentFreezeRequest(models.Model):
    """Modelo para gestionar solicitudes de congelamiento desde el portal.
    
    Este modelo permite a los estudiantes solicitar congelamiento de sus
    matrículas activas sin modificar directamente el modelo backend.
    Crea registros en benglish.student.freeze.period con estado 'borrador'.
    """
    _name = "portal.student.freeze.request"
    _description = "Solicitud de Congelamiento desde Portal"
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Campos básicos
    name = fields.Char(compute="_compute_name", store=True)
    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        required=True,
        ondelete="cascade",
        index=True
    )
    enrollment_id = fields.Many2one(
        comodel_name="benglish.enrollment",
        string="Matrícula",
        required=True,
        domain="[('student_id', '=', student_id), ('state', 'in', ['enrolled', 'in_progress'])]"
    )
    
    # Fechas de congelamiento
    fecha_inicio = fields.Date(
        string="Fecha de Inicio",
        required=True,
        help="Fecha de inicio del periodo de congelamiento"
    )
    fecha_fin = fields.Date(
        string="Fecha de Fin",
        required=True,
        help="Fecha de finalización del periodo de congelamiento"
    )
    dias = fields.Integer(
        string="Días Solicitados",
        compute="_compute_dias",
        store=True
    )
    
    # Motivo
    freeze_reason_id = fields.Many2one(
        comodel_name="benglish.freeze.reason",
        string="Motivo",
        required=True,
        domain="[('active', '=', True), ('es_especial', '=', False)]"
    )
    motivo_detalle = fields.Text(
        string="Descripción Detallada",
        help="Explique con más detalle su situación"
    )
    
    # Documentos
    documento_soporte_ids = fields.Many2many(
        'ir.attachment',
        'portal_freeze_request_attachment_rel',
        'request_id',
        'attachment_id',
        string='Documentos de Soporte'
    )
    
    # Estado
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('sent', 'Enviado'),
        ('processing', 'En Proceso'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ], default='draft', string='Estado', tracking=True)
    
    # Información computada del plan
    plan_id = fields.Many2one(
        related='enrollment_id.plan_id',
        string='Plan',
        store=True
    )
    freeze_config_id = fields.Many2one(
        comodel_name='benglish.plan.freeze.config',
        compute='_compute_freeze_config',
        store=True
    )
    dias_disponibles = fields.Integer(
        compute='_compute_dias_info',
        string='Días Disponibles'
    )
    dias_usados = fields.Integer(
        compute='_compute_dias_info',
        string='Días Ya Usados'
    )
    puede_solicitar = fields.Boolean(
        compute='_compute_puede_solicitar',
        string='Puede Solicitar'
    )
    mensaje_validacion = fields.Text(
        compute='_compute_puede_solicitar',
        string='Mensaje de Validación'
    )
    
    # Referencia al periodo de congelamiento creado
    freeze_period_id = fields.Many2one(
        comodel_name='benglish.student.freeze.period',
        string='Periodo de Congelamiento',
        readonly=True
    )
    
    @api.depends('student_id', 'enrollment_id', 'fecha_inicio', 'fecha_fin')
    def _compute_name(self):
        for rec in self:
            if rec.student_id and rec.fecha_inicio:
                rec.name = f"Solicitud de {rec.student_id.name} - {rec.fecha_inicio}"
            else:
                rec.name = "Nueva Solicitud de Congelamiento"
    
    @api.depends('fecha_inicio', 'fecha_fin')
    def _compute_dias(self):
        for rec in self:
            if rec.fecha_inicio and rec.fecha_fin:
                delta = rec.fecha_fin - rec.fecha_inicio
                rec.dias = delta.days + 1
            else:
                rec.dias = 0
    
    @api.depends('enrollment_id.plan_id')
    def _compute_freeze_config(self):
        FreezeConfig = self.env['benglish.plan.freeze.config'].sudo()
        for rec in self:
            if rec.enrollment_id and rec.enrollment_id.plan_id:
                rec.freeze_config_id = FreezeConfig.get_config_for_plan(
                    rec.enrollment_id.plan_id
                )
            else:
                rec.freeze_config_id = False
    
    @api.depends('student_id', 'enrollment_id', 'freeze_config_id')
    def _compute_dias_info(self):
        for rec in self:
            if not rec.freeze_config_id:
                rec.dias_usados = 0
                rec.dias_disponibles = 0
                continue
            
            # Obtener días usados del estudiante
            FreezePeriod = self.env['benglish.student.freeze.period'].sudo()
            congelamientos_previos = FreezePeriod.search([
                ('enrollment_id', '=', rec.enrollment_id.id),
                ('estado', 'in', ('aprobado', 'finalizado')),
                ('es_especial', '=', False),
            ])
            rec.dias_usados = sum(congelamientos_previos.mapped('dias'))
            rec.dias_disponibles = max(
                0,
                rec.freeze_config_id.max_dias_acumulados - rec.dias_usados
            )
    
    @api.depends('dias', 'dias_disponibles', 'freeze_config_id', 'student_id')
    def _compute_puede_solicitar(self):
        for rec in self:
            if not rec.freeze_config_id:
                rec.puede_solicitar = False
                rec.mensaje_validacion = "No hay configuración de congelamiento para este plan"
                continue
            
            config = rec.freeze_config_id
            
            # Verificar si el plan permite congelamiento
            if not config.permite_congelamiento:
                rec.puede_solicitar = False
                rec.mensaje_validacion = "Su plan no permite solicitar congelamiento"
                continue
            
            # Verificar días mínimos
            if rec.dias and rec.dias < config.min_dias_congelamiento:
                rec.puede_solicitar = False
                rec.mensaje_validacion = f"El mínimo de días es {config.min_dias_congelamiento}"
                continue
            
            # Verificar días máximos por solicitud
            if rec.dias and rec.dias > config.max_dias_congelamiento:
                rec.puede_solicitar = False
                rec.mensaje_validacion = f"El máximo de días por solicitud es {config.max_dias_congelamiento}"
                continue
            
            # Verificar días disponibles
            if rec.dias and (rec.dias_usados + rec.dias) > config.max_dias_acumulados:
                rec.puede_solicitar = False
                rec.mensaje_validacion = f"Excedes el máximo acumulado. Disponibles: {rec.dias_disponibles} días"
                continue
            
            # Verificar estado de pagos
            if config.requiere_pago_al_dia and rec.student_id:
                if not rec.student_id.al_dia_en_pagos:
                    rec.puede_solicitar = False
                    rec.mensaje_validacion = "Debes estar al día en tus pagos para solicitar congelamiento"
                    continue
            
            rec.puede_solicitar = True
            rec.mensaje_validacion = f"Puedes solicitar de {config.min_dias_congelamiento} a {min(config.max_dias_congelamiento, rec.dias_disponibles)} días"
    
    @api.constrains('fecha_inicio', 'fecha_fin')
    def _check_fechas(self):
        for rec in self:
            if rec.fecha_inicio and rec.fecha_fin:
                if rec.fecha_fin < rec.fecha_inicio:
                    raise ValidationError(
                        "La fecha de fin debe ser posterior o igual a la fecha de inicio"
                    )
                if (rec.fecha_fin - rec.fecha_inicio).days > 365:
                    raise ValidationError(
                        "El periodo de congelamiento no puede exceder 365 días"
                    )
    
    def action_submit(self):
        """Envía la solicitud y crea un periodo de congelamiento en estado borrador."""
        self.ensure_one()
        
        # Validar que puede solicitar
        if not self.puede_solicitar:
            raise ValidationError(self.mensaje_validacion or "No puedes solicitar congelamiento")
        
        # Crear periodo de congelamiento
        FreezePeriod = self.env['benglish.student.freeze.period'].sudo()
        
        # Preparar motivo completo
        motivo_completo = f"[{self.freeze_reason_id.name}]"
        if self.motivo_detalle:
            motivo_completo += f"\n\n{self.motivo_detalle}"
        
        # Crear el periodo
        freeze_period = FreezePeriod.create({
            'student_id': self.student_id.id,
            'enrollment_id': self.enrollment_id.id,
            'fecha_inicio': self.fecha_inicio,
            'fecha_fin': self.fecha_fin,
            'freeze_reason_id': self.freeze_reason_id.id,
            'motivo_detalle': self.motivo_detalle,
            'estado': 'pendiente',  # Crear directamente en pendiente para aprobación
            'es_especial': False,
            'visible_portal': True,
        })
        
        # Adjuntar documentos si hay
        if self.documento_soporte_ids:
            for attachment in self.documento_soporte_ids:
                attachment.sudo().write({
                    'res_model': 'benglish.student.freeze.period',
                    'res_id': freeze_period.id,
                })
        
        # Actualizar estado y vincular
        self.write({
            'state': 'sent',
            'freeze_period_id': freeze_period.id,
        })
        
        # Enviar mensaje de confirmación
        freeze_period.message_post(
            body=f"""
            <strong>Solicitud recibida desde el Portal del Estudiante</strong><br/>
            <ul>
                <li>Estudiante: {self.student_id.name}</li>
                <li>Días solicitados: {self.dias}</li>
                <li>Periodo: {self.fecha_inicio} - {self.fecha_fin}</li>
                <li>Motivo: {self.freeze_reason_id.name}</li>
            </ul>
            """
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '¡Solicitud Enviada!',
                'message': f'Tu solicitud de congelamiento por {self.dias} días ha sido enviada para aprobación.',
                'type': 'success',
                'sticky': False,
            }
        }


class PortalStudentWeeklyPlanLine(models.Model):
    _name = "portal.student.weekly.plan.line"
    _description = "Línea de plan semanal de portal"
    _order = "start_datetime asc, id asc"

    plan_id = fields.Many2one(
        comodel_name="portal.student.weekly.plan",
        string="Plan",
        required=True,
        ondelete="cascade",
    )
    session_id = fields.Many2one(
        comodel_name="benglish.academic.session",
        string="Sesión",
        required=True,
        ondelete="cascade",
    )
    subject_id = fields.Many2one(
        comodel_name="benglish.subject", related="session_id.subject_id", store=True
    )
    effective_subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        compute="_compute_effective_subject",
        store=True,
        help="Asignatura efectiva homologada para el estudiante.",
    )
    student_alias = fields.Char(
        related="session_id.student_alias",
        store=True,
        help="Alias visible para el estudiante.",
    )
    start_datetime = fields.Datetime(related="session_id.datetime_start", store=True)
    end_datetime = fields.Datetime(related="session_id.datetime_end", store=True)
    date = fields.Date(related="session_id.date", store=True)
    delivery_mode = fields.Selection(related="session_id.delivery_mode", store=True)
    meeting_link = fields.Char(related="session_id.meeting_link", store=True)
    campus_id = fields.Many2one(
        comodel_name="benglish.campus", related="session_id.campus_id", store=True
    )
    prerequisites_ok = fields.Boolean(compute="_compute_prerequisites_flag")
    missing_prerequisites = fields.Char(compute="_compute_prerequisites_flag")

    _sql_constraints = [
        (
            "unique_session_per_plan",
            "unique(plan_id, session_id)",
            "La clase ya está en tu horario semanal.",
        )
    ]

    @api.depends(
        "session_id",
        "session_id.subject_id",
        "session_id.template_id",
        "session_id.audience_unit_from",
        "session_id.audience_unit_to",
        "plan_id.student_id",
    )
    def _compute_effective_subject(self):
        Enrollment = self.env["benglish.session.enrollment"].sudo()
        for line in self:
            subject = False
            student = line.plan_id.student_id if line.plan_id else False
            session = line.session_id
            if student and session:
                enrollment = Enrollment.search(
                    [
                        ("session_id", "=", session.id),
                        ("student_id", "=", student.id),
                    ],
                    limit=1,
                )
                if enrollment and enrollment.effective_subject_id:
                    subject = enrollment.effective_subject_id
                elif hasattr(session, "resolve_effective_subject"):
                    subject = session.resolve_effective_subject(
                        student,
                        check_completed=False,
                        raise_on_error=False,
                        check_prereq=False,
                    ) or session.subject_id
                else:
                    subject = session.subject_id
            line.effective_subject_id = subject.id if subject else False

    def _get_effective_subject(
        self,
        session=None,
        student=None,
        check_completed=True,
        check_prereq=True,
        raise_on_error=False,
        prefer_enrollment=True,
    ):
        line = self[:1] if self else False
        session = session or (line.session_id if line else False)
        if not session:
            return False
        if not student and line and line.plan_id:
            student = line.plan_id.student_id
        
        # ═══════════════════════════════════════════════════════════════════════
        # CORRECCIÓN: NO usar enrollment cacheado si check_completed=True
        # ═══════════════════════════════════════════════════════════════════════
        # Si check_completed=True, significa que estamos validando para agendar
        # En ese caso, NO podemos usar el effective_subject_id cacheado porque
        # el estudiante puede haber completado asignaturas desde la última vez
        # 
        # Ejemplo: Estudiante intentó agendar B-check cuando estaba en Unit 7
        # → Se guardó "B-check Unit 7" en enrollment.effective_subject_id
        # Luego completó B-check Unit 7
        # → Al intentar agendar de nuevo, necesita recalcular (debería dar Unit 8)
        # ═══════════════════════════════════════════════════════════════════════
        if prefer_enrollment and student and not check_completed:
            Enrollment = self.env["benglish.session.enrollment"].sudo()
            enrollment = Enrollment.search(
                [
                    ("session_id", "=", session.id),
                    ("student_id", "=", student.id),
                ],
                limit=1,
            )
            if enrollment and enrollment.effective_subject_id:
                return enrollment.effective_subject_id
        
        if student and hasattr(session, "resolve_effective_subject"):
            return session.resolve_effective_subject(
                student,
                check_completed=check_completed,
                raise_on_error=raise_on_error,
                check_prereq=check_prereq,
            ) or session.subject_id
        return session.subject_id

    @api.constrains('session_id', 'plan_id')
    def _check_subject_not_completed(self):
        """
        Validación: No permitir programar una clase si el estudiante ya completó esa asignatura.
        Para BChecks en pareja: Validar que haya completado todas las skills de la unidad anterior.
        """
        for line in self:
            if not line.session_id or not line.plan_id or not line.plan_id.student_id:
                continue
            
            student = line.plan_id.student_id
            session = line.session_id
            
            # Intentar resolver el effective_subject forzando recálculo
            try:
                subject = line._get_effective_subject(
                    check_completed=True,  # CRÍTICO: Forzar recálculo para evitar usar caché stale
                    check_prereq=False,
                )
            except UserError as e:
                # Si falla la resolución (ej: debe completar skills), capturar el error y re-lanzarlo
                message = getattr(e, "name", None) or (e.args[0] if e.args else str(e))
                raise ValidationError(message)
            
            if not subject:
                continue
            
            # ═══════════════════════════════════════════════════════════════════════
            # VALIDACIÓN DE DUPLICADOS
            # ═══════════════════════════════════════════════════════════════════════
            # IMPORTANTE: Cada B-check de cada unidad tiene su propio subject_id
            # - B-check Unit 7 (ID: 123) ≠ B-check Unit 8 (ID: 124)
            # - Si ambos comparten el mismo ID, es error de configuración
            # 
            # Esta validación es CORRECTA: busca por subject_id exacto
            # Si falla, significa que resolve_effective_subject devolvió el subject incorrecto
            # ═══════════════════════════════════════════════════════════════════════
            History = self.env['benglish.academic.history'].sudo()
            has_history = History.search_count([
                ('student_id', '=', student.id),
                ('subject_id', '=', subject.id),  # Busca el subject_id EXACTO
                ('attendance_status', 'in', ['attended', 'absent'])
            ])
            
            if has_history > 0:
                unit_info = f" (Unit {subject.unit_number})" if subject.unit_number else ""
                raise ValidationError(
                    _("❌ No puedes programar esta clase.\n\n"
                      "Ya tienes la asignatura '%(subject)s%(unit)s' en tu historial académico.\n\n"
                      "Un estudiante no puede programar la misma clase dos veces. "
                      "Esta clase no debería aparecer en tu lista de clases disponibles.") % {
                        'subject': subject.alias or subject.name,
                        'unit': unit_info
                    }
                )

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

    def _format_session_label(self, session):
        if not session:
            return ""
        subject = session.subject_id
        label = session.student_alias or (
            subject.alias if subject and subject.alias else (subject.name if subject else _("Clase"))
        )
        date_label = ""
        if session.date:
            date_label = fields.Date.to_string(session.date)
        elif session.datetime_start:
            date_value = fields.Datetime.to_datetime(session.datetime_start).date()
            date_label = fields.Date.to_string(date_value)
        time_label = ""
        if session.time_start is not False:
            hours = int(session.time_start)
            minutes = int(round((session.time_start % 1) * 60))
            if minutes >= 60:
                hours += 1
                minutes = 0
            time_label = f"{hours:02d}:{minutes:02d}"
        elif session.datetime_start:
            time_label = fields.Datetime.to_string(session.datetime_start)[11:16]
        parts = [p for p in [label, date_label, time_label] if p]
        return " | ".join(parts)

    def _get_class_booking_policy(self, company_id=None):
        """Configuración centralizada en Benglish Academic para reglas de portal."""
        return self.env["benglish.academic.settings"].sudo().get_class_booking_policy(company_id=company_id)

    def _get_policy_timezone(self, plan=None, student=None):
        tz = None
        if student and student.user_id and student.user_id.tz:
            tz = student.user_id.tz
        elif plan and plan.student_id and plan.student_id.user_id and plan.student_id.user_id.tz:
            tz = plan.student_id.user_id.tz
        elif self and self.plan_id and self.plan_id.student_id and self.plan_id.student_id.user_id and self.plan_id.student_id.user_id.tz:
            tz = self.plan_id.student_id.user_id.tz
        return tz or self.env.user.tz

    def _evaluate_session_for_plan(self, plan, session, student=None, ignore_line=None, raise_on_error=False):
        """
        Valida si se puede programar la sesión en el plan semanal.

        ACTUALIZACIÓN CRÍTICA:
        - Rechaza sesiones en estado 'done' (dictadas)
        - Rechaza sesiones en estado 'cancelled' (canceladas)
        - Solo permite programar sesiones en estado 'active' o 'with_enrollment'

        Devuelve un dict con:
        {
            ok: bool,
            blocked_reason: str,
            errors: list[{code, message}],
            prerequisites_ok: bool,
            missing_prerequisites: list,
            prerequisite_subjects: list[int],
            oral_test: dict,
        }
        """
        subject = False
        result = {
            "ok": True,
            "blocked_reason": "",
            "errors": [],
            "prerequisites_ok": True,
            "missing_prerequisites": [],
            "prerequisite_subjects": [],
            "oral_test": {},
        }

        def add_error(code, message):
            result["ok"] = False
            if not result["blocked_reason"]:
                result["blocked_reason"] = message
            result["errors"].append({"code": code, "message": message})

        # Datos requeridos
        if not plan or not session:
            add_error("missing_data", _("Falta información de plan o sesión."))
            return result

        policy = self._get_class_booking_policy()
        minutos_agendar = max(0, int(policy.get("minutos_anticipacion_agendar", 0) or 0))

        # VALIDACIÓN CRÍTICA: Estado de la sesión
        if session.state == "done":
            add_error("session_finished", _("Esta clase ya fue dictada y no puede ser programada."))
        if session.state == "cancelled":
            add_error("session_cancelled", _("No se puede programar una clase cancelada."))
        if session.state not in ["active", "with_enrollment"]:
            add_error("session_invalid_state", _("Solo se pueden programar clases activas."))

        student = student or plan.student_id
        try:
            subject = self._get_effective_subject(
                session,
                student=student,
                check_completed=True,
                check_prereq=False,
                raise_on_error=True,
            )
        except UserError as exc:
            message = getattr(exc, "name", None) or (exc.args[0] if exc.args else str(exc))
            add_error("no_effective_subject", message)
            return result
        if not subject:
            subject = session.subject_id
        if subject:
            result["prerequisite_subjects"] = subject.prerequisite_ids.ids
        
        # VALIDACIÓN: Verificar si el estudiante ya tiene esta asignatura en su historial
        History = self.env['benglish.academic.history'].sudo()
        has_history = History.search_count([
            ('student_id', '=', plan.student_id.id),
            ('subject_id', '=', subject.id if subject else False),
            ('attendance_status', 'in', ['attended', 'absent'])
        ])
        if has_history > 0:
            add_error("already_completed", 
                     _("Ya tienes esta clase en tu historial académico. No puedes programar la misma clase dos veces."))
        
        # Validaciones existentes
        if not session.is_published:
            add_error("session_not_published", _("Solo se pueden programar clases publicadas."))
        if not self._check_week_range(plan, session):
            add_error("out_of_range", _("La clase no pertenece a la semana seleccionada."))
        if not self._check_booking_window(session, minutos_agendar, plan=plan, student=student):
            add_error(
                "booking_window",
                _("No puedes programar esta clase con menos de %s minutos de anticipación.")
                % minutos_agendar,
            )

        # Matrícula / prerrequisitos
        if not self._validate_enrollment(plan, session):
            subject_name = (
                session.student_alias
                or (subject.alias if subject and subject.alias else False)
                or (subject.name if subject else "esta asignatura")
            )
            add_error("enrollment_missing", _("No tienes matrícula activa en '{}'.".format(subject_name)))

        # VALIDACIÓN CRÍTICA: Oral Test pendiente bloquea acceso a siguientes unidades
        # Si el estudiante completó unidades 1-4, DEBE hacer Oral Test Unit 4 antes de Unit 5+
        is_oral_test = (
            (subject and subject.subject_category == 'oral_test')
            or (subject and any(keyword in (subject.name or '').lower()
                               for keyword in ['oral test', 'oral_test', 'prueba oral']))
        )
        
        # Solo validar para asignaturas que NO sean Oral Test
        if not is_oral_test and subject and hasattr(subject, 'unit_number') and subject.unit_number:
            student = plan.student_id.sudo()
            current_subject_unit = subject.unit_number
            
            # Determinar qué Oral Tests debería haber completado según la unidad de la clase
            # Bloques: (1-4), (5-8), (9-12), (13-16), (17-20), (21-24)
            required_oral_tests = []
            if current_subject_unit > 4:
                required_oral_tests.append(4)  # Oral Test Unit 4
            if current_subject_unit > 8:
                required_oral_tests.append(8)  # Oral Test Unit 8
            if current_subject_unit > 12:
                required_oral_tests.append(12)  # Oral Test Unit 12
            if current_subject_unit > 16:
                required_oral_tests.append(16)  # Oral Test Unit 16
            if current_subject_unit > 20:
                required_oral_tests.append(20)  # Oral Test Unit 20
            
            # Verificar si falta algún Oral Test obligatorio
            History = self.env['benglish.academic.history'].sudo()
            student_program = subject.program_id  # Programa de la asignatura que intenta programar
            
            for oral_unit in required_oral_tests:
                # Verificar si el estudiante tiene CUALQUIER Oral Test del programa con unit_block_end = oral_unit en su historial
                # Buscar directamente en el historial académico del portal
                has_oral_history = History.search_count([
                    ('student_id', '=', student.id),
                    ('subject_id.subject_category', '=', 'oral_test'),
                    ('subject_id.unit_block_end', '=', oral_unit),
                    ('subject_id.program_id', '=', student_program.id),  # Mismo programa
                    ('attendance_status', 'in', ['attended', 'absent'])
                ]) > 0
                
                if not has_oral_history:
                    # Buscar el Oral Test del programa para mostrar en el mensaje
                    OralTest = self.env['benglish.subject'].sudo()
                    oral_subject = OralTest.search([
                        ('subject_category', '=', 'oral_test'),
                        ('unit_block_end', '=', oral_unit),
                        ('program_id', '=', student_program.id)
                    ], limit=1)
                    
                    oral_test_name = oral_subject.name if oral_subject else f"Oral Test Unit {oral_unit}"
                    
                    # Bloquear el agendamiento
                    add_error(
                        "oral_test_pending",
                        _("🎤 ORAL TEST PENDIENTE - Acceso Bloqueado\n\n"
                          "No puedes programar clases de unidades superiores sin completar el Oral Test del bloque anterior.\n\n"
                          "📊 SITUACIÓN:\n"
                          "• Quieres programar: {} (Unidad {})\n"
                          "• Oral Test pendiente: {} (Unidad {})\n\n"
                          "📚 ¿POR QUÉ ES OBLIGATORIO?\n"
                          "Los Oral Tests evalúan tu dominio completo del bloque de unidades (1-4, 5-8, etc). "
                          "Debes demostrar que dominas el contenido anterior antes de avanzar a nuevas unidades.\n\n"
                          "✅ PRÓXIMOS PASOS:\n"
                          "1. Programa y completa tu Oral Test Unit {}\n"
                          "2. Una vez aprobado, podrás acceder a unidades superiores\n"
                         "3. Consulta con tu coordinador si tienes dudas sobre tu progreso"
                         ).format(
                            session.student_alias or subject.alias or subject.name,
                            current_subject_unit,
                            oral_test_name,
                            oral_unit,
                            oral_unit
                         )
                    )
                    # Detener validación aquí, no continuar con otras validaciones
                    return result

        # No validar prerrequisitos para BCheck (ellos son el prerrequisito)
        is_bcheck = self._is_prerequisite_subject(subject)

        if not is_bcheck:
            # REGLA 1: Para BSkills y clases prácticas, el BCheck del mismo nivel debe estar matriculado O agendado
            # Verificar prerrequisitos de asignatura (relaciones entre subjects)
            prereq_subjects = subject.prerequisite_ids if subject else self.env["benglish.subject"]
            
            if prereq_subjects:
                student = plan.student_id
                for prereq_subject in prereq_subjects:
                    # Si el prerrequisito es BCheck, usar lógica especial
                    is_prereq_bcheck = (
                        prereq_subject.subject_category == 'bcheck'
                        or prereq_subject.subject_classification == 'prerequisite'
                        or 'bcheck' in (prereq_subject.name or '').lower()
                        or 'b check' in (prereq_subject.name or '').lower()
                    )
                    
                    if is_prereq_bcheck:
                        # LÓGICA CORRECTA PARA BCHECK:
                        # Solo requiere que esté AGENDADO en la misma semana (puede ser antes o después)
                        # NO requiere que esté completado/calificado primero
                        
                        # Verificar si está agendado en el plan semanal actual
                        has_scheduled = False
                        for line in plan.line_ids:
                            line_subject = line.effective_subject_id or line._get_effective_subject(
                                check_completed=False,
                                check_prereq=False,
                            )
                            if line_subject and line_subject.id == prereq_subject.id:
                                has_scheduled = True
                                break
                        
                        if not has_scheduled:
                            # Si no está agendado, verificar si tiene algún registro en el historial
                            # (asistió O no asistió - cualquiera cuenta)
                            History = self.env['benglish.academic.history'].sudo()
                            has_history = History.search_count([
                                ('student_id', '=', student.id),
                                ('subject_id', '=', prereq_subject.id),
                                ('attendance_status', 'in', ['attended', 'absent'])
                            ]) > 0
                            
                            # Si NO tiene historial (ni attended ni absent) Y NO está agendado → Error
                            # La inasistencia NO debe bloquear el acceso a otras asignaturas
                            if not has_history:
                                add_error("missing_prerequisites",
                                         _("⚠️ PRERREQUISITO OBLIGATORIO: BCheck\n\n"
                                           "Debes programar el BCheck ({}) en tu horario semanal para poder programar Skills.\n\n"
                                           "💡 IMPORTANTE:\n"
                                           "• Puedes programar el BCheck cualquier día de la semana (incluso después de las Skills)\n"
                                           "• Ejemplo: BCheck viernes + Skills lunes-jueves = ✅ VÁLIDO\n"
                                           "• Solo necesitas que esté en la MISMA semana\n\n"
                                           "✅ ACCIÓN REQUERIDA:\n"
                                           "Busca y programa el BCheck primero, luego podrás programar tus Skills.").format(prereq_subject.name))
                                result["prerequisites_ok"] = False
                    else:
                        # Para otros prerrequisitos: usar validación estándar (completados)
                        prereq_check = subject.check_prerequisites_completed(student) if subject else {}
                        if not prereq_check.get("completed"):
                            result["prerequisites_ok"] = prereq_check.get("completed")
                            result["missing_prerequisites"] = prereq_check.get("missing", [])
                            add_error("missing_prerequisites", prereq_check.get("message") or _("No cumples prerrequisitos."))
                            break

        # Validar solapes de horario antes de crear la línea
        if plan and session and session.datetime_start and session.datetime_end:
            ignore_id = ignore_line.id if ignore_line else False
            overlaps = plan.line_ids.filtered(
                lambda l: l.id != ignore_id
                and l.start_datetime
                and l.end_datetime
                and l.start_datetime < session.datetime_end
                and l.end_datetime > session.datetime_start
            )
            if overlaps:
                overlap_labels = [self._format_session_label(ln.session_id) for ln in overlaps]
                overlap_labels = [label for label in overlap_labels if label]
                overlap_desc = ", ".join(overlap_labels) if overlap_labels else _("otra clase")
                add_error(
                    "time_overlap",
                    _("No puedes programar dos clases a la misma hora. Conflicto con: %s") % overlap_desc,
                )

        return result

    def _validate_enrollment(self, plan, session):
        """
        Valida que el estudiante tenga matrícula activa en la asignatura.
        EXCEPCIÓN: Los BCheck y prerrequisitos NO requieren matrícula específica.
        """
        subject = self._get_effective_subject(
            session,
            student=plan.student_id,
            check_completed=False,
            check_prereq=False,
            raise_on_error=False,
        ) or session.subject_id
        
        # Los BCheck/prerrequisitos no requieren matrícula específica
        is_bcheck = self._is_prerequisite_subject(subject)
        
        _logger = logging.getLogger(__name__)
        _logger.info(f"[ENROLLMENT DEBUG] Validating session {session.id} - {self._format_session_label(session)}")
        _logger.info(f"[ENROLLMENT DEBUG] is_bcheck: {is_bcheck}")
        _logger.info(f"[ENROLLMENT DEBUG] is_prerequisite_subject: {is_bcheck}")
        _logger.info(f"[ENROLLMENT DEBUG] subject_category: {subject.subject_category if subject else 'N/A'}")
        _logger.info(f"[ENROLLMENT DEBUG] subject_classification: {subject.subject_classification if subject else 'N/A'}")
        
        # Para BCheck: SIEMPRE permitir (no requieren matrícula)
        if is_bcheck:
            _logger.info(f"[ENROLLMENT DEBUG] BCheck detected - bypassing enrollment check")
            return True
        
        # Para otras asignaturas: requiere matrícula específica
        Enrollment = self.env["benglish.enrollment"].sudo()
        domain = [
            ("student_id", "=", plan.student_id.id),
            ("subject_id", "=", subject.id if subject else False),
            ("state", "in", ["active", "enrolled", "in_progress"]),
        ]
        enrollment_count = Enrollment.search_count(domain)
        _logger.info(f"[ENROLLMENT DEBUG] Searching enrollments with domain: {domain}")
        _logger.info(f"[ENROLLMENT DEBUG] Found {enrollment_count} active enrollments")
        
        if enrollment_count > 0:
            _logger.info(f"[ENROLLMENT DEBUG] Enrollment found - validation passed")
            return True
            
        # Fallback: permitir si la asignatura pertenece al mismo plan del estudiante
        student_plan = plan.student_id.plan_id
        subject_plans = subject.plan_ids if subject else self.env["benglish.plan"]
        _logger.info(f"[ENROLLMENT DEBUG] Checking plan fallback - student_plan: {student_plan.id if student_plan else None}, subject_plans: {subject_plans.ids if subject_plans else []}")

        if student_plan and subject_plans and student_plan in subject_plans:
            _logger.info(f"[ENROLLMENT DEBUG] Plan match found - validation passed")
            return True
        
        _logger.info(f"[ENROLLMENT DEBUG] No enrollment or plan match - validation FAILED")
        return False

    def _check_week_range(self, plan, session):
        if plan.week_start and session.date:
            if session.date < plan.week_start:
                return False
            if plan.week_end and session.date > plan.week_end:
                return False
        return True

    def _check_booking_window(self, session, minutos_anticipacion, plan=None, student=None):
        """Valida que falten al menos N minutos para iniciar."""
        if not session or not session.datetime_start:
            return True
        tz = self._get_policy_timezone(plan=plan, student=student)
        ctx_self = self.with_context(tz=tz) if tz else self
        now_local = fields.Datetime.context_timestamp(ctx_self, fields.Datetime.now())
        start_local = fields.Datetime.context_timestamp(
            ctx_self,
            fields.Datetime.to_datetime(session.datetime_start),
        )
        return (start_local - now_local) >= timedelta(minutes=minutos_anticipacion)

    @api.constrains("session_id", "plan_id")
    def _check_session_constraints(self):
        for line in self:
            plan = line.plan_id
            session = line.session_id
            if not plan or not session:
                continue
            policy = line._get_class_booking_policy()
            minutos_agendar = max(0, int(policy.get("minutos_anticipacion_agendar", 0) or 0))

            try:
                subject = line.effective_subject_id or line._get_effective_subject(
                    session,
                    student=plan.student_id,
                    check_completed=False,
                    check_prereq=False,
                    raise_on_error=True,
                )
            except UserError as exc:
                message = getattr(exc, "name", None) or (exc.args[0] if exc.args else str(exc))
                raise ValidationError(message)
            if not subject:
                subject = session.subject_id

            if session.state == "cancelled":
                raise ValidationError(_("No se puede programar una clase cancelada."))
            if not session.is_published:
                raise ValidationError(_("Solo se pueden programar clases publicadas."))
            if not self._check_week_range(plan, session):
                raise ValidationError(_("La clase no pertenece a la semana seleccionada."))
            if not self._check_booking_window(session, minutos_agendar, plan=plan):
                raise ValidationError(
                    _("No puedes programar esta clase con menos de %s minutos de anticipación.")
                    % minutos_agendar
                )
            if not self._validate_enrollment(plan, session):
                subject_name = (
                    session.student_alias
                    or (subject.alias if subject and subject.alias else False)
                    or (subject.name if subject else "esta asignatura")
                )
                raise ValidationError(
                    _("⚠️ NO TIENES MATRÍCULA ACTIVA\n\n"
                      "No puedes programar clases de '{}' porque no tienes una matrícula activa "
                      "en esta asignatura.\n\n"
                      "📚 SOLUCIÓN:\n"
                      "Verifica que tengas una matrícula activa (estado: Matriculado o En Progreso) "
                      "para esta asignatura. Si crees que es un error, contacta con administración.".format(subject_name))
                )

            # NO validar prerrequisitos si es un BCheck (ellos SON prerrequisitos)
            is_bcheck = self._is_prerequisite_subject(subject)
            
            # Validar prerrequisitos de asignatura
            if not is_bcheck:
                prereq_subjects = subject.prerequisite_ids if subject else self.env["benglish.subject"]
                student = plan.student_id
                
                if prereq_subjects:
                    for prereq_subject in prereq_subjects:
                        # Si el prerrequisito es BCheck, validar que esté matriculado Y agendado
                        is_prereq_bcheck = (
                            prereq_subject.subject_category == 'bcheck'
                            or prereq_subject.subject_classification == 'prerequisite'
                            or 'bcheck' in (prereq_subject.name or '').lower()
                            or 'b check' in (prereq_subject.name or '').lower()
                        )
                        
                        if is_prereq_bcheck:
                            # Para BCheck: DEBE estar en historial (asistió o no asistió)
                            # Verificar si tiene este prerequisito en su historial
                            History = self.env['benglish.academic.history'].sudo()
                            has_bcheck_history = History.search_count([
                                ('student_id', '=', student.id),
                                ('subject_id', '=', prereq_subject.id),
                                ('attendance_status', 'in', ['attended', 'absent'])
                            ]) > 0
                            
                            if has_bcheck_history:
                                # Si ya tiene el BCheck en historial, permitir programar
                                continue
                            
                            # Si no lo ha completado, verificar si está agendado en esta semana
                            has_scheduled = False
                            for line_item in plan.line_ids:
                                if line_item.id == line.id:
                                    continue
                                line_subject = line_item.effective_subject_id or line_item._get_effective_subject(
                                    check_completed=False,
                                    check_prereq=False,
                                )
                                if line_subject and line_subject.id == prereq_subject.id:
                                    has_scheduled = True
                                    break
                            
                            if not has_scheduled:
                                raise ValidationError(
                                    _("⚠️ PRERREQUISITO OBLIGATORIO\n\n"
                                      "Debes programar primero '{}' antes de poder programar esta clase.\n\n"
                                      "Este B-check es obligatorio y debe estar en tu horario semanal antes de las clases prácticas.").format(prereq_subject.name)
                                )
                        else:
                            # Para otros prerrequisitos normales: validar que estén completados
                            prereq_check = subject.check_prerequisites_completed(student) if subject else {}
                            if not prereq_check.get("completed"):
                                raise ValidationError(prereq_check.get("message") or _("No cumples prerrequisitos."))

            # T-PE-BCHK-01: Validación de máximo UN Bcheck por semana
            if is_bcheck:
                # Verificar si ya existe otro Bcheck en esta semana
                existing_bcheck = self.env["portal.student.weekly.plan.line"]
                for line_item in plan.line_ids:
                    if line_item.id == line.id:
                        continue
                    line_subject = line_item.effective_subject_id or line_item._get_effective_subject(
                        check_completed=False,
                        check_prereq=False,
                    )
                    if (
                        line_subject
                        and self._is_prerequisite_subject(line_subject)
                        and line_item.date >= plan.week_start
                        and line_item.date <= plan.week_end
                    ):
                        existing_bcheck |= line_item
                if existing_bcheck:
                    existing_label = self._format_session_label(existing_bcheck[0].session_id)
                    raise ValidationError(
                        _("⚠️ SOLO PUEDES PROGRAMAR UN (1) BCHECK POR SEMANA\n\n"
                          "Ya tienes un BCheck programado en esta semana:\n"
                          "• %s\n\n"
                          "La metodología del curso requiere máximo un BCheck por semana calendario.\n"
                          "Si necesitas cambiar tu BCheck, primero cancela el actual y luego programa el nuevo.")
                        % existing_label
                    )
            
            # T-PE-BCHK-02: Validar prerrequisito BCheck obligatorio antes de clases prácticas
            # SOLO APLICA PARA BSKILLS Y CONVERSATION CLUB (clases prácticas)
            # NO APLICA para clases regulares ni otros tipos
            if not is_bcheck:
                # Verificar si esta sesión es de tipo BSkill o Conversation Club
                # Identificar si es clase práctica (BSkill, Conversation, etc.)
                is_practical_class = (
                    (subject and subject.subject_category in ['bskills', 'conversation_club'])
                    or (subject and any(keyword in (subject.name or '').lower() 
                                       for keyword in ['bskill', 'b skill', 'bskills', 'conversation club']))
                )
                
                # SOLO validar BCheck para clases prácticas
                if is_practical_class:
                    # Verificar que exista al menos un BCheck agendado O completado
                    existing_prerequisite = False
                    for line_item in plan.line_ids:
                        if line_item.id == line.id:
                            continue
                        line_subject = line_item.effective_subject_id or line_item._get_effective_subject(
                            check_completed=False,
                            check_prereq=False,
                        )
                        if line_subject and self._is_prerequisite_subject(line_subject):
                            existing_prerequisite = True
                            break
                    
                    # Si no está agendado, verificar si tiene historial de BCheck (asistió o no asistió)
                    if not existing_prerequisite:
                        History = self.env['benglish.academic.history'].sudo()
                        # Buscar cualquier BCheck en historial (attended o absent)
                        has_bcheck_history = History.search_count([
                            ('student_id', '=', student.id),
                            ('attendance_status', 'in', ['attended', 'absent']),
                            ('subject_id.subject_category', '=', 'bcheck')
                        ])
                        
                        if has_bcheck_history == 0:
                            raise ValidationError(
                                _("⚠️ PRERREQUISITO OBLIGATORIO: Debes programar primero el BCHECK\n\n"
                                  "Antes de poder programar clases prácticas (BSkills, Conversation Club), "
                                  "DEBES tener al menos un BCheck programado en tu horario semanal.\n\n"
                                  "📚 ¿Por qué?\n"
                                  "El BCheck es una evaluación diagnóstica obligatoria que debe realizarse al inicio "
                                  "de cada semana. Solo después de completar tu BCheck podrás acceder a las "
                                  "clases prácticas correspondientes.\n\n"
                                  "✅ ACCIÓN REQUERIDA:\n"
                              "1. Busca la clase marcada con ⚡ PRERREQUISITO en la lista de clases disponibles\n"
                              "2. Agrégala primero a tu horario semanal\n"
                              "3. Luego podrás programar tus clases prácticas (BSkills, Conversation Club)")
                        )
            
            # T-PE-ORAL-01: Validar habilitación condicional de Oral Test por avance en unidades
            # Las clases de Oral Test solo se habilitan cuando el estudiante ha completado
            # el bloque de unidades correspondiente (unidades 4, 8, 12, 16, 20, 24)
            is_oral_test = (
                (subject and subject.subject_category == 'oral_test')
                or (subject and any(keyword in (subject.name or '').lower() 
                                   for keyword in ['oral test', 'oral_test', 'prueba oral']))
            )
            if is_oral_test:
                # Obtener la unidad actual del estudiante desde su perfil académico
                student = plan.student_id.sudo()
                
                # La unidad actual se determina por la matrícula activa más reciente
                active_enrollments = student.enrollment_ids.filtered(
                    lambda e: e.state in ['active', 'enrolled', 'in_progress']
                ).sorted('enrollment_date', reverse=True)
                
                if not active_enrollments:
                    raise ValidationError(
                        _("NO PUEDES PROGRAMAR ORAL TEST\n\n"
                          "No se encontró una matrícula activa para determinar tu avance académico.\n\n"
                          "Por favor contacta a tu coordinador académico.")
                    )
                
                # CORRECCIÓN CRÍTICA: Calcular el progreso REAL del estudiante basado en historial académico
                # El portal lee DIRECTAMENTE del historial académico para obtener el progreso real
                
                # Buscar todas las asignaturas en el historial académico (asistidas o no)
                History = self.env['benglish.academic.history'].sudo()
                completed_subjects = History.search([
                    ('student_id', '=', student.id),
                    ('attendance_status', 'in', ['attended', 'absent'])
                ])
                
                # Calcular la unidad máxima completada basándose en las asignaturas del historial
                student_max_unit = 0
                if completed_subjects:
                    # Obtener todos los números de unidad de las asignaturas completadas
                    completed_units = []
                    for history in completed_subjects:
                        if history.subject_id and hasattr(history.subject_id, 'unit_number') and history.subject_id.unit_number:
                            completed_units.append(history.subject_id.unit_number)
                    
                    # La unidad máxima es la más alta completada
                    if completed_units:
                        student_max_unit = max(completed_units)
                
                # Si no hay progreso en historial, usar el nivel de la matrícula como fallback
                if student_max_unit == 0:
                    current_level = active_enrollments[0].current_level_id or student.current_level_id
                    if current_level:
                        student_max_unit = current_level.max_unit or 0
                
                # Obtener el nombre del nivel para el mensaje (solo para mostrar)
                current_enrollment = active_enrollments[0]
                current_level = current_enrollment.current_level_id or student.current_level_id
                level_name = current_level.name if current_level else "Desconocido"
                
                # Obtener las unidades prerequisito del Oral Test
                required_units = [4, 8, 12, 16, 20, 24]
                subject_block_end = getattr(subject, "unit_block_end", 0) or 0
                if subject_block_end:
                    required_units = [subject_block_end]
                can_take_oral = any(student_max_unit >= req_unit for req_unit in required_units)
                if not can_take_oral:
                    next_unit = min(
                        [u for u in required_units if u > student_max_unit],
                        default=required_units[0],
                    )
                    raise ValidationError(
                        _("ORAL TEST NO DISPONIBLE: Avance insuficiente\n\n"
                          "Los Oral Tests solo están disponibles al completar bloques de unidades específicos.\n\n"
                          "TU SITUACIÓN ACADÉMICA:\n"
                          "- Nivel actual: %s\n"
                          "- Unidad actual: hasta unidad %d\n"
                          "- Oral Test requiere: unidad %d completada\n\n"
                          "¿Qué son los bloques de unidades?\n"
                          "El programa está dividido en bloques de 4 unidades:\n"
                          "- Bloque 1: Unidades 1-4 (Oral Test al completar unidad 4)\n"
                          "- Bloque 2: Unidades 5-8 (Oral Test al completar unidad 8)\n"
                          "- Bloque 3: Unidades 9-12 (Oral Test al completar unidad 12)\n"
                          "- Bloque 4: Unidades 13-16 (Oral Test al completar unidad 16)\n"
                          "- Bloque 5: Unidades 17-20 (Oral Test al completar unidad 20)\n"
                          "- Bloque 6: Unidades 21-24 (Oral Test al completar unidad 24)\n\n"
                          "PRÓXIMOS PASOS:\n"
                          "1. Completa las unidades de tu bloque actual\n"
                          "2. El Oral Test se habilitará al alcanzar la unidad %d\n"
                          "3. Consulta tu progreso con tu coordinador académico si tienes dudas\n\n"
                          "El Oral Test evalúa el bloque completo y se habilita al final de cada bloque.")
                        % (
                            level_name,
                            student_max_unit,
                            next_unit,
                            next_unit,
                        )
                    )
            overlaps = plan.line_ids.filtered(
                lambda l: l.id != line.id
                and l.start_datetime
                and session.datetime_start
                and l.start_datetime < session.datetime_end
                and l.end_datetime > session.datetime_start
            )
            if overlaps:
                overlap_labels = [self._format_session_label(ln.session_id) for ln in overlaps]
                overlap_labels = [label for label in overlap_labels if label]
                raise ValidationError(
                    _("No puedes programar dos clases a la misma hora. Conflicto con: %s")
                    % ", ".join(overlap_labels)
                )

    @api.depends("plan_id.student_id", "effective_subject_id")
    def _compute_prerequisites_flag(self):
        for line in self:
            subject = line.effective_subject_id or line._get_effective_subject(
                check_completed=False,
                check_prereq=False,
            )
            if line.plan_id and subject and line.plan_id.student_id:
                result = subject.check_prerequisites_completed(line.plan_id.student_id)
                line.prerequisites_ok = result.get("completed", True)
                missing = result.get("missing_prerequisites") or self.env["benglish.subject"]
                missing_names = [m.alias or m.name for m in missing]
                line.missing_prerequisites = ", ".join([n for n in missing_names if n])
            else:
                line.prerequisites_ok = True
                line.missing_prerequisites = ""

    def to_portal_dict(self):
        self.ensure_one()
        subject = self.effective_subject_id or self._get_effective_subject(
            check_completed=False,
            check_prereq=False,
        )
        subject_label = (
            self.student_alias
            or (subject.alias if subject and subject.alias else False)
            or (subject.name if subject else "")
        )
        return {
            "id": self.id,
            "session_id": self.session_id.id,
            "subject": subject_label,
            # Campo de grupo eliminado; mantenemos sujeto y horarios
            "start": fields.Datetime.to_string(self.start_datetime) if self.start_datetime else "",
            "end": fields.Datetime.to_string(self.end_datetime) if self.end_datetime else "",
            "delivery_mode": self.delivery_mode,
            "meeting_link": self.session_id.teacher_meeting_link or self.meeting_link,
        }
    
    @api.model
    def _cron_clean_finished_sessions_from_agenda(self):
        """
        PROCESO AUTOMÁTICO (CRON JOB)
        
        Limpia automáticamente las líneas de agenda semanal que referencian
        sesiones que ya fueron dictadas o canceladas.
        
        Esto garantiza que las clases dictadas desaparezcan automáticamente
        de la agenda del estudiante, incluso si quedaron agendadas.
        
        Se ejecuta periódicamente (recomendado: cada 1 hora).
        Es IDEMPOTENTE: puede ejecutarse múltiples veces sin problemas.
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        # Buscar líneas de agenda que referencian sesiones dictadas o canceladas
        lines_to_remove = self.search([
            ("session_id.state", "in", ["done", "cancelled"])
        ])
        
        if not lines_to_remove:
            _logger.info("[CRON CLEAN AGENDA] No lines to remove")
            return
        
        _logger.info(
            f"[CRON CLEAN AGENDA] Found {len(lines_to_remove)} lines referencing "
            f"finished/cancelled sessions"
        )
        
        removed_count = 0
        error_count = 0
        
        for line in lines_to_remove:
            try:
                student_name = line.plan_id.student_id.name if line.plan_id.student_id else "Unknown"
                session_name = line.session_id.display_name if line.session_id else "Unknown"
                session_state = line.session_id.state if line.session_id else "unknown"
                
                _logger.info(
                    f"[CRON CLEAN AGENDA] Removing line {line.id}: "
                    f"Student={student_name}, Session={session_name}, State={session_state}"
                )
                
                line.unlink()
                removed_count += 1
                
            except Exception as e:
                error_count += 1
                _logger.error(
                    f"[CRON CLEAN AGENDA] Error removing line {line.id}: {str(e)}"
                )
                continue
        
        _logger.info(
            f"[CRON CLEAN AGENDA] Finished: {removed_count} removed, {error_count} errors"
        )
        
        return {
            "removed": removed_count,
            "errors": error_count,
            "total": len(lines_to_remove)
        }
