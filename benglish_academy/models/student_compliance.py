# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class StudentCompliance(models.Model):
    """
    Cumplimiento Académico del Estudiante.

    Registra qué requisito fue cumplido con qué clase ejecutada.
    Es el vínculo entre la ejecución de una clase y la actualización
    del estado de requisitos del estudiante.

    Equivalencia con el modelo de datos:
    - Tabla: Estudiante_Cumplimiento

    Reglas implementadas:
    - R22: Generación de cumplimiento al cerrar clase ejecutada
    - R23: Asociación cumplimiento → estado de requisito
    - R24: Actualización de estado de requisito a 'completed'
    - R31: No duplicar cumplimiento para el mismo requisito
    """

    _name = "benglish.student.compliance"
    _description = "Cumplimiento Académico del Estudiante"
    _inherit = ["mail.thread"]
    _order = "compliance_date desc, id desc"
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

    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        required=True,
        ondelete="cascade",
        index=True,
        readonly=True,
        help="Estudiante que cumplió el requisito",
    )

    enrollment_id = fields.Many2one(
        comodel_name="benglish.enrollment",
        string="Matrícula",
        required=True,
        ondelete="cascade",
        index=True,
        readonly=True,
        help="Matrícula activa del estudiante",
    )

    requirement_status_id = fields.Many2one(
        comodel_name="benglish.student.requirement.status",
        string="Estado de Requisito",
        required=True,
        ondelete="restrict",
        index=True,
        readonly=True,
        help="Estado de requisito que se cumplió (R23)",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ORIGEN DEL CUMPLIMIENTO
    # ═══════════════════════════════════════════════════════════════════════════

    class_execution_id = fields.Many2one(
        comodel_name="benglish.class.execution",
        string="Clase Ejecutada",
        ondelete="restrict",
        index=True,
        readonly=True,
        help="Clase ejecutada que generó este cumplimiento",
    )

    session_id = fields.Many2one(
        comodel_name="benglish.academic.session",
        string="Sesión",
        ondelete="set null",
        readonly=True,
        help="Sesión de clase asociada",
    )

    subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura",
        required=True,
        ondelete="restrict",
        readonly=True,
        help="Asignatura que se contabilizó para el cumplimiento",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # INFORMACIÓN DEL CUMPLIMIENTO
    # ═══════════════════════════════════════════════════════════════════════════

    compliance_type = fields.Selection(
        selection=[
            ("course", "Prerrequisito Completado"),
            ("elective", "Electiva Contabilizada"),
            ("choice", "Opción Seleccionada"),
            ("unlockable", "Asignatura Desbloqueada Completada"),
            ("manual", "Registro Manual"),
        ],
        string="Tipo de Cumplimiento",
        required=True,
        readonly=True,
        help="Tipo de requisito que se cumplió",
    )

    compliance_date = fields.Datetime(
        string="Fecha de Cumplimiento",
        required=True,
        default=fields.Datetime.now,
        readonly=True,
        index=True,
        help="Fecha y hora en que se registró el cumplimiento",
    )

    # Contexto académico (denormalizado para consultas)
    level_id = fields.Many2one(
        comodel_name="benglish.level",
        string="Nivel",
        related="requirement_status_id.level_id",
        store=True,
        readonly=True,
    )

    phase_id = fields.Many2one(
        comodel_name="benglish.phase",
        string="Fase",
        related="requirement_status_id.phase_id",
        store=True,
        readonly=True,
    )

    notes = fields.Text(
        string="Observaciones",
        help="Notas sobre el cumplimiento",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RESTRICCIONES SQL (R31: No duplicar cumplimiento)
    # ═══════════════════════════════════════════════════════════════════════════

    _sql_constraints = [
        (
            "unique_student_requirement",
            "UNIQUE(student_id, requirement_status_id, subject_id)",
            "Ya existe un registro de cumplimiento para este requisito, "
            "estudiante y asignatura. No se permite duplicación (R31).",
        ),
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # CAMPOS COMPUTADOS
    # ═══════════════════════════════════════════════════════════════════════════

    @api.depends("student_id", "subject_id", "compliance_type", "compliance_date")
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.student_id:
                parts.append(rec.student_id.name)
            if rec.subject_id:
                parts.append(rec.subject_id.alias or rec.subject_id.name)
            if rec.compliance_type:
                parts.append(
                    dict(self._fields["compliance_type"].selection).get(rec.compliance_type, "")
                )
            rec.display_name = " / ".join(parts) if parts else _("Cumplimiento")

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS DE NEGOCIO
    # ═══════════════════════════════════════════════════════════════════════════

    @api.model
    def register_compliance(
        self,
        student,
        enrollment,
        requirement_status,
        subject,
        class_execution=None,
        session=None,
        notes=None,
    ):
        """
        Registra cumplimiento académico y actualiza el estado del requisito.

        Args:
            student: benglish.student
            enrollment: benglish.enrollment
            requirement_status: benglish.student.requirement.status
            subject: benglish.subject
            class_execution: benglish.class.execution (opcional)
            session: benglish.academic.session (opcional)
            notes: str (opcional)

        Returns:
            benglish.student.compliance record
        """
        # Verificar duplicados (R31)
        existing = self.search([
            ("student_id", "=", student.id),
            ("requirement_status_id", "=", requirement_status.id),
            ("subject_id", "=", subject.id),
        ], limit=1)

        if existing:
            _logger.warning(
                "Cumplimiento duplicado rechazado: estudiante=%s, requisito=%s, asignatura=%s",
                student.name,
                requirement_status.display_name,
                subject.name,
            )
            return existing

        # Determinar tipo de cumplimiento
        type_map = {
            "course": "course",
            "electives": "elective",
            "choice": "choice",
            "unlockable": "unlockable",
        }
        compliance_type = type_map.get(requirement_status.requirement_type, "manual")

        vals = {
            "student_id": student.id,
            "enrollment_id": enrollment.id,
            "requirement_status_id": requirement_status.id,
            "subject_id": subject.id,
            "compliance_type": compliance_type,
            "notes": notes,
        }
        if class_execution:
            vals["class_execution_id"] = class_execution.id
        if session:
            vals["session_id"] = session.id

        compliance = self.create(vals)

        # Actualizar estado del requisito (R24)
        if requirement_status.requirement_type == "electives":
            requirement_status.increment_elective_count(
                session_id=session.id if session else False
            )
        else:
            requirement_status.action_mark_completed(
                session_id=session.id if session else False
            )

        _logger.info(
            "Cumplimiento registrado: %s para estudiante %s (matrícula %s).",
            compliance.display_name,
            student.name,
            enrollment.code,
        )

        return compliance
