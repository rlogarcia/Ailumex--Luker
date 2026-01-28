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
        
        HU-E8: LÓGICA POR UNIDAD (unit_number)
        Si se elimina un B-Check de Unidad N:
        - Eliminar TODAS las Skills de Unidad N agendadas (porque necesitan ese B-Check)
        
        NO eliminar:
        - B-Checks o Skills de otras unidades
        - Skills de Unidad N que ya estén COMPLETADAS (no afecta)
        """
        self.ensure_one()
        lines_to_unlink = self.env["portal.student.weekly.plan.line"]
        
        # Obtener la asignatura de la línea base
        base_subject = base_line.effective_subject_id or base_line._get_effective_subject(
            check_completed=False,
            check_prereq=False,
        )
        if not base_subject:
            return lines_to_unlink

        # ═══════════════════════════════════════════════════════════════════════════════
        # LÓGICA ESPECIAL PARA B-CHECK: Eliminar Skills de LA MISMA UNIDAD
        # ═══════════════════════════════════════════════════════════════════════════════
        if base_line._is_prerequisite_subject(base_subject):
            bcheck_unit = base_subject.unit_number or 0
            _logger = logging.getLogger(__name__)
            _logger.info(f"[CANCEL DEBUG] Cancelando B-Check Unidad {bcheck_unit}")
            
            # Solo eliminar líneas de la misma unidad
            for line in self.line_ids:
                if line.id == base_line.id:
                    continue  # No eliminar la línea base
                    
                line_subject = line.effective_subject_id or line._get_effective_subject(
                    check_completed=False,
                    check_prereq=False,
                )
                if not line_subject:
                    continue
                
                # NO eliminar otros B-Checks
                if line._is_prerequisite_subject(line_subject):
                    _logger.info(f"[CANCEL DEBUG] Preservando B-Check: {line_subject.name}")
                    continue
                
                # Eliminar Skills de LA MISMA UNIDAD
                line_unit = line_subject.unit_number or 0
                if line_unit == bcheck_unit and bcheck_unit > 0:
                    _logger.info(f"[CANCEL DEBUG] Eliminando Skill Unidad {line_unit}: {line_subject.name}")
                    lines_to_unlink |= line
                else:
                    _logger.info(f"[CANCEL DEBUG] Preservando Skill de otra unidad ({line_unit}): {line_subject.name}")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # LÓGICA PARA OTRAS DEPENDENCIAS (prerrequisitos de asignaturas)
        # ═══════════════════════════════════════════════════════════════════════════════
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
        # CORRECCIÓN CRÍTICA PARA B-CHECKS CON INASISTENCIA
        # ═══════════════════════════════════════════════════════════════════════
        # Si el estudiante tiene un B-check con 'absent' (no asistió), el sistema
        # debe permitir agendar un NUEVO B-check de la MISMA unidad, no avanzar.
        # 
        # Problema: resolve_effective_subject considera 'absent' como "completado"
        # y avanza a la siguiente unidad incorrectamente.
        # 
        # Solución: Para B-checks, verificar si hay 'absent' sin 'attended' en la
        # unidad y forzar que se resuelva a esa misma unidad.
        # ═══════════════════════════════════════════════════════════════════════
        
        # Primero obtener el subject base para saber si es B-check
        base_subject = session.subject_id
        is_bcheck = self._is_prerequisite_subject(base_subject) if base_subject else False
        
        if is_bcheck and student and check_completed:
            # Para B-checks: Verificar si hay registro con 'absent' sin 'attended'
            History = self.env['benglish.academic.history'].sudo()
            Subject = self.env['benglish.subject'].sudo()
            
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
                        _logger = logging.getLogger(__name__)
                        _logger.info(f"[BCHECK RECOVERY] Estudiante {student.id} tiene B-check Unidad {bcheck_subj.unit_number} con 'absent'. Forzando resolución a esta unidad.")
                        return bcheck_subj
                    
                    # Si NO tiene ni 'attended' ni 'absent', esta es la siguiente unidad pendiente
                    if not has_attended and not has_absent:
                        _logger = logging.getLogger(__name__)
                        _logger.info(f"[BCHECK NEXT] Estudiante {student.id} siguiente B-check pendiente: Unidad {bcheck_subj.unit_number}")
                        return bcheck_subj
        
        # ═══════════════════════════════════════════════════════════════════════
        # LÓGICA ORIGINAL: NO usar enrollment cacheado si check_completed=True
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
        if self.env.context.get("skip_portal_plan_constraints"):
            return
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
            # EXCEPCIÓN PARA B-CHECKS: Si el estudiante tiene un B-check con 'absent'
            # (no asistió), PUEDE agendar una NUEVA sesión de ese mismo B-check.
            # Esto permite "recuperar" un B-check al que no asistió.
            # ═══════════════════════════════════════════════════════════════════════
            History = self.env['benglish.academic.history'].sudo()
            is_bcheck = self._is_prerequisite_subject(subject)
            
            # Verificar si ya asistió (attended) - NO puede volver a programar
            has_attended = History.search_count([
                ('student_id', '=', student.id),
                ('subject_id', '=', subject.id),
                ('attendance_status', '=', 'attended')
            ])
            
            if has_attended > 0:
                unit_info = f" (Unit {subject.unit_number})" if subject.unit_number else ""
                raise ValidationError(
                    _("❌ No puedes programar esta clase.\n\n"
                      "Ya tienes la asignatura '%(subject)s%(unit)s' completada en tu historial académico.\n\n"
                      "Un estudiante no puede programar la misma clase dos veces. "
                      "Esta clase no debería aparecer en tu lista de clases disponibles.") % {
                        'subject': subject.alias or subject.name,
                        'unit': unit_info
                    }
                )
            
            # Para B-Checks: Si tiene 'absent', PERMITIR agendar nuevo (recuperación)
            # Para otras clases (Skills): Si tiene 'absent', NO permitir
            if not is_bcheck:
                has_absent = History.search_count([
                    ('student_id', '=', student.id),
                    ('subject_id', '=', subject.id),
                    ('attendance_status', '=', 'absent')
                ])
                
                if has_absent > 0:
                    unit_info = f" (Unit {subject.unit_number})" if subject.unit_number else ""
                    raise ValidationError(
                        _("❌ No puedes programar esta clase.\n\n"
                          "Ya tienes la asignatura '%(subject)s%(unit)s' en tu historial académico (no asististe).\n\n"
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
        # EXCEPCIÓN: Para B-Checks con 'absent', permitir agendar nuevo (recuperación)
        History = self.env['benglish.academic.history'].sudo()
        is_bcheck = self._is_prerequisite_subject(subject)
        
        # Si ya ASISTIÓ (attended) → NO puede programar de nuevo
        has_attended = History.search_count([
            ('student_id', '=', plan.student_id.id),
            ('subject_id', '=', subject.id if subject else False),
            ('attendance_status', '=', 'attended')
        ])
        if has_attended > 0:
            add_error("already_completed", 
                     _("Ya tienes esta clase completada en tu historial académico. No puedes programar la misma clase dos veces."))
        
        # Para clases que NO son B-Check: Si tiene 'absent' también bloquear
        if not is_bcheck:
            has_absent = History.search_count([
                ('student_id', '=', plan.student_id.id),
                ('subject_id', '=', subject.id if subject else False),
                ('attendance_status', '=', 'absent')
            ])
            if has_absent > 0:
                add_error("already_in_history", 
                         _("Ya tienes esta clase en tu historial académico (no asististe). No puedes programar la misma clase dos veces."))
        
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
            OralTestSubject = self.env['benglish.subject'].sudo()
            student_program = subject.program_id  # Programa de la asignatura que intenta programar
            
            for oral_unit in required_oral_tests:
                # Primero buscar los Oral Tests de este bloque
                oral_test_subjects = OralTestSubject.search([
                    ('subject_category', '=', 'oral_test'),
                    ('unit_block_end', '=', oral_unit),
                    ('program_id', '=', student_program.id)
                ])
                
                # Verificar si el estudiante tiene ALGÚN Oral Test de este bloque en historial
                has_oral_history = False
                if oral_test_subjects:
                    has_oral_history = History.search_count([
                        ('student_id', '=', student.id),
                        ('subject_id', 'in', oral_test_subjects.ids),
                        ('attendance_status', 'in', ['attended', 'absent'])
                    ]) > 0
                
                if not has_oral_history:
                    oral_test_name = oral_test_subjects[0].name if oral_test_subjects else f"Oral Test Unit {oral_unit}"
                    
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
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # VALIDACIÓN B-CHECK / SKILLS POR UNIDAD (unit_number) - CORREGIDA
        # ═══════════════════════════════════════════════════════════════════════════════
        # LÓGICA CORREGIDA:
        # - Skills de unidad N NO requieren B-Check como prerrequisito
        # - B-Check de unidad N+1 SÍ requiere que TODAS las Skills de unidad N estén completadas
        # - El B-Check es obligatorio para AVANZAR de unidad, no para ver skills
        # ═══════════════════════════════════════════════════════════════════════════════
        subject_unit = subject.unit_number if subject else 0
        student = plan.student_id.sudo()
        History = self.env['benglish.academic.history'].sudo()
        Subject = self.env['benglish.subject'].sudo()
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # VALIDACIÓN ESPECIAL PARA ORAL TESTS
        # ═══════════════════════════════════════════════════════════════════════════════
        # Oral Tests requieren que el estudiante haya ASISTIDO al B-check de la unidad
        # correspondiente (última unidad del bloque: 4, 8, 12, 16, 20, 24)
        # ═══════════════════════════════════════════════════════════════════════════════
        if is_oral_test and subject:
            # Determinar la unidad del Oral Test (usar unit_block_end o audience_unit_to)
            oral_test_unit = getattr(subject, 'unit_block_end', 0) or 0
            if not oral_test_unit and session:
                oral_test_unit = session.audience_unit_to or 0
            
            if oral_test_unit:
                # Buscar B-check de la unidad correspondiente al Oral Test
                bcheck_for_oral = Subject.search([
                    ('subject_category', '=', 'bcheck'),
                    ('unit_number', '=', oral_test_unit),
                    ('program_id', '=', subject.program_id.id)
                ], limit=1)
                
                if bcheck_for_oral:
                    # Verificar si ASISTIÓ al B-check
                    bcheck_attended = History.search_count([
                        ('student_id', '=', student.id),
                        ('subject_id', '=', bcheck_for_oral.id),
                        ('attendance_status', '=', 'attended')
                    ]) > 0
                    
                    if not bcheck_attended:
                        # Verificar si faltó para dar mensaje específico
                        bcheck_absent = History.search_count([
                            ('student_id', '=', student.id),
                            ('subject_id', '=', bcheck_for_oral.id),
                            ('attendance_status', '=', 'absent')
                        ]) > 0
                        
                        if bcheck_absent:
                            add_error("oral_test_bcheck_absent",
                                     _("⚠️ NO PUEDES AGENDAR ORAL TEST - FALTASTE AL B-CHECK\n\n"
                                       "Para presentar el Oral Test de la Unidad {unit}, debías haber ASISTIDO "
                                       "al B-Check de esa unidad, pero faltaste.\n\n"
                                       "📋 SITUACIÓN:\n"
                                       "• Oral Test que intentas agendar: Unidad {unit}\n"
                                       "• B-Check requerido: Unidad {unit} - NO ASISTISTE\n\n"
                                       "✅ SOLUCIÓN:\n"
                                       "1. Solicita que te habiliten un NUEVO B-Check de la Unidad {unit}\n"
                                       "2. Asiste al B-Check de recuperación\n"
                                       "3. Después podrás agendar el Oral Test\n\n"
                                       "💡 Contacta a tu coordinador académico para la recuperación.").format(
                                        unit=oral_test_unit))
                        else:
                            add_error("oral_test_bcheck_missing",
                                     _("⚠️ NO PUEDES AGENDAR ORAL TEST - B-CHECK PENDIENTE\n\n"
                                       "Para presentar el Oral Test de la Unidad {unit}, debes haber ASISTIDO "
                                       "al B-Check de esa unidad.\n\n"
                                       "📋 SITUACIÓN:\n"
                                       "• Oral Test que intentas agendar: Unidad {unit}\n"
                                       "• B-Check requerido: Unidad {unit} - NO COMPLETADO\n\n"
                                       "✅ PRÓXIMOS PASOS:\n"
                                       "1. Agenda el B-Check de la Unidad {unit}\n"
                                       "2. Asiste al B-Check\n"
                                       "3. Luego podrás agendar el Oral Test").format(
                                        unit=oral_test_unit))
                        result["prerequisites_ok"] = False
                        return result
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # VALIDACIÓN PARA SKILLS (NO aplica a B-checks ni Oral Tests)
        # ═══════════════════════════════════════════════════════════════════════════════
        if not is_bcheck and not is_oral_test:
            # ═══════════════════════════════════════════════════════════════════════
            # CASO 1: SKILLS - No requieren prerrequisitos de B-check de la misma unidad  
            # ═══════════════════════════════════════════════════════════════════════
            # Las skills se pueden VER y AGENDAR libremente en su unidad correspondiente
            # El B-check es obligatorio para AVANZAR de unidad, no para acceder a skills
            pass
            
            # ═══════════════════════════════════════════════════════════════════
            # PASO 2: Buscar B-Check de la MISMA UNIDAD que la skill
            # ═══════════════════════════════════════════════════════════════════
            bcheck_same_unit = Subject.search([
                ('subject_category', '=', 'bcheck'),
                ('unit_number', '=', subject_unit),
                ('program_id', '=', subject.program_id.id)
            ], limit=1)
            
            # Verificar si está COMPLETADO en historial
            # IMPORTANTE: Solo cuenta como "completado" si ASISTIÓ (attended)
            # Si faltó (absent), NO puede agendar Skills - debe agendar nuevo B-Check
            bcheck_completed = False
            bcheck_absent = False  # Para dar mensaje específico
            if bcheck_same_unit:
                bcheck_completed = History.search_count([
                    ('student_id', '=', student.id),
                    ('subject_id', '=', bcheck_same_unit.id),
                    ('attendance_status', '=', 'attended')  # Solo 'attended', NO 'absent'
                ]) > 0
                
                # Verificar si tiene 'absent' para mensaje específico
                if not bcheck_completed:
                    bcheck_absent = History.search_count([
                        ('student_id', '=', student.id),
                        ('subject_id', '=', bcheck_same_unit.id),
                        ('attendance_status', '=', 'absent')
                    ]) > 0
            
            # Verificar si está AGENDADO en esta semana
            bcheck_scheduled = False
            if not bcheck_completed:
                for line in plan.line_ids:
                    line_subject = line.effective_subject_id or line._get_effective_subject(
                        check_completed=False,
                        check_prereq=False,
                    )
                    if (line_subject and 
                        self._is_prerequisite_subject(line_subject) and
                        line_subject.unit_number == subject_unit):
                        bcheck_scheduled = True
                        break
            
            # Si NO está completado NI agendado → ERROR
            if not bcheck_completed and not bcheck_scheduled:
                # Mensaje específico si faltó al B-Check
                if bcheck_absent:
                    add_error("bcheck_absent",
                             _("⚠️ NO ASISTISTE AL B-CHECK DE UNIDAD {unit}\n\n"
                               "No puedes agendar '{skill_name}' porque faltaste al B-Check de la Unidad {unit}.\n\n"
                               "📋 SITUACIÓN:\n"
                               "• Tenías un B-Check programado pero NO asististe\n"
                               "• Sin completar el B-Check, no puedes acceder a las Skills de esta unidad\n\n"
                               "✅ SOLUCIÓN:\n"
                               "1. Solicita que te habiliten un NUEVO B-Check de la Unidad {unit}\n"
                               "2. Agenda y asiste al nuevo B-Check\n"
                               "3. Después podrás agendar las Skills de esta unidad\n\n"
                               "💡 Contacta a tu coordinador académico para que te habilite la recuperación.").format(
                                unit=subject_unit,
                                skill_name=subject.alias or subject.name))
                else:
                    add_error("missing_bcheck_same_unit",
                             _("⚠️ PRERREQUISITO: B-CHECK UNIDAD {unit}\n\n"
                               "Para agendar '{skill_name}', necesitas el B-Check de la Unidad {unit}:\n"
                               "• Completado (ya asististe) O\n"
                               "• Agendado en tu horario semanal\n\n"
                               "📚 ACCIÓN:\n"
                               "1. Agenda el B-Check de la Unidad {unit}\n"
                               "2. Luego podrás agendar las Skills").format(
                                unit=subject_unit,
                                skill_name=subject.alias or subject.name))
                result["prerequisites_ok"] = False
        
        elif is_bcheck and subject_unit and subject_unit > 1:
            # ═══════════════════════════════════════════════════════════════════════
            # CASO 2: B-CHECK - Requiere TODAS las Skills de unidad anterior COMPLETADAS
            # ═══════════════════════════════════════════════════════════════════════
            # REGLA DE NEGOCIO CORRECTA:
            # Para agendar B-check de unidad N, DEBE haber completado (asistido) 
            # TODAS las Skills de la unidad N-1 en su historial académico.
            # 
            # REGLA ESPECIAL: Si tienes skills Y bcheck de la misma unidad agendados,
            # y eliminas el bcheck, también se deben eliminar las skills (el bcheck 
            # es obligatorio para pasar de unidad).
            # 
            # Ejemplo: Para agendar B-check Unit 8, debe tener TODAS las skills de 
            # Unit 7 completadas (4 skills con attendance_status='attended')
            # ═══════════════════════════════════════════════════════════════════════
            previous_unit = subject_unit - 1
            
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(f"[BCHECK VALIDATION] Validando B-check Unit {subject_unit} - Revisando skills Unit {previous_unit}")
            
            # Buscar TODAS las Skills de la unidad anterior
            skills_previous = Subject.search([
                ('subject_category', '=', 'bskills'),
                ('unit_number', '=', previous_unit),
                ('program_id', '=', subject.program_id.id)
            ])
            
            _logger.info(f"[BCHECK VALIDATION] Skills de Unit {previous_unit} encontradas: {len(skills_previous)} - IDs: {skills_previous.ids}")
            
            if skills_previous:
                # Verificar cuántas Skills están COMPLETADAS (asistió)
                skills_completed = 0
                skills_pending = []
                
                for skill in skills_previous:
                    # Buscar en historial académico si ASISTIÓ a esta skill
                    completed = History.search([
                        ('student_id', '=', student.id),
                        ('subject_id', '=', skill.id),
                        ('attendance_status', '=', 'attended')
                    ])
                    
                    _logger.info(f"[BCHECK VALIDATION] Skill '{skill.name}' (ID: {skill.id}) - Completada: {len(completed) > 0}")
                    
                    if len(completed) > 0:
                        skills_completed += 1
                    else:
                        skills_pending.append(skill.alias or skill.name)
                
                _logger.info(f"[BCHECK VALIDATION] RESUMEN: {skills_completed}/{len(skills_previous)} skills completadas de Unit {previous_unit}")
                
                # Si NO todas las skills están completadas → ERROR
                if skills_completed < len(skills_previous):
                    missing_list = "\n".join([f"• {s}" for s in skills_pending[:5]])
                    if len(skills_pending) > 5:
                        missing_list += f"\n• ... y {len(skills_pending) - 5} más"
                    
                    _logger.info(f"[BCHECK VALIDATION] ❌ BLOQUEADO - Faltan {len(skills_pending)} skills de Unit {previous_unit}")
                    
                    add_error("incomplete_previous_skills",
                             _("⚠️ PRERREQUISITO: SKILLS DE UNIDAD {prev_unit}\n\n"
                               "Para agendar '{bcheck_name}' (Unidad {current_unit}), DEBES completar "
                               "TODAS las Skills de la Unidad {prev_unit}.\n\n"
                               "📋 SKILLS PENDIENTES ({pending}/{total}):\n{missing}\n\n"
                               "📚 FLUJO CORRECTO:\n"
                               "1. Completa todas las Skills de Unidad {prev_unit}\n"
                               "2. Luego podrás agendar el B-Check de Unidad {current_unit}\n\n"
                               "💡 REVISIÓN: Verifica tu historial académico para confirmar que asististe a todas las skills.").format(
                                prev_unit=previous_unit,
                                current_unit=subject_unit,
                                bcheck_name=subject.alias or subject.name,
                                pending=len(skills_pending),
                                total=len(skills_previous),
                                missing=missing_list))
                    result["prerequisites_ok"] = False
                else:
                    _logger.info(f"[BCHECK VALIDATION] ✅ PERMITIDO - Todas las skills de Unit {previous_unit} completadas")
            else:
                _logger.info(f"[BCHECK VALIDATION] ⚠️ No se encontraron skills para Unit {previous_unit} - permitiendo")

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
        if self.env.context.get("skip_portal_plan_constraints"):
            return
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

            # Determinar si es un BCheck (prerrequisito)
            is_bcheck = self._is_prerequisite_subject(subject)

            # ═══════════════════════════════════════════════════════════════════════════════
            # T-PE-BCHK-02: VALIDACIÓN B-CHECK / SKILLS POR UNIDAD (unit_number)
            # ═══════════════════════════════════════════════════════════════════════════════
            # LÓGICA CORREGIDA:
            # - Skills de unidad N NO requieren B-Check como prerrequisito
            #   (puedes agendar skills y bcheck de la misma unidad en cualquier orden)
            # - B-Check de unidad N+1 SÍ requiere que TODAS las Skills de unidad N estén completadas
            # - El B-Check es obligatorio solo para AVANZAR de unidad, no para ver skills
            # ═══════════════════════════════════════════════════════════════════════════════
            
            subject_unit = subject.unit_number if subject else 0
            _logger = logging.getLogger(__name__)
            
            if not is_bcheck:
                # ═══════════════════════════════════════════════════════════════════════
                # CASO 1: SKILLS - No requieren prerrequisitos de B-check de la misma unidad
                # ═══════════════════════════════════════════════════════════════════════
                # REGLA CORREGIDA: Las skills se pueden agendar libremente en su unidad.
                # El B-check es obligatorio para AVANZAR de unidad, no para ver skills.
                # ═══════════════════════════════════════════════════════════════════════
                # Skills no requieren validaciones adicionales de prerrequisitos
                pass
            
            else:
                # ═══════════════════════════════════════════════════════════════════════
                # CASO 2: B-CHECK - Requiere TODAS las Skills de unidad anterior COMPLETADAS
                # ═══════════════════════════════════════════════════════════════════════
                # REGLA DE NEGOCIO CORRECTA:
                # Para agendar B-check de unidad N, DEBE haber completado (asistido) 
                # TODAS las Skills de la unidad N-1 en su historial académico.
                #
                # Ejemplo: Para agendar B-check Unit 8, debe tener TODAS las skills de 
                # Unit 7 completadas (4 skills con attendance_status='attended')
                # ═══════════════════════════════════════════════════════════════════════
                pass  # Las skills se validan correctamente en _check_session_constraints

        # Validar solapes de horario antes de crear la línea
        if plan and session and session.datetime_start and session.datetime_end:
                    
                    student = plan.student_id
                    History = self.env['benglish.academic.history'].sudo()
                    Subject = self.env['benglish.subject'].sudo()
                    
                    # Calcular la pareja actual
                    # Parejas: (1,2), (3,4), (5,6), (7,8), etc.
                    pair_start = ((subject_unit - 1) // 2) * 2 + 1  # 1,3,5,7,9...
                    previous_unit = subject_unit - 1
                    
                    _logger.info(f"[BCHECK DEBUG] Unidad {subject_unit}, Inicio de pareja: {pair_start}, Unidad anterior: {previous_unit}")
                    
                    # ═══════════════════════════════════════════════════════════════════
                    # VERIFICACIÓN: Skills de la unidad anterior COMPLETADAS
                    # ═══════════════════════════════════════════════════════════════════
                    # Para cualquier B-Check > 1, debe tener las Skills de la unidad anterior
                    
                    # Buscar las Skills de la unidad anterior
                    skills_previous_unit = Subject.search([
                        ('subject_category', '=', 'bskills'),
                        ('unit_number', '=', previous_unit),
                        ('program_id', '=', subject.program_id.id)
                    ])
                    
                    _logger.info(f"[BCHECK DEBUG] Skills de Unidad {previous_unit} encontradas: {len(skills_previous_unit)}")
                    
                    if skills_previous_unit:
                        # Verificar cuántas Skills de la unidad anterior están completadas
                        skills_completed = 0
                        skills_not_completed = []
                        
                        _logger.info(f"[BCHECK DEBUG] Estudiante ID: {student.id} - Programa ID: {subject.program_id.id}")
                        
                        for skill in skills_previous_unit:
                            # Buscar historial específico para esta skill
                            history_records = History.search([
                                ('student_id', '=', student.id),
                                ('subject_id', '=', skill.id),
                                ('attendance_status', '=', 'attended')
                            ])
                            
                            skill_completed = len(history_records) > 0
                            _logger.info(f"[BCHECK DEBUG] Skill '{skill.name}' (ID:{skill.id}, Unit:{skill.unit_number}) - Completada: {skill_completed}")
                            
                            if history_records:
                                _logger.info(f"[BCHECK DEBUG] Historia encontrada: IDs {[h.id for h in history_records]}")
                            
                            if skill_completed:
                                skills_completed += 1
                            else:
                                skills_not_completed.append(skill.alias or skill.name)
                        
                        _logger.info(f"[BCHECK DEBUG] TOTAL Skills Unidad {previous_unit}: {skills_completed}/{len(skills_previous_unit)} completadas")
                        
                        # Si NO todas las skills están completadas → ERROR
                        if skills_completed < len(skills_previous_unit):
                            missing_list = "\n".join([f"• {s}" for s in skills_not_completed[:5]])
                            if len(skills_not_completed) > 5:
                                missing_list += f"\n• ... y {len(skills_not_completed) - 5} más"
                            
                            _logger.info(f"[BCHECK DEBUG] ❌ BLOQUEADO - Faltan {len(skills_not_completed)} Skills de Unidad {previous_unit}")
                            _logger.info(f"[BCHECK DEBUG] Skills faltantes: {skills_not_completed}")
                            
                            raise ValidationError(
                                _("⚠️ PRERREQUISITO: SKILLS DE UNIDAD {prev_unit}\n\n"
                                  "Para agendar '{bcheck_name}' (Unidad {current_unit}), DEBES completar "
                                  "TODAS las Skills de la Unidad {prev_unit}.\n\n"
                                  "📋 SKILLS PENDIENTES ({pending}/{total}):\n{missing_list}\n\n"
                                  "📚 FLUJO CORRECTO:\n"
                                  "1. Completa todas las Skills de Unidad {prev_unit}\n"
                                  "2. Luego podrás agendar el B-Check de Unidad {current_unit}\n\n"
                                  "🔍 DEBUG: Revisa tu historial académico para verificar que asististe a todas las skills.").format(
                                    prev_unit=previous_unit,
                                    current_unit=subject_unit,
                                    bcheck_name=subject.alias or subject.name,
                                    pending=len(skills_not_completed),
                                    total=len(skills_previous_unit),
                                    missing_list=missing_list)
                            )
                        else:
                            _logger.info(f"[BCHECK DEBUG] ✅ PERMITIDO - Todas las Skills de Unidad {previous_unit} completadas")
                    else:
                        _logger.info(f"[BCHECK DEBUG] ⚠️ No se encontraron Skills para Unidad {previous_unit} - permitiendo")

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
    
    def unlink(self):
        """
        REGLA DE ELIMINACIÓN AUTOMÁTICA PARA B-CHECKS
        
        Implementa la lógica: "Si eliminas un B-check → eliminar automáticamente las skills de la misma unidad"
        
        Esta regla garantiza la consistencia del sistema de prerrequisitos:
        - Las skills solo tienen sentido si hay un B-check para la unidad
        - Al eliminar el B-check, las skills de esa unidad quedan sin propósito
        - Por tanto, se eliminan automáticamente para evitar inconsistencias
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        lines_to_auto_remove = self.env['portal.student.weekly.plan.line']
        
        for line in self:
            # Solo procesar si es un B-check
            subject = line.effective_subject_id or line._get_effective_subject(
                check_completed=False, 
                check_prereq=False
            )
            
            if not subject or not self._is_prerequisite_subject(subject):
                continue  # No es un B-check, continuar normal
                
            # Es un B-check - buscar skills de la misma unidad para eliminar
            try:
                # Obtener el número de unidad del B-check
                bcheck_unit = getattr(subject, 'unit_number', None)
                if not bcheck_unit:
                    _logger.warning(
                        f"[AUTO-DELETE] B-check {subject.name} no tiene unit_number definido"
                    )
                    continue
                
                # Buscar todas las skills de la misma unidad en la misma semana
                plan = line.plan_id
                if not plan:
                    continue
                    
                same_unit_skills = plan.line_ids.filtered(
                    lambda l: l.id != line.id  # Excluir el B-check actual
                    and l.effective_subject_id
                    and getattr(l.effective_subject_id, 'unit_number', None) == bcheck_unit
                    and l.effective_subject_id.subject_category == 'skill'
                    and not self._is_prerequisite_subject(l.effective_subject_id)
                )
                
                if same_unit_skills:
                    student_name = plan.student_id.name if plan.student_id else "Desconocido"
                    skill_names = [
                        s.effective_subject_id.alias or s.effective_subject_id.name 
                        for s in same_unit_skills
                    ]
                    
                    _logger.info(
                        f"[AUTO-DELETE] Eliminando B-check {subject.alias or subject.name} "
                        f"de estudiante {student_name} - También se eliminarán {len(same_unit_skills)} "
                        f"skills de Unit {bcheck_unit}: {', '.join(skill_names)}"
                    )
                    
                    lines_to_auto_remove |= same_unit_skills
                    
            except Exception as e:
                _logger.error(
                    f"[AUTO-DELETE] Error procesando eliminación automática para línea {line.id}: {str(e)}"
                )
                continue
        
        # Primero eliminar las skills automáticamente
        if lines_to_auto_remove:
            try:
                _logger.info(
                    f"[AUTO-DELETE] Eliminando automáticamente {len(lines_to_auto_remove)} "
                    f"skills por eliminación de B-checks"
                )
                lines_to_auto_remove.unlink()
            except Exception as e:
                _logger.error(
                    f"[AUTO-DELETE] Error eliminando skills automáticamente: {str(e)}"
                )
        
        # Luego proceder con la eliminación normal
        return super(PortalStudentWeeklyPlanLine, self).unlink()
    
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
