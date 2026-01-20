# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from ..utils.normalizers import (
    normalize_to_uppercase,
    normalize_name_field,
    normalize_documento,
)
import logging
import re

_logger = logging.getLogger(__name__)


class Student(models.Model):
    """
    Modelo para gestionar Estudiantes.
    Almacena información personal, académica y de contacto.
    Se integra con el sistema de matrícula y estructura académica.
    """

    _name = "benglish.student"
    _description = "Estudiante"
    _order = "name"
    _rec_name = "name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    _EDIT_HISTORY_EXCLUDED_FIELDS = {
        "message_follower_ids",
        "message_ids",
        "activity_ids",
        "activity_state",
        "activity_summary",
        "activity_type_id",
        "activity_user_id",
        "activity_date_deadline",
        "message_attachment_count",
        "message_main_attachment_id",
        "__last_update",
        "state",
        "profile_state_id",
    }

    def _filter_partner_vals(self, partner_vals):
        """Filtra campos inexistentes en res.partner para evitar fallos en instalaciones sin OX."""
        partner_fields = self.env["res.partner"]._fields
        return {key: val for key, val in partner_vals.items() if key in partner_fields}

    def _normalize_portal_document(self, document):
        """Normaliza documento para password/login del portal."""
        doc_value = (document or "").strip()
        if not doc_value:
            return ""
        if re.search(r"[A-Za-z]", doc_value):
            return re.sub(r"[^0-9A-Za-z]", "", doc_value)
        return normalize_documento(doc_value) or ""

    #  INFORMACIÓN BÁSICA

    # Nombre completo (computado automáticamente desde nombres desagregados)
    name = fields.Char(
        string="Nombre Completo",
        compute="_compute_name",
        store=True,
        readonly=True,
        tracking=True,
        help="Nombre completo del estudiante, generado automáticamente desde los campos de nombre",
    )

    # Nombres desagregados (útil para importación y reportes oficiales)
    first_name = fields.Char(
        string="Primer Nombre",
        tracking=True,
        help="Primer nombre del estudiante",
    )
    second_name = fields.Char(
        string="Segundo Nombre",
        tracking=True,
        help="Segundo nombre del estudiante (opcional)",
    )
    first_last_name = fields.Char(
        string="Primer Apellido",
        tracking=True,
        help="Primer apellido del estudiante",
    )
    second_last_name = fields.Char(
        string="Segundo Apellido",
        tracking=True,
        help="Segundo apellido del estudiante (opcional)",
    )

    code = fields.Char(
        string="Código de Estudiante",
        required=True,
        copy=False,
        tracking=True,
        help="Código único identificador del estudiante (ej: EST-2025-001)",
    )
    image_1920 = fields.Image(string="Foto", help="Imagen del estudiante (avatar)")
    student_id_number = fields.Char(
        string="Documento de Identidad",
        tracking=True,
        help="Número de documento de identidad del estudiante",
    )
    id_type_id = fields.Many2one(
        comodel_name="l10n_latam.identification.type",
        string="Tipo de Documento",
        tracking=True,
        help="Tipo de documento de identidad (Cédula, Tarjeta de Identidad, etc.)",
    )
    birth_date = fields.Date(
        string="Fecha de Nacimiento",
        tracking=True,
        help="Fecha de nacimiento del estudiante",
    )
    age = fields.Integer(
        string="Edad",
        compute="_compute_age",
        store=True,
        help="Edad calculada automáticamente",
    )
    gender = fields.Selection(
        selection=[
            ("male", "Masculino"),
            ("female", "Femenino"),
            ("other", "Otro"),
        ],
        string="Género",
        tracking=True,
        help="Género del estudiante",
    )

    #  INFORMACIÓN DE CONTACTO

    email = fields.Char(
        string="Correo Electrónico",
        tracking=True,
        help="Correo electrónico principal del estudiante",
    )
    phone = fields.Char(
        string="Teléfono", tracking=True, help="Número de teléfono del estudiante"
    )
    mobile = fields.Char(
        string="Celular", tracking=True, help="Número de celular del estudiante"
    )
    address = fields.Text(
        string="Dirección", help="Dirección de residencia del estudiante"
    )
    city = fields.Char(string="Ciudad", help="Ciudad de residencia")
    country_id = fields.Many2one(
        comodel_name="res.country", string="País", help="País de residencia"
    )

    #  CONTACTO DE EMERGENCIA

    emergency_contact_name = fields.Char(
        string="Contacto de Emergencia", help="Nombre del contacto de emergencia"
    )
    emergency_contact_phone = fields.Char(
        string="Teléfono de Emergencia", help="Teléfono del contacto de emergencia"
    )
    emergency_contact_relationship = fields.Char(
        string="Parentesco", help="Relación con el estudiante (padre, madre, etc.)"
    )

    #  BENEFICIARIO / RESPONSABLE (importación Excel)

    responsible_is_emergency = fields.Boolean(
        string="Beneficiario",
        default=False,
        help="Indica si el estudiante es Beneficiario (marcado) o tiene un responsable diferente (desmarcado). Si es Beneficiario, usar sus datos como contacto de emergencia",
    )
    responsible_name = fields.Char(
        string="Nombre del Titular",
        help="Nombre del titular o responsable del estudiante (para facturación/contacto)",
    )
    responsible_phone = fields.Char(
        string="Teléfono del Titular",
        help="Teléfono del titular o responsable",
    )
    responsible_relationship = fields.Char(
        string="Parentesco del Titular",
        help="Relación del titular con el estudiante (padre, madre, tutor, etc.)",
    )

    @api.onchange("responsible_is_emergency")
    def _onchange_responsible_is_emergency(self):
        """Si es Titular (checked), copiar contacto de emergencia a responsable. Si es Beneficiario (unchecked), limpiar responsable"""
        if self.responsible_is_emergency:
            # Es Titular: usar contacto de emergencia como responsable
            self.responsible_name = self.emergency_contact_name
            self.responsible_phone = self.emergency_contact_phone
            self.responsible_relationship = self.emergency_contact_relationship
        else:
            # Es Beneficiario: limpiar campos de responsable
            self.responsible_name = False
            self.responsible_phone = False
            self.responsible_relationship = False

    #  INFORMACIÓN ACADÉMICA
    #
    # IMPORTANTE: Estos campos son INFORMATIVOS y de SOLO LECTURA.
    # Se actualizan automáticamente al aprobar matrículas.
    # NO son obligatorios ni bloquean la creación del estudiante.

    # Programa actual (editable al crear, actualizado desde matrícula)
    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa Actual",
        readonly=False,  # Editable para pre-selección
        tracking=True,
        help="Programa académico en el que está inscrito el estudiante. "
        "Se actualiza automáticamente al aprobar una matrícula.",
    )
    plan_id = fields.Many2one(
        comodel_name="benglish.plan",
        string="Plan de Estudio Actual",
        readonly=False,  # Editable para pre-selección
        tracking=True,
        domain="[('program_id', '=', program_id)]",
        help="Plan de estudio que cursa el estudiante. "
        "Se actualiza automáticamente al aprobar una matrícula.",
    )

    # Nivel actual (computado desde la última matrícula activa)
    current_level_id = fields.Many2one(
        comodel_name="benglish.level",
        string="Nivel Actual",
        compute="_compute_current_academic_info",
        store=True,
        help="Nivel actual del estudiante (última matrícula activa)",
    )
    current_phase_id = fields.Many2one(
        comodel_name="benglish.phase",
        string="Fase Actual",
        compute="_compute_current_academic_info",
        store=True,
        help="Fase actual del estudiante",
    )
    current_subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura Actual",
        compute="_compute_current_academic_info",
        store=True,
        help="Asignatura actual del estudiante (de matrículas activas)",
    )

    # Unidad máxima completada según historial académico (PROGRESO REAL)
    max_unit_completed = fields.Integer(
        string="Unidad Máxima Completada",
        compute="_compute_max_unit_from_history",
        store=True,
        help="Unidad más alta completada según historial académico. "
        "Este campo refleja el progreso REAL del estudiante, no solo su nivel asignado. "
        "Se usa para validar acceso a Oral Tests y unidades superiores.",
    )

    # Sede principal
    preferred_campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Sede Principal",
        tracking=True,
        help="Sede principal del estudiante",
    )

    # Modalidad preferida
    preferred_delivery_mode = fields.Selection(
        selection=[
            ("presential", "Presencial"),
            ("virtual", "Virtual"),
            ("hybrid", "Híbrido"),
        ],
        string="Modalidad Preferida",
        default="presential",
        tracking=True,
        help="Modalidad de clases preferida por el estudiante",
    )

    def _get_virtual_campus(self):
        campus = self.env.ref("benglish_academy.campus_virtual", raise_if_not_found=False)
        if campus:
            return campus
        return self.env["benglish.campus"].search(
            [("campus_type", "=", "online")], limit=1
        )

    @api.onchange("preferred_delivery_mode")
    def _onchange_preferred_delivery_mode(self):
        if self.preferred_delivery_mode == "virtual":
            campus = self._get_virtual_campus()
            if campus:
                self.preferred_campus_id = campus
        elif (
            self.preferred_campus_id
            and self.preferred_campus_id.campus_type == "online"
        ):
            self.preferred_campus_id = False

    @api.onchange("program_id")
    def _onchange_program_id(self):
        """Limpia el plan si cambia el programa."""
        if self.program_id and self.plan_id:
            if self.plan_id.program_id != self.program_id:
                self.plan_id = False

    def _apply_virtual_campus_default(self, vals):
        vals = dict(vals or {})
        if vals.get("preferred_delivery_mode") == "virtual":
            campus = self._get_virtual_campus()
            if campus:
                vals["preferred_campus_id"] = campus.id
        return vals

    #  MATRÍCULAS

    enrollment_ids = fields.One2many(
        comodel_name="benglish.enrollment",
        inverse_name="student_id",
        string="Matrículas",
        help="Historial completo de matrículas del estudiante",
    )
    active_enrollment_ids = fields.One2many(
        comodel_name="benglish.enrollment",
        inverse_name="student_id",
        string="Matrículas Activas",
        domain=[("state", "in", ["active", "enrolled", "in_progress"])],
        help="Matrículas actualmente activas. Incluye 'active' (estado principal), "
        "'enrolled' e 'in_progress' (estados legacy para compatibilidad).",
    )

    # Asignaturas del plan (para vista de asistencia/notas)
    subject_ids = fields.Many2many(
        comodel_name="benglish.subject",
        string="Asignaturas del Plan",
        compute="_compute_subject_ids",
        store=False,
        help="Todas las asignaturas del plan de estudios del estudiante",
    )

    # Historial académico (sesiones dictadas)
    academic_history_ids = fields.One2many(
        comodel_name="benglish.academic.history",
        inverse_name="student_id",
        string="Historial Académico",
        help="Registro de todas las sesiones dictadas con asistencia y notas",
    )

    # Tracking de sesiones por asignatura (TODAS las asignaturas del plan)
    session_tracking_ids = fields.One2many(
        comodel_name="benglish.subject.session.tracking",
        inverse_name="student_id",
        string="Tracking de Asignaturas",
        help="Seguimiento de TODAS las asignaturas del plan con sus sesiones",
    )

    #  ESTADÍSTICAS ACADÉMICAS

    total_enrollments = fields.Integer(
        string="Total de Matrículas",
        compute="_compute_enrollment_statistics",
        store=True,
        help="Número total de matrículas realizadas",
    )
    active_enrollments = fields.Integer(
        string="Matrículas Activas",
        compute="_compute_enrollment_statistics",
        store=True,
        help="Número de matrículas actualmente activas",
    )
    completed_enrollments = fields.Integer(
        string="Matrículas Completadas",
        compute="_compute_enrollment_statistics",
        store=True,
        help="Número de asignaturas completadas exitosamente",
    )
    failed_enrollments = fields.Integer(
        string="Matrículas Reprobadas",
        compute="_compute_enrollment_statistics",
        store=True,
        help="Número de asignaturas reprobadas",
    )

    # RF-04: Progreso Académico (por asignaturas, horas o mixto)
    academic_progress_percentage = fields.Float(
        string="Progreso Académico (%)",
        compute="_compute_academic_progress",
        store=True,
        help="Porcentaje de progreso según el método configurado en el plan",
    )
    completed_hours = fields.Float(
        string="Horas Completadas",
        compute="_compute_academic_progress",
        store=True,
        help="Total de horas académicas completadas",
    )
    total_plan_hours = fields.Float(
        string="Total Horas del Plan",
        related="plan_id.total_hours",
        help="Total de horas del plan de estudio",
    )

    # RF-03: KPIs adicionales para Historia Académica
    total_subjects_in_plan = fields.Integer(
        string="Total Asignaturas en Plan",
        compute="_compute_academic_history_kpis",
        store=True,
        help="Número total de asignaturas en el plan actual",
    )
    completed_subjects_count = fields.Integer(
        string="Asignaturas Completadas",
        compute="_compute_academic_history_kpis",
        store=True,
        help="Número de asignaturas completadas en el plan actual",
    )
    in_progress_subjects_count = fields.Integer(
        string="Asignaturas en Progreso",
        compute="_compute_academic_history_kpis",
        store=True,
        help="Número de asignaturas actualmente en progreso",
    )
    pending_subjects_count = fields.Integer(
        string="Asignaturas Pendientes",
        compute="_compute_academic_history_kpis",
        store=True,
        help="Número de asignaturas pendientes por cursar",
    )
    failed_subjects_count = fields.Integer(
        string="Asignaturas Reprobadas",
        compute="_compute_academic_history_kpis",
        store=True,
        help="Número de asignaturas reprobadas",
    )
    completion_rate = fields.Float(
        string="Tasa de Completitud (%)",
        compute="_compute_academic_history_kpis",
        store=True,
        digits=(5, 2),
        help="Porcentaje de asignaturas completadas del total del plan",
    )
    average_grade = fields.Float(
        string="Promedio General",
        compute="_compute_academic_history_kpis",
        store=True,
        digits=(5, 2),
        help="Promedio de calificaciones de asignaturas completadas",
    )
    average_attendance = fields.Float(
        string="Asistencia Promedio (%)",
        compute="_compute_attendance_kpis",
        store=True,
        digits=(5, 2),
        help="Porcentaje promedio de asistencia a clases",
    )
    total_classes_attended = fields.Integer(
        string="Clases Asistidas",
        compute="_compute_attendance_kpis",
        store=True,
        help="Número total de clases a las que ha asistido",
    )
    total_classes_scheduled = fields.Integer(
        string="Clases Programadas",
        compute="_compute_attendance_kpis",
        store=True,
        help="Número total de clases programadas",
    )

    # Asignaturas aprobadas (para validación de prerrequisitos)
    approved_subject_ids = fields.Many2many(
        comodel_name="benglish.subject",
        relation="benglish_student_approved_subject_rel",
        column1="student_id",
        column2="subject_id",
        string="Asignaturas Aprobadas",
        compute="_compute_approved_subjects",
        store=True,
        help="Listado de asignaturas que el estudiante ha aprobado",
    )

    #  ESTADO Y CONTROL

    state = fields.Selection(
        selection=[
            ("prospect", "Prospecto"),
            ("enrolled", "Matriculado"),
            ("active", "Activo"),
            ("inactive", "Inactivo"),
            ("graduated", "Graduado"),
            ("withdrawn", "Retirado"),
        ],
        string="Estado",
        default="prospect",
        required=True,
        tracking=True,
        help="Estado actual del estudiante en la institución",
    )

    #  ESTADO DE PERFIL

    profile_state_id = fields.Many2one(
        comodel_name="benglish.student.profile.state",
        string="Estado de Perfil",
        tracking=True,
        help="Estado del perfil que determina permisos y restricciones del estudiante",
    )
    motivo_bloqueo = fields.Text(
        string="Motivo de Bloqueo",
        tracking=True,
        help="Razón del bloqueo o restricción cuando el estado lo requiere",
    )
    profile_state_history_ids = fields.One2many(
        comodel_name="benglish.student.state.history",
        inverse_name="student_id",
        string="Historial de Estado de Perfil",
        readonly=True,
    )
    lifecycle_state_history_ids = fields.One2many(
        comodel_name="benglish.student.lifecycle.history",
        inverse_name="student_id",
        string="Historial de Estado",
        readonly=True,
    )
    edit_history_ids = fields.One2many(
        comodel_name="benglish.student.edit.history",
        inverse_name="student_id",
        string="Historial de Edición",
        readonly=True,
    )

    # HISTORIAL ACADÉMICO (ASISTENCIA Y NOTAS)

    academic_history_ids = fields.One2many(
        comodel_name="benglish.academic.history",
        inverse_name="student_id",
        string="Historial Académico",
        help="Registro completo de asistencia y notas del estudiante por sesión",
        readonly=True,
    )

    # PROGRESO ACADÉMICO POR ASIGNATURA

    enrollment_progress_ids = fields.One2many(
        comodel_name="benglish.enrollment.progress",
        inverse_name="student_id",
        string="Progreso en Asignaturas",
        help="Progreso del estudiante en cada asignatura del plan (incluye pendientes, en progreso y completadas)",
        readonly=True,
    )

    # ESTADO DE CARTERA

    # Mejora 4: Campo computed desde facturas
    al_dia_en_pagos = fields.Boolean(
        string="Al Día en Pagos",
        compute="_compute_al_dia_en_pagos",
        store=True,
        tracking=True,
        help="Indica si el estudiante está al día en sus pagos. "
        "Calculado automáticamente desde facturas pendientes.",
    )

    # Campo manual para override
    al_dia_en_pagos_manual = fields.Boolean(
        string="Al Día (Override Manual)",
        default=True,
        tracking=True,
        help="Override manual del estado de cartera. "
        "Usar cuando no hay integración con facturación.",
    )

    usar_calculo_cartera = fields.Boolean(
        string="Usar Cálculo Automático",
        default=False,
        help="Si está activo, el estado de cartera se calcula automáticamente "
        "desde las facturas. Si no, se usa el valor manual.",
    )

    monto_pendiente = fields.Monetary(
        string="Monto Pendiente",
        compute="_compute_al_dia_en_pagos",
        store=True,
        currency_field="currency_id",
        help="Monto total de facturas vencidas pendientes",
    )

    facturas_vencidas_count = fields.Integer(
        string="Facturas Vencidas",
        compute="_compute_al_dia_en_pagos",
        store=True,
        help="Número de facturas vencidas pendientes",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id,
    )

    fecha_ultima_mora = fields.Date(
        string="Fecha Última Mora", help="Fecha de la última mora registrada"
    )

    #  CONGELAMIENTOS

    freeze_period_ids = fields.One2many(
        comodel_name="benglish.student.freeze.period",
        inverse_name="student_id",
        string="Periodos de Congelamiento",
        help="Historial de solicitudes de congelamiento del estudiante",
    )
    dias_congelamiento_usados = fields.Integer(
        string="Días Congelamiento Usados",
        compute="_compute_freeze_statistics",
        help="Total de días de congelamiento utilizados en matrículas activas",
    )
    dias_congelamiento_disponibles = fields.Integer(
        string="Días Congelamiento Disponibles",
        compute="_compute_freeze_statistics",
        help="Días de congelamiento disponibles según el plan actual",
    )
    tiene_congelamiento_activo = fields.Boolean(
        string="Congelamiento Activo",
        compute="_compute_freeze_statistics",
        help="Indica si tiene un congelamiento vigente actualmente",
    )
    active = fields.Boolean(
        string="Activo",
        default=True,
        tracking=True,
        help="Si está inactivo, el estudiante no aparecerá en las búsquedas",
    )
    enrollment_date = fields.Date(
        string="Fecha de Ingreso",
        default=fields.Date.context_today,
        tracking=True,
        help="Fecha de primera matrícula en la institución",
    )
    withdrawal_date = fields.Date(
        string="Fecha de Retiro",
        tracking=True,
        help="Fecha de retiro de la institución",
    )
    withdrawal_reason = fields.Text(
        string="Motivo de Retiro", help="Razón por la cual el estudiante se retiró"
    )

    # NOTAS Y OBSERVACIONES

    notes = fields.Text(
        string="Notas Internas", help="Observaciones internas sobre el estudiante"
    )
    medical_notes = fields.Text(
        string="Notas Médicas",
        help="Información médica relevante (alergias, condiciones especiales, etc.)",
    )

    # RELACIÓN CON USUARIO

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Usuario Portal",
        help="Usuario de Odoo asociado (para acceso al portal)",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contacto",
        help="Contacto asociado en el sistema",
    )

    #  MÉTODOS COMPUTADOS

    @api.depends("birth_date")
    def _compute_age(self):
        """Calcula la edad del estudiante basándose en su fecha de nacimiento"""
        today = fields.Date.context_today(self)
        for student in self:
            if student.birth_date:
                student.age = (today - student.birth_date).days // 365
            else:
                student.age = 0

    @api.depends("first_name", "second_name", "first_last_name", "second_last_name")
    def _compute_name(self):
        """Calcula el nombre completo concatenando los nombres desagregados"""
        for student in self:
            name_parts = []
            if student.first_name:
                name_parts.append(student.first_name)
            if student.second_name:
                name_parts.append(student.second_name)
            if student.first_last_name:
                name_parts.append(student.first_last_name)
            if student.second_last_name:
                name_parts.append(student.second_last_name)

            student.name = " ".join(name_parts) if name_parts else "Sin Nombre"

    @api.depends("plan_id", "plan_id.subject_ids")
    def _compute_subject_ids(self):
        """Calcula todas las asignaturas del plan actual del estudiante"""
        for student in self:
            if student.plan_id:
                # Obtener todas las asignaturas del plan a través de las fases
                phases = self.env["benglish.phase"].search(
                    [("program_id", "=", student.plan_id.program_id.id)]
                )
                levels = self.env["benglish.level"].search(
                    [("phase_id", "in", phases.ids)]
                )
                student.subject_ids = self.env["benglish.subject"].search(
                    [("level_id", "in", levels.ids)]
                )
            else:
                student.subject_ids = False

    @api.depends("enrollment_ids", "enrollment_ids.state")
    def _compute_enrollment_statistics(self):
        """Calcula estadísticas de matrículas del estudiante"""
        for student in self:
            # Forzar recarga de las matrículas para asegurar datos actualizados
            student.enrollment_ids.invalidate_recordset(["state"])
            enrollments = student.enrollment_ids

            student.total_enrollments = len(enrollments)
            student.active_enrollments = len(
                enrollments.filtered(
                    lambda e: e.state in ["enrolled", "in_progress", "active"]
                )
            )
            student.completed_enrollments = len(
                enrollments.filtered(lambda e: e.state == "completed")
            )
            student.failed_enrollments = len(
                enrollments.filtered(lambda e: e.state == "failed")
            )

    @api.depends("enrollment_ids", "enrollment_ids.state", "enrollment_ids.final_grade")
    def _compute_approved_subjects(self):
        """
        Calcula las asignaturas aprobadas por el estudiante.
        Una asignatura se considera aprobada si tiene matrícula completada
        con calificación aprobatoria.
        """
        for student in self:
            approved_subjects = self.env["benglish.subject"]
            completed_enrollments = student.enrollment_ids.filtered(
                lambda e: e.state == "completed" and e.is_approved
            )
            for enrollment in completed_enrollments:
                if enrollment.subject_id:
                    approved_subjects |= enrollment.subject_id
            student.approved_subject_ids = approved_subjects

    @api.depends(
        "enrollment_ids",
        "enrollment_ids.enrollment_progress_ids",
        "enrollment_ids.enrollment_progress_ids.state",
        "enrollment_ids.state",
        "plan_id",
        "plan_id.progress_calculation_method",
    )
    def _compute_academic_progress(self):
        """
        RF-04: Calcula el progreso académico según el método del plan.

        Métodos soportados:
        - by_subjects: Progreso por asignaturas completadas
        - by_hours: Progreso por horas académicas completadas
        - mixed: Promedio de ambos métodos (50% + 50%)

        NUEVO: Ahora usa enrollment_progress_ids (progreso por asignatura)
        en lugar de contar matrículas completas (modelo antiguo).
        """
        for student in self:
            if not student.plan_id:
                student.academic_progress_percentage = 0.0
                student.completed_hours = 0.0
                continue

            method = student.plan_id.progress_calculation_method or "by_subjects"

            # Obtener matrícula activa
            active_enrollment = (
                student.active_enrollment_ids[:1]
                if student.active_enrollment_ids
                else False
            )

            if not active_enrollment:
                # Si no hay matrícula activa, intentar con cualquier matrícula
                active_enrollment = (
                    student.enrollment_ids[:1] if student.enrollment_ids else False
                )

            if not active_enrollment:
                student.academic_progress_percentage = 0.0
                student.completed_hours = 0.0
                continue

            # Obtener todos los registros de progreso
            progress_records = active_enrollment.enrollment_progress_ids

            # Asignaturas completadas (estado = 'completed')
            completed_progress = progress_records.filtered(
                lambda p: p.state == "completed"
                and (
                    not p.subject_id
                    or p.subject_id.subject_category != "bskills"
                    or (p.subject_id.bskill_number or 0) <= 6
                )
            )

            # Total de asignaturas del programa
            total_subjects = self.env["benglish.subject"].search_count(
                [
                    ("program_id", "=", student.plan_id.program_id.id),
                    ("active", "=", True),
                    "|",
                    ("subject_category", "!=", "bskills"),
                    ("bskill_number", "<=", 6),
                ]
            )

            if total_subjects == 0:
                total_subjects = (
                    len(student.plan_id.subject_ids)
                    if student.plan_id.subject_ids
                    else 1
                )

            # 1. Calcular progreso por asignaturas
            completed_subjects = len(completed_progress)
            progress_by_subjects = (
                (completed_subjects / total_subjects * 100) if total_subjects > 0 else 0
            )

            # 2. Calcular progreso por horas
            completed_hours = 0.0
            for progress in completed_progress:
                if progress.subject_id and progress.subject_id.duration_hours:
                    completed_hours += progress.subject_id.duration_hours

            student.completed_hours = completed_hours
            total_hours = student.plan_id.total_hours or 1
            progress_by_hours = (
                (completed_hours / total_hours * 100) if total_hours > 0 else 0
            )

            # 3. Calcular según método
            if method == "by_subjects":
                student.academic_progress_percentage = progress_by_subjects
            elif method == "by_hours":
                student.academic_progress_percentage = progress_by_hours
            elif method == "mixed":
                student.academic_progress_percentage = (
                    progress_by_subjects + progress_by_hours
                ) / 2
            else:
                student.academic_progress_percentage = progress_by_subjects

    @api.depends(
        "active_enrollment_ids",
        "active_enrollment_ids.current_level_id",
        "active_enrollment_ids.level_id",
        "active_enrollment_ids.current_subject_id",
        "active_enrollment_ids.subject_id",
        "active_enrollment_ids.state",
        "enrollment_ids.state",
    )
    def _compute_current_academic_info(self):
        """
        Calcula el nivel, fase y asignatura actual del estudiante basándose
        en sus matrículas activas.
        """
        for student in self:
            active_enrollments = student.active_enrollment_ids

            # DEBUG: Logging detallado para diagnosticar problemas de matrículas activas
            all_enrollments = student.enrollment_ids
            _logger.info(
                f"🔍 [STUDENT {student.code}] Diagnóstico de Matrículas:\n"
                f"  • Total matrículas: {len(all_enrollments)}\n"
                f"  • Matrículas activas detectadas: {len(active_enrollments)}\n"
                f"  • Estados de todas las matrículas: {[(e.code, e.state) for e in all_enrollments]}\n"
                f"  • IDs de matrículas activas: {active_enrollments.ids}"
            )

            if active_enrollments:
                # Tomar el nivel más alto de las matrículas activas
                # Priorizar current_level_id (nuevo) sobre level_id (legacy)
                levels = active_enrollments.mapped(
                    "current_level_id"
                ) or active_enrollments.mapped("level_id")

                _logger.info(
                    f"🎓 [STUDENT {student.code}] Niveles encontrados: "
                    f"{[(l.name, l.phase_id.name) for l in levels]}"
                )

                if levels:
                    # Ordenar por secuencia y tomar el último
                    sorted_levels = levels.sorted(
                        key=lambda l: (l.phase_id.sequence, l.sequence)
                    )
                    student.current_level_id = sorted_levels[-1]
                    student.current_phase_id = sorted_levels[-1].phase_id

                    # Obtener la asignatura de la matrícula activa más reciente
                    latest_enrollment = active_enrollments.sorted(
                        key=lambda e: e.enrollment_date, reverse=True
                    )[0]
                    # Priorizar current_subject_id sobre subject_id (legacy)
                    student.current_subject_id = (
                        latest_enrollment.current_subject_id
                        or latest_enrollment.subject_id
                    )

                    _logger.info(
                        f"✅ [STUDENT {student.code}] Info académica actualizada:\n"
                        f"  • Fase: {student.current_phase_id.name if student.current_phase_id else 'N/A'}\n"
                        f"  • Nivel: {student.current_level_id.name if student.current_level_id else 'N/A'}\n"
                        f"  • Asignatura: {student.current_subject_id.name if student.current_subject_id else 'N/A'}"
                    )
                else:
                    student.current_level_id = False
                    student.current_phase_id = False
                    student.current_subject_id = False
                    _logger.warning(
                        f"⚠️ [STUDENT {student.code}] No se encontraron niveles en matrículas activas"
                    )
            else:
                student.current_level_id = False
                student.current_phase_id = False
                student.current_subject_id = False
                _logger.warning(
                    f"⚠️ [STUDENT {student.code}] No tiene matrículas activas. "
                    f"Total matrículas en sistema: {len(all_enrollments)}"
                )

    @api.depends(
        "academic_history_ids",
        "academic_history_ids.attendance_status",
        "academic_history_ids.subject_id",
    )
    def _compute_max_unit_from_history(self):
        """
        Calcula la unidad máxima completada basándose en el historial académico REAL del estudiante.

        LÓGICA CORRECTA REFACTORIZADA:
        - Una unidad está completa SOLO si tiene B-check + 4 skills
        - Cuenta TODAS las skills sin importar bskill_number
        - Usa set() para contar skills únicas (permite repeticiones)
        - Avanza solo hasta la última unidad COMPLETA

        Este método es CRÍTICO para:
        - Validar acceso a Oral Tests
        - Validar acceso a unidades superiores
        - Mostrar progreso real en portal y backend
        """
        for student in self:
            # Buscar todas las asignaturas completadas en historial académico
            completed_subjects = student.academic_history_ids.filtered(
                lambda h: h.attendance_status == "attended" and h.subject_id
            )

            if not completed_subjects:
                # Fallback: usar el max_unit del nivel asignado si no hay historial
                if student.current_level_id and student.current_level_id.max_unit:
                    student.max_unit_completed = student.current_level_id.max_unit
                    _logger.warning(
                        f"⚠️ [STUDENT {student.code}] Sin historial académico. "
                        f"Usando max_unit del nivel asignado: {student.max_unit_completed}"
                    )
                else:
                    student.max_unit_completed = 0
                    _logger.warning(
                        f"⚠️ [STUDENT {student.code}] Sin historial ni nivel asignado. "
                        f"max_unit_completed = 0"
                    )
                continue

            # ═════════════════════════════════════════════════════════════
            # LÓGICA CORRECTA: Agrupar por unidad y verificar completitud
            # ═════════════════════════════════════════════════════════════
            units_progress = {}
            for history in completed_subjects:
                subject = history.subject_id
                unit = subject.unit_number
                if not unit:
                    continue
                
                if unit not in units_progress:
                    units_progress[unit] = {
                        'bcheck': False,
                        'skills': set()  # Usar set para contar skills únicas
                    }
                
                if subject.subject_category == 'bcheck':
                    units_progress[unit]['bcheck'] = True
                elif subject.subject_category == 'bskills':
                    # Agregar a set para evitar duplicados
                    # Contar TODAS las skills (incluso bskill_number > 4)
                    units_progress[unit]['skills'].add(subject.id)
            
            # Encontrar última unidad COMPLETA (B-check + 4 skills)
            max_complete = 0
            for unit in sorted(units_progress.keys()):
                progress = units_progress[unit]
                is_complete = progress['bcheck'] and len(progress['skills']) >= 4
                
                if is_complete:
                    max_complete = unit
                else:
                    # Primera unidad incompleta, detener
                    break
            
            student.max_unit_completed = max_complete
            
            # Log detallado
            _logger.info(
                f"📊 [STUDENT {student.code}] Progreso Real Calculado (Lógica Correcta):\n"
                f"  • Asignaturas completadas: {len(completed_subjects)}\n"
                f"  • Unidades con progreso: {sorted(units_progress.keys())}\n"
                f"  • Unidad máxima COMPLETA: {student.max_unit_completed}"
            )
            
            # Log de progreso por unidad
            for unit in sorted(units_progress.keys()):
                progress = units_progress[unit]
                bcheck_icon = "✓" if progress['bcheck'] else "✗"
                skills_count = len(progress['skills'])
                complete_icon = "✅" if (progress['bcheck'] and skills_count >= 4) else "⚠️"
                
                _logger.info(
                    f"  {complete_icon} Unit {unit:2}: B-check [{bcheck_icon}] | "
                    f"Skills: {skills_count}/4"
                )

    @api.depends(
        "freeze_period_ids",
        "freeze_period_ids.estado",
        "freeze_period_ids.dias",
        "plan_id",
    )
    def _compute_freeze_statistics(self):
        """
        Calcula estadísticas de congelamiento del estudiante.
        Implementa parte de T-GA-CONG-02.
        """
        today = fields.Date.context_today(self)
        FreezeConfig = self.env["benglish.plan.freeze.config"]

        for student in self:
            # Calcular días usados (solo de congelamientos aprobados o finalizados, no especiales)
            congelamientos_validos = student.freeze_period_ids.filtered(
                lambda f: f.estado in ("aprobado", "finalizado") and not f.es_especial
            )
            student.dias_congelamiento_usados = sum(
                congelamientos_validos.mapped("dias")
            )

            # Verificar si tiene congelamiento activo
            congelamiento_activo = student.freeze_period_ids.filtered(
                lambda f: f.estado == "aprobado"
                and f.fecha_inicio <= today <= f.fecha_fin
            )
            student.tiene_congelamiento_activo = bool(congelamiento_activo)

            # Calcular días disponibles según el plan
            if student.plan_id:
                config = FreezeConfig.get_config_for_plan(student.plan_id)
                if config and config.permite_congelamiento:
                    student.dias_congelamiento_disponibles = max(
                        0,
                        config.max_dias_acumulados - student.dias_congelamiento_usados,
                    )
                else:
                    student.dias_congelamiento_disponibles = 0
            else:
                student.dias_congelamiento_disponibles = 0

    @api.depends(
        "enrollment_ids",
        "enrollment_ids.enrollment_progress_ids",
        "enrollment_ids.enrollment_progress_ids.state",
        "enrollment_ids.enrollment_progress_ids.final_grade",
        "plan_id",
        "plan_id.subject_ids",
    )
    def _compute_academic_history_kpis(self):
        """
        RF-03: Calcula KPIs para la Historia Académica del estudiante.
        Incluye métricas de completitud, progreso y calificaciones.
        """
        for student in self:
            # Obtener matrícula activa al plan
            active_enrollment = student.active_enrollment_ids.filtered(
                lambda e: e.plan_id and e.state in ["active", "enrolled", "in_progress"]
            )[:1]

            if not active_enrollment or not active_enrollment.plan_id:
                student.total_subjects_in_plan = 0
                student.completed_subjects_count = 0
                student.in_progress_subjects_count = 0
                student.pending_subjects_count = 0
                student.failed_subjects_count = 0
                student.completion_rate = 0.0
                student.average_grade = 0.0
                continue

            # Obtener todos los progress records de la matrícula activa
            progress_records = active_enrollment.enrollment_progress_ids

            # Total de asignaturas en el plan
            total = len(active_enrollment.plan_id.subject_ids)
            student.total_subjects_in_plan = total

            # Contar por estado
            completed = progress_records.filtered(lambda p: p.state == "completed")
            in_progress = progress_records.filtered(lambda p: p.state == "in_progress")
            failed = progress_records.filtered(lambda p: p.state == "failed")
            pending = progress_records.filtered(lambda p: p.state == "pending")

            student.completed_subjects_count = len(completed)
            student.in_progress_subjects_count = len(in_progress)
            student.failed_subjects_count = len(failed)
            student.pending_subjects_count = len(pending)

            # Tasa de completitud
            student.completion_rate = (
                (len(completed) / total * 100) if total > 0 else 0.0
            )

            # Promedio general (solo asignaturas completadas con calificación)
            grades = completed.filtered(lambda p: p.final_grade > 0).mapped(
                "final_grade"
            )
            student.average_grade = sum(grades) / len(grades) if grades else 0.0

    @api.depends(
        "academic_history_ids",
        "academic_history_ids.attendance_status",
        "academic_history_ids.attended",
    )
    def _compute_attendance_kpis(self):
        """
        RF-03: Calcula KPIs de asistencia del estudiante.
        Incluye porcentaje de asistencia y contadores de clases.

        CAMBIO: Ahora usa benglish.academic.history (academic_history_ids) en lugar de benglish.attendance
        Se recalcula automáticamente cuando cambia el historial académico
        """
        for student in self:
            # Valores por defecto
            student.average_attendance = 0.0
            student.total_classes_attended = 0
            student.total_classes_scheduled = 0

            # ⭐ CAMBIO: Usar academic history para calcular asistencia
            try:
                History = self.env["benglish.academic.history"].sudo()

                # Buscar todos los registros de historial del estudiante
                all_history = History.search(
                    [
                        ("student_id", "=", student.id),
                    ]
                )

                # Total de clases registradas (attended + absent + pending)
                total_scheduled = len(all_history)

                # Total de clases a las que asistió
                total_attended = len(
                    all_history.filtered(
                        lambda h: h.attendance_status == "attended"
                        or h.attended == True
                    )
                )

                student.total_classes_scheduled = total_scheduled
                student.total_classes_attended = total_attended
                student.average_attendance = (
                    (total_attended / total_scheduled * 100)
                    if total_scheduled > 0
                    else 0.0
                )

                _logger.info(
                    f"[ATTENDANCE-KPI] Estudiante {student.name}: "
                    f"Asistidas={total_attended}, Programadas={total_scheduled}, "
                    f"Porcentaje={student.average_attendance:.1f}%"
                )
            except Exception as e:
                # Si hay error, mantener valores por defecto (0)
                _logger.warning(
                    f"Error calculando KPIs de asistencia para {student.name}: {str(e)}"
                )
                pass

    # ADICIONALES

    @api.depends("partner_id", "usar_calculo_cartera", "al_dia_en_pagos_manual")
    def _compute_al_dia_en_pagos(self):
        """
        Mejora 4: Calcula el estado de cartera desde facturas reales.

        Busca facturas vencidas (account.move) asociadas al partner del estudiante.
        Si no hay integración con facturación, usa el campo manual.
        """
        today = fields.Date.context_today(self)

        for student in self:
            # Si no usa cálculo automático, tomar valor manual
            if not student.usar_calculo_cartera:
                student.al_dia_en_pagos = student.al_dia_en_pagos_manual
                student.monto_pendiente = 0
                student.facturas_vencidas_count = 0
                continue

            # Verificar si existe el modelo account.move (módulo account instalado)
            if "account.move" not in self.env:
                student.al_dia_en_pagos = student.al_dia_en_pagos_manual
                student.monto_pendiente = 0
                student.facturas_vencidas_count = 0
                continue

            # Si no hay partner, usar valor manual
            if not student.partner_id:
                student.al_dia_en_pagos = student.al_dia_en_pagos_manual
                student.monto_pendiente = 0
                student.facturas_vencidas_count = 0
                continue

            # Buscar facturas vencidas del partner
            try:
                facturas_vencidas = (
                    self.env["account.move"]
                    .sudo()
                    .search(
                        [
                            ("partner_id", "=", student.partner_id.id),
                            (
                                "move_type",
                                "=",
                                "out_invoice",
                            ),  # Solo facturas de cliente
                            ("state", "=", "posted"),  # Solo publicadas
                            (
                                "payment_state",
                                "in",
                                ["not_paid", "partial"],
                            ),  # No pagadas o parciales
                            ("invoice_date_due", "<", today),  # Vencidas
                        ]
                    )
                )

                student.facturas_vencidas_count = len(facturas_vencidas)
                student.monto_pendiente = sum(
                    facturas_vencidas.mapped("amount_residual")
                )
                student.al_dia_en_pagos = len(facturas_vencidas) == 0

                # Actualizar fecha de última mora si hay facturas vencidas
                if facturas_vencidas and not student.al_dia_en_pagos:
                    if (
                        not student.fecha_ultima_mora
                        or student.fecha_ultima_mora < today
                    ):
                        student.fecha_ultima_mora = today

            except Exception:
                # Si hay error (modelo no existe, etc.), usar valor manual
                student.al_dia_en_pagos = student.al_dia_en_pagos_manual
                student.monto_pendiente = 0
                student.facturas_vencidas_count = 0

    # VALIDACIONES

    @api.constrains("code")
    def _check_code_unique(self):
        """Valida que el código del estudiante sea único"""
        for student in self:
            if student.code:
                domain = [("code", "=", student.code), ("id", "!=", student.id)]
                if self.search_count(domain) > 0:
                    raise ValidationError(
                        _(
                            'El código de estudiante "%s" ya existe. '
                            "Cada estudiante debe tener un código único."
                        )
                        % student.code
                    )

    @api.constrains("email")
    def _check_email_format(self):
        """Valida el formato del correo electrónico"""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        for student in self:
            if student.email and not re.match(email_pattern, student.email):
                raise ValidationError(
                    _('El formato del correo electrónico "%s" no es válido.')
                    % student.email
                )

    @api.constrains("birth_date")
    def _check_birth_date(self):
        """Valida que la fecha de nacimiento sea lógica"""
        today = fields.Date.context_today(self)
        for student in self:
            if student.birth_date:
                if student.birth_date > today:
                    raise ValidationError(
                        _("La fecha de nacimiento no puede ser futura.")
                    )
                age = (today - student.birth_date).days // 365
                if age < 3:
                    raise ValidationError(
                        _("El estudiante debe tener al menos 3 años de edad.")
                    )
                if age > 120:
                    raise ValidationError(
                        _(
                            "La fecha de nacimiento no parece ser válida (edad > 120 años)."
                        )
                    )

    @api.constrains("first_name", "first_last_name")
    def _check_name_fields(self):
        """Valida que se proporcionen al menos el primer nombre y primer apellido"""
        for student in self:
            if not student.first_name or not student.first_last_name:
                raise ValidationError(
                    _(
                        "Debe proporcionar al menos el Primer Nombre y el Primer Apellido del estudiante."
                    )
                )

    #  MÉTODOS DE NEGOCIO

    def action_view_enrollments(self):
        """Abre la vista de matrículas del estudiante"""
        self.ensure_one()
        return {
            "name": _("Matrículas de %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.enrollment",
            "view_mode": "list,form,kanban",
            "domain": [("student_id", "=", self.id)],
            "context": {
                "default_student_id": self.id,
                "default_program_id": self.program_id.id if self.program_id else False,
                "default_preferred_campus_id": (
                    self.preferred_campus_id.id if self.preferred_campus_id else False
                ),
            },
        }

    def action_view_active_enrollments(self):
        """Abre la vista de matrículas activas del estudiante"""
        self.ensure_one()
        return {
            "name": _("Matrículas Activas de %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.enrollment",
            "view_mode": "list,form,kanban",
            "domain": [
                ("student_id", "=", self.id),
                ("state", "in", ["enrolled", "in_progress"]),
            ],
            "context": {"default_student_id": self.id},
        }

    def action_view_plan_details(self):
        """RF-03: Abre la vista detallada del plan de estudios del estudiante"""
        self.ensure_one()
        if not self.plan_id:
            raise UserError(_("Este estudiante no tiene un plan de estudios asignado."))

        return {
            "name": _("Plan de Estudios: %s") % self.plan_id.name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.plan",
            "res_id": self.plan_id.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_view_lifecycle_history(self):
        """Abre el historial de cambios de estado del estudiante en una ventana separada.

        Si el modelo `benglish.student.lifecycle.history` no está disponible, muestra
        una notificación indicando que el historial no está implementado.
        """
        self.ensure_one()
        model_name = "benglish.student.lifecycle.history"
        if model_name not in self.env:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Historial no disponible"),
                    "message": _(
                        "El modelo de historial no está instalado o no está disponible."
                    ),
                    "type": "warning",
                    "sticky": False,
                },
            }

        return {
            "name": _("Historial de Estados: %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": model_name,
            "view_mode": "list,form",
            "domain": [("student_id", "=", self.id)],
            "context": {"search_default_filter_by_student": 1},
        }

    def action_enroll(self):
        """Abre el asistente de matrícula para el estudiante"""
        self.ensure_one()
        return {
            "name": _("Matricular Estudiante: %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.enrollment",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_student_id": self.id,
                "default_program_id": self.program_id.id if self.program_id else False,
                "default_campus_id": (
                    self.preferred_campus_id.id if self.preferred_campus_id else False
                ),
                "default_delivery_mode": self.preferred_delivery_mode,
            },
        }

    def _create_single_portal_user(self):
        """
        Método privado para crear un usuario de portal para un solo estudiante.
        Retorna un diccionario con el resultado:
        {
            'success': True/False,
            'message': str,
            'user_id': int (si success=True)
        }
        """
        self.ensure_one()

        # Validaciones
        if self.user_id:
            return {
                "success": False,
                "message": _("Ya tiene un usuario asignado"),
                "code": "already_exists",
            }

        if not self.email:
            return {
                "success": False,
                "message": _("No tiene correo configurado"),
                "code": "no_email",
            }

        normalized_document = self._normalize_portal_document(self.student_id_number)
        if not normalized_document:
            return {
                "success": False,
                "message": _("No tiene documento de identidad válido para la contraseña"),
                "code": "no_document",
            }

        # Verificar si ya existe usuario con ese número de identificación como login
        existing = (
            self.env["res.users"].sudo().search([("login", "=", normalized_document)], limit=1)
        )
        if existing:
            return {
                "success": False,
                "message": _("Ya existe un usuario con el documento %s") % self.student_id_number,
                "code": "document_exists",
            }

        try:
            with self.env.cr.savepoint():
                # Calcular tipo de documento
                # PRIORIDAD: usar el tipo de documento del estudiante si existe,
                # sino calcular según edad
                identification_type_id = False
                if self.id_type_id:
                    # Usar el tipo de documento seleccionado en el estudiante
                    identification_type_id = self.id_type_id.id
                elif self.birth_date:
                    # Fallback: calcular según edad si no hay tipo de documento
                    from datetime import date

                    today = date.today()
                    age = (
                        today.year
                        - self.birth_date.year
                        - (
                            (today.month, today.day)
                            < (self.birth_date.month, self.birth_date.day)
                        )
                    )

                    # Buscar tipo de documento según edad
                    IdentificationType = self.env["l10n_latam.identification.type"]
                    if age >= 18:
                        id_type = IdentificationType.search(
                            [("name", "=", "Cedula de ciudadania")], limit=1
                        )
                    else:
                        id_type = IdentificationType.search(
                            [("name", "=", "Tarjeta de identidad")], limit=1
                        )

                    if id_type:
                        identification_type_id = id_type.id

                # Mapear género del estudiante al formato de res.partner (OX)
                # Estudiante: male/female/other → Partner OX: masculino/femenino
                genero_partner = False
                if self.gender == "male":
                    genero_partner = "masculino"
                elif self.gender == "female":
                    genero_partner = "femenino"
                # Si es 'other', dejar en False (no hay equivalente directo en OX)

                # Preparar valores completos del partner con TODA la información del estudiante
                partner_vals = {
                    "name": self.name,
                    "email": self.email,
                    "phone": self.phone,
                    "mobile": self.mobile,
                    "is_company": False,
                    "is_student": True,
                    "company_type": "person",
                    # Campos de nombre desagregados (extensión colombiana OX)
                    "primer_nombre": self.first_name,
                    "otros_nombres": self.second_name,
                    "primer_apellido": self.first_last_name,
                    "segundo_apellido": self.second_last_name,
                    # Documento de identidad (usar student_id_number para ambos campos)
                    "ref": self.student_id_number
                    or False,  # Campo estándar de identificación
                    "vat": self.student_id_number,  # Campo NIT/VAT
                    "l10n_latam_identification_type_id": identification_type_id,
                    # Información personal adicional (campos OX)
                    "fecha_nacimiento": self.birth_date,  # Fecha de nacimiento (OX)
                    "genero": genero_partner,  # Género (OX)
                    "sexo_biologico": genero_partner,  # Sexo biológico (OX)
                    # Dirección y ubicación
                    "street": self.address,  # Dirección
                    "country_id": self.country_id.id if self.country_id else False,
                    # Imagen
                    "image_1920": self.image_1920,  # Foto
                    # Notas en el campo comment
                    "comment": f"""Información del Estudiante:
- Código: {self.code}
- Documento: {self.student_id_number or 'N/A'}
- Fecha Nacimiento: {self.birth_date or 'N/A'}
- Edad: {self.age or 'N/A'}
- Género: {dict(self._fields['gender'].selection).get(self.gender, 'N/A') if self.gender else 'N/A'}

Contacto de Emergencia:
- Nombre: {self.emergency_contact_name or 'N/A'}
- Teléfono: {self.emergency_contact_phone or 'N/A'}
- Parentesco: {self.emergency_contact_relationship or 'N/A'}

{('Titular/Responsable:' + chr(10) + '- Nombre: ' + (self.responsible_name or 'N/A') + chr(10) + '- Teléfono: ' + (self.responsible_phone or 'N/A') + chr(10) + '- Parentesco: ' + (self.responsible_relationship or 'N/A')) if not self.responsible_is_emergency else 'Es Titular (usa mismo contacto de emergencia)'}

Información Académica:
- Programa: {self.program_id.name if self.program_id else 'N/A'}
- Plan: {self.plan_id.name if self.plan_id else 'N/A'}
- Nivel Actual: {self.current_level_id.name if self.current_level_id else 'N/A'}
- Fase Actual: {self.current_phase_id.name if self.current_phase_id else 'N/A'}
- Sede Principal: {self.preferred_campus_id.name if self.preferred_campus_id else 'N/A'}
- Modalidad Preferida: {dict(self._fields['preferred_delivery_mode'].selection).get(self.preferred_delivery_mode, 'N/A') if self.preferred_delivery_mode else 'N/A'}
""",
                }
                partner_vals = self._filter_partner_vals(partner_vals)

                # Manejar ciudad: buscar en res.city o usar texto libre
                if self.city:
                    city_obj = self.env["res.city"].search(
                        [
                            ("name", "=ilike", self.city),
                            (
                                "state_id.country_id",
                                "=",
                                self.country_id.id if self.country_id else False,
                            ),
                        ],
                        limit=1,
                    )

                    if city_obj:
                        partner_vals["city_id"] = city_obj.id
                        partner_vals["city"] = city_obj.name
                    else:
                        # Si no existe en res.city, usar texto libre
                        partner_vals["city"] = self.city

                # Crear o actualizar partner
                if not self.partner_id:
                    partner = self.env["res.partner"].sudo().create(partner_vals)
                    self.partner_id = partner
                else:
                    # Actualizar partner existente con toda la información
                    self.partner_id.sudo().write(partner_vals)

                # Obtener grupos
                portal_group = self.env.ref("base.group_portal")
                student_group = self.env.ref(
                    "benglish_student_portal.group_benglish_student",
                    raise_if_not_found=False,
                )
                groups_ids = [portal_group.id] + (
                    [student_group.id] if student_group else []
                )

                # Crear usuario
                password = normalized_document
                user = (
                    self.env["res.users"]
                    .with_context(no_reset_password=True)
                    .sudo()
                    .create(
                        {
                            "name": self.name,
                            "login": normalized_document,  # Login es el número de identificación
                            "email": self.email,
                            "partner_id": self.partner_id.id,
                            "groups_id": [(6, 0, groups_ids)],
                            "active": True,
                            "password": password,  # Password es el número de identificación
                        }
                    )
                )

                self.user_id = user

                return {
                    "success": True,
                    "message": _("Usuario creado exitosamente"),
                    "user_id": user.id,
                    "login": normalized_document,  # Retorna el número de identificación
                }

        except Exception as e:
            return {
                "success": False,
                "message": _("Error al crear usuario: %s") % str(e),
                "code": "error",
            }

    def action_create_portal_user(self):
        """
        Crea un usuario de portal para el/los estudiante(s) seleccionado(s).
        Soporta múltiples estudiantes (batch).
        """
        # Si es un solo estudiante, mostrar mensaje directo
        if len(self) == 1:
            result = self._create_single_portal_user()
            if result["success"]:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Usuario de portal creado"),
                        "message": _("Se creó el usuario con número de identificación: %s\nPassword inicial: %s")
                        % (result["login"], result["login"]),
                        "type": "success",
                        "sticky": True,
                    },
                }
            else:
                raise UserError(result["message"])

        # Si son múltiples estudiantes, abrir wizard de resultados
        results = {"created": [], "skipped": [], "failed": []}

        for student in self:
            result = student._create_single_portal_user()
            if result["success"]:
                results["created"].append(
                    {
                        "student_name": student.name,
                        "student_code": student.code,
                        "login": result["login"],
                    }
                )
            elif result.get("code") == "already_exists":
                results["skipped"].append(
                    {
                        "student_name": student.name,
                        "student_code": student.code,
                        "reason": result["message"],
                    }
                )
            else:
                results["failed"].append(
                    {
                        "student_name": student.name,
                        "student_code": student.code,
                        "reason": result["message"],
                    }
                )

        # Crear wizard con resultados
        wizard = self.env["benglish.portal.user.creation.wizard"].create(
            {
                "total_selected": len(self),
                "created_count": len(results["created"]),
                "skipped_count": len(results["skipped"]),
                "failed_count": len(results["failed"]),
                "created_details": (
                    "\n".join(
                        [
                            f"- {r['student_code']}: {r['student_name']} (Login: {r['login']})"
                            for r in results["created"]
                        ]
                    )
                    if results["created"]
                    else "Ninguno"
                ),
                "skipped_details": (
                    "\n".join(
                        [
                            f"- {r['student_code']}: {r['student_name']} - {r['reason']}"
                            for r in results["skipped"]
                        ]
                    )
                    if results["skipped"]
                    else "Ninguno"
                ),
                "failed_details": (
                    "\n".join(
                        [
                            f"- {r['student_code']}: {r['student_name']} - {r['reason']}"
                            for r in results["failed"]
                        ]
                    )
                    if results["failed"]
                    else "Ninguno"
                ),
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("Resultado de Creación de Usuarios Portal"),
            "res_model": "benglish.portal.user.creation.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_fix_portal_access(self):
        """Reasigna los grupos de portal al usuario vinculado."""
        self.ensure_one()
        if not self.user_id:
            raise UserError(_("Este estudiante no tiene un usuario asignado."))

        portal_group = self.env.ref("base.group_portal")
        student_group = self.env.ref(
            "benglish_student_portal.group_benglish_student", raise_if_not_found=False
        )
        groups_ids = [portal_group.id] + ([student_group.id] if student_group else [])

        self.user_id.sudo().write(
            {
                "groups_id": [(6, 0, groups_ids)],
                "active": True,
            }
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Acceso de portal corregido"),
                "message": _("Se reasignaron los permisos de portal."),
                "type": "success",
                "sticky": False,
            },
        }

    def action_sync_to_partner(self):
        """
        Sincroniza manualmente la información del estudiante al contacto (res.partner).
        Útil para actualizar partners existentes con datos completos del estudiante.
        """
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("Este estudiante no tiene un contacto asociado."))

        # Calcular tipo de documento
        # PRIORIDAD: usar el tipo de documento del estudiante si existe,
        # sino calcular según edad
        identification_type_id = False
        if self.id_type_id:
            # Usar el tipo de documento seleccionado en el estudiante
            identification_type_id = self.id_type_id.id
        elif self.birth_date:
            # Fallback: calcular según edad si no hay tipo de documento
            from datetime import date

            today = date.today()
            age = (
                today.year
                - self.birth_date.year
                - (
                    (today.month, today.day)
                    < (self.birth_date.month, self.birth_date.day)
                )
            )

            # Buscar tipo de documento según edad
            IdentificationType = self.env["l10n_latam.identification.type"]
            if age >= 18:
                id_type = IdentificationType.search(
                    [("name", "=", "Cedula de ciudadania")], limit=1
                )
            else:
                id_type = IdentificationType.search(
                    [("name", "=", "Tarjeta de identidad")], limit=1
                )

            if id_type:
                identification_type_id = id_type.id

        # Mapear género del estudiante al formato de res.partner (OX)
        # Estudiante: male/female/other → Partner OX: masculino/femenino
        genero_partner = False
        if self.gender == "male":
            genero_partner = "masculino"
        elif self.gender == "female":
            genero_partner = "femenino"
        # Si es 'other', dejar en False (no hay equivalente directo en OX)

        # Preparar valores para actualizar
        partner_vals = {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "mobile": self.mobile,
            # Campos de nombre desagregados (extensión colombiana OX)
            "primer_nombre": self.first_name,
            "otros_nombres": self.second_name,
            "primer_apellido": self.first_last_name,
            "segundo_apellido": self.second_last_name,
            # Documento de identidad
            "ref": self.student_id_number or False,  # Campo estándar de identificación
            "vat": self.student_id_number,  # Campo NIT/VAT
            "l10n_latam_identification_type_id": identification_type_id,
            # Información personal adicional (campos OX)
            "fecha_nacimiento": self.birth_date,  # Fecha de nacimiento (OX)
            "genero": genero_partner,  # Género (OX)
            "sexo_biologico": genero_partner,  # Sexo biológico (OX)
            # Dirección y ubicación
            "street": self.address,  # Dirección
            "country_id": self.country_id.id if self.country_id else False,
            # Imagen
            "image_1920": self.image_1920,  # Foto
            # Asegurar que sea estudiante
            "is_student": True,
            "is_company": False,
            "company_type": "person",
        }
        partner_vals = self._filter_partner_vals(partner_vals)

        # Manejar ciudad: buscar en res.city o usar texto libre
        if self.city:
            city_obj = self.env["res.city"].search(
                [
                    ("name", "=ilike", self.city),
                    (
                        "state_id.country_id",
                        "=",
                        self.country_id.id if self.country_id else False,
                    ),
                ],
                limit=1,
            )

            if city_obj:
                partner_vals["city_id"] = city_obj.id
                partner_vals["city"] = city_obj.name
            else:
                # Si no existe en res.city, usar texto libre
                partner_vals["city"] = self.city

        # Actualizar el partner
        self.partner_id.sudo().write(partner_vals)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Contacto actualizado"),
                "message": _(
                    "Se sincronizó la información del estudiante al contacto correctamente."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_set_active(self):
        """Activa al estudiante"""
        return self.with_context(
            default_estado_nuevo="active"
        ).action_open_lifecycle_state_wizard()

    def action_set_inactive(self):
        """Inactiva al estudiante"""
        return self.with_context(
            default_estado_nuevo="inactive"
        ).action_open_lifecycle_state_wizard()

    def action_set_withdrawn(self):
        """Marca al estudiante como retirado"""
        return self.with_context(
            default_estado_nuevo="withdrawn"
        ).action_open_lifecycle_state_wizard()

    def action_set_graduated(self):
        """Marca al estudiante como graduado"""
        return self.with_context(
            default_estado_nuevo="graduated"
        ).action_open_lifecycle_state_wizard()

    # MÉTODOS DE ESTADO DE PERFIL

    def _get_effective_profile_state(self):
        """Retorna el estado de perfil efectivo (asignado o por defecto)."""
        self.ensure_one()
        profile = self.profile_state_id
        lifecycle_profile = self._get_profile_state_from_lifecycle()
        if lifecycle_profile:
            profile = lifecycle_profile
        if not profile:
            profile = self.env["benglish.student.profile.state"].get_default_state()
        return profile

    def _get_profile_state_from_lifecycle(self):
        """Obtiene el estado de perfil asociado al estado de ciclo de vida."""
        self.ensure_one()
        Transition = self.env["benglish.student.lifecycle.transition"].sudo()
        if not self.state:
            return self.env["benglish.student.profile.state"].browse()
        transition = Transition.search(
            [
                ("state_to", "=", self.state),
                ("active", "=", True),
                ("profile_state_id", "!=", False),
            ],
            order="sequence asc, id asc",
            limit=1,
        )
        return (
            transition.profile_state_id
            if transition
            else self.env["benglish.student.profile.state"].browse()
        )

    def can_schedule_classes(self):
        """
        Verifica si el estudiante puede agendar clases según su estado de perfil.

        Returns:
            tuple: (puede: bool, mensaje: str)
        """
        self.ensure_one()
        profile = self._get_effective_profile_state()
        if not profile:
            return (True, "")

        if not profile.can_schedule:
            return (
                False,
                profile.student_message
                or "No tiene permiso para agendar clases en su estado actual.",
            )
        return (True, "")

    def can_attend_classes(self):
        """
        Verifica si el estudiante puede asistir a clases según su estado de perfil.

        Returns:
            tuple: (puede: bool, mensaje: str)
        """
        self.ensure_one()
        profile = self._get_effective_profile_state()
        if not profile:
            return (True, "")

        if not profile.can_attend:
            return (
                False,
                profile.student_message
                or "No tiene permiso para asistir a clases en su estado actual.",
            )
        return (True, "")

    def can_use_apps(self):
        """
        Verifica si el estudiante puede usar aplicaciones según su estado de perfil.

        Returns:
            tuple: (puede: bool, mensaje: str)
        """
        self.ensure_one()
        profile = self._get_effective_profile_state()
        if not profile:
            return (True, "")

        if not profile.can_use_apps:
            return (
                False,
                profile.student_message
                or "No tiene acceso a aplicaciones en su estado actual.",
            )
        return (True, "")

    def can_request_freeze(self):
        """
        Verifica si el estudiante puede solicitar congelamiento según su estado de perfil
        y la configuración del plan.

        Returns:
            tuple: (puede: bool, mensaje: str)
        """
        self.ensure_one()

        # Verificar estado de perfil
        profile = self._get_effective_profile_state()
        if profile and not profile.can_request_freeze:
            return (
                False,
                profile.student_message
                or "No puede solicitar congelamiento en su estado actual.",
            )

        # Verificar si tiene plan asignado
        if not self.plan_id:
            return (False, "No tiene un plan asignado.")

        # Verificar configuración del plan
        FreezeConfig = self.env["benglish.plan.freeze.config"]
        config = FreezeConfig.get_config_for_plan(self.plan_id)

        if not config:
            return (False, "No hay configuración de congelamiento para su plan.")

        if not config.permite_congelamiento:
            return (False, "Su plan no permite solicitar congelamiento.")

        # Verificar si tiene días disponibles
        if self.dias_congelamiento_disponibles < config.min_dias_congelamiento:
            return (
                False,
                f"No tiene suficientes días disponibles. "
                f"Mínimo requerido: {config.min_dias_congelamiento}.",
            )

        return (
            True,
            f"Puede solicitar de {config.min_dias_congelamiento} a "
            f"{min(config.max_dias_congelamiento, self.dias_congelamiento_disponibles)} días.",
        )

    def get_profile_permissions_summary(self):
        """
        Obtiene un resumen de los permisos del estudiante según su estado de perfil.

        Returns:
            dict: Diccionario con los permisos y estados
        """
        self.ensure_one()

        state = self._get_effective_profile_state()
        if not state:
            return {
                "estado": "Sin estado asignado",
                "puede_agendar": True,
                "puede_asistir": True,
                "puede_usar_apps": True,
                "puede_congelar": True,
                "bloqueado": False,
                "mensaje": "",
            }

        return {
            "estado": state.name,
            "puede_agendar": state.can_schedule,
            "puede_asistir": state.can_attend,
            "puede_usar_apps": state.can_use_apps,
            "puede_ver_historial": state.can_view_history,
            "puede_congelar": state.can_request_freeze,
            "bloqueado": state.blocks_enrollment,
            "mensaje": state.student_message or "",
            "color": state.color,
            "icon": state.icon,
        }

    def portal_get_access_rules(self):
        """Reglas de acceso del portal basadas en el estado de perfil."""
        self.ensure_one()

        profile = self._get_effective_profile_state()
        portal_visible = profile.portal_visible if profile else True
        allow_login = bool(self.active) and portal_visible

        if profile:
            capabilities = profile.get_permissions_summary()
        else:
            capabilities = {
                "can_schedule": True,
                "can_attend": True,
                "can_use_apps": True,
                "can_view_history": True,
                "can_request_freeze": True,
                "blocks_enrollment": False,
            }

        message = ""
        if profile and profile.portal_visible and profile.student_message:
            message = profile.student_message
        elif self.motivo_bloqueo:
            message = self.motivo_bloqueo

        limited = any(
            not bool(capabilities.get(flag, True))
            for flag in [
                "can_schedule",
                "can_attend",
                "can_use_apps",
                "can_view_history",
                "can_request_freeze",
            ]
        )

        if not allow_login:
            level = "blocked"
        elif limited:
            level = "limited"
        else:
            level = "full"

        rules = {
            "allow_login": allow_login,
            "level": level,
            "message": message,
            "state": self.state,
            "profile_state": {
                "id": profile.id if profile else False,
                "name": profile.name if profile else "",
                "code": profile.code if profile else "",
                "portal_visible": portal_visible,
            },
            "capabilities": {
                "can_schedule": bool(capabilities.get("can_schedule", True)),
                "can_attend": bool(capabilities.get("can_attend", True)),
                "can_use_apps": bool(capabilities.get("can_use_apps", True)),
                "can_view_history": bool(capabilities.get("can_view_history", True)),
                "can_request_freeze": bool(
                    capabilities.get("can_request_freeze", True)
                ),
                "blocks_enrollment": bool(capabilities.get("blocks_enrollment", False)),
            },
        }

        _logger.debug(
            "Portal access rules for student %s (state=%s, profile=%s): %s",
            self.id,
            self.state,
            profile.code if profile else "none",
            rules,
        )
        return rules

    def action_view_freeze_periods(self):
        """Abre la vista de periodos de congelamiento del estudiante."""
        self.ensure_one()
        return {
            "name": _("Congelamientos de %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.student.freeze.period",
            "view_mode": "list,form",
            "domain": [("student_id", "=", self.id)],
            "context": {
                "default_student_id": self.id,
            },
        }

    def action_request_freeze(self):
        """Abre el wizard para solicitar congelamiento."""
        self.ensure_one()

        # Validar si puede solicitar
        puede, mensaje = self.can_request_freeze()
        if not puede:
            raise UserError(mensaje)

        return {
            "name": _("Solicitar Congelamiento"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.student.freeze.period",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_student_id": self.id,
                "default_enrollment_id": (
                    self.active_enrollment_ids[0].id
                    if self.active_enrollment_ids
                    else False
                ),
            },
        }

    def action_open_freeze_request_wizard(self):
        """Return an action that opens the freeze request wizard with proper defaults.

        This server-side action sets `default_student_id` (and `default_enrollment_id` if
        available) in the context to avoid referencing `active_id` from XML views.
        """
        self.ensure_one()

        # Validate permission to request freeze
        puede, mensaje = self.can_request_freeze()
        if not puede:
            raise UserError(mensaje)

        enrollment_id = (
            self.active_enrollment_ids[0].id if self.active_enrollment_ids else False
        )

        return {
            "name": _("Solicitar Congelamiento"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.freeze.request.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_student_id": self.id,
                "default_enrollment_id": enrollment_id,
            },
        }

    def can_enroll_in_subject(self, subject_id):
        """
        Valida si el estudiante puede matricularse en una asignatura específica.
        Verifica que cumpla con todos los prerrequisitos.

        :param subject_id: ID de la asignatura
        :return: (bool, str) - (puede_matricular, mensaje)
        """
        self.ensure_one()
        subject = self.env["benglish.subject"].browse(subject_id)

        if not subject.exists():
            return False, _("La asignatura no existe")

        # Verificar prerrequisitos
        if subject.prerequisite_ids:
            approved_subjects = self.approved_subject_ids
            missing_prerequisites = subject.prerequisite_ids - approved_subjects

            if missing_prerequisites:
                missing_names = ", ".join(missing_prerequisites.mapped("name"))
                return False, _("Faltan prerrequisitos: %s") % missing_names

        return True, _("El estudiante cumple con los requisitos")

    @api.model
    def create(self, vals):
        """Sobrescribe create para auto-generar código si no se proporciona y crear/vincular partner"""
        vals = self._apply_virtual_campus_default(vals)
        if not vals.get("code"):
            # Generar código automático: EST-YYYY-NNNN
            year = fields.Date.context_today(self).year
            sequence = (
                self.env["ir.sequence"].next_by_code("benglish.student") or "0001"
            )
            vals["code"] = f"EST-{year}-{sequence}"

        # Calcular nombre completo desde campos desagregados para uso en partner
        name_parts = []
        if vals.get("first_name"):
            name_parts.append(vals["first_name"])
        if vals.get("second_name"):
            name_parts.append(vals["second_name"])
        if vals.get("first_last_name"):
            name_parts.append(vals["first_last_name"])
        if vals.get("second_last_name"):
            name_parts.append(vals["second_last_name"])
        computed_name = " ".join(name_parts) if name_parts else "Estudiante sin nombre"

        # Crear partner automáticamente si no existe
        if not vals.get("partner_id"):
            # Calcular tipo de documento
            # PRIORIDAD: usar el tipo de documento proporcionado en vals,
            # sino calcular según edad
            identification_type_id = False
            if vals.get("id_type_id"):
                # Usar el tipo de documento proporcionado
                identification_type_id = vals.get("id_type_id")
            elif vals.get("birth_date"):
                # Fallback: calcular según edad si no hay tipo de documento
                from datetime import date

                birth_date = fields.Date.from_string(vals.get("birth_date"))
                today = date.today()
                age = (
                    today.year
                    - birth_date.year
                    - ((today.month, today.day) < (birth_date.month, birth_date.day))
                )

                # Buscar tipo de documento según edad
                IdentificationType = self.env["l10n_latam.identification.type"]
                if age >= 18:
                    # Cedula de ciudadania
                    id_type = IdentificationType.search(
                        [("name", "=", "Cedula de ciudadania")], limit=1
                    )
                else:
                    # Tarjeta de identidad
                    id_type = IdentificationType.search(
                        [("name", "=", "Tarjeta de identidad")], limit=1
                    )

                if id_type:
                    identification_type_id = id_type.id

            # Mapear género del estudiante al formato de res.partner (OX)
            # Estudiante: male/female/other → Partner OX: masculino/femenino
            genero_partner = False
            if vals.get("gender") == "male":
                genero_partner = "masculino"
            elif vals.get("gender") == "female":
                genero_partner = "femenino"
            # Si es 'other', dejar en False (no hay equivalente directo en OX)

            partner_vals = {
                "name": computed_name,
                "email": vals.get("email"),
                "phone": vals.get("phone"),
                "mobile": vals.get("mobile"),
                "street": vals.get("address"),
                "country_id": vals.get("country_id"),
                "image_1920": vals.get("image_1920"),  # Foto del estudiante
                # Campos de nombre desagregados (extensión colombiana OX)
                "primer_nombre": vals.get("first_name"),
                "otros_nombres": vals.get("second_name"),
                "primer_apellido": vals.get("first_last_name"),
                "segundo_apellido": vals.get("second_last_name"),
                # Documento de identidad
                "ref": vals.get("student_id_number")
                or "",  # Campo estándar de identificación
                "vat": vals.get("student_id_number"),  # Campo NIT/VAT
                "l10n_latam_identification_type_id": identification_type_id,
                # Información personal adicional (campos OX)
                "fecha_nacimiento": vals.get("birth_date"),  # Fecha de nacimiento (OX)
                "genero": genero_partner,  # Género (OX)
                "sexo_biologico": genero_partner,  # Sexo biológico (OX)
                # Tipo de persona
                "is_company": False,
                "company_type": "person",
                "comment": f"""Información del Estudiante:
- Código: {vals.get("code", "N/A")}
- Documento: {vals.get("student_id_number") or "N/A"}

Contacto de Emergencia:
- Nombre: {vals.get("emergency_contact_name") or "N/A"}
- Teléfono: {vals.get("emergency_contact_phone") or "N/A"}
- Parentesco: {vals.get("emergency_contact_relationship") or "N/A"}

Contacto creado automáticamente desde el sistema académico.
""",
            }

            # Manejar ciudad: buscar en res.city o usar texto libre
            if vals.get("city"):
                city_obj = self.env["res.city"].search(
                    [
                        ("name", "=ilike", vals["city"]),
                        ("state_id.country_id", "=", vals.get("country_id", False)),
                    ],
                    limit=1,
                )

                if city_obj:
                    partner_vals["city_id"] = city_obj.id
                    partner_vals["city"] = city_obj.name
                else:
                    # Si no existe en res.city, usar texto libre
                    partner_vals["city"] = vals["city"]

            # Limpiar SOLO valores None (NO eliminar strings vacíos válidos como '')
            partner_vals = {k: v for k, v in partner_vals.items() if v is not None}
            partner_vals = self._filter_partner_vals(partner_vals)

            try:
                partner = self.env["res.partner"].sudo().create(partner_vals)
                vals["partner_id"] = partner.id
                _logger.info(
                    f"✓ Partner creado automáticamente ID={partner.id} para estudiante {computed_name}"
                )
            except Exception as e:
                _logger.warning(f"No se pudo crear partner automáticamente: {e}")

        result = super(Student, self).create(vals)

        # Marcar el partner como estudiante si existe
        if result.partner_id:
            result.partner_id.sudo().write({"is_student": True})
            _logger.info(
                f"✓ Partner ID={result.partner_id.id} marcado como is_student=True"
            )

        # Mejora 1: Registrar estado inicial si se asignó
        if vals.get("profile_state_id"):
            estado_nuevo = self.env["benglish.student.profile.state"].browse(
                vals["profile_state_id"]
            )
            self.env["benglish.student.state.history"].registrar_cambio(
                student=result,
                estado_anterior=False,
                estado_nuevo=estado_nuevo,
                motivo="Asignación inicial al crear estudiante",
                origen="manual",
            )

        if vals.get("state") or result.state:
            self.env["benglish.student.lifecycle.history"].registrar_cambio(
                student=result,
                estado_anterior=False,
                estado_nuevo=result.state,
                motivo="Asignación inicial al crear estudiante",
                origen=self.env.context.get("origen_cambio_estado") or "manual",
            )

        return result

    def write(self, vals):
        """
        Sobrescribe write para registrar cambios de estado automáticamente.
        Mejora 1: Historial de cambios de estado del estudiante.
        Mejora 5: Validación de transiciones permitidas.
        """
        vals = dict(vals or {})
        vals = self._apply_virtual_campus_default(vals)
        profile_changes = {}
        lifecycle_changes = {}
        edit_changes = {}

        if vals.get("state") == "withdrawn" and not vals.get("withdrawal_date"):
            vals["withdrawal_date"] = fields.Date.context_today(self)
        if vals.get("state") == "active" and "active" not in vals:
            vals["active"] = True

        track_fields = []
        if not self.env.context.get("skip_edit_history"):
            for field_name in vals.keys():
                if field_name in self._EDIT_HISTORY_EXCLUDED_FIELDS:
                    continue
                field = self._fields.get(field_name)
                if not field or field.type in ("one2many", "many2many"):
                    continue
                track_fields.append(field_name)

        if track_fields:
            for student in self:
                edit_changes[student.id] = {
                    field_name: student[field_name] for field_name in track_fields
                }

        if "profile_state_id" in vals:
            nuevo_estado_id = vals.get("profile_state_id")
            origen_perfil = (
                self.env.context.get("origen_cambio_perfil")
                or self.env.context.get("origen_cambio_estado")
                or "manual"
            )
            skip_profile_transition = self.env.context.get(
                "skip_profile_transition_validation"
            )

            for student in self:
                estado_anterior = student.profile_state_id
                estado_nuevo = (
                    self.env["benglish.student.profile.state"].browse(nuevo_estado_id)
                    if nuevo_estado_id
                    else False
                )

                if estado_anterior.id != nuevo_estado_id:
                    transicion = False
                    if estado_anterior and estado_nuevo and not skip_profile_transition:
                        Transition = self.env["benglish.student.state.transition"]
                        valida, mensaje, transicion = Transition.validar_transicion(
                            estado_anterior.id, estado_nuevo.id
                        )

                        if not valida:
                            raise ValidationError(
                                _(
                                    "Transición de estado no permitida:\n"
                                    "De: %s\n"
                                    "A: %s\n\n"
                                    "%s"
                                )
                                % (estado_anterior.name, estado_nuevo.name, mensaje)
                            )

                        if transicion and transicion.requiere_motivo:
                            motivo = vals.get("motivo_bloqueo") or self.env.context.get(
                                "motivo_cambio_estado"
                            )
                            if not motivo:
                                raise ValidationError(
                                    _(
                                        "Esta transición de estado requiere indicar un motivo.\n"
                                        'Por favor complete el campo "Motivo de Bloqueo" o use el '
                                        "wizard de cambio de estado."
                                    )
                                )

                    profile_changes[student.id] = {
                        "estado_anterior": estado_anterior,
                        "estado_nuevo": estado_nuevo,
                        "motivo": vals.get("motivo_bloqueo")
                        or self.env.context.get("motivo_cambio_estado"),
                        "origen": origen_perfil,
                        "transicion": transicion,
                    }

        if "state" in vals:
            nuevo_estado = vals.get("state")
            origen_estado = self.env.context.get("origen_cambio_estado") or "manual"

            for student in self:
                estado_anterior = student.state
                if estado_anterior != nuevo_estado:
                    Transition = self.env["benglish.student.lifecycle.transition"]
                    valida, mensaje, transicion = Transition.validar_transicion(
                        estado_anterior, nuevo_estado
                    )
                    if not valida:
                        selection = self._fields["state"].selection
                        selection = (
                            selection(self) if callable(selection) else selection
                        )
                        label_map = dict(selection)
                        raise ValidationError(
                            _(
                                "Transición de estado no permitida:\n"
                                "De: %s\n"
                                "A: %s\n\n"
                                "%s"
                            )
                            % (
                                label_map.get(estado_anterior, estado_anterior),
                                label_map.get(nuevo_estado, nuevo_estado),
                                mensaje,
                            )
                        )

                    if transicion and transicion.requires_reason:
                        motivo = vals.get("withdrawal_reason") or self.env.context.get(
                            "motivo_cambio_estado"
                        )
                        if not motivo:
                            raise ValidationError(
                                _(
                                    "Esta transición de estado requiere indicar un motivo.\n"
                                    "Use el wizard de cambio de estado para continuar."
                                )
                            )

                    lifecycle_changes[student.id] = {
                        "estado_anterior": estado_anterior,
                        "estado_nuevo": nuevo_estado,
                        "motivo": vals.get("withdrawal_reason")
                        or self.env.context.get("motivo_cambio_estado"),
                        "origen": origen_estado,
                        "transicion": transicion,
                    }

        result = super(Student, self).write(vals)

        if profile_changes:
            History = self.env["benglish.student.state.history"]
            for student in self:
                cambio = profile_changes.get(student.id)
                if not cambio:
                    continue
                History.registrar_cambio(
                    student=student,
                    estado_anterior=cambio["estado_anterior"],
                    estado_nuevo=cambio["estado_nuevo"],
                    motivo=cambio["motivo"],
                    origen=cambio["origen"],
                    transicion=cambio["transicion"],
                )

        if lifecycle_changes:
            History = self.env["benglish.student.lifecycle.history"]
            for student in self:
                cambio = lifecycle_changes.get(student.id)
                if not cambio:
                    continue
                History.registrar_cambio(
                    student=student,
                    estado_anterior=cambio["estado_anterior"],
                    estado_nuevo=cambio["estado_nuevo"],
                    motivo=cambio["motivo"],
                    origen=cambio["origen"],
                    transicion=cambio["transicion"],
                )

            if not self.env.context.get("skip_profile_state_sync"):
                for student in self:
                    cambio = lifecycle_changes.get(student.id)
                    if not cambio:
                        continue
                    transicion = cambio.get("transicion")
                    target_profile = (
                        transicion.profile_state_id if transicion else False
                    )
                    if not target_profile:
                        continue
                    if student.profile_state_id == target_profile:
                        continue
                    ctx = dict(
                        self.env.context,
                        skip_profile_state_sync=True,
                        skip_profile_transition_validation=True,
                        origen_cambio_perfil="automatico",
                    )
                    motivo = cambio.get("motivo")
                    if motivo:
                        ctx["motivo_cambio_estado"] = motivo
                    vals_profile = {"profile_state_id": target_profile.id}
                    if motivo:
                        vals_profile["motivo_bloqueo"] = motivo
                    student.with_context(ctx).write(vals_profile)

        if edit_changes:
            EditHistory = self.env["benglish.student.edit.history"]
            for student in self:
                old_values = edit_changes.get(student.id)
                if not old_values:
                    continue
                line_vals = []
                for field_name, old_value in old_values.items():
                    field = self._fields.get(field_name)
                    new_value = student[field_name]
                    if not self._values_differ(field, old_value, new_value):
                        continue
                    line_vals.append(
                        {
                            "field_name": field_name,
                            "field_label": field.string or field_name,
                            "old_value": self._format_history_value(field, old_value),
                            "new_value": self._format_history_value(field, new_value),
                        }
                    )
                if line_vals:
                    EditHistory.create(
                        {
                            "student_id": student.id,
                            "origin": self.env.context.get("origen_edicion", "manual"),
                            "note": self.env.context.get("nota_edicion"),
                            "line_ids": [(0, 0, line) for line in line_vals],
                        }
                    )

        return result

    @api.model
    def create(self, vals):
        """Override create para inicializar tracking de asignaturas si hay plan"""
        vals = self._apply_virtual_campus_default(vals)
        student = super(Student, self).create(vals)

        # Si se crea con un plan, inicializar tracking
        if student.plan_id:
            self.env["benglish.subject.session.tracking"].create_tracking_for_student(
                student.id
            )

        return student

    def write(self, vals):
        """Override write para detectar cambios de plan y crear tracking"""
        vals = self._apply_virtual_campus_default(vals)
        # Detectar si se está cambiando el plan
        plan_changed = "plan_id" in vals and vals.get("plan_id")

        result = super(Student, self).write(vals)

        # Si el plan cambió, crear/actualizar tracking
        if plan_changed:
            for student in self:
                if student.plan_id:
                    self.env[
                        "benglish.subject.session.tracking"
                    ].create_tracking_for_student(student.id)

        return result

    def _format_history_value(self, field, value):
        """Formatea valores para el historial de edición."""
        if field.type == "many2one":
            return value.display_name if value else ""
        if field.type in ("one2many", "many2many"):
            return ", ".join(value.mapped("display_name")) if value else ""
        if field.type == "boolean":
            return _("Si") if value else _("No")
        if field.type == "selection":
            selection = (
                field.selection(self) if callable(field.selection) else field.selection
            )
            return dict(selection).get(value, value or "")
        if field.type == "date":
            return fields.Date.to_string(value) if value else ""
        if field.type == "datetime":
            return fields.Datetime.to_string(value) if value else ""
        return str(value) if value not in (False, None) else ""

    def _values_differ(self, field, old_value, new_value):
        if field.type == "many2one":
            return (old_value.id if old_value else False) != (
                new_value.id if new_value else False
            )
        if field.type in ("one2many", "many2many"):
            return set(old_value.ids) != set(new_value.ids)
        return old_value != new_value

    def action_cambiar_estado(self):
        """Abre el wizard para cambiar el estado del perfil."""
        self.ensure_one()
        return {
            "name": _("Cambiar Estado de Perfil"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.student.change.state.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_student_id": self.id,
                "default_estado_actual_id": (
                    self.profile_state_id.id if self.profile_state_id else False
                ),
            },
        }

    def action_open_lifecycle_state_wizard(self):
        """Abre el wizard para cambiar el estado del estudiante."""
        self.ensure_one()
        return {
            "name": _("Cambiar Estado del Estudiante"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.student.change.lifecycle.state.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_student_id": self.id,
                "default_estado_actual": self.state,
                "default_estado_nuevo": self.env.context.get("default_estado_nuevo"),
            },
        }

    def action_force_delete(self):
        """
        Elimina definitivamente al estudiante y todas sus matrículas usando SQL directo.
        ADVERTENCIA: Esto elimina PERMANENTEMENTE todo el historial del estudiante.
        Solo usar en casos excepcionales (datos de prueba, duplicados, etc).
        """
        user_ids = self.mapped("user_id").ids
        for student in self:
            if student.enrollment_ids:
                # Usar SQL directo para bypasear todas las restricciones FK y validaciones
                enrollment_ids = tuple(student.enrollment_ids.ids)
                if enrollment_ids:
                    # Eliminar matrículas con SQL directo
                    self.env.cr.execute(
                        "DELETE FROM benglish_enrollment WHERE id IN %s",
                        (enrollment_ids,),
                    )
                    # Invalidar cache
                    self.env["benglish.enrollment"]._invalidate_cache()

            # Eliminar estudiante con SQL directo
            self.env.cr.execute(
                "DELETE FROM benglish_student WHERE id = %s", (student.id,)
            )
            # Invalidar cache
            self._invalidate_cache()

        if user_ids:
            self.env.cr.execute(
                "UPDATE benglish_agenda_log SET user_id = NULL WHERE user_id IN %s",
                (tuple(user_ids),),
            )
            self.env["res.users"].sudo().browse(user_ids).unlink()

        return {"type": "ir.actions.act_window_close"}

    def action_initialize_session_tracking(self):
        """
        Inicializa el tracking de sesiones para el estudiante.
        Crea registros para TODAS las asignaturas del plan.
        """
        self.ensure_one()

        if not self.plan_id:
            raise UserError(_("El estudiante no tiene un plan asignado."))

        Tracking = self.env["benglish.subject.session.tracking"]

        # Verificar si ya tiene tracking
        existing = Tracking.search([("student_id", "=", self.id)])
        if existing:
            raise UserError(
                _(
                    "El estudiante ya tiene %d registros de tracking.\n\n"
                    "Si necesita recrearlos, elimine primero los existentes."
                )
                % len(existing)
            )

        # Crear tracking
        created = Tracking.create_tracking_for_student(self.id)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Tracking Inicializado"),
                "message": _(
                    "Se crearon %d registros de tracking para las asignaturas del plan %s"
                )
                % (len(created), self.plan_id.name),
                "type": "success",
                "sticky": False,
            },
        }

    def unlink(self):
        """
        BLOQUEADO: No se permite eliminar estudiantes con matrículas por integridad de datos.

        Alternativas:
        - Para dar de baja: usar botón "Retirar" (archiva al estudiante preservando historial)
        - Para eliminar definitivamente: usar botón "Eliminar Definitivamente" (solo administradores)

        Esta restricción evita pérdida de datos académicos y garantiza trazabilidad.
        """
        students_with_enrollments = self.filtered(lambda s: s.enrollment_ids)
        students_without_enrollments = self - students_with_enrollments

        if students_with_enrollments:
            raise ValidationError(
                _(
                    "No se pueden eliminar estudiantes con matrículas registradas.\n\n"
                    "Estudiantes bloqueados: %s\n\n"
                    "Opciones:\n"
                    '1. Use el botón "Retirar" para archivar al estudiante (preserva historial)\n'
                    '2. Use el botón "Eliminar Definitivamente" para borrado permanente (solo administradores)\n\n'
                    "Total de matrículas que se perderían: %d"
                )
                % (
                    ", ".join(students_with_enrollments.mapped("name")),
                    len(students_with_enrollments.mapped("enrollment_ids")),
                )
            )

        # Solo permitir eliminar estudiantes sin matrículas
        return super(Student, students_without_enrollments).unlink()

    def action_recalculate_attendance_kpis(self):
        """
        Recalcula manualmente los KPIs de asistencia del estudiante.
        Útil cuando hay inconsistencias en los datos.
        """
        self._compute_attendance_kpis()

        message = []
        for student in self:
            message.append(
                f"✅ {student.name}:\n"
                f"   • Clases Asistidas: {student.total_classes_attended}\n"
                f"   • Clases Programadas: {student.total_classes_scheduled}\n"
                f"   • Asistencia: {student.average_attendance:.1f}%"
            )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "🔄 KPIs Recalculados",
                "message": "\n\n".join(message),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_generate_historical_progress(self):
        """
        Genera historial académico retroactivo para estudiantes importados.
        Crea registros 'attended' para todas las clases de unidades anteriores
        a la unidad actual del estudiante.
        """
        from datetime import timedelta

        historical_date = fields.Date.today() - timedelta(days=30)
        Subject = self.env["benglish.subject"].sudo()
        History = self.env["benglish.academic.history"].sudo()

        results = []
        total_created = 0

        for student in self:
            # Usar savepoint para que si falla un estudiante, no aborte toda la transacción
            try:
                with self.env.cr.savepoint():
                    active_enrollments = student.enrollment_ids.filtered(
                        lambda e: e.state in ["enrolled", "in_progress"]
                    ).sorted("enrollment_date", reverse=True)

                    if not active_enrollments:
                        results.append("⚠️ %s: Sin matrícula activa" % student.name)
                        continue

                    enrollment = active_enrollments[0]
                    current_level = (
                        enrollment.current_level_id
                    )  # Nivel ACTUAL (no el inicial)
                    program = enrollment.program_id
                    plan = (
                        enrollment.plan_id
                    )  # El plan viene de la matrícula, NO del estudiante

                    if not current_level or not program or not plan:
                        results.append(
                            "⚠️ %s: Sin nivel/programa/plan (Nivel: %s, Programa: %s, Plan: %s)"
                            % (
                                student.name,
                                current_level.name if current_level else "N/A",
                                program.name if program else "N/A",
                                plan.name if plan else "N/A",
                            )
                        )
                        continue

                    current_unit = current_level.max_unit or 0

                    if current_unit <= 1:
                        results.append(
                            "✓ %s: En Unit %d - Sin historial previo"
                            % (student.name, current_unit)
                        )
                        continue

                    previous_units = list(range(1, current_unit))

                    # BUSCAR TODAS las asignaturas de unidades previas (bcheck, bskills, oral_test, etc.)
                    # Incluir:
                    # 1. Asignaturas con unit_number en previous_units (B-checks, B-skills 1-4 únicamente)
                    # 2. Oral Tests cuyo unit_block_end < current_unit (NO incluir el del nivel actual)
                    # NOTA: Para bskills solo generar 1-4 (curriculares), no las extras (5-6-7)
                    subjects_to_complete = Subject.search(
                        [
                            ("program_id", "=", program.id),
                            ("active", "=", True),
                            "|",
                            "&",
                            ("unit_number", "in", previous_units),
                            "|",
                            ("subject_category", "!=", "bskills"),  # Incluir todas las no-bskills
                            "&",
                            ("subject_category", "=", "bskills"),
                            ("bskill_number", "<=", 4),  # Solo bskills 1-4
                            "&",
                            ("subject_category", "=", "oral_test"),
                            (
                                "unit_block_end",
                                "<",
                                current_unit,
                            ),  # MENOR QUE, no menor o igual
                        ]
                    )

                    _logger.info(
                        f"Estudiante {student.name}: Unit actual={current_unit}, "
                        f"Units previas={previous_units}, "
                        f"Asignaturas encontradas={len(subjects_to_complete)}"
                    )

                    if not subjects_to_complete:
                        results.append(
                            "⚠️ %s: No hay asignaturas previas" % student.name
                        )
                        continue

                    existing_history = History.search(
                        [
                            ("student_id", "=", student.id),
                            ("subject_id", "in", subjects_to_complete.ids),
                            ("attendance_status", "=", "attended"),
                        ]
                    )

                    _logger.info(
                        f"Estudiante {student.name}: Historial existente={len(existing_history)} registros"
                    )

                    existing_subject_ids = existing_history.mapped("subject_id").ids
                    subjects_without_history = subjects_to_complete.filtered(
                        lambda s: s.id not in existing_subject_ids
                    )

                    # Buscar matrícula al plan para actualizar progreso
                    plan_enrollment = student.enrollment_ids.filtered(
                        lambda e: e.plan_id == plan
                        and e.state in ["enrolled", "in_progress", "active"]
                    ).sorted("enrollment_date", reverse=True)
                    plan_enrollment = plan_enrollment[0] if plan_enrollment else False

                    Progress = self.env["benglish.enrollment.progress"].sudo()
                    created_count = 0
                    progress_updated = 0

                    # PARTE 1: Crear historial y progreso para asignaturas SIN historial
                    Tracking = self.env["benglish.subject.session.tracking"].sudo()

                    for subject in subjects_without_history:
                        # Crear historial académico
                        History.create(
                            {
                                "student_id": student.id,
                                "subject_id": subject.id,
                                "enrollment_id": False,  # No hay session enrollment para historial retroactivo
                                "program_id": program.id,
                                "plan_id": plan.id if plan else False,
                                "phase_id": (
                                    subject.phase_id.id if subject.phase_id else False
                                ),
                                "level_id": (
                                    subject.level_id.id if subject.level_id else False
                                ),
                                "session_date": historical_date,
                                "attendance_status": "attended",
                                "attended": True,  # ⭐ IMPORTANTE: Marcar campo booleano
                                "attendance_registered_at": fields.Datetime.now(),
                                "created_at": fields.Datetime.now(),
                                "campus_id": (
                                    enrollment.campus_id.id
                                    if enrollment.campus_id
                                    else False
                                ),
                            }
                        )
                        created_count += 1

                        # ⭐ SINCRONIZAR con subject_session_tracking
                        tracking = Tracking.search(
                            [
                                ("student_id", "=", student.id),
                                ("subject_id", "=", subject.id),
                            ],
                            limit=1,
                        )

                        if tracking:
                            # Actualizar tracking existente
                            tracking.with_context(skip_history_sync=True).write(
                                {
                                    "attended": True,
                                    "state": "registered",
                                }
                            )
                            _logger.info(
                                f"[HISTORIAL-RETROACTIVO] Tracking actualizado: "
                                f"{student.name} - {subject.code or subject.name}"
                            )
                        else:
                            # Crear nuevo tracking si no existe
                            Tracking.create(
                                {
                                    "student_id": student.id,
                                    "subject_id": subject.id,
                                    "phase_id": (
                                        subject.phase_id.id
                                        if subject.phase_id
                                        else False
                                    ),
                                    "level_id": (
                                        subject.level_id.id
                                        if subject.level_id
                                        else False
                                    ),
                                    "attended": True,
                                    "state": "registered",
                                }
                            )
                            _logger.info(
                                f"[HISTORIAL-RETROACTIVO] Tracking creado: "
                                f"{student.name} - {subject.code or subject.name}"
                            )

                    # PARTE 2: Actualizar progreso académico para TODAS las asignaturas (con o sin historial previo)
                    if plan_enrollment:
                        for subject in subjects_to_complete:
                            existing_progress = Progress.search(
                                [
                                    ("enrollment_id", "=", plan_enrollment.id),
                                    ("subject_id", "=", subject.id),
                                ],
                                limit=1,
                            )

                            if existing_progress:
                                # Actualizar si NO está completado
                                if existing_progress.state != "completed":
                                    existing_progress.write(
                                        {
                                            "state": "completed",
                                            "start_date": historical_date,
                                            "end_date": historical_date,
                                        }
                                    )
                                    progress_updated += 1
                            else:
                                # Crear nuevo registro de progreso
                                Progress.create(
                                    {
                                        "enrollment_id": plan_enrollment.id,
                                        "subject_id": subject.id,
                                        "state": "completed",
                                        "start_date": historical_date,
                                        "end_date": historical_date,
                                    }
                                )
                                progress_updated += 1

                    # ⭐ PARTE 3: Sincronizar tracking para asignaturas que YA tenían historial
                    # (solo actualizar las que NO se procesaron en PARTE 1)
                    subjects_with_existing_history = subjects_to_complete.filtered(
                        lambda s: s.id in existing_subject_ids
                    )

                    for subject in subjects_with_existing_history:
                        tracking = Tracking.search(
                            [
                                ("student_id", "=", student.id),
                                ("subject_id", "=", subject.id),
                            ],
                            limit=1,
                        )

                        if tracking and not tracking.attended:
                            # Actualizar tracking que existe pero no está marcado como attended
                            tracking.with_context(skip_history_sync=True).write(
                                {
                                    "attended": True,
                                    "state": "registered",
                                }
                            )
                            _logger.info(
                                f"[HISTORIAL-RETROACTIVO-FIX] Tracking corregido: "
                                f"{student.name} - {subject.code or subject.name}"
                            )
                        elif not tracking:
                            # Crear tracking si no existe
                            Tracking.create(
                                {
                                    "student_id": student.id,
                                    "subject_id": subject.id,
                                    "phase_id": (
                                        subject.phase_id.id
                                        if subject.phase_id
                                        else False
                                    ),
                                    "level_id": (
                                        subject.level_id.id
                                        if subject.level_id
                                        else False
                                    ),
                                    "attended": True,
                                    "state": "registered",
                                }
                            )
                            _logger.info(
                                f"[HISTORIAL-RETROACTIVO-FIX] Tracking creado (historial existente): "
                                f"{student.name} - {subject.code or subject.name}"
                            )

                    total_created += created_count

                    if created_count > 0 or progress_updated > 0:
                        results.append(
                            "✅ %s: %d historial + %d progreso (Units %s)"
                            % (
                                student.name,
                                created_count,
                                progress_updated,
                                (
                                    f"{min(previous_units)}-{max(previous_units)}"
                                    if previous_units
                                    else "N/A"
                                ),
                            )
                        )
                    else:
                        results.append(
                            "✓ %s: Ya tiene historial y progreso completo"
                            % student.name
                        )
            except Exception as e:
                results.append("❌ %s: ERROR - %s" % (student.name, str(e)))
                _logger.error("Error procesando estudiante %s: %s", student.name, e)

        message = "\n".join(results)
        message += (
            "\n\n" + "=" * 50 + "\n✅ COMPLETADO\nRegistros creados: %d" % total_created
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "🔄 Historial Académico Retroactivo",
                "message": message,
                "type": "success",
                "sticky": True,
            },
        }
