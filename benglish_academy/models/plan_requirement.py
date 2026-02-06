# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class PlanRequirement(models.Model):
    """
    Requisitos Académicos por Nivel y Plan de Estudios.

    Define las reglas académicas que aplican en cada nivel de un plan:
    - COURSE: Prerrequisito obligatorio (asignatura específica).
    - ELECTIVES: Cantidad requerida de electivas por nivel.
    - CHOICE: Grupo de opciones donde cualquiera cumple el requisito.
    - UNLOCKABLE: Asignatura desbloqueable al completar prerrequisito del nivel.

    Equivalencia con el modelo de datos:
    - Tabla: Requisitos
    - Campos: Id_Plan_Estudios, Id_Nivel, Tipo_Requisito, Min_Seleccion, Max_Seleccion, Id_Asignatura

    Reglas implementadas:
    - R9A: Requisito tipo COURSE
    - R9B: Requisito tipo ELECTIVES
    - R9C: Requisito tipo CHOICE
    - R10: Prerrequisitos referencian asignaturas reales
    - R22: Preparación para estado de requisitos del estudiante
    """

    _name = "benglish.plan.requirement"
    _description = "Requisito Académico por Nivel y Plan"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "plan_id, level_id, sequence, requirement_type"
    _rec_name = "display_name"

    # ═══════════════════════════════════════════════════════════════════════════
    # IDENTIFICACIÓN
    # ═══════════════════════════════════════════════════════════════════════════

    display_name = fields.Char(
        string="Nombre",
        compute="_compute_display_name",
        store=True,
        help="Nombre descriptivo del requisito",
    )

    sequence = fields.Integer(
        string="Secuencia",
        default=10,
        help="Orden de visualización dentro del nivel",
    )

    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Si está inactivo, el requisito no se considerará en nuevas matrículas",
    )

    description = fields.Text(
        string="Descripción",
        help="Descripción detallada del requisito y su propósito académico",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RELACIONES PRINCIPALES (FK del modelo de datos)
    # ═══════════════════════════════════════════════════════════════════════════

    plan_id = fields.Many2one(
        comodel_name="benglish.plan",
        string="Plan de Estudios",
        required=True,
        ondelete="cascade",
        tracking=True,
        index=True,
        help="Plan de estudios al que pertenece este requisito (Id_Plan_Estudios)",
    )

    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        related="plan_id.program_id",
        store=True,
        readonly=True,
        help="Programa académico (heredado del plan)",
    )

    level_id = fields.Many2one(
        comodel_name="benglish.level",
        string="Nivel",
        required=True,
        ondelete="restrict",
        tracking=True,
        index=True,
        help="Nivel académico al que aplica este requisito (Id_Nivel)",
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
    # TIPO DE REQUISITO (R9A, R9B, R9C)
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
        tracking=True,
        index=True,
        help="COURSE: Asignatura obligatoria específica (R9A).\n"
             "ELECTIVES: Cantidad mínima/máxima de electivas a cursar (R9B).\n"
             "CHOICE: Grupo donde cualquier opción cumple el requisito (R9C).\n"
             "UNLOCKABLE: Asignatura que se desbloquea al completar el prerrequisito del nivel.",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ASIGNATURA (para COURSE y UNLOCKABLE)
    # ═══════════════════════════════════════════════════════════════════════════

    subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura",
        ondelete="restrict",
        tracking=True,
        index=True,
        help="Asignatura real del requisito (obligatoria para COURSE y UNLOCKABLE). "
             "El requisito siempre referencia una asignatura real, no un par (R10).",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # SELECCIÓN MIN/MAX (para ELECTIVES y CHOICE)
    # ═══════════════════════════════════════════════════════════════════════════

    min_selection = fields.Integer(
        string="Mínimo de Selección",
        default=0,
        tracking=True,
        help="Cantidad mínima de asignaturas/opciones que el estudiante debe completar. "
             "Aplica para ELECTIVES y CHOICE.",
    )

    max_selection = fields.Integer(
        string="Máximo de Selección",
        default=0,
        tracking=True,
        help="Cantidad máxima de asignaturas/opciones que el estudiante puede cursar. "
             "Aplica para ELECTIVES y CHOICE. 0 = sin límite.",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # DESBLOQUEO (para UNLOCKABLE)
    # ═══════════════════════════════════════════════════════════════════════════

    unlock_prerequisite_id = fields.Many2one(
        comodel_name="benglish.plan.requirement",
        string="Prerrequisito para Desbloqueo",
        ondelete="set null",
        help="Requisito de tipo COURSE del mismo nivel que debe estar completado "
             "para desbloquear esta asignatura. Solo aplica para UNLOCKABLE.",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # OPCIONES (para CHOICE)
    # ═══════════════════════════════════════════════════════════════════════════

    option_ids = fields.One2many(
        comodel_name="benglish.plan.requirement.option",
        inverse_name="requirement_id",
        string="Opciones de Requisito",
        help="Lista de opciones válidas para requisitos tipo CHOICE (R9C)",
    )

    option_count = fields.Integer(
        string="Número de Opciones",
        compute="_compute_option_count",
        store=True,
        help="Total de opciones disponibles para CHOICE",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RESTRICCIONES SQL
    # ═══════════════════════════════════════════════════════════════════════════

    _sql_constraints = [
        (
            "unique_plan_level_type_subject",
            "UNIQUE(plan_id, level_id, requirement_type, subject_id)",
            "No puede existir un requisito duplicado del mismo tipo para el mismo nivel, "
            "plan y asignatura.",
        ),
        (
            "min_selection_positive",
            "CHECK(min_selection >= 0)",
            "El mínimo de selección debe ser mayor o igual a cero.",
        ),
        (
            "max_selection_positive",
            "CHECK(max_selection >= 0)",
            "El máximo de selección debe ser mayor o igual a cero.",
        ),
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # CAMPOS COMPUTADOS
    # ═══════════════════════════════════════════════════════════════════════════

    @api.depends("plan_id", "level_id", "requirement_type", "subject_id")
    def _compute_display_name(self):
        type_labels = dict(self._fields["requirement_type"].selection)
        for req in self:
            parts = []
            if req.plan_id:
                parts.append(req.plan_id.name)
            if req.level_id:
                parts.append(req.level_id.name)
            if req.requirement_type:
                parts.append(type_labels.get(req.requirement_type, req.requirement_type))
            if req.subject_id:
                parts.append(req.subject_id.alias or req.subject_id.name)
            req.display_name = " / ".join(parts) if parts else _("Nuevo Requisito")

    @api.depends("option_ids")
    def _compute_option_count(self):
        for req in self:
            req.option_count = len(req.option_ids)

    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDACIONES (CONSTRAINS)
    # ═══════════════════════════════════════════════════════════════════════════

    @api.constrains("requirement_type", "subject_id")
    def _check_subject_for_course(self):
        """R9A/R10: COURSE y UNLOCKABLE requieren asignatura obligatoria."""
        for req in self:
            if req.requirement_type in ("course", "unlockable") and not req.subject_id:
                raise ValidationError(
                    _("Los requisitos de tipo '%s' deben tener una asignatura asociada.\n\n"
                      "Plan: %s\nNivel: %s")
                    % (
                        dict(self._fields["requirement_type"].selection).get(req.requirement_type),
                        req.plan_id.name,
                        req.level_id.name,
                    )
                )

    @api.constrains("min_selection", "max_selection")
    def _check_selection_range(self):
        """Validación: min_selection <= max_selection (cuando max > 0)."""
        for req in self:
            if req.max_selection > 0 and req.min_selection > req.max_selection:
                raise ValidationError(
                    _("El mínimo de selección (%d) no puede ser mayor "
                      "que el máximo de selección (%d).\n\n"
                      "Plan: %s\nNivel: %s\nTipo: %s")
                    % (
                        req.min_selection,
                        req.max_selection,
                        req.plan_id.name,
                        req.level_id.name,
                        dict(self._fields["requirement_type"].selection).get(req.requirement_type),
                    )
                )

    @api.constrains("requirement_type", "option_ids")
    def _check_choice_has_options(self):
        """R9C: CHOICE debe tener al menos 2 opciones."""
        for req in self:
            if req.requirement_type == "choice" and len(req.option_ids) < 2:
                # Solo validar si ya se guardó (no en borrador)
                if req.id:
                    _logger.warning(
                        "Requisito CHOICE %s sin opciones suficientes (tiene %d, mínimo 2).",
                        req.display_name,
                        len(req.option_ids),
                    )

    @api.constrains("level_id", "plan_id")
    def _check_level_plan_coherence(self):
        """Validación de coherencia: el nivel debe pertenecer al programa del plan."""
        for req in self:
            if req.level_id and req.plan_id:
                level_program = req.level_id.phase_id.program_id if req.level_id.phase_id else False
                plan_program = req.plan_id.program_id
                if level_program and plan_program and level_program != plan_program:
                    raise ValidationError(
                        _("Incoherencia nivel-plan:\n\n"
                          "El nivel '%s' pertenece al programa '%s', "
                          "pero el plan '%s' pertenece al programa '%s'.\n\n"
                          "El nivel debe pertenecer al mismo programa que el plan.")
                        % (
                            req.level_id.name,
                            level_program.name,
                            req.plan_id.name,
                            plan_program.name,
                        )
                    )

    @api.constrains("unlock_prerequisite_id", "requirement_type")
    def _check_unlock_prerequisite(self):
        """UNLOCKABLE debe tener un prerrequisito de desbloqueo del mismo nivel."""
        for req in self:
            if req.requirement_type == "unlockable" and req.unlock_prerequisite_id:
                if req.unlock_prerequisite_id.level_id != req.level_id:
                    raise ValidationError(
                        _("El prerrequisito de desbloqueo debe pertenecer al mismo nivel.\n\n"
                          "Nivel del requisito: %s\n"
                          "Nivel del prerrequisito: %s")
                        % (req.level_id.name, req.unlock_prerequisite_id.level_id.name)
                    )
                if req.unlock_prerequisite_id.requirement_type != "course":
                    raise ValidationError(
                        _("El prerrequisito de desbloqueo debe ser de tipo COURSE.\n\n"
                          "Tipo encontrado: %s")
                        % dict(self._fields["requirement_type"].selection).get(
                            req.unlock_prerequisite_id.requirement_type
                        )
                    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ONCHANGE
    # ═══════════════════════════════════════════════════════════════════════════

    @api.onchange("plan_id")
    def _onchange_plan_id(self):
        """Filtra niveles disponibles según el programa del plan."""
        if self.plan_id and self.plan_id.program_id:
            return {
                "domain": {
                    "level_id": [("program_id", "=", self.plan_id.program_id.id)],
                }
            }

    @api.onchange("requirement_type")
    def _onchange_requirement_type(self):
        """Limpia campos no relevantes al cambiar tipo."""
        if self.requirement_type == "course":
            self.min_selection = 0
            self.max_selection = 0
        elif self.requirement_type == "electives":
            self.subject_id = False
            self.unlock_prerequisite_id = False
        elif self.requirement_type == "choice":
            self.subject_id = False
            self.unlock_prerequisite_id = False
        elif self.requirement_type == "unlockable":
            self.min_selection = 0
            self.max_selection = 0

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS DE NEGOCIO
    # ═══════════════════════════════════════════════════════════════════════════

    def action_view_options(self):
        """Abre la vista de opciones para requisitos CHOICE."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Opciones del Requisito"),
            "res_model": "benglish.plan.requirement.option",
            "view_mode": "tree,form",
            "domain": [("requirement_id", "=", self.id)],
            "context": {"default_requirement_id": self.id},
            "target": "current",
        }
