# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class Enrollment(models.Model):
    """
    Modelo para gestionar Matrículas de Estudiantes a un PLAN DE ESTUDIOS COMPLETO.

    ╔═══════════════════════════════════════════════════════════════════════════════╗
    ║  CONCEPTO FUNDAMENTAL (Odoo 18 - 2025)                                        ║
    ║  ═══════════════════════════════════════════════════════════════════════════  ║
    ║  ✅ CORRECTO: La matrícula es al PLAN DE ESTUDIOS completo                    ║
    ║  ❌ INCORRECTO: Matricular a asignaturas individuales                         ║
    ║                                                                               ║
    ║  Un estudiante tiene UNA matrícula activa a UN plan completo.                 ║
    ║  El progreso en asignaturas se registra en benglish.enrollment.progress       ║
    ╚═══════════════════════════════════════════════════════════════════════════════╝

    COMPATIBILIDAD BACKWARD:
    ========================
    - subject_id: OPCIONAL (legacy), para matrículas antiguas pre-refactorización
    - current_subject_id: Campo nuevo que indica asignatura actual en progresión

    NUEVO MODELO (post-refactorización):
    ====================================
    Matrícula → Plan de Estudios
      ├─ Progresión actual: current_phase_id, current_level_id, current_subject_id
      └─ Detalle por asignatura: enrollment_progress_ids (benglish.enrollment.progress)
    """

    _name = "benglish.enrollment"
    _description = "Matrícula de Estudiante a Plan de Estudios"
    _order = "enrollment_date desc, id desc"
    _rec_name = "display_name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    display_name = fields.Char(
        string="Nombre",
        compute="_compute_display_name",
        store=True,
        help="Nombre completo de la matrícula para visualización",
    )
    code = fields.Char(
        string="Código de Matrícula",
        required=True,
        copy=False,
        default="/",
        tracking=True,
        help="Código único de la matrícula (auto-generado)",
    )
    enrollment_date = fields.Date(
        string="Fecha de Matrícula",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help="Fecha en la que se realizó la matrícula",
    )

    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        required=True,
        ondelete="cascade",
        tracking=True,
        help="Estudiante matriculado",
    )
    student_code = fields.Char(
        string="Código de Estudiante",
        related="student_id.code",
        store=True,
        help="Código del estudiante",
    )
    student_email = fields.Char(
        string="Email del Estudiante",
        related="student_id.email",
        help="Correo electrónico del estudiante",
    )
    student_phone = fields.Char(
        string="Teléfono del Estudiante",
        related="student_id.mobile",
        help="Teléfono del estudiante",
    )

    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        required=True,  # ✅ OBLIGATORIO: Define la estructura curricular
        tracking=True,
        help="Programa académico del estudiante. Define la estructura curricular "
        "(fases, niveles, asignaturas) que el estudiante puede cursar.",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # PLAN COMERCIAL (NUEVA LÓGICA - Feb 2026)
    # ═══════════════════════════════════════════════════════════════════════════
    # El Plan Comercial define la ESTRUCTURA de asignaturas que el estudiante
    # debe ver (cantidades por tipo), NO una lista fija de asignaturas.
    # El progreso del estudiante se calcula dinámicamente según lo que realmente cursa.
    # 
    # REEMPLAZA a benglish.plan como el mecanismo principal de "qué ve el estudiante"

    commercial_plan_id = fields.Many2one(
        comodel_name="benglish.commercial.plan",
        string="Plan Comercial",
        domain="[('program_id', '=', program_id), ('active', '=', True)]",
        required=True,  # ✅ OBLIGATORIO: Define qué ve el estudiante
        tracking=True,
        index=True,
        help="Plan comercial que define la estructura de asignaturas que el estudiante "
        "debe cursar (cantidades por tipo: selección, electivas, oral tests, etc.). "
        "Define CUÁNTAS asignaturas de cada tipo debe ver el estudiante por nivel. "
        "Ejemplos: Plan Plus (78), Plan Gold (126), Módulo (42).",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # PLAN DE ESTUDIOS (LEGACY - Mantener para compatibilidad)
    # ═══════════════════════════════════════════════════════════════════════════
    # DEPRECADO: Usar commercial_plan_id para nuevas matrículas
    # Se mantiene para matrículas existentes que aún no migran al nuevo modelo

    plan_id = fields.Many2one(
        comodel_name="benglish.plan",
        string="Plan de Estudios (Legacy)",
        domain="[('program_id', '=', program_id)]",
        required=False,  # ❌ YA NO OBLIGATORIO - Deprecado
        tracking=True,
        help="[DEPRECADO] Plan de estudios estático. "
        "Para nuevas matrículas usar commercial_plan_id. "
        "Se mantiene para compatibilidad con datos existentes.",
    )

    # Campos computados desde el Plan Comercial
    commercial_total_subjects = fields.Integer(
        string="Total Asignaturas (Comercial)",
        related="commercial_plan_id.total_subjects",
        store=True,
        help="Total de asignaturas que debe cursar según el plan comercial",
    )

    commercial_total_electives = fields.Integer(
        string="Total Electivas (Comercial)",
        related="commercial_plan_id.total_electives",
        store=True,
        help="Total de electivas según el plan comercial",
    )

    commercial_total_oral_tests = fields.Integer(
        string="Total Oral Tests (Comercial)",
        related="commercial_plan_id.total_oral_test",
        store=True,
        help="Total de oral tests según el plan comercial",
    )

    # Relación con los registros de progreso por nivel (Plan Comercial)
    commercial_progress_ids = fields.One2many(
        comodel_name="benglish.student.commercial.progress",
        inverse_name="enrollment_id",
        string="Progreso por Nivel (Plan Comercial)",
        help="Detalle del progreso del estudiante por cada nivel según el plan comercial. "
        "Se genera automáticamente cuando se asigna un plan comercial.",
    )

    # Totales consolidados del progreso comercial
    commercial_total_expected = fields.Integer(
        string="Total Esperado (Comercial)",
        compute="_compute_commercial_progress_totals",
        store=True,
        help="Total de asignaturas esperadas según el plan comercial",
    )

    commercial_total_completed = fields.Integer(
        string="Total Completado (Comercial)",
        compute="_compute_commercial_progress_totals",
        store=True,
        help="Total de asignaturas completadas",
    )

    commercial_progress_percentage = fields.Float(
        string="% Avance (Comercial)",
        compute="_compute_commercial_progress_totals",
        store=True,
        digits=(5, 2),
        help="Porcentaje de avance según el plan comercial",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CAMPOS DE PROGRESIÓN ACADÉMICA (ESTADO DENTRO DEL PLAN)
    # ═══════════════════════════════════════════════════════════════════════════
    # Estos campos indican DÓNDE está el estudiante dentro de su plan de estudios

    current_phase_id = fields.Many2one(
        comodel_name="benglish.phase",
        string="Fase Actual",
        tracking=True,
        help="Fase en la que se encuentra el estudiante actualmente dentro de su plan. "
        "Representa su PROGRESIÓN, no una matrícula independiente.",
    )
    current_level_id = fields.Many2one(
        comodel_name="benglish.level",
        string="Nivel Actual",
        domain="[('phase_id', '=', current_phase_id)]",
        tracking=True,
        help="Nivel en el que se encuentra el estudiante actualmente dentro de su plan. "
        "Representa su PROGRESIÓN, no una matrícula independiente.",
    )
    current_subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura Actual",
        domain="[('level_id', '=', current_level_id)]",
        tracking=True,
        help="Asignatura que está cursando el estudiante actualmente. "
        "Representa su PROGRESIÓN, no una matrícula independiente.",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # MATRÍCULA POR NIVEL (Feb 2026 - Reunión)
    # ═══════════════════════════════════════════════════════════════════════════
    # La matrícula se realiza por NIVEL, no por asignatura.
    # El nivel es un valor entero que representa la posición del estudiante
    # dentro del rango del plan comercial (level_start a level_end).
    # Regla de negocio: La primera asignatura de cada nivel siempre es Bcheck.

    current_level = fields.Integer(
        string="Nivel Actual",
        default=1,
        required=True,
        tracking=True,
        index=True,
        help="Nivel actual del estudiante (valor numérico 1-24). "
        "Este es el campo principal para controlar el progreso por niveles. "
        "Debe estar dentro del rango del plan comercial (level_start - level_end).",
    )

    starting_level = fields.Integer(
        string="Nivel de Inicio",
        readonly=True,
        tracking=True,
        help="Nivel en el que el estudiante inició según el plan comercial. "
        "Se establece automáticamente al asignar el plan comercial.",
    )

    max_level = fields.Integer(
        string="Nivel Máximo",
        related="commercial_plan_id.level_end",
        store=True,
        readonly=True,
        help="Nivel máximo que puede alcanzar según su plan comercial.",
    )

    min_level = fields.Integer(
        string="Nivel Mínimo",
        related="commercial_plan_id.level_start",
        store=True,
        readonly=True,
        help="Nivel mínimo del plan comercial.",
    )

    levels_completed = fields.Integer(
        string="Niveles Completados",
        compute="_compute_levels_progress",
        store=True,
        help="Cantidad de niveles que el estudiante ha completado.",
    )

    level_progress_percentage = fields.Float(
        string="% Progreso por Niveles",
        compute="_compute_levels_progress",
        store=True,
        digits=(5, 2),
        help="Porcentaje de avance basado en niveles completados vs niveles totales del plan.",
    )

    bcheck_current_level_completed = fields.Boolean(
        string="Bcheck del Nivel Completado",
        compute="_compute_bcheck_status",
        store=True,
        help="Indica si el Bcheck (prerrequisito) del nivel actual está completado. "
        "Regla de negocio: El Bcheck debe completarse antes de ver otras asignaturas del nivel.",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CAMPOS LEGACY (COMPATIBILIDAD BACKWARD)
    # ═══════════════════════════════════════════════════════════════════════════
    # DEPRECADOS: Estos campos se mantienen para compatibilidad con datos antiguos
    # En nuevas matrículas, usar current_subject_id en su lugar

    phase_id = fields.Many2one(
        comodel_name="benglish.phase",
        string="Fase (Legacy)",
        compute="_compute_academic_hierarchy",
        store=True,
        help="[DEPRECADO] Campo computado desde subject_id (legacy). "
        "Usar current_phase_id para nuevas implementaciones.",
    )
    level_id = fields.Many2one(
        comodel_name="benglish.level",
        string="Nivel (Legacy)",
        compute="_compute_academic_hierarchy",
        store=True,
        help="[DEPRECADO] Campo computado desde subject_id (legacy). "
        "Usar current_level_id para nuevas implementaciones.",
    )
    subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura (Legacy)",
        required=False,  # ✅ YA NO ES OBLIGATORIO
        ondelete="cascade",
        tracking=True,
        help="[DEPRECADO - Solo para compatibilidad con matrículas antiguas]\n"
        "Este campo representa el modelo antiguo donde la matrícula era a una asignatura.\n"
        "En el modelo correcto, la matrícula es al PLAN completo.\n"
        "Para nuevas matrículas, usar current_subject_id.",
    )

    #  DATOS DEL CONTRATO ACADÉMICO (importación Excel)

    categoria = fields.Char(
        string="Categoría",
        tracking=True,
        help="Categoría académica o comercial del estudiante (ej: Regular, Intensivo, VIP, etc.)",
    )
    course_start_date = fields.Date(
        string="Fecha Inicio del Curso",
        tracking=True,
        help="Fecha de inicio del curso/contrato académico específico",
    )
    course_end_date = fields.Date(
        string="Fecha Fin del Curso",
        tracking=True,
        help="Fecha de finalización prevista del curso/contrato",
    )
    max_freeze_date = fields.Date(
        string="Fecha Máxima de Congelamiento",
        tracking=True,
        help="Fecha límite hasta la cual el estudiante puede solicitar congelamiento",
    )
    course_days = fields.Integer(
        string="Días del Curso",
        tracking=True,
        help="Duración total del curso en días (información contractual)",
    )

    group_id = fields.Many2one(
        comodel_name="benglish.group",
        string="Grupo",
        required=False,
        ondelete="cascade",
        tracking=True,
        help="Grupo al que se asigna el estudiante",
    )
    course_id = fields.Many2one(
        comodel_name="benglish.course",
        string="Curso",
        related="group_id.course_id",
        store=True,
        help="Curso asociado al grupo",
    )

    campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Sede",
        related="group_id.campus_id",
        store=True,
        help="Sede donde se dictan las clases",
    )
    subcampus_id = fields.Many2one(
        comodel_name="benglish.subcampus",
        string="Aula",
        related="group_id.subcampus_id",
        store=True,
        help="Aula específica",
    )

    delivery_mode = fields.Selection(
        selection=[
            ("presential", "Presencial"),
            ("virtual", "Virtual"),
            ("hybrid", "Híbrido"),
        ],
        string="Modalidad de Asistencia",
        required=True,
        default="presential",
        tracking=True,
        help="Modalidad en la que el estudiante tomará las clases",
    )
    attendance_type = fields.Selection(
        selection=[
            ("presential", "Presencial"),
            ("virtual", "Virtual (Remoto)"),
        ],
        string="Tipo de Asistencia",
        compute="_compute_attendance_type",
        store=True,
        tracking=True,
        help="Tipo de asistencia específico (para modalidad híbrida)",
    )

    coach_id = fields.Many2one(
        comodel_name="benglish.coach",
        string="Coach/Docente",
        related="group_id.coach_id",
        store=True,
        help="Docente asignado al grupo",
    )

    start_date = fields.Date(
        string="Fecha de Inicio",
        related="group_id.start_date",
        store=True,
        help="Fecha de inicio del grupo",
    )
    end_date = fields.Date(
        string="Fecha de Fin",
        related="group_id.end_date",
        store=True,
        help="Fecha de finalización del grupo",
    )
    schedule = fields.Text(
        string="Horario",
        related="group_id.schedule",
        help="Descripción del horario de clases",
    )

    # Sesiones del grupo
    session_ids = fields.Many2many(
        comodel_name="benglish.class.session",
        compute="_compute_session_ids",
        string="Sesiones de Clase",
        help="Sesiones programadas para este grupo",
    )
    total_sessions = fields.Integer(
        string="Total de Sesiones",
        compute="_compute_session_statistics",
        store=True,
        help="Número total de sesiones programadas",
    )

    group_capacity = fields.Integer(
        string="Capacidad del Grupo",
        related="group_id.total_capacity",
        help="Capacidad total del grupo",
    )
    group_current_students = fields.Integer(
        string="Estudiantes en el Grupo",
        related="group_id.current_students",
        help="Número actual de estudiantes matriculados",
    )
    group_available_seats = fields.Integer(
        string="Cupos Disponibles",
        related="group_id.available_seats",
        help="Cupos disponibles en el grupo",
    )

    # Control de cupos por modalidad (híbrido)
    presential_capacity = fields.Integer(
        string="Capacidad Presencial",
        related="group_id.presential_capacity",
        help="Capacidad presencial del grupo",
    )
    virtual_capacity = fields.Integer(
        string="Capacidad Virtual",
        related="group_id.virtual_capacity",
        help="Capacidad virtual del grupo",
    )
    current_presential = fields.Integer(
        string="Estudiantes Presenciales",
        related="group_id.current_presential",
        help="Estudiantes presenciales actuales",
    )
    current_virtual = fields.Integer(
        string="Estudiantes Virtuales",
        related="group_id.current_virtual",
        help="Estudiantes virtuales actuales",
    )

    prerequisite_ids = fields.Many2many(
        comodel_name="benglish.subject",
        string="Prerrequisitos",
        related="subject_id.prerequisite_ids",
        help="Asignaturas que deben estar aprobadas",
    )
    prerequisite_count = fields.Integer(
        string="Número de Prerrequisitos",
        related="subject_id.prerequisite_count",
        help="Cantidad de prerrequisitos requeridos",
    )
    prerequisites_met = fields.Boolean(
        string="Cumple Prerrequisitos",
        compute="_compute_prerequisites_met",
        store=True,
        help="Indica si el estudiante cumple con todos los prerrequisitos",
    )
    missing_prerequisites = fields.Char(
        string="Prerrequisitos Faltantes",
        compute="_compute_prerequisites_met",
        store=True,
        help="Asignaturas prerrequisito que faltan por aprobar",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # PROGRESO ACADÉMICO EN ASIGNATURAS
    # ═══════════════════════════════════════════════════════════════════════════

    enrollment_progress_ids = fields.One2many(
        comodel_name="benglish.enrollment.progress",
        inverse_name="enrollment_id",
        string="Progreso en Asignaturas",
        help="Detalle del progreso del estudiante en cada asignatura del plan. "
        "Cada registro representa el estado en una asignatura específica.",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ESTADO DE REQUISITOS ACADÉMICOS
    # ═══════════════════════════════════════════════════════════════════════════

    requirement_status_ids = fields.One2many(
        comodel_name="benglish.student.requirement.status",
        inverse_name="enrollment_id",
        string="Estado de Requisitos",
        help="Estado de cumplimiento de los requisitos académicos del plan "
        "para este estudiante. Generados automáticamente desde los requisitos del plan.",
    )

    compliance_ids = fields.One2many(
        comodel_name="benglish.student.compliance",
        inverse_name="enrollment_id",
        string="Cumplimientos Académicos",
        help="Registro de cumplimientos académicos del estudiante.",
    )

    total_subjects = fields.Integer(
        string="Total de Asignaturas",
        compute="_compute_progress_statistics",
        store=True,
        help="Número total de asignaturas en el plan de estudios",
    )
    completed_subjects = fields.Integer(
        string="Asignaturas Completadas",
        compute="_compute_progress_statistics",
        store=True,
        help="Número de asignaturas aprobadas",
    )
    in_progress_subjects = fields.Integer(
        string="Asignaturas en Progreso",
        compute="_compute_progress_statistics",
        store=True,
        help="Número de asignaturas actualmente en curso",
    )
    failed_subjects = fields.Integer(
        string="Asignaturas Reprobadas",
        compute="_compute_progress_statistics",
        store=True,
        help="Número de asignaturas reprobadas",
    )
    completion_percentage = fields.Float(
        string="% Completado",
        compute="_compute_progress_statistics",
        store=True,
        digits=(5, 2),
        help="Porcentaje de completitud del plan de estudios",
    )

    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("pending", "Pendiente de Aprobación"),
            ("enrolled", "Matriculado"),  # Deprecated: migrar a 'active'
            ("active", "Activa"),  # Estado principal de matrícula en curso
            ("in_progress", "En Progreso"),  # Deprecated: migrar a 'active'
            ("suspended", "Suspendida"),  # Para congelamientos
            ("completed", "Completado"),  # Deprecated: migrar a 'finished'
            ("failed", "Reprobado"),  # Deprecated: migrar a 'finished'
            ("finished", "Finalizada"),  # Agrupa aprobados y reprobados
            ("homologated", "Homologado"),  # RF-04: Asignatura convalidada/homologada
            ("withdrawn", "Retirado"),
            ("cancelled", "Cancelado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
        help="Estado actual de la matrícula. "
        "active=cursando, suspended=congelada, finished=completada (aprobada/reprobada)",
    )

    # Calificaciones
    final_grade = fields.Float(
        string="Calificación Final",
        digits=(5, 2),
        tracking=True,
        help="Calificación final obtenida (0-100)",
    )
    is_approved = fields.Boolean(
        string="Aprobado",
        compute="_compute_is_approved",
        store=True,
        help="Indica si el estudiante aprobó la asignatura",
    )
    min_passing_grade = fields.Float(
        string="Nota Mínima para Aprobar",
        default=70.0,
        help="Calificación mínima requerida para aprobar",
    )

    notes = fields.Text(
        string="Observaciones", help="Notas y comentarios sobre la matrícula"
    )

    # Override de prerrequisitos (solo para coordinador/manager)
    prerequisite_override = fields.Boolean(
        string="Excepción de Prerrequisitos",
        default=False,
        tracking=True,
        help="Permite aprobar la matrícula aunque no se cumplan los prerrequisitos. "
        "Solo puede ser autorizado por coordinadores o administradores académicos.",
    )
    override_reason = fields.Text(
        string="Justificación de Excepción",
        tracking=True,
        help="Razón por la cual se autoriza la excepción de prerrequisitos",
    )
    override_by = fields.Many2one(
        comodel_name="res.users",
        string="Excepción Autorizada Por",
        tracking=True,
        help="Usuario que autorizó la excepción",
    )
    withdrawal_date = fields.Date(
        string="Fecha de Retiro",
        tracking=True,
        help="Fecha en la que el estudiante se retiró",
    )
    withdrawal_reason = fields.Text(
        string="Motivo de Retiro",
        tracking=True,
        help="Razón del retiro de la asignatura",
    )
    cancellation_reason = fields.Text(
        string="Motivo de Cancelación",
        tracking=True,
        help="Razón de la cancelación de la matrícula",
    )

    approved_date = fields.Date(
        string="Fecha de Aprobación",
        tracking=True,
        help="Fecha en que se aprobó la matrícula",
    )
    approved_by = fields.Many2one(
        comodel_name="res.users",
        string="Aprobado Por",
        help="Usuario que aprobó la matrícula",
    )
    completed_date = fields.Date(
        string="Fecha de Finalización",
        tracking=True,
        help="Fecha en que el estudiante completó la asignatura",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # PLACEMENT TEST
    # ═══════════════════════════════════════════════════════════════════════════
    
    placement_test_completed = fields.Boolean(
        string="Placement Test Completado",
        default=False,
        tracking=True,
        help="Indica si el estudiante realizó el Placement Test inicial"
    )
    
    placement_test_date = fields.Date(
        string="Fecha Placement Test",
        readonly=True,
        tracking=True,
        help="Fecha en que se completó el Placement Test"
    )
    
    placement_test_score = fields.Float(
        string="Score Placement Test (%)",
        digits=(5, 2),
        readonly=True,
        help="Calificación final consolidada del Placement Test"
    )

    # RF-04: Campos para Homologación
    homologation_date = fields.Date(
        string="Fecha de Homologación",
        tracking=True,
        help="Fecha en que se homologó/convalidó la asignatura",
    )
    homologation_reason = fields.Text(
        string="Justificación de Homologación",
        tracking=True,
        help="Razón por la cual se homologa la asignatura (estudios previos, experiencia, etc.)",
    )
    homologated_by = fields.Many2one(
        comodel_name="res.users",
        string="Homologado Por",
        tracking=True,
        help="Usuario que autorizó la homologación",
    )
    homologation_document = fields.Binary(
        string="Documento Soporte",
        help="Certificado o documento que sustenta la homologación",
    )
    homologation_document_name = fields.Char(
        string="Nombre del Documento",
    )

    @api.depends("student_id", "plan_id", "current_subject_id", "subject_id")
    def _compute_display_name(self):
        """
        Genera el nombre de visualización de la matrícula.
        PRIORIZA el nuevo modelo (plan) sobre el legacy (subject).
        """
        for enrollment in self:
            if enrollment.student_id and enrollment.plan_id:
                # MODELO CORRECTO: Matrícula a plan
                if enrollment.current_subject_id:
                    enrollment.display_name = (
                        f"{enrollment.student_id.name} - {enrollment.plan_id.name} "
                        f"(Cursando: {enrollment.current_subject_id.alias or enrollment.current_subject_id.name})"
                    )
                else:
                    enrollment.display_name = (
                        f"{enrollment.student_id.name} - {enrollment.plan_id.name}"
                    )
            elif enrollment.student_id and enrollment.subject_id:
                # MODELO LEGACY: Matrícula a asignatura (compatibilidad backward)
                enrollment.display_name = f"{enrollment.student_id.name} - {enrollment.subject_id.name} [Legacy]"
            else:
                enrollment.display_name = enrollment.code or "Nueva Matrícula"

    @api.depends("subject_id")
    def _compute_academic_hierarchy(self):
        """
        [LEGACY] Calcula la jerarquía académica.
        NOTA: Las asignaturas ya no tienen level_id/phase_id.
        """
        for enrollment in self:
            enrollment.level_id = False
            enrollment.phase_id = False

    @api.depends("delivery_mode")
    def _compute_attendance_type(self):
        """Determina el tipo de asistencia según la modalidad"""
        for enrollment in self:
            if enrollment.delivery_mode == "presential":
                enrollment.attendance_type = "presential"
            elif enrollment.delivery_mode == "virtual":
                enrollment.attendance_type = "virtual"
            else:  # hybrid
                # Por defecto presencial, pero puede cambiarse
                if not enrollment.attendance_type:
                    enrollment.attendance_type = "presential"

    @api.depends("subject_id", "campus_id")
    def _compute_session_ids(self):
        """Obtiene las sesiones del grupo (por asignatura y sede)"""
        for enrollment in self:
            if enrollment.subject_id and enrollment.campus_id:
                enrollment.session_ids = self.env["benglish.class.session"].search(
                    [
                        ("subject_id", "=", enrollment.subject_id.id),
                        ("campus_id", "=", enrollment.campus_id.id),
                        ("state", "!=", "cancelled"),
                    ]
                )
            else:
                enrollment.session_ids = False

    @api.depends("session_ids")
    def _compute_session_statistics(self):
        """Calcula estadísticas de sesiones"""
        for enrollment in self:
            enrollment.total_sessions = len(enrollment.session_ids)

    @api.depends("enrollment_progress_ids", "enrollment_progress_ids.state", "plan_id")
    def _compute_progress_statistics(self):
        """
        Calcula estadísticas de progreso en el plan de estudios.
        Cuenta asignaturas completadas, en progreso, reprobadas, etc.
        """
        for enrollment in self:
            progress_records = enrollment.enrollment_progress_ids

            if progress_records:
                enrollment.total_subjects = len(progress_records)
                enrollment.completed_subjects = len(
                    progress_records.filtered(lambda p: p.state == "completed")
                )
                enrollment.in_progress_subjects = len(
                    progress_records.filtered(lambda p: p.state == "in_progress")
                )
                enrollment.failed_subjects = len(
                    progress_records.filtered(lambda p: p.state == "failed")
                )

                # Calcular porcentaje de completitud
                if enrollment.total_subjects > 0:
                    enrollment.completion_percentage = (
                        enrollment.completed_subjects / enrollment.total_subjects
                    ) * 100
                else:
                    enrollment.completion_percentage = 0.0
            elif enrollment.plan_id:
                # Si no hay registros de progreso pero hay plan, obtener total de asignaturas del plan
                total_plan_subjects = self.env["benglish.subject"].search_count(
                    [("program_id", "=", enrollment.plan_id.program_id.id)]
                )
                enrollment.total_subjects = total_plan_subjects
                enrollment.completed_subjects = 0
                enrollment.in_progress_subjects = 0
                enrollment.failed_subjects = 0
                enrollment.completion_percentage = 0.0
            else:
                enrollment.total_subjects = 0
                enrollment.completed_subjects = 0
                enrollment.in_progress_subjects = 0
                enrollment.failed_subjects = 0
                enrollment.completion_percentage = 0.0

    @api.depends("commercial_progress_ids.expected_total", "commercial_progress_ids.completed_total")
    def _compute_commercial_progress_totals(self):
        """
        Calcula los totales consolidados del progreso según el plan comercial.
        Este progreso es DINÁMICO: se actualiza según las clases realmente cumplidas.
        """
        for enrollment in self:
            total_expected = sum(enrollment.commercial_progress_ids.mapped('expected_total'))
            total_completed = sum(enrollment.commercial_progress_ids.mapped('completed_total'))
            
            enrollment.commercial_total_expected = total_expected
            enrollment.commercial_total_completed = total_completed
            
            if total_expected > 0:
                enrollment.commercial_progress_percentage = (total_completed / total_expected) * 100
            else:
                enrollment.commercial_progress_percentage = 0.0

    @api.depends("current_level", "commercial_plan_id.level_start", "commercial_plan_id.level_end")
    def _compute_levels_progress(self):
        """
        Calcula el progreso por niveles (Feb 2026 - Matrícula por Nivel).
        
        REGLA DE NEGOCIO:
        - levels_completed = current_level - level_start del plan comercial
        - level_progress_percentage = niveles completados / total niveles del plan * 100
        """
        for enrollment in self:
            if enrollment.commercial_plan_id and enrollment.current_level:
                start = enrollment.commercial_plan_id.level_start or 1
                total_levels = enrollment.commercial_plan_id.total_levels or 1
                
                # Niveles completados = nivel actual - nivel de inicio
                # (si estás en nivel 1 y empezaste en 1, has completado 0 niveles)
                enrollment.levels_completed = max(0, enrollment.current_level - start)
                
                # Porcentaje de progreso
                if total_levels > 0:
                    enrollment.level_progress_percentage = (
                        enrollment.levels_completed / total_levels
                    ) * 100
                else:
                    enrollment.level_progress_percentage = 0.0
                    
                _logger.debug(
                    f"[ENROLLMENT] Progreso por niveles calculado para {enrollment.code}: "
                    f"nivel actual={enrollment.current_level}, completados={enrollment.levels_completed}, "
                    f"porcentaje={enrollment.level_progress_percentage:.2f}%"
                )
            else:
                enrollment.levels_completed = 0
                enrollment.level_progress_percentage = 0.0

    @api.depends("current_level", "commercial_progress_ids.completed_selection", "commercial_progress_ids.level_sequence")
    def _compute_bcheck_status(self):
        """
        Verifica si el Bcheck del nivel actual está completado (Feb 2026).
        
        REGLA DE NEGOCIO CRÍTICA:
        - La primera asignatura de cualquier nivel siempre es "Bcheck"
        - El Bcheck es el prerrequisito para ver otras asignaturas del nivel
        - Se verifica mirando el campo completed_selection del progreso comercial del nivel actual
        
        En el modelo de progreso comercial:
        - selection = B-check (1 por nivel normalmente)
        - Si completed_selection >= expected_selection para el nivel actual, Bcheck está completado
        """
        for enrollment in self:
            if not enrollment.commercial_plan_id or not enrollment.current_level:
                enrollment.bcheck_current_level_completed = False
                continue
            
            # Buscar el registro de progreso comercial para el nivel actual
            current_level_progress = enrollment.commercial_progress_ids.filtered(
                lambda p: p.level_sequence == enrollment.current_level
            )
            
            if current_level_progress:
                # El Bcheck está completado si completed_selection >= expected_selection
                progress = current_level_progress[0]
                enrollment.bcheck_current_level_completed = (
                    progress.completed_selection >= progress.expected_selection 
                    and progress.expected_selection > 0
                )
                
                _logger.debug(
                    f"[ENROLLMENT] Bcheck status para {enrollment.code} nivel {enrollment.current_level}: "
                    f"completed={progress.completed_selection}, expected={progress.expected_selection}, "
                    f"completado={enrollment.bcheck_current_level_completed}"
                )
            else:
                enrollment.bcheck_current_level_completed = False

    @api.depends("student_id", "subject_id", "student_id.approved_subject_ids")
    def _compute_prerequisites_met(self):
        """
        [LEGACY] Valida prerrequisitos para subject_id (compatibilidad backward).
        Para el nuevo modelo, los prerrequisitos se validan en enrollment.progress.
        """
        for enrollment in self:
            if not enrollment.subject_id or not enrollment.student_id:
                enrollment.prerequisites_met = True
                enrollment.missing_prerequisites = ""
                continue

            prerequisites = enrollment.subject_id.prerequisite_ids
            if not prerequisites:
                enrollment.prerequisites_met = True
                enrollment.missing_prerequisites = ""
                continue

            approved_subjects = enrollment.student_id.approved_subject_ids
            missing = prerequisites - approved_subjects

            if missing:
                enrollment.prerequisites_met = False
                enrollment.missing_prerequisites = ", ".join(missing.mapped("name"))
            else:
                enrollment.prerequisites_met = True
                enrollment.missing_prerequisites = ""

    @api.depends("final_grade", "min_passing_grade", "state")
    def _compute_is_approved(self):
        """Determina si el estudiante aprobó la asignatura"""
        for enrollment in self:
            if enrollment.state == "completed" and enrollment.final_grade:
                enrollment.is_approved = (
                    enrollment.final_grade >= enrollment.min_passing_grade
                )
            else:
                enrollment.is_approved = False

    @api.onchange("student_id")
    def _onchange_student_id(self):
        """Carga información del estudiante al seleccionarlo"""
        if self.student_id:
            self.program_id = self.student_id.program_id
            self.plan_id = self.student_id.plan_id

    @api.onchange("commercial_plan_id")
    def _onchange_commercial_plan_id(self):
        """
        Establece el nivel inicial automáticamente al seleccionar plan comercial (Feb 2026).
        
        REGLA DE NEGOCIO:
        - El nivel actual se establece al nivel inicial del plan comercial
        - El starting_level se guarda para referencia histórica
        - Si el plan comercial cambia, se actualiza el nivel actual
        """
        if self.commercial_plan_id:
            level_start = self.commercial_plan_id.level_start or 1
            
            # Solo establecer si no hay un nivel actual o si es una nueva matrícula
            if not self.current_level or self.current_level < level_start:
                self.current_level = level_start
                
            # Siempre actualizar starting_level con el nivel inicial del plan
            self.starting_level = level_start
            
            _logger.info(
                f"[ENROLLMENT] Plan comercial seleccionado: {self.commercial_plan_id.name}. "
                f"Nivel inicial establecido en {level_start}, rango: {level_start}-{self.commercial_plan_id.level_end}"
            )
            
            return {
                "warning": {
                    "title": _("Plan Comercial Configurado"),
                    "message": _(
                        "Se ha configurado el nivel inicial en %d.\n"
                        "Rango de niveles del plan: %d - %d"
                    ) % (level_start, level_start, self.commercial_plan_id.level_end),
                }
            }

    @api.onchange("group_id")
    def _onchange_group_id(self):
        """
        Carga información del grupo al seleccionarlo.
        Valida capacidad y modalidad.
        """
        if self.group_id:
            # Heredar asignatura del grupo si coincide
            if self.group_id.subject_id:
                self.subject_id = self.group_id.subject_id

            # Heredar modalidad del grupo
            self.delivery_mode = self.group_id.delivery_mode

            # Validar cupos disponibles
            if self.group_id.available_seats <= 0:
                return {
                    "warning": {
                        "title": _("Grupo Completo"),
                        "message": _(
                            'El grupo "%s" no tiene cupos disponibles. '
                            "Capacidad: %d / %d estudiantes."
                        )
                        % (
                            self.group_id.name,
                            self.group_id.current_students,
                            self.group_id.total_capacity,
                        ),
                    }
                }

    @api.onchange("delivery_mode")
    def _onchange_delivery_mode(self):
        """Valida la modalidad seleccionada"""
        if self.group_id and self.delivery_mode:
            group_mode = self.group_id.delivery_mode

            # Validar compatibilidad de modalidades
            if group_mode == "presential" and self.delivery_mode != "presential":
                return {
                    "warning": {
                        "title": _("Modalidad Incompatible"),
                        "message": _(
                            "El grupo es presencial. "
                            "No se puede matricular en modalidad virtual."
                        ),
                    }
                }
            elif group_mode == "virtual" and self.delivery_mode != "virtual":
                return {
                    "warning": {
                        "title": _("Modalidad Incompatible"),
                        "message": _(
                            "El grupo es virtual. "
                            "No se puede matricular en modalidad presencial."
                        ),
                    }
                }

    @api.constrains("student_id", "group_id", "state")
    def _check_duplicate_enrollment(self):
        """Evita matrículas duplicadas del mismo estudiante en el mismo grupo"""
        for enrollment in self:
            if (
                enrollment.state not in ["cancelled", "withdrawn"]
                and enrollment.group_id
            ):
                domain = [
                    ("student_id", "=", enrollment.student_id.id),
                    ("group_id", "=", enrollment.group_id.id),
                    ("id", "!=", enrollment.id),
                    ("state", "not in", ["cancelled", "withdrawn"]),
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(
                        _(
                            'El estudiante "%s" ya está matriculado en el grupo "%s". '
                            "No se permiten matrículas duplicadas."
                        )
                        % (enrollment.student_id.name, enrollment.group_id.name)
                    )

    @api.constrains("student_id", "plan_id", "state")
    def _check_single_active_enrollment_per_plan(self):
        """
        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║  REGLA DE NEGOCIO FUNDAMENTAL                                                 ║
        ║  ═══════════════════════════════════════════════════════════════════════════  ║
        ║  Un estudiante solo puede tener UNA matrícula activa por plan simultáneamente║
        ║  Esto garantiza la integridad del modelo académico.                          ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝

        VALIDACIÓN:
        - Solo valida si plan_id está presente
        - Permite matrículas en diferentes planes del mismo programa (raro pero válido)
        - Bloquea duplicación de matrículas al mismo plan
        """
        for enrollment in self:
            if (
                enrollment.state in ["active", "enrolled", "in_progress"]
                and enrollment.plan_id
            ):
                # Buscar otras matrículas activas del mismo plan
                duplicate = self.search(
                    [
                        ("student_id", "=", enrollment.student_id.id),
                        ("plan_id", "=", enrollment.plan_id.id),
                        ("id", "!=", enrollment.id),
                        ("state", "in", ["active", "enrolled", "in_progress"]),
                    ],
                    limit=1,
                )

                if duplicate:
                    raise ValidationError(
                        _(
                            "❌ MATRÍCULA DUPLICADA NO PERMITIDA\n\n"
                            'El estudiante "%s" ya tiene una matrícula activa en el plan "%s".\n\n'
                            "📋 Matrícula existente:\n"
                            "   • Código: %s\n"
                            "   • Estado: %s\n"
                            "   • Fase actual: %s\n"
                            "   • Nivel actual: %s\n\n"
                            "💡 Acción requerida:\n"
                            "Complete, retire o cancele la matrícula anterior antes de crear una nueva.\n"
                            "Un estudiante solo puede tener UNA matrícula activa por plan."
                        )
                        % (
                            enrollment.student_id.name,
                            enrollment.plan_id.name,
                            duplicate.code,
                            dict(duplicate._fields["state"].selection).get(
                                duplicate.state
                            ),
                            (
                                duplicate.current_phase_id.name
                                if duplicate.current_phase_id
                                else "N/A"
                            ),
                            (
                                duplicate.current_level_id.name
                                if duplicate.current_level_id
                                else "N/A"
                            ),
                        )
                    )

    @api.constrains("current_level", "commercial_plan_id")
    def _check_level_within_plan_range(self):
        """
        Valida que el nivel actual esté dentro del rango del plan comercial (Feb 2026).
        
        REGLA DE NEGOCIO:
        - El nivel actual debe estar entre level_start y level_end del plan comercial
        - Si no hay plan comercial, solo valida que el nivel sea positivo
        """
        for enrollment in self:
            if not enrollment.current_level:
                continue
                
            if enrollment.current_level < 1:
                raise ValidationError(
                    _("❌ NIVEL INVÁLIDO\n\n"
                      "El nivel actual debe ser mayor a 0.\n"
                      "Nivel ingresado: %d") % enrollment.current_level
                )
            
            if enrollment.commercial_plan_id:
                plan = enrollment.commercial_plan_id
                
                if enrollment.current_level < plan.level_start:
                    raise ValidationError(
                        _(
                            "❌ NIVEL FUERA DE RANGO\n\n"
                            "El nivel actual (%d) no puede ser menor al nivel inicial del plan comercial (%d).\n\n"
                            "📋 Plan Comercial: %s\n"
                            "📊 Rango de niveles: %d - %d"
                        ) % (
                            enrollment.current_level,
                            plan.level_start,
                            plan.name,
                            plan.level_start,
                            plan.level_end,
                        )
                    )
                    
                if enrollment.current_level > plan.level_end:
                    raise ValidationError(
                        _(
                            "❌ NIVEL FUERA DE RANGO\n\n"
                            "El nivel actual (%d) no puede exceder el nivel máximo del plan comercial (%d).\n\n"
                            "📋 Plan Comercial: %s\n"
                            "📊 Rango de niveles: %d - %d\n\n"
                            "💡 El estudiante ha completado todos los niveles de este plan."
                        ) % (
                            enrollment.current_level,
                            plan.level_end,
                            plan.name,
                            plan.level_start,
                            plan.level_end,
                        )
                    )
                    
                _logger.debug(
                    f"[ENROLLMENT] Nivel validado para {enrollment.code}: "
                    f"nivel={enrollment.current_level}, rango={plan.level_start}-{plan.level_end}"
                )

    @api.constrains("student_id", "subject_id")
    def _check_prerequisites(self):
        """
        [LEGACY] Valida prerrequisitos para subject_id.
        Esta validación es ACADÉMICA, no financiera.
        Solo se aplica a matrículas legacy que usan subject_id.
        """
        for enrollment in self:
            # Solo validar en estados activos (no en draft/pending donde puede haber override)
            if enrollment.state in ["active", "finished"]:
                if (
                    not enrollment.prerequisites_met
                    and not enrollment.prerequisite_override
                ):
                    raise ValidationError(
                        _(
                            "❌ PRERREQUISITOS NO CUMPLIDOS\n\n"
                            'El estudiante "%s" no cumple con los prerrequisitos '
                            'para la asignatura "%s".\n\n'
                            "📚 Prerrequisitos faltantes:\n%s\n\n"
                            "El estudiante debe aprobar estas asignaturas antes de matricularse."
                        )
                        % (
                            enrollment.student_id.name,
                            enrollment.subject_id.name,
                            enrollment.missing_prerequisites,
                        )
                    )

    @api.constrains("group_id", "attendance_type", "state")
    def _check_group_capacity(self):
        """
        Valida que haya cupos disponibles en el grupo.
        Considera capacidad presencial/virtual para grupos híbridos.
        """
        for enrollment in self:
            if enrollment.state in ["enrolled", "in_progress"] and enrollment.group_id:
                group = enrollment.group_id

                # Validar según modalidad del grupo
                if group.delivery_mode == "hybrid":
                    # Grupo híbrido: validar cupos presenciales o virtuales
                    if enrollment.attendance_type == "presential":
                        available = group.presential_capacity - group.current_presential
                        capacity_type = "presencial"
                        capacity = group.presential_capacity
                        current = group.current_presential
                    else:  # virtual
                        available = group.virtual_capacity - group.current_virtual
                        capacity_type = "virtual"
                        capacity = group.virtual_capacity
                        current = group.current_virtual

                    if available <= 0:
                        raise ValidationError(
                            _(
                                'No hay cupos %s disponibles en el grupo "%s".\n'
                                "Capacidad %s: %d / %d estudiantes.\n\n"
                                "Por favor, seleccione otro grupo o cambie la modalidad de asistencia."
                            )
                            % (
                                capacity_type,
                                group.name,
                                capacity_type,
                                current,
                                capacity,
                            )
                        )

                else:
                    # Grupo presencial o virtual: validar capacidad total
                    if group.available_seats <= 0:
                        raise ValidationError(
                            _(
                                'No hay cupos disponibles en el grupo "%s".\n'
                                "Capacidad: %d / %d estudiantes.\n\n"
                                "Por favor, seleccione otro grupo con cupos disponibles."
                            )
                            % (group.name, group.current_students, group.total_capacity)
                        )

    @api.constrains("final_grade")
    def _check_grade_range(self):
        """Valida que la calificación esté en el rango válido"""
        for enrollment in self:
            if enrollment.final_grade:
                if enrollment.final_grade < 0 or enrollment.final_grade > 100:
                    raise ValidationError(
                        _("La calificación final debe estar entre 0 y 100.")
                    )

    @api.constrains("enrollment_date", "start_date")
    def _check_enrollment_date(self):
        """Valida que la fecha de matrícula sea lógica"""
        for enrollment in self:
            if enrollment.start_date and enrollment.enrollment_date:
                if enrollment.enrollment_date > enrollment.start_date + timedelta(
                    days=30
                ):
                    raise ValidationError(
                        _(
                            "La fecha de matrícula no puede ser más de 30 días "
                            "después del inicio del grupo."
                        )
                    )

    @api.model
    def create(self, vals):
        """
        Auto-genera el código de matrícula al crear.
        Inicializa la progresión académica en la primera fase/nivel del plan.
        """
        if vals.get("code", "/") == "/":
            vals["code"] = (
                self.env["ir.sequence"].next_by_code("benglish.enrollment") or "/"
            )

        # ═══════════════════════════════════════════════════════════════════════
        # INICIALIZACIÓN DE PROGRESIÓN ACADÉMICA
        # ═══════════════════════════════════════════════════════════════════════
        # CORREGIDO: Usa fases y niveles desde el plan de estudio (Many2many)
        # No usa program_id directamente en fases/niveles (no existe ese campo)
        
        if vals.get("plan_id") and not vals.get("current_phase_id") and not vals.get("current_level_id"):
            plan = self.env["benglish.plan"].browse(vals["plan_id"])
            if plan:
                # Obtener primera fase del plan (Many2many ordenado por secuencia)
                first_phase = plan.phase_ids.sorted(lambda p: p.sequence)[:1]
                if first_phase:
                    vals["current_phase_id"] = first_phase.id

                    # Obtener primer nivel de esa fase
                    first_level = first_phase.level_ids.sorted(lambda l: l.sequence)[:1]
                    if first_level:
                        vals["current_level_id"] = first_level.id

                # Obtener primera asignatura del plan (Many2many ordenado por secuencia)
                first_subject = plan.subject_ids.sorted(lambda s: s.sequence)[:1]
                if first_subject:
                    vals["current_subject_id"] = first_subject.id

        # ═══════════════════════════════════════════════════════════════════════
        # INICIALIZACIÓN DESDE PLAN COMERCIAL (si no hay plan legacy)
        # ═══════════════════════════════════════════════════════════════════════
        if vals.get("commercial_plan_id"):
            commercial_plan = self.env["benglish.commercial.plan"].browse(vals["commercial_plan_id"])
            if commercial_plan:
                # ═══════════════════════════════════════════════════════════════
                # INICIALIZACIÓN DE NIVEL (Feb 2026 - Matrícula por Nivel)
                # ═══════════════════════════════════════════════════════════════
                # Establecer current_level y starting_level desde el plan comercial
                level_start = commercial_plan.level_start or 1
                
                if not vals.get("current_level"):
                    vals["current_level"] = level_start
                    
                if not vals.get("starting_level"):
                    vals["starting_level"] = level_start
                    
                _logger.info(
                    f"[ENROLLMENT] Inicializando matrícula con plan comercial {commercial_plan.name}: "
                    f"current_level={vals.get('current_level')}, starting_level={vals.get('starting_level')}"
                )
                
                # current_level_id para compatibilidad (si existen niveles como registros)
                if not vals.get("current_level_id") and commercial_plan.level_ids:
                    # Obtener el primer nivel del plan comercial (ordenado por secuencia)
                    first_level = commercial_plan.level_ids.sorted(lambda l: (l.sequence, l.id))[:1]
                    if first_level:
                        vals["current_level_id"] = first_level.id
                        # Obtener la fase del nivel
                        if first_level.phase_id:
                            vals["current_phase_id"] = first_level.phase_id.id

        # Crear la matrícula
        enrollment = super(Enrollment, self).create(vals)

        # Actualizar contador de estudiantes en el grupo (solo si hay grupo asignado)
        if enrollment.group_id:
            enrollment._update_group_student_count()

        # Auto-generar registros de progreso para todas las asignaturas del plan (legacy)
        if enrollment.plan_id and not enrollment.enrollment_progress_ids:
            enrollment._generate_progress_records()

        # ═══════════════════════════════════════════════════════════════════════
        # GENERACIÓN AUTOMÁTICA DE PROGRESO COMERCIAL (Feb 2026)
        # ═══════════════════════════════════════════════════════════════════════
        if enrollment.commercial_plan_id and not enrollment.commercial_progress_ids:
            enrollment._generate_commercial_progress()

        return enrollment

    def write(self, vals):
        """Actualiza contadores al modificar estado y regenera progreso comercial si cambia el plan."""
        # Guardar los planes comerciales anteriores para comparar
        old_commercial_plans = {rec.id: rec.commercial_plan_id.id for rec in self}
        
        result = super(Enrollment, self).write(vals)

        # Si cambia el estado, actualizar contadores
        if "state" in vals or "attendance_type" in vals:
            for enrollment in self:
                enrollment._update_group_student_count()

        # ═══════════════════════════════════════════════════════════════════════
        # REGENERAR PROGRESO COMERCIAL SI CAMBIA EL PLAN (Feb 2026)
        # ═══════════════════════════════════════════════════════════════════════
        if "commercial_plan_id" in vals:
            for enrollment in self:
                old_plan_id = old_commercial_plans.get(enrollment.id)
                new_plan_id = enrollment.commercial_plan_id.id if enrollment.commercial_plan_id else False
                
                # Solo regenerar si el plan realmente cambió
                if old_plan_id != new_plan_id and new_plan_id:
                    enrollment._generate_commercial_progress()

        return result

    def unlink(self):
        """
        ELIMINACIÓN FORZADA HABILITADA PARA GESTORES.
        Permite eliminar matrículas sin restricciones para facilitar gestión.
        """
        # Permitir eliminación forzada sin validaciones
        return super(Enrollment, self).unlink()

    def _update_group_student_count(self):
        """Actualiza el contador de estudiantes en el grupo"""
        self.ensure_one()
        if self.group_id:
            # Contar estudiantes activos
            active_enrollments = self.search(
                [
                    ("group_id", "=", self.group_id.id),
                    ("state", "in", ["enrolled", "in_progress"]),
                ]
            )

            # Actualizar contadores por modalidad
            presential_count = len(
                active_enrollments.filtered(lambda e: e.attendance_type == "presential")
            )
            virtual_count = len(
                active_enrollments.filtered(lambda e: e.attendance_type == "virtual")
            )

            self.group_id.write(
                {
                    "current_presential": presential_count,
                    "current_virtual": virtual_count,
                }
            )

    def _generate_progress_records(self):
        """
        Genera registros de progreso para todas las asignaturas del plan.
        Se ejecuta automáticamente al crear una matrícula nueva.
        También genera los estados de requisitos académicos (R22).
        
        NUEVO (Feb 2026): También genera registros de progreso del Plan Comercial
        si la matrícula tiene un plan comercial asignado.
        """
        self.ensure_one()

        if not self.plan_id:
            _logger.warning(
                f"No se puede generar progreso para matrícula {self.code}: no hay plan asignado"
            )
            return

        # Obtener todas las asignaturas del programa
        subjects = self.env["benglish.subject"].search(
            [("program_id", "=", self.plan_id.program_id.id)],
            order="level_id, sequence",
        )

        if not subjects:
            _logger.warning(
                f"No se encontraron asignaturas para el programa {self.plan_id.program_id.name}"
            )
            return

        # Crear registros de progreso
        progress_vals = []
        for subject in subjects:
            progress_vals.append(
                {
                    "enrollment_id": self.id,
                    "subject_id": subject.id,
                    "state": "pending",
                }
            )

        if progress_vals:
            self.env["benglish.enrollment.progress"].create(progress_vals)
            _logger.info(
                f"[ENROLLMENT] Generados {len(progress_vals)} registros de progreso "
                f"para matrícula {self.code} - Plan: {self.plan_id.name}"
            )

        # R22: Generar estados de requisitos para el nivel actual
        self._generate_requirement_statuses()
        
        # NUEVO (Feb 2026): Generar progreso del Plan Comercial
        self._generate_commercial_progress()

    def _generate_requirement_statuses(self, level=None):
        """
        Genera los estados de requisitos académicos para la matrícula (R22).
        Se basa en los requisitos configurados en el plan de estudios.

        Args:
            level: Si se especifica, genera solo para ese nivel.
                   Si no, genera para el nivel actual de la matrícula.
        """
        self.ensure_one()
        RequirementStatus = self.env["benglish.student.requirement.status"]
        target_level = level or self.current_level_id

        if not target_level:
            _logger.info(
                f"[ENROLLMENT] No hay nivel para generar requisitos en matrícula {self.code}"
            )
            return

        created = RequirementStatus.generate_for_enrollment(self, target_level)
        if created:
            self.message_post(
                body=_(
                    "Se generaron %d estados de requisitos para el nivel %s."
                ) % (len(created), target_level.name),
                subject=_("Requisitos Generados"),
            )

    def _generate_commercial_progress(self):
        """
        Genera los registros de progreso del Plan Comercial para la matrícula.
        Se ejecuta automáticamente al crear la matrícula si tiene plan comercial.
        
        NUEVA LÓGICA (Feb 2026):
        - Usa el modelo benglish.student.commercial.progress
        - Crea un registro por cada nivel del plan comercial
        - Define las cantidades esperadas según la configuración del plan
        """
        self.ensure_one()
        
        if not self.commercial_plan_id:
            _logger.debug(
                f"No se genera progreso comercial para matrícula {self.code}: "
                "no tiene plan comercial asignado"
            )
            return
        
        CommercialProgress = self.env["benglish.student.commercial.progress"]
        commercial_plan = self.commercial_plan_id
        
        # Obtener los niveles del plan comercial
        levels = commercial_plan.level_ids
        
        if not levels:
            _logger.warning(
                f"Plan comercial {commercial_plan.name} no tiene niveles configurados"
            )
            return
        
        progress_records = []
        
        for idx, level in enumerate(levels, start=commercial_plan.level_start):
            # Obtener requisitos para este nivel desde el plan comercial
            requirements = commercial_plan.get_requirements_for_level(idx)
            
            # Verificar si ya existe un registro de progreso para este nivel
            existing = CommercialProgress.search([
                ("enrollment_id", "=", self.id),
                ("level_id", "=", level.id),
            ], limit=1)
            
            if existing:
                # Actualizar los valores esperados si cambiaron
                existing.write({
                    'expected_selection': requirements.get('selection', 0),
                    'expected_oral_test': requirements.get('oral_test', 0),
                    'expected_electives': requirements.get('elective', 0),
                    'expected_regular': requirements.get('regular', 0),
                    'expected_bskills': requirements.get('bskills', 0),
                })
            else:
                # Crear nuevo registro de progreso
                progress_records.append({
                    'enrollment_id': self.id,
                    'level_id': level.id,
                    'expected_selection': requirements.get('selection', 0),
                    'expected_oral_test': requirements.get('oral_test', 0),
                    'expected_electives': requirements.get('elective', 0),
                    'expected_regular': requirements.get('regular', 0),
                    'expected_bskills': requirements.get('bskills', 0),
                })
        
        if progress_records:
            CommercialProgress.create(progress_records)
            _logger.info(
                f"[ENROLLMENT] Generados {len(progress_records)} registros de progreso comercial "
                f"para matrícula {self.code} - Plan Comercial: {commercial_plan.name}"
            )
            
            self.message_post(
                body=_(
                    "Se generaron %d registros de progreso para el Plan Comercial '%s' "
                    "(Total asignaturas: %d)"
                ) % (len(progress_records), commercial_plan.name, commercial_plan.total_subjects),
                subject=_("Progreso Comercial Generado"),
            )

    def action_advance_level(self):
        """
        Avanza manualmente el nivel del estudiante (Feb 2026 - Matrícula por Nivel).
        
        REGLAS DE NEGOCIO:
        1. Verifica que el nivel actual esté completado en el progreso comercial
        2. Verifica que el Bcheck del nivel actual esté completado (prerrequisito)
        3. Incrementa current_level en 1
        4. Valida que no exceda el nivel máximo del plan comercial
        5. Actualiza current_level_id y current_phase_id para compatibilidad
        """
        self.ensure_one()

        if not self.commercial_plan_id:
            raise ValidationError(
                _("❌ No hay plan comercial asignado. No se puede avanzar de nivel.")
            )

        if not self.current_level:
            raise ValidationError(
                _("❌ No hay nivel actual definido. No se puede avanzar.")
            )

        # Verificar que no exceda el nivel máximo del plan
        if self.current_level >= self.commercial_plan_id.level_end:
            raise ValidationError(
                _(
                    "🎓 ¡PLAN COMPLETADO!\n\n"
                    "El estudiante ya está en el nivel máximo del plan comercial (%d).\n"
                    "No hay más niveles disponibles en el plan '%s'."
                ) % (self.commercial_plan_id.level_end, self.commercial_plan_id.name)
            )

        # Verificar que el Bcheck del nivel actual esté completado
        if not self.bcheck_current_level_completed:
            raise ValidationError(
                _(
                    "❌ BCHECK NO COMPLETADO\n\n"
                    "No se puede avanzar al siguiente nivel porque el Bcheck "
                    "(prerrequisito) del nivel %d no está completado.\n\n"
                    "💡 El estudiante debe completar el Bcheck antes de avanzar de nivel."
                ) % self.current_level
            )

        # Verificar completitud del nivel actual en progreso comercial
        current_level_progress = self.commercial_progress_ids.filtered(
            lambda p: p.level_sequence == self.current_level
        )
        
        if current_level_progress:
            progress = current_level_progress[0]
            if progress.level_status != 'completed':
                raise ValidationError(
                    _(
                        "❌ NIVEL NO COMPLETADO\n\n"
                        "No se puede avanzar porque el nivel %d no está completado.\n\n"
                        "📊 Estado actual:\n"
                        "   • Total esperado: %d\n"
                        "   • Completado: %d\n"
                        "   • Pendiente: %d\n"
                        "   • Porcentaje: %.1f%%\n\n"
                        "💡 Complete todas las asignaturas del nivel antes de avanzar."
                    ) % (
                        self.current_level,
                        progress.expected_total,
                        progress.completed_total,
                        progress.pending_total,
                        progress.progress_percentage,
                    )
                )

        # Todo validado - Avanzar al siguiente nivel
        new_level = self.current_level + 1
        
        _logger.info(
            f"[ENROLLMENT] Avanzando nivel para {self.code}: "
            f"{self.current_level} → {new_level}"
        )
        
        # Actualizar nivel actual (campo entero principal)
        vals_to_update = {
            'current_level': new_level,
        }
        
        # Actualizar current_level_id para compatibilidad (si existe nivel con esa secuencia)
        if self.commercial_plan_id.level_ids:
            new_level_record = self.commercial_plan_id.level_ids.filtered(
                lambda l: l.sequence == new_level
            )
            if new_level_record:
                vals_to_update['current_level_id'] = new_level_record[0].id
                if new_level_record[0].phase_id:
                    vals_to_update['current_phase_id'] = new_level_record[0].phase_id.id
        
        self.write(vals_to_update)

        # Generar requisitos para el nuevo nivel si hay un record de nivel
        if self.current_level_id:
            self._generate_requirement_statuses(level=self.current_level_id)

        # Log en chatter
        self.message_post(
            body=_(
                "⬆️ AVANCE DE NIVEL\n\n"
                "El estudiante ha avanzado del nivel %d al nivel %d.\n"
                "Plan comercial: %s"
            ) % (self.current_level - 1, self.current_level, self.commercial_plan_id.name),
            subject=_("Avance de Nivel"),
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("✅ Nivel Avanzado"),
                "message": _("El estudiante ha avanzado al nivel %d.") % self.current_level,
                "type": "success",
                "sticky": False,
            },
        }

    def action_advance_to_next_subject(self):
        """
        Avanza el estudiante a la siguiente asignatura del plan.
        Actualiza current_subject_id, current_level_id y current_phase_id según corresponda.
        """
        self.ensure_one()

        if not self.current_subject_id:
            raise ValidationError(
                _("No hay asignatura actual definida. No se puede avanzar.")
            )

        # Buscar siguiente asignatura en el programa (ya no dependen del nivel)
        next_subject = self.env["benglish.subject"].search(
            [
                ("program_id", "=", self.plan_id.program_id.id),
                ("sequence", ">", self.current_subject_id.sequence),
            ],
            order="sequence ASC",
            limit=1,
        )

        if next_subject:
            # Hay más asignaturas en el programa
            self.write({"current_subject_id": next_subject.id})
            return

        # No hay más asignaturas - plan completado
        raise ValidationError(
            _(
                "✅ ¡Felicitaciones! El estudiante ha completado todas las asignaturas del plan de estudios.\n"
                "No hay más asignaturas disponibles para avanzar."
            )
        )

    def action_submit(self):
        """Envía la matrícula para aprobación"""
        for enrollment in self:
            if enrollment.state == "draft":
                enrollment.write({"state": "pending"})

    def _update_student_academic_info(self):
        """
        Actualiza la información académica del estudiante basándose en la matrícula.

        Este método se ejecuta al aprobar la matrícula y actualiza:
        - Programa actual
        - Plan de estudio actual

        LÓGICA INTELIGENTE:
        - Si la matrícula tiene program_id/plan_id, los usa directamente
        - Si NO tiene program_id/plan_id, los DERIVA desde subject_id
        - Esto permite matricular estudiantes sin información académica previa

        Nota: current_level_id y current_phase_id son campos computados que se
        actualizan automáticamente desde active_enrollment_ids.

        ARQUITECTURA:
        - Método privado y desacoplado
        - NO valida información académica previa
        - Solo actualiza información INFORMATIVA
        - Se ejecuta DESPUÉS de aprobar, no antes
        """
        self.ensure_one()

        student = self.student_id

        # Valores a actualizar en el estudiante
        vals_to_update = {}
        vals_enrollment_update = {}  # Para actualizar la matrícula misma

        # 1. Determinar programa (desde matrícula o derivar desde subject)
        program_to_use = self.program_id
        if not program_to_use and self.subject_id:
            # Derivar programa desde asignatura
            program_to_use = self.subject_id.program_id
            if program_to_use:
                vals_enrollment_update["program_id"] = program_to_use.id
                _logger.info(
                    f"[ENROLLMENT] Programa derivado desde asignatura: {program_to_use.name}"
                )

        if program_to_use:
            vals_to_update["program_id"] = program_to_use.id

        # 2. Determinar plan (desde matrícula o inferir desde programa)
        plan_to_use = self.plan_id
        if not plan_to_use and program_to_use:
            # Intentar obtener el plan activo del programa
            # Usar el primer plan activo encontrado
            plan_to_use = self.env["benglish.plan"].search(
                [("program_id", "=", program_to_use.id), ("active", "=", True)],
                limit=1,
            )
            if plan_to_use:
                vals_enrollment_update["plan_id"] = plan_to_use.id
                _logger.info(
                    f"[ENROLLMENT] Plan inferido desde programa: {plan_to_use.name}"
                )

        if plan_to_use:
            vals_to_update["plan_id"] = plan_to_use.id

        # Actualizar la matrícula si se derivaron valores
        if vals_enrollment_update:
            self.write(vals_enrollment_update)

        # Aplicar actualización al estudiante si hay cambios
        if vals_to_update:
            student.write(vals_to_update)

            # CRÍTICO: Invalidar caché para que active_enrollment_ids se recalcule
            student.invalidate_recordset(["active_enrollment_ids"])

            # Forzar recálculo de campos computados (fase, nivel, asignatura)
            student._compute_current_academic_info()

            # Log informativo
            _logger.info(
                f"[ENROLLMENT APPROVED] Información académica actualizada para estudiante {student.name} "
                f"(Programa: {self.program_id.name if self.program_id else 'N/A'}, "
                f"Plan: {self.plan_id.name if self.plan_id else 'N/A'})"
            )

    def action_approve(self):
        """Aprueba la matrícula"""
        for enrollment in self:
            if enrollment.state == "pending":
                # Verificar prerrequisitos antes de aprobar
                if enrollment.subject_id and enrollment.subject_id.prerequisite_ids:
                    prereq_check = enrollment.subject_id.check_prerequisites_completed(
                        enrollment.student_id
                    )

                    # Si no cumple prerrequisitos y no hay override autorizado
                    if (
                        not prereq_check["completed"]
                        and not enrollment.prerequisite_override
                    ):
                        # Verificar si el usuario actual puede autorizar override
                        can_override = self.env.user.has_group(
                            "benglish_academy.group_academic_coordinator"
                        ) or self.env.user.has_group(
                            "benglish_academy.group_academic_manager"
                        )

                        # Retornar notificación temporal en lugar de ValidationError estático
                        message = prereq_check["message"]
                        if can_override:
                            full_message = _(
                                '⚠️ El estudiante "%s" no cumple con los prerrequisitos para "%s".\n\n'
                                "%s\n\n"
                                "📋 Para aprobar como EXCEPCIÓN:\n"
                                '1. Marcar "Excepción de Prerrequisitos"\n'
                                "2. Justificar la excepción\n"
                                "3. Volver a aprobar"
                            ) % (
                                enrollment.student_id.name,
                                enrollment.subject_id.name,
                                message,
                            )
                        else:
                            full_message = _(
                                '❌ El estudiante "%s" no cumple con los prerrequisitos para "%s".\n\n'
                                "%s\n\n"
                                "Contacte al coordinador para autorizar excepción."
                            ) % (
                                enrollment.student_id.name,
                                enrollment.subject_id.name,
                                message,
                            )

                        return {
                            "type": "ir.actions.client",
                            "tag": "display_notification",
                            "params": {
                                "title": _("Prerrequisitos No Cumplidos"),
                                "message": full_message,
                                "type": "danger",
                                "sticky": True,  # Sticky = True para que tenga botón de cerrar
                                "next": {"type": "ir.actions.act_window_close"},
                            },
                        }

                    # Si hay override, registrar quien lo autorizó
                    if enrollment.prerequisite_override and not enrollment.override_by:
                        enrollment.write({"override_by": self.env.user.id})

                enrollment.write(
                    {
                        "state": "active",  # Nuevo: usar 'active' en lugar de 'enrolled'
                        "approved_date": fields.Date.context_today(self),
                        "approved_by": self.env.user.id,
                    }
                )

                # IMPORTANTE: Actualizar información académica DESPUÉS del write
                # para que active_enrollment_ids incluya esta matrícula
                enrollment._update_student_academic_info()

                # Actualizar estado del estudiante si es su primera matrícula
                if enrollment.student_id.state == "prospect":
                    enrollment.student_id.with_context(
                        origen_cambio_estado="matricula"
                    ).write({"state": "enrolled"})

    def action_start(self):
        """
        Inicia clases - VALIDACIÓN FINANCIERA AQUÍ.

        REGLA DE NEGOCIO:
        - Matrícula (contrato académico) ≠ Pago (estado financiero)
        - Se puede APROBAR matrícula aunque no esté al día en pagos
        - Se valida estado financiero al INICIAR clases
        """
        for enrollment in self:
            # Mapeo de estados legacy
            valid_states = ["enrolled", "active"]
            if enrollment.state not in valid_states:
                continue

            student = enrollment.student_id

            # VALIDACIÓN FINANCIERA
            # Determinar si usar cálculo automático o manual
            al_dia = (
                student.al_dia_en_pagos
                if student.usar_calculo_cartera
                else student.al_dia_en_pagos_manual
            )

            if not al_dia:
                # Verificar si el usuario puede autorizar override financiero
                can_override = self.env.user.has_group(
                    "benglish_academy.group_academic_coordinator"
                ) or self.env.user.has_group("benglish_academy.group_academic_manager")

                if not can_override:
                    raise ValidationError(
                        _(
                            "⛔ ESTADO FINANCIERO NO PERMITE INICIO DE CLASES\n\n"
                            'El estudiante "%s" NO está al día en pagos.\n\n'
                            "💰 Detalles financieros:\n"
                            "   • Monto pendiente: %s\n"
                            "   • Facturas vencidas: %d\n\n"
                            "📋 Acción requerida:\n"
                            "El estudiante debe regularizar su situación financiera "
                            "antes de iniciar clases.\n\n"
                            "💡 Nota: La matrícula está aprobada académicamente, "
                            "pero el inicio está condicionado al pago."
                        )
                        % (
                            student.name,
                            f"{student.currency_id.symbol} {student.monto_pendiente:,.2f}",
                            student.facturas_vencidas_count,
                        )
                    )
                else:
                    # Log de override financiero autorizado
                    enrollment.message_post(
                        body=_(
                            "⚠️ OVERRIDE FINANCIERO AUTORIZADO\n\n"
                            "Inicio de clases aprobado con mora pendiente.\n"
                            "Autorizado por: %s\n"
                            "Monto pendiente: %s"
                        )
                        % (
                            self.env.user.name,
                            f"{student.currency_id.symbol} {student.monto_pendiente:,.2f}",
                        ),
                        subject="Override Financiero",
                    )

            # Actualizar a estado 'active'
            enrollment.write({"state": "active"})

            # Actualizar estado del estudiante
            if enrollment.student_id.state != "active":
                enrollment.student_id.with_context(
                    origen_cambio_estado="matricula"
                ).write({"state": "active"})

    def action_complete(self):
        """
        Marca la matrícula como completada (APROBADA).

        REGLA DE NEGOCIO:
        - Actualiza estado a 'finished'
        - Agrega asignatura a approved_subject_ids del estudiante
        - Actualiza historia académica
        """
        for enrollment in self:
            # Validar estados válidos (mapeo legacy)
            valid_states = ["in_progress", "active"]
            if enrollment.state not in valid_states:
                continue

            # Validar que tenga calificación; intentar inferirla automáticamente
            if not enrollment.final_grade:
                # 1) Si existen notas en enrollment_progress_ids, usar su promedio
                progress_grades = [
                    p.final_grade for p in enrollment.enrollment_progress_ids if p.final_grade not in (None, False)
                ]
                inferred_grade = None

                if progress_grades:
                    try:
                        inferred_grade = float(sum(progress_grades) / len(progress_grades))
                        enrollment.write({"final_grade": inferred_grade})
                        enrollment.message_post(
                            body=_(
                                "Nota final inferida automáticamente a partir de las calificaciones de asignaturas: %.2f"
                            ) % inferred_grade,
                            subject="Auto-inferir nota final",
                        )
                    except Exception:
                        inferred_grade = None

                # 2) Si no hay notas pero todos los progresos están 'completed', asignar nota mínima aprobatoria
                if inferred_grade is None and enrollment.enrollment_progress_ids:
                    all_completed = all(
                        p.state == "completed" for p in enrollment.enrollment_progress_ids
                    )
                    if all_completed:
                        inferred_grade = float(enrollment.min_passing_grade or 0.0)
                        enrollment.write({"final_grade": inferred_grade})
                        enrollment.message_post(
                            body=_(
                                "Nota final establecida automáticamente en nota mínima aprobatoria: %.2f"
                            ) % inferred_grade,
                            subject="Auto-asignar nota mínima",
                        )

                # 3) Si existe resultado de placement test, usarlo como fallback
                if inferred_grade is None and getattr(enrollment, "placement_test_score", None):
                    inferred_grade = float(enrollment.placement_test_score)
                    enrollment.write({"final_grade": inferred_grade})
                    enrollment.message_post(
                        body=_(
                            "Nota final establecida desde Placement Test: %.2f"
                        ) % inferred_grade,
                        subject="Auto-asignar nota Placement Test",
                    )

                # Si aún no pudimos inferir, bloquear la acción
                if not enrollment.final_grade:
                    has_any_grade = any(
                        p.final_grade not in (None, False)
                        for p in enrollment.enrollment_progress_ids
                    )
                    has_completed = any(
                        p.state == "completed"
                        for p in enrollment.enrollment_progress_ids
                    )
                    has_placement = bool(
                        getattr(enrollment, "placement_test_score", None)
                    )
                    if not has_any_grade and not has_completed and not has_placement:
                        return {
                            "type": "ir.actions.client",
                            "tag": "display_notification",
                            "params": {
                                "title": _("Matrícula sin calificación"),
                                "message": _(
                                    "Esta matrícula no tiene calificaciones registradas. "
                                    "Se mantiene en estado activa. "
                                    "Registre la nota final para finalizar."
                                ),
                                "type": "warning",
                                "sticky": False,
                            },
                        }

                    # Log detallado para diagnóstico: por qué no se pudo inferir nota
                    try:
                        progress_info = [
                            {
                                'id': int(p.id),
                                'subject': getattr(p.subject_id, 'name', False),
                                'state': p.state,
                                'final_grade': p.final_grade,
                            }
                            for p in enrollment.enrollment_progress_ids
                        ]
                    except Exception:
                        progress_info = 'error_building_progress_info'

                    _logger.error(
                        "No se pudo inferir final_grade para enrollment id=%s student=%s; placement_test_score=%s; min_passing_grade=%s; progress=%s",
                        getattr(enrollment, 'id', 'n/a'),
                        getattr(enrollment.student_id, 'id', 'n/a'),
                        getattr(enrollment, 'placement_test_score', None),
                        getattr(enrollment, 'min_passing_grade', None),
                        progress_info,
                    )

                    raise ValidationError(
                        _(
                            "⚠️ No se puede completar la matrícula sin calificación final.\n\n"
                            "Por favor, registre la calificación antes de completar."
                        )
                    )

            # Validar que la calificación sea aprobatoria
            if enrollment.final_grade < enrollment.min_passing_grade:
                raise ValidationError(
                    _(
                        "⚠️ La calificación %.2f es REPROBATORIA.\n\n"
                        "Nota mínima requerida: %.2f\n\n"
                        'Use el botón "Reprobar" en su lugar.'
                    )
                    % (enrollment.final_grade, enrollment.min_passing_grade)
                )

            # Actualizar enrollment
            enrollment.write(
                {
                    "state": "finished",
                    "completed_date": fields.Date.context_today(self),
                }
            )

            # CRÍTICO: Agregar asignatura a aprobadas del estudiante
            if enrollment.subject_id:
                enrollment.student_id.write(
                    {"approved_subject_ids": [(4, enrollment.subject_id.id)]}
                )

                # Log en chatter del estudiante
                enrollment.student_id.message_post(
                    body=_(
                        "✅ ASIGNATURA APROBADA\n\n"
                        "Asignatura: %s\n"
                        "Calificación: %.2f\n"
                        "Plan: %s\n"
                        "Matrícula: %s"
                    )
                    % (
                        enrollment.subject_id.name,
                        enrollment.final_grade,
                        (
                            enrollment.plan_frozen_id.name
                            if "plan_frozen_id" in enrollment._fields
                            and enrollment.plan_frozen_id
                            else (
                                enrollment.plan_id.name
                                if enrollment.plan_id
                                else "N/A"
                            )
                        ),
                        enrollment.code,
                    ),
                    subject="Asignatura Aprobada",
                )

    def action_fail(self):
        """
        Marca la matrícula como reprobada.

        REGLA DE NEGOCIO:
        - Actualiza estado a 'finished'
        - NO agrega asignatura a approved_subject_ids
        - Registra en historia académica
        """
        for enrollment in self:
            # Validar estados válidos (mapeo legacy)
            valid_states = ["in_progress", "active"]
            if enrollment.state not in valid_states:
                continue

            # Actualizar enrollment
            enrollment.write(
                {
                    "state": "finished",
                    "completed_date": fields.Date.context_today(self),
                }
            )

            # NO agregar a approved_subject_ids
            # Log en chatter del estudiante
            enrollment.student_id.message_post(
                body=_(
                    "❌ ASIGNATURA REPROBADA\n\n"
                    "Asignatura: %s\n"
                    "Calificación: %.2f\n"
                    "Nota mínima: %.2f\n"
                    "Matrícula: %s"
                )
                % (
                    enrollment.subject_id.name,
                    enrollment.final_grade or 0.0,
                    enrollment.min_passing_grade,
                    enrollment.code,
                ),
                subject="Asignatura Reprobada",
            )

    def action_homologate(self):
        """
        Homologa/Convalida la asignatura.

        RF-04: Permite reconocer asignaturas cursadas en otra institución
        o convalidar conocimientos previos.

        REGLA DE NEGOCIO:
        - Requiere justificación obligatoria
        - Marca como homologada y aprobada
        - Agrega a approved_subject_ids (permite avanzar)
        - Requiere permisos de coordinador/manager
        """
        # Verificar permisos
        if not (
            self.env.user.has_group("benglish_academy.group_academic_coordinator")
            or self.env.user.has_group("benglish_academy.group_academic_manager")
        ):
            raise ValidationError(
                _("Solo coordinadores académicos pueden homologar asignaturas.")
            )

        for enrollment in self:
            # Validar que no esté ya homologada
            if enrollment.state == "homologated":
                raise ValidationError(_("La matrícula ya está homologada."))

            # Validar justificación obligatoria
            if not enrollment.homologation_reason:
                raise ValidationError(
                    _("Debe proporcionar una justificación para la homologación.")
                )

            # Actualizar matrícula
            enrollment.write(
                {
                    "state": "homologated",
                    "is_approved": True,
                    "homologation_date": fields.Date.context_today(self),
                    "homologated_by": self.env.user.id,
                    "completed_date": fields.Date.context_today(self),
                }
            )

            # Agregar a asignaturas aprobadas (permite avanzar)
            if enrollment.subject_id not in enrollment.student_id.approved_subject_ids:
                enrollment.student_id.write(
                    {"approved_subject_ids": [(4, enrollment.subject_id.id)]}
                )

            # Log en chatter del estudiante
            enrollment.student_id.message_post(
                body=_(
                    "✅ ASIGNATURA HOMOLOGADA\n\n"
                    "Asignatura: %s\n"
                    "Homologada por: %s\n"
                    "Justificación: %s\n"
                    "Fecha: %s"
                )
                % (
                    enrollment.subject_id.name,
                    self.env.user.name,
                    enrollment.homologation_reason,
                    fields.Date.to_string(enrollment.homologation_date),
                ),
                subject="Asignatura Homologada",
            )

    def action_withdraw(self):
        """Retira al estudiante de la asignatura"""
        for enrollment in self:
            if enrollment.state in ["enrolled", "in_progress"]:
                enrollment.write(
                    {
                        "state": "withdrawn",
                        "withdrawal_date": fields.Date.context_today(self),
                    }
                )

    def action_cancel(self):
        """Cancela la matrícula"""
        for enrollment in self:
            if enrollment.state in ["draft", "pending"]:
                enrollment.write({"state": "cancelled"})

    def action_set_to_draft(self):
        """Regresa la matrícula a borrador"""
        for enrollment in self:
            enrollment.write({"state": "draft"})

    def action_suspend(self):
        """
        Suspende la matrícula (usado por congelamientos).

        REGLA DE NEGOCIO:
        - Solo se pueden suspender matrículas activas
        - Al suspender, se mantiene el contrato pero se pausa la actividad académica
        - Usado automáticamente por el sistema de congelamientos
        """
        for enrollment in self:
            if enrollment.state != "active":
                raise ValidationError(
                    _(
                        "⚠️ Solo se pueden suspender matrículas en estado ACTIVO.\n\n"
                        "Estado actual: %s"
                    )
                    % dict(enrollment._fields["state"].selection).get(
                        enrollment.state, enrollment.state
                    )
                )

            enrollment.write({"state": "suspended"})

            # Log
            enrollment.message_post(
                body=_("⏸️ Matrícula suspendida (congelamiento iniciado)"),
                subject="Matrícula Suspendida",
            )

    def action_reactivate(self):
        """
        Reactiva una matrícula suspendida (usado al finalizar congelamientos).

        REGLA DE NEGOCIO:
        - Solo se pueden reactivar matrículas suspendidas
        - Valida que el estudiante esté al día en pagos antes de reactivar
        """
        for enrollment in self:
            if enrollment.state != "suspended":
                raise ValidationError(
                    _(
                        "⚠️ Solo se pueden reactivar matrículas en estado SUSPENDIDO.\n\n"
                        "Estado actual: %s"
                    )
                    % dict(enrollment._fields["state"].selection).get(
                        enrollment.state, enrollment.state
                    )
                )

            # Validar estado financiero antes de reactivar
            student = enrollment.student_id
            al_dia = (
                student.al_dia_en_pagos
                if student.usar_calculo_cartera
                else student.al_dia_en_pagos_manual
            )

            if not al_dia:
                # Permitir override por coordinador
                can_override = self.env.user.has_group(
                    "benglish_academy.group_academic_coordinator"
                )

                if not can_override:
                    raise ValidationError(
                        _(
                            "⛔ NO SE PUEDE REACTIVAR - MORA PENDIENTE\n\n"
                            'El estudiante "%s" NO está al día en pagos.\n\n'
                            "El estudiante debe regularizar antes de reactivar la matrícula."
                        )
                        % student.name
                    )
                else:
                    enrollment.message_post(
                        body=_("⚠️ Reactivación autorizada con mora pendiente por %s")
                        % self.env.user.name,
                        subject="Override Financiero en Reactivación",
                    )

            enrollment.write({"state": "active"})

            # Log
            enrollment.message_post(
                body=_("▶️ Matrícula reactivada (congelamiento finalizado)"),
                subject="Matrícula Reactivada",
            )

    def action_view_student(self):
        """Abre la vista del estudiante"""
        self.ensure_one()
        return {
            "name": _("Estudiante: %s") % self.student_id.name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.student",
            "res_id": self.student_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_group(self):
        """Abre la vista del grupo"""
        self.ensure_one()
        if not self.group_id:
            raise ValidationError(_("Esta matrícula no tiene un grupo asignado."))
        return {
            "name": _("Grupo: %s") % self.group_id.name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.group",
            "res_id": self.group_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_sessions(self):
        """Abre las sesiones del grupo (por asignatura y sede)"""
        self.ensure_one()
        if not self.group_id:
            raise ValidationError(_("Esta matrícula no tiene un grupo asignado."))
        return {
            "name": _("Sesiones: %s") % self.group_id.name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.class.session",
            "view_mode": "list,form,calendar",
            "domain": [
                ("subject_id", "=", self.subject_id.id),
                ("campus_id", "=", self.campus_id.id),
            ],
            "context": {
                "default_subject_id": self.subject_id.id,
                "default_campus_id": self.campus_id.id,
            },
        }

    def action_view_commercial_progress(self):
        """
        Abre la vista de progreso comercial del estudiante por nivel.
        Muestra el detalle de asignaturas esperadas vs completadas.
        """
        self.ensure_one()
        if not self.commercial_plan_id:
            raise ValidationError(_("Esta matrícula no tiene un plan comercial asignado."))
        
        return {
            "name": _("Progreso Comercial: %s") % self.student_id.name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.student.commercial.progress",
            "view_mode": "list,form",
            "domain": [("enrollment_id", "=", self.id)],
            "context": {
                "default_enrollment_id": self.id,
                "create": False,
            },
        }

    def action_regenerate_commercial_progress(self):
        """
        Regenera los registros de progreso comercial para esta matrícula.
        Útil si el plan comercial cambió o si hay inconsistencias.
        """
        self.ensure_one()
        if not self.commercial_plan_id:
            raise ValidationError(_("Esta matrícula no tiene un plan comercial asignado."))
        
        self._generate_commercial_progress()
        
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Progreso Regenerado"),
                "message": _("Se regeneraron los registros de progreso comercial."),
                "type": "success",
                "sticky": False,
            }
        }


