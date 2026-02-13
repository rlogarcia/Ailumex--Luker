# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class EnrollmentProgress(models.Model):
    """
    Modelo para gestionar el Progreso Académico de un Estudiante dentro de su Plan de Estudios.

    CONCEPTO CLAVE:
    ===============
    Este modelo NO representa una matrícula independiente a una asignatura.
    Representa el PROGRESO/ESTADO del estudiante en cada asignatura DENTRO de su matrícula al plan.

    Un estudiante tiene UNA matrícula (a un plan completo).
    Esa matrícula tiene MÚLTIPLES registros de progreso (uno por cada asignatura del plan).

    Ejemplo:
    --------
    Estudiante: Juan Pérez
    Matrícula: ENROLL-2025-001 → Plan: Benglish General 2025
    Progreso:
        - Asignatura: Basic 1 → Estado: Completado, Nota: 85
        - Asignatura: Basic 2 → Estado: En Progreso, Nota: --
        - Asignatura: Basic 3 → Estado: Pendiente, Nota: --
    """

    _name = "benglish.enrollment.progress"
    _description = "Progreso Académico en Asignaturas"
    _order = "enrollment_id, subject_id"
    _rec_name = "display_name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    display_name = fields.Char(
        string="Nombre",
        compute="_compute_display_name",
        store=True,
        help="Nombre de visualización del progreso",
    )

    # RELACIÓN CON LA MATRÍCULA PRINCIPAL
    enrollment_id = fields.Many2one(
        comodel_name="benglish.enrollment",
        string="Matrícula",
        required=True,
        ondelete="cascade",
        index=True,
        help="Matrícula al plan de estudios a la que pertenece este progreso",
    )
    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        related="enrollment_id.student_id",
        store=True,
        index=True,
        help="Estudiante (heredado de la matrícula)",
    )
    plan_id = fields.Many2one(
        comodel_name="benglish.plan",
        string="Plan de Estudios",
        related="enrollment_id.plan_id",
        store=True,
        help="Plan de estudios (heredado de la matrícula)",
    )

    # ASIGNATURA Y JERARQUÍA ACADÉMICA
    subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura",
        required=True,
        ondelete="cascade",
        index=True,
        help="Asignatura del plan de estudios",
    )
    
    # Tipo de asignatura (relacionado desde la asignatura)
    subject_type_id = fields.Many2one(
        comodel_name="benglish.subject.type",
        string="Tipo de Asignatura",
        related="subject_id.subject_type_id",
        store=True,
        help="Tipo de la asignatura",
    )

    # GRUPO Y CONFIGURACIÓN ACADÉMICA
    group_id = fields.Many2one(
        comodel_name="benglish.group",
        string="Grupo Asignado",
        ondelete="cascade",
        help="Grupo en el que el estudiante cursa esta asignatura",
    )
    coach_id = fields.Many2one(
        comodel_name="benglish.coach",
        string="Coach/Docente",
        related="group_id.coach_id",
        store=True,
        help="Docente que imparte la asignatura",
    )
    campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Sede",
        related="group_id.campus_id",
        store=True,
        help="Sede donde se cursa la asignatura",
    )

    # MODALIDAD DE ASISTENCIA
    delivery_mode = fields.Selection(
        selection=[
            ("presential", "Presencial"),
            ("virtual", "Virtual"),
            ("hybrid", "Híbrido"),
        ],
        string="Modalidad",
        help="Modalidad en la que el estudiante cursa esta asignatura",
    )
    attendance_type = fields.Selection(
        selection=[
            ("presential", "Presencial"),
            ("virtual", "Virtual (Remoto)"),
        ],
        string="Tipo de Asistencia",
        help="Tipo de asistencia específico (para modalidad híbrida)",
    )

    # ESTADO DEL PROGRESO EN LA ASIGNATURA
    state = fields.Selection(
        selection=[
            ("pending", "Pendiente"),
            ("in_progress", "En Progreso"),
            ("completed", "Completado"),
            ("failed", "Reprobado"),
            ("withdrawn", "Retirado"),
        ],
        string="Estado",
        default="pending",
        required=True,
        index=True,
        help="Estado del estudiante en esta asignatura",
    )

    # FECHAS
    start_date = fields.Date(
        string="Fecha de Inicio",
        help="Fecha en que el estudiante comenzó esta asignatura",
    )
    end_date = fields.Date(
        string="Fecha de Finalización",
        help="Fecha en que el estudiante completó esta asignatura",
    )

    # CALIFICACIONES Y ASISTENCIA
    final_grade = fields.Float(
        string="Calificación Final",
        digits=(5, 2),
        help="Calificación final obtenida (0-100)",
    )
    attendance_percentage = fields.Float(
        string="% Asistencia",
        digits=(5, 2),
        help="Porcentaje de asistencia a clases",
    )
    absences_count = fields.Integer(
        string="Inasistencias",
        help="Número de inasistencias registradas",
    )

    # PRERREQUISITOS
    prerequisite_ids = fields.Many2many(
        comodel_name="benglish.subject",
        string="Prerrequisitos",
        related="subject_id.prerequisite_ids",
        help="Asignaturas que deben estar aprobadas",
    )
    prerequisites_met = fields.Boolean(
        string="Cumple Prerrequisitos",
        compute="_compute_prerequisites_met",
        store=True,
        help="Indica si el estudiante cumple con todos los prerrequisitos",
    )

    # NOTAS Y COMENTARIOS
    notes = fields.Text(
        string="Observaciones",
        help="Notas adicionales sobre el progreso del estudiante",
    )

    # RESTRICCIONES SQL
    _sql_constraints = [
        (
            "unique_enrollment_subject",
            "UNIQUE(enrollment_id, subject_id)",
            "Ya existe un registro de progreso para esta asignatura en esta matrícula.",
        ),
    ]

    @api.depends("student_id", "subject_id")
    def _compute_display_name(self):
        """Genera el nombre de visualización"""
        for progress in self:
            if progress.student_id and progress.subject_id:
                progress.display_name = (
                    f"{progress.student_id.name} - {progress.subject_id.name}"
                )
            else:
                progress.display_name = "Progreso Académico"

    @api.depends("student_id", "subject_id", "prerequisite_ids")
    def _compute_prerequisites_met(self):
        """Valida si el estudiante cumple con los prerrequisitos"""
        for progress in self:
            if not progress.subject_id or not progress.student_id:
                progress.prerequisites_met = True
                continue

            if not progress.prerequisite_ids:
                progress.prerequisites_met = True
                continue

            # Buscar progreso completado en todas las asignaturas prerrequisito
            completed_prerequisites = self.search(
                [
                    ("student_id", "=", progress.student_id.id),
                    ("subject_id", "in", progress.prerequisite_ids.ids),
                    ("state", "=", "completed"),
                    ("final_grade", ">=", 60),  # Nota mínima aprobatoria
                ]
            )

            progress.prerequisites_met = len(completed_prerequisites) == len(
                progress.prerequisite_ids
            )

    @api.constrains("final_grade")
    def _check_grade_range(self):
        """Valida que la calificación esté en el rango válido"""
        for progress in self:
            if progress.final_grade:
                if progress.final_grade < 0 or progress.final_grade > 100:
                    raise ValidationError(
                        _("La calificación final debe estar entre 0 y 100.")
                    )

    @api.constrains("subject_id", "enrollment_id")
    def _check_subject_belongs_to_plan(self):
        """Valida que la asignatura pertenezca al plan de la matrícula"""
        for progress in self:
            if progress.subject_id and progress.enrollment_id:
                # Verificar que la asignatura pertenece al mismo programa del plan
                subject_program = progress.subject_id.program_id
                plan_program = progress.enrollment_id.plan_id.program_id

                if subject_program != plan_program:
                    raise ValidationError(
                        _(
                            'La asignatura "%s" no pertenece al plan de estudios "%s".\n'
                            "Solo puede registrar progreso en asignaturas del mismo programa."
                        )
                        % (
                            progress.subject_id.name,
                            progress.enrollment_id.plan_id.name,
                        )
                    )

    def action_start(self):
        """Marca la asignatura como en progreso"""
        for progress in self:
            if progress.state == "pending":
                progress.write(
                    {
                        "state": "in_progress",
                        "start_date": fields.Date.context_today(self),
                    }
                )

    def action_complete(self):
        """Marca la asignatura como completada"""
        for progress in self:
            if progress.state == "in_progress":
                if not progress.final_grade or progress.final_grade < 60:
                    raise ValidationError(
                        _(
                            "No se puede completar la asignatura sin una calificación aprobatoria (>= 60)."
                        )
                    )

                progress.write(
                    {
                        "state": "completed",
                        "end_date": fields.Date.context_today(self),
                    }
                )

    def action_fail(self):
        """Marca la asignatura como reprobada"""
        for progress in self:
            if progress.state in ["in_progress", "pending"]:
                progress.write(
                    {
                        "state": "failed",
                        "end_date": fields.Date.context_today(self),
                    }
                )

    def action_withdraw(self):
        """Retira al estudiante de la asignatura"""
        for progress in self:
            if progress.state in ["in_progress", "pending"]:
                progress.write(
                    {
                        "state": "withdrawn",
                        "end_date": fields.Date.context_today(self),
                    }
                )
