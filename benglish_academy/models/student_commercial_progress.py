# -*- coding: utf-8 -*-
"""
Modelo de Progreso del Plan Comercial del Estudiante.

Registra el progreso DINÁMICO del estudiante según su plan comercial.
A diferencia del progreso estático del plan de estudios, este se construye
basándose en las clases realmente ejecutadas y cumplidas.

Flujo:
1. Estudiante se matricula con un Plan Comercial
2. Se crean los requisitos esperados por nivel (desde commercial_plan)
3. A medida que el estudiante ve clases, se marca el cumplimiento
4. El progreso se calcula dinámicamente comparando cumplido vs esperado
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class StudentCommercialProgress(models.Model):
    """
    Progreso del Estudiante en Plan Comercial.
    
    Registra el progreso dinámico del estudiante según su plan comercial.
    Se actualiza automáticamente cuando se registra cumplimiento académico.
    
    Campos clave:
    - expected_*: Cantidades esperadas según el plan comercial
    - completed_*: Cantidades completadas (clases ejecutadas con cumplimiento)
    - pending_*: Cantidades pendientes (expected - completed)
    """

    _name = "benglish.student.commercial.progress"
    _description = "Progreso del Estudiante en Plan Comercial"
    _inherit = ["mail.thread"]
    _order = "enrollment_id, level_sequence"
    _rec_name = "display_name"

    # ═══════════════════════════════════════════════════════════════════════════
    # IDENTIFICACIÓN
    # ═══════════════════════════════════════════════════════════════════════════

    display_name = fields.Char(
        string="Nombre",
        compute="_compute_display_name",
        store=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RELACIONES PRINCIPALES
    # ═══════════════════════════════════════════════════════════════════════════

    enrollment_id = fields.Many2one(
        comodel_name="benglish.enrollment",
        string="Matrícula",
        required=True,
        ondelete="cascade",
        index=True,
        help="Matrícula del estudiante",
    )

    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        related="enrollment_id.student_id",
        store=True,
        readonly=True,
    )

    commercial_plan_id = fields.Many2one(
        comodel_name="benglish.commercial.plan",
        string="Plan Comercial",
        related="enrollment_id.commercial_plan_id",
        store=True,
        readonly=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CONTEXTO ACADÉMICO (Nivel actual)
    # ═══════════════════════════════════════════════════════════════════════════

    level_id = fields.Many2one(
        comodel_name="benglish.level",
        string="Nivel",
        required=True,
        ondelete="restrict",
        index=True,
        help="Nivel académico de este registro de progreso",
    )

    level_sequence = fields.Integer(
        string="Número de Nivel",
        related="level_id.sequence",
        store=True,
        help="Secuencia del nivel (1, 2, 3... 24)",
    )

    phase_id = fields.Many2one(
        comodel_name="benglish.phase",
        string="Fase",
        related="level_id.phase_id",
        store=True,
        readonly=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CANTIDADES ESPERADAS (del Plan Comercial)
    # ═══════════════════════════════════════════════════════════════════════════

    expected_selection = fields.Integer(
        string="Selección Esperada",
        default=0,
        help="Cantidad de asignaturas de selección/B-check esperadas según el plan comercial",
    )

    expected_oral_test = fields.Integer(
        string="Oral Tests Esperados",
        default=0,
        help="Cantidad de oral tests esperados según el plan comercial",
    )

    expected_electives = fields.Integer(
        string="Electivas Esperadas",
        default=0,
        help="Cantidad de electivas esperadas según el plan comercial",
    )

    expected_regular = fields.Integer(
        string="Regulares Esperadas",
        default=0,
        help="Cantidad de asignaturas regulares esperadas según el plan comercial",
    )

    expected_bskills = fields.Integer(
        string="B-Skills Esperados",
        default=0,
        help="Cantidad de B-Skills esperados según el plan comercial",
    )

    expected_total = fields.Integer(
        string="Total Esperado",
        compute="_compute_expected_total",
        store=True,
        help="Total de asignaturas esperadas en este nivel",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CANTIDADES COMPLETADAS (cumplimiento real)
    # ═══════════════════════════════════════════════════════════════════════════

    completed_selection = fields.Integer(
        string="Selección Completada",
        default=0,
        help="Cantidad de asignaturas de selección/B-check completadas",
    )

    completed_oral_test = fields.Integer(
        string="Oral Tests Completados",
        default=0,
        help="Cantidad de oral tests completados",
    )

    completed_electives = fields.Integer(
        string="Electivas Completadas",
        default=0,
        help="Cantidad de electivas completadas",
    )

    completed_regular = fields.Integer(
        string="Regulares Completadas",
        default=0,
        help="Cantidad de asignaturas regulares completadas",
    )

    completed_bskills = fields.Integer(
        string="B-Skills Completados",
        default=0,
        help="Cantidad de B-Skills completados",
    )

    completed_total = fields.Integer(
        string="Total Completado",
        compute="_compute_completed_total",
        store=True,
        help="Total de asignaturas completadas en este nivel",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CANTIDADES PENDIENTES (calculadas)
    # ═══════════════════════════════════════════════════════════════════════════

    pending_selection = fields.Integer(
        string="Selección Pendiente",
        compute="_compute_pending",
        store=True,
    )

    pending_oral_test = fields.Integer(
        string="Oral Tests Pendientes",
        compute="_compute_pending",
        store=True,
    )

    pending_electives = fields.Integer(
        string="Electivas Pendientes",
        compute="_compute_pending",
        store=True,
    )

    pending_regular = fields.Integer(
        string="Regulares Pendientes",
        compute="_compute_pending",
        store=True,
    )

    pending_bskills = fields.Integer(
        string="B-Skills Pendientes",
        compute="_compute_pending",
        store=True,
    )

    pending_total = fields.Integer(
        string="Total Pendiente",
        compute="_compute_pending",
        store=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # PORCENTAJE DE AVANCE
    # ═══════════════════════════════════════════════════════════════════════════

    progress_percentage = fields.Float(
        string="% Avance",
        compute="_compute_progress_percentage",
        store=True,
        digits=(5, 2),
        help="Porcentaje de avance en este nivel",
    )

    level_status = fields.Selection(
        selection=[
            ("not_started", "No Iniciado"),
            ("in_progress", "En Progreso"),
            ("completed", "Completado"),
        ],
        string="Estado del Nivel",
        compute="_compute_level_status",
        store=True,
        help="Estado de avance en este nivel",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RESTRICCIONES SQL
    # ═══════════════════════════════════════════════════════════════════════════

    _sql_constraints = [
        (
            "unique_enrollment_level",
            "UNIQUE(enrollment_id, level_id)",
            "Solo puede haber un registro de progreso por nivel por matrícula.",
        ),
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS COMPUTE
    # ═══════════════════════════════════════════════════════════════════════════

    @api.depends("enrollment_id.student_id.name", "level_id.name")
    def _compute_display_name(self):
        for record in self:
            student_name = record.student_id.name if record.student_id else "Sin estudiante"
            level_name = record.level_id.name if record.level_id else "Sin nivel"
            record.display_name = f"{student_name} - {level_name}"

    @api.depends(
        "expected_selection", "expected_oral_test", "expected_electives",
        "expected_regular", "expected_bskills"
    )
    def _compute_expected_total(self):
        for record in self:
            record.expected_total = (
                record.expected_selection + record.expected_oral_test +
                record.expected_electives + record.expected_regular +
                record.expected_bskills
            )

    @api.depends(
        "completed_selection", "completed_oral_test", "completed_electives",
        "completed_regular", "completed_bskills"
    )
    def _compute_completed_total(self):
        for record in self:
            record.completed_total = (
                record.completed_selection + record.completed_oral_test +
                record.completed_electives + record.completed_regular +
                record.completed_bskills
            )

    @api.depends(
        "expected_selection", "expected_oral_test", "expected_electives",
        "expected_regular", "expected_bskills",
        "completed_selection", "completed_oral_test", "completed_electives",
        "completed_regular", "completed_bskills"
    )
    def _compute_pending(self):
        for record in self:
            record.pending_selection = max(0, record.expected_selection - record.completed_selection)
            record.pending_oral_test = max(0, record.expected_oral_test - record.completed_oral_test)
            record.pending_electives = max(0, record.expected_electives - record.completed_electives)
            record.pending_regular = max(0, record.expected_regular - record.completed_regular)
            record.pending_bskills = max(0, record.expected_bskills - record.completed_bskills)
            record.pending_total = (
                record.pending_selection + record.pending_oral_test +
                record.pending_electives + record.pending_regular +
                record.pending_bskills
            )

    @api.depends("expected_total", "completed_total")
    def _compute_progress_percentage(self):
        for record in self:
            if record.expected_total > 0:
                record.progress_percentage = (record.completed_total / record.expected_total) * 100
            else:
                record.progress_percentage = 0.0

    @api.depends("completed_total", "expected_total")
    def _compute_level_status(self):
        for record in self:
            if record.completed_total == 0:
                record.level_status = "not_started"
            elif record.completed_total >= record.expected_total:
                record.level_status = "completed"
            else:
                record.level_status = "in_progress"

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS DE NEGOCIO
    # ═══════════════════════════════════════════════════════════════════════════

    def update_from_compliance(self, subject_type, increment=1):
        """
        Actualiza el progreso cuando se registra un cumplimiento.
        
        Args:
            subject_type: Tipo de asignatura ('selection', 'oral_test', 'elective', etc.)
            increment: Cantidad a incrementar (normalmente 1)
        """
        self.ensure_one()
        
        field_map = {
            'selection': 'completed_selection',
            'oral_test': 'completed_oral_test',
            'elective': 'completed_electives',
            'regular': 'completed_regular',
            'bskills': 'completed_bskills',
        }
        
        if subject_type in field_map:
            field_name = field_map[subject_type]
            current_value = getattr(self, field_name)
            setattr(self, field_name, current_value + increment)
            _logger.info(
                f"Progreso actualizado para {self.student_id.name} nivel {self.level_id.name}: "
                f"{field_name} = {current_value + increment}"
            )

    @api.model
    def create_progress_for_enrollment(self, enrollment):
        """
        Crea los registros de progreso para una matrícula basándose en su plan comercial.
        
        Args:
            enrollment: Registro de matrícula (benglish.enrollment)
        """
        if not enrollment.commercial_plan_id:
            _logger.warning(f"Matrícula {enrollment.code} no tiene plan comercial asignado")
            return
        
        commercial_plan = enrollment.commercial_plan_id
        
        # Obtener los niveles del plan comercial
        levels = commercial_plan.level_ids
        
        if not levels:
            _logger.warning(f"Plan comercial {commercial_plan.name} no tiene niveles configurados")
            return
        
        progress_records = []
        
        for idx, level in enumerate(levels, start=1):
            # Obtener requisitos para este nivel
            requirements = commercial_plan.get_requirements_for_level(idx)
            
            # Verificar si ya existe un registro de progreso para este nivel
            existing = self.search([
                ("enrollment_id", "=", enrollment.id),
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
                    'enrollment_id': enrollment.id,
                    'level_id': level.id,
                    'expected_selection': requirements.get('selection', 0),
                    'expected_oral_test': requirements.get('oral_test', 0),
                    'expected_electives': requirements.get('elective', 0),
                    'expected_regular': requirements.get('regular', 0),
                    'expected_bskills': requirements.get('bskills', 0),
                })
        
        if progress_records:
            self.create(progress_records)
            _logger.info(
                f"Creados {len(progress_records)} registros de progreso para matrícula {enrollment.code}"
            )


class EnrollmentCommercialProgressMixin(models.AbstractModel):
    """
    Mixin para agregar funcionalidad de Plan Comercial a la matrícula.
    """
    _name = "benglish.enrollment.commercial.progress.mixin"
    _description = "Mixin para Progreso de Plan Comercial en Matrícula"

    # Relación con los registros de progreso por nivel
    commercial_progress_ids = fields.One2many(
        comodel_name="benglish.student.commercial.progress",
        inverse_name="enrollment_id",
        string="Progreso por Nivel (Plan Comercial)",
        help="Detalle del progreso del estudiante por cada nivel según el plan comercial",
    )

    # Totales consolidados
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

    @api.depends("commercial_progress_ids.expected_total", "commercial_progress_ids.completed_total")
    def _compute_commercial_progress_totals(self):
        for record in self:
            total_expected = sum(record.commercial_progress_ids.mapped('expected_total'))
            total_completed = sum(record.commercial_progress_ids.mapped('completed_total'))
            
            record.commercial_total_expected = total_expected
            record.commercial_total_completed = total_completed
            
            if total_expected > 0:
                record.commercial_progress_percentage = (total_completed / total_expected) * 100
            else:
                record.commercial_progress_percentage = 0.0
