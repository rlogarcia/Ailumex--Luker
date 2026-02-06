# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class PlanRequirementOption(models.Model):
    """
    Opciones de Requisito para tipo CHOICE.

    Cada opción representa una asignatura que puede cumplir un requisito
    de tipo CHOICE. El estudiante puede elegir cualquiera de las opciones
    para satisfacer el requisito.

    Equivalencia con el modelo de datos:
    - Tabla: Opcion_Requisitos
    - Campos: Id_Requisito, Id_Asignatura

    Regla implementada:
    - R9C: Opciones válidas para requisitos tipo CHOICE
    """

    _name = "benglish.plan.requirement.option"
    _description = "Opción de Requisito Académico"
    _order = "requirement_id, sequence"
    _rec_name = "display_name"

    # ═══════════════════════════════════════════════════════════════════════════
    # IDENTIFICACIÓN
    # ═══════════════════════════════════════════════════════════════════════════

    display_name = fields.Char(
        string="Nombre",
        compute="_compute_display_name",
        store=True,
        help="Nombre descriptivo de la opción",
    )

    sequence = fields.Integer(
        string="Secuencia",
        default=10,
        help="Orden de visualización dentro del grupo de opciones",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RELACIONES
    # ═══════════════════════════════════════════════════════════════════════════

    requirement_id = fields.Many2one(
        comodel_name="benglish.plan.requirement",
        string="Requisito",
        required=True,
        ondelete="cascade",
        index=True,
        help="Requisito de tipo CHOICE al que pertenece esta opción",
    )

    plan_id = fields.Many2one(
        comodel_name="benglish.plan",
        string="Plan de Estudios",
        related="requirement_id.plan_id",
        store=True,
        readonly=True,
        help="Plan de estudios (heredado del requisito)",
    )

    level_id = fields.Many2one(
        comodel_name="benglish.level",
        string="Nivel",
        related="requirement_id.level_id",
        store=True,
        readonly=True,
        help="Nivel académico (heredado del requisito)",
    )

    subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura",
        required=True,
        ondelete="restrict",
        index=True,
        help="Asignatura que cumple como opción para este requisito CHOICE",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RESTRICCIONES
    # ═══════════════════════════════════════════════════════════════════════════

    _sql_constraints = [
        (
            "unique_requirement_subject",
            "UNIQUE(requirement_id, subject_id)",
            "La asignatura ya está registrada como opción en este requisito.",
        ),
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # CAMPOS COMPUTADOS
    # ═══════════════════════════════════════════════════════════════════════════

    @api.depends("requirement_id", "subject_id")
    def _compute_display_name(self):
        for option in self:
            if option.subject_id:
                option.display_name = option.subject_id.alias or option.subject_id.name
            else:
                option.display_name = _("Nueva Opción")

    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDACIONES
    # ═══════════════════════════════════════════════════════════════════════════

    @api.constrains("requirement_id")
    def _check_requirement_type(self):
        """Solo se permiten opciones en requisitos de tipo CHOICE."""
        for option in self:
            if option.requirement_id and option.requirement_id.requirement_type != "choice":
                raise ValidationError(
                    _("Solo se pueden agregar opciones a requisitos de tipo CHOICE.\n\n"
                      "El requisito '%s' es de tipo '%s'.")
                    % (
                        option.requirement_id.display_name,
                        dict(option.requirement_id._fields["requirement_type"].selection).get(
                            option.requirement_id.requirement_type
                        ),
                    )
                )
