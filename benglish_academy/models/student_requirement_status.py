# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class StudentRequirementStatus(models.Model):
    """
    Estado de Requisitos del Estudiante.

    Instancia los requisitos académicos del plan para cada estudiante.
    Se genera automáticamente al crear la matrícula o al avanzar de nivel.

    Equivalencia con el modelo de datos:
    - Tabla: Estado_Requisitos_Estudiante
    - Campos: Id_Matricula, Id_Requisito, Id_Nivel, Estado, Tipo

    Reglas implementadas:
    - R22: Creación automática de estado de requisitos desde plantilla
    - R23: Asociación a nivel (Id_Nivel)
    - R24: Preparación para actualización de estados
    - R9A/R9B/R9C: Tipos instanciados desde Requisitos del plan
    """

    _name = "benglish.student.requirement.status"
    _description = "Estado de Requisito del Estudiante"
    _inherit = ["mail.thread"]
    _order = "enrollment_id, level_id, requirement_type, sequence"
    _rec_name = "display_name"

    # ═══════════════════════════════════════════════════════════════════════════
    # IDENTIFICACIÓN
    # ═══════════════════════════════════════════════════════════════════════════

    display_name = fields.Char(
        string="Nombre",
        compute="_compute_display_name",
        store=True,
        help="Nombre descriptivo del estado de requisito",
    )

    sequence = fields.Integer(
        string="Secuencia",
        default=10,
        help="Orden de visualización",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RELACIÓN CON MATRÍCULA Y ESTUDIANTE
    # ═══════════════════════════════════════════════════════════════════════════

    enrollment_id = fields.Many2one(
        comodel_name="benglish.enrollment",
        string="Matrícula",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
        help="Matrícula del estudiante",
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

    # ═══════════════════════════════════════════════════════════════════════════
    # RELACIÓN CON REQUISITO PLANTILLA
    # ═══════════════════════════════════════════════════════════════════════════

    requirement_id = fields.Many2one(
        comodel_name="benglish.plan.requirement",
        string="Requisito Base",
        ondelete="set null",
        index=True,
        help="Requisito del plan desde el cual se generó este estado (plantilla)",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CONTEXTO ACADÉMICO
    # ═══════════════════════════════════════════════════════════════════════════

    level_id = fields.Many2one(
        comodel_name="benglish.level",
        string="Nivel",
        required=True,
        ondelete="restrict",
        index=True,
        help="Nivel académico al que corresponde este requisito (R23)",
    )

    phase_id = fields.Many2one(
        comodel_name="benglish.phase",
        string="Fase",
        related="level_id.phase_id",
        store=True,
        readonly=True,
        help="Fase académica (heredada del nivel)",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # TIPO E INFORMACIÓN DEL REQUISITO (copiados de la plantilla)
    # ═══════════════════════════════════════════════════════════════════════════

    requirement_type = fields.Selection(
        selection=[
            ("course", "Prerrequisito Obligatorio (COURSE)"),
            ("electives", "Electivas Requeridas (ELECTIVES)"),
            ("choice", "Grupo de Opciones (CHOICE)"),
            ("unlockable", "Asignatura Desbloqueable (UNLOCKABLE)"),
        ],
        string="Tipo de Requisito",
        required=True,
        index=True,
        help="Tipo de requisito instanciado para el estudiante",
    )

    subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura",
        ondelete="restrict",
        help="Asignatura del requisito (para COURSE y UNLOCKABLE)",
    )

    min_selection = fields.Integer(
        string="Mínimo Requerido",
        default=0,
        help="Cantidad mínima de electivas/opciones que el estudiante debe completar",
    )

    max_selection = fields.Integer(
        string="Máximo Permitido",
        default=0,
        help="Cantidad máxima de electivas/opciones que el estudiante puede tomar",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ESTADO DEL REQUISITO PARA EL ESTUDIANTE
    # ═══════════════════════════════════════════════════════════════════════════

    state = fields.Selection(
        selection=[
            ("pending", "Pendiente"),
            ("in_progress", "En Progreso"),
            ("completed", "Completado"),
            ("locked", "Bloqueado"),
        ],
        string="Estado",
        default="pending",
        required=True,
        tracking=True,
        index=True,
        help="pending: Disponible pero no completado.\n"
             "in_progress: Iniciado (el estudiante está cursando).\n"
             "completed: Requisito cumplido.\n"
             "locked: No visible hasta cumplir condición de desbloqueo.",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CONTADOR DE PROGRESO (para ELECTIVES)
    # ═══════════════════════════════════════════════════════════════════════════

    completed_count = fields.Integer(
        string="Completadas",
        default=0,
        help="Cantidad de electivas completadas (para tipo ELECTIVES)",
    )

    progress_percentage = fields.Float(
        string="% Progreso",
        compute="_compute_progress_percentage",
        store=True,
        digits=(5, 2),
        help="Porcentaje de completitud del requisito",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # TRAZABILIDAD
    # ═══════════════════════════════════════════════════════════════════════════

    completed_date = fields.Datetime(
        string="Fecha de Completado",
        readonly=True,
        help="Fecha y hora en que se completó el requisito",
    )

    completed_by_session_id = fields.Many2one(
        comodel_name="benglish.academic.session",
        string="Completado en Sesión",
        ondelete="set null",
        readonly=True,
        help="Sesión de clase que generó el cumplimiento de este requisito",
    )

    notes = fields.Text(
        string="Observaciones",
        help="Notas sobre el estado del requisito",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RESTRICCIONES SQL
    # ═══════════════════════════════════════════════════════════════════════════

    _sql_constraints = [
        (
            "unique_enrollment_requirement",
            "UNIQUE(enrollment_id, requirement_id)",
            "No se puede duplicar el estado de un requisito para la misma matrícula.",
        ),
        (
            "unique_enrollment_level_type_subject",
            "UNIQUE(enrollment_id, level_id, requirement_type, subject_id)",
            "Ya existe un estado de requisito para este nivel, tipo y asignatura "
            "en esta matrícula.",
        ),
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # CAMPOS COMPUTADOS
    # ═══════════════════════════════════════════════════════════════════════════

    @api.depends("student_id", "level_id", "requirement_type", "subject_id", "state")
    def _compute_display_name(self):
        type_labels = dict(self._fields["requirement_type"].selection)
        state_labels = dict(self._fields["state"].selection)
        for rec in self:
            parts = []
            if rec.student_id:
                parts.append(rec.student_id.name)
            if rec.level_id:
                parts.append(rec.level_id.name)
            if rec.requirement_type:
                parts.append(type_labels.get(rec.requirement_type, ""))
            if rec.subject_id:
                parts.append(rec.subject_id.alias or rec.subject_id.name)
            if rec.state:
                parts.append(f"[{state_labels.get(rec.state, '')}]")
            rec.display_name = " / ".join(parts) if parts else _("Estado de Requisito")

    @api.depends("requirement_type", "completed_count", "min_selection", "state")
    def _compute_progress_percentage(self):
        for rec in self:
            if rec.state == "completed":
                rec.progress_percentage = 100.0
            elif rec.requirement_type == "electives" and rec.min_selection > 0:
                rec.progress_percentage = min(
                    (rec.completed_count / rec.min_selection) * 100.0, 100.0
                )
            elif rec.state == "in_progress":
                rec.progress_percentage = 50.0
            else:
                rec.progress_percentage = 0.0

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS DE NEGOCIO
    # ═══════════════════════════════════════════════════════════════════════════

    @api.model
    def generate_for_enrollment(self, enrollment, level=None):
        """
        Genera los estados de requisitos para una matrícula basándose
        en los requisitos del plan (R22).

        Args:
            enrollment: Registro benglish.enrollment
            level: Registro benglish.level (si None, usa el nivel actual de la matrícula)

        Returns:
            Recordset de estados generados
        """
        if not enrollment or not enrollment.plan_id:
            _logger.warning("No se pueden generar requisitos sin matrícula o plan.")
            return self.browse()

        target_level = level or enrollment.current_level_id
        if not target_level:
            _logger.warning(
                "No se pueden generar requisitos sin nivel para matrícula %s.",
                enrollment.code,
            )
            return self.browse()

        # Buscar requisitos del plan para el nivel
        requirements = self.env["benglish.plan.requirement"].search([
            ("plan_id", "=", enrollment.plan_id.id),
            ("level_id", "=", target_level.id),
            ("active", "=", True),
        ])

        if not requirements:
            _logger.info(
                "No hay requisitos configurados para plan %s, nivel %s.",
                enrollment.plan_id.name,
                target_level.name,
            )
            return self.browse()

        created = self.browse()
        for req in requirements:
            # Verificar que no exista ya
            existing = self.search([
                ("enrollment_id", "=", enrollment.id),
                ("requirement_id", "=", req.id),
            ], limit=1)
            if existing:
                continue

            # Determinar estado inicial
            initial_state = "pending"
            if req.requirement_type == "unlockable":
                initial_state = "locked"

            vals = {
                "enrollment_id": enrollment.id,
                "requirement_id": req.id,
                "level_id": target_level.id,
                "requirement_type": req.requirement_type,
                "subject_id": req.subject_id.id if req.subject_id else False,
                "min_selection": req.min_selection,
                "max_selection": req.max_selection,
                "state": initial_state,
                "sequence": req.sequence,
            }
            created |= self.create(vals)

        _logger.info(
            "Generados %d estados de requisitos para matrícula %s, nivel %s.",
            len(created),
            enrollment.code,
            target_level.name,
        )
        return created

    def action_mark_in_progress(self):
        """Marca un requisito como en progreso."""
        for rec in self:
            if rec.state == "pending":
                rec.write({"state": "in_progress"})

    def action_mark_completed(self, session_id=None):
        """Marca un requisito como completado."""
        for rec in self:
            if rec.state in ("pending", "in_progress"):
                vals = {
                    "state": "completed",
                    "completed_date": fields.Datetime.now(),
                }
                if session_id:
                    vals["completed_by_session_id"] = session_id
                rec.write(vals)

                # Verificar desbloqueos: si este es un COURSE, desbloquear UNLOCKABLE del mismo nivel
                if rec.requirement_type == "course":
                    rec._check_unlockables()

    def _check_unlockables(self):
        """
        Verifica si al completar este COURSE se debe desbloquear algún UNLOCKABLE
        del mismo nivel y matrícula.
        """
        self.ensure_one()
        if self.requirement_type != "course":
            return

        # Buscar UNLOCKABLE del mismo nivel/matrícula que dependen de este COURSE
        unlockables = self.search([
            ("enrollment_id", "=", self.enrollment_id.id),
            ("level_id", "=", self.level_id.id),
            ("requirement_type", "=", "unlockable"),
            ("state", "=", "locked"),
        ])

        for unlockable in unlockables:
            if unlockable.requirement_id and unlockable.requirement_id.unlock_prerequisite_id:
                # Verificar si el prerrequisito de desbloqueo coincide con este requisito completado
                if unlockable.requirement_id.unlock_prerequisite_id == self.requirement_id:
                    unlockable.write({"state": "pending"})
                    _logger.info(
                        "Desbloqueado requisito '%s' para matrícula %s.",
                        unlockable.display_name,
                        self.enrollment_id.code,
                    )
            else:
                # Si no tiene prerrequisito específico, desbloquear si TODOS los COURSE
                # del mismo nivel están completados
                course_statuses = self.search([
                    ("enrollment_id", "=", self.enrollment_id.id),
                    ("level_id", "=", self.level_id.id),
                    ("requirement_type", "=", "course"),
                ])
                all_completed = all(s.state == "completed" for s in course_statuses)
                if all_completed:
                    unlockable.write({"state": "pending"})
                    _logger.info(
                        "Desbloqueado requisito '%s' (todos los COURSE completados) para matrícula %s.",
                        unlockable.display_name,
                        self.enrollment_id.code,
                    )

    def increment_elective_count(self, session_id=None):
        """
        Incrementa el contador de electivas completadas.
        Si alcanza el mínimo, marca como completado.
        """
        self.ensure_one()
        if self.requirement_type != "electives":
            return

        new_count = self.completed_count + 1
        vals = {"completed_count": new_count}

        if self.min_selection > 0 and new_count >= self.min_selection:
            vals["state"] = "completed"
            vals["completed_date"] = fields.Datetime.now()
            if session_id:
                vals["completed_by_session_id"] = session_id

        self.write(vals)
