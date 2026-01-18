# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AcademicLevel(models.Model):
    """
    Modelo para gestionar los Niveles Académicos.
    Un nivel pertenece a una fase y contiene asignaturas.
    """

    _name = "benglish.level"
    _description = "Nivel Académico"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "phase_id, sequence, name"
    _rec_name = "complete_name"

    # Campos básicos
    name = fields.Char(
        string="Nombre del Nivel",
        required=True,
        tracking=True,
        help="Nombre del nivel académico (ej: Nivel 1, Básico, etc.)",
    )
    code = fields.Char(
        string="Código",
        required=True,
        copy=False,
        default="/",
        tracking=True,
        help="Código único identificador del nivel (generado automáticamente o manual)",
    )
    sequence = fields.Integer(
        string="Secuencia",
        default=10,
        required=True,
        help="Orden del nivel dentro de la fase",
    )
    complete_name = fields.Char(
        string="Nombre Completo",
        compute="_compute_complete_name",
        store=True,
        help="Nombre completo incluyendo fase, plan y programa",
    )
    description = fields.Text(
        string="Descripción", help="Descripción detallada del nivel académico"
    )

    # Información académica
    duration_weeks = fields.Integer(
        string="Duración (semanas)", help="Duración estimada en semanas del nivel"
    )
    total_hours = fields.Float(
        string="Total de Horas", help="Total de horas académicas del nivel"
    )
    max_unit = fields.Integer(
        string="Unidad Máxima",
        default=0,
        help="Unidad máxima alcanzada al completar este nivel (ej: 4, 8, 12, 16, 20, 24). "
        "Usado para validar habilitación de Oral Tests.",
    )

    # Estado
    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Si está inactivo, el nivel no estará disponible para nuevas operaciones",
    )

    # Relaciones
    phase_id = fields.Many2one(
        comodel_name="benglish.phase",
        string="Fase",
        required=True,
        ondelete="restrict",
        help="Fase a la que pertenece este nivel (compartida por todos los planes del programa)",
    )
    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        related="phase_id.program_id",
        store=True,
        help="Programa asociado (a través de la fase) - compartido por todos los planes",
    )
    plan_ids = fields.Many2many(
        comodel_name="benglish.plan",
        relation="benglish_level_plan_rel",
        column1="level_id",
        column2="plan_id",
        string="Planes de Estudio",
        compute="_compute_plan_ids",
        store=False,
        help="Planes que usan este nivel (todos los del programa)",
    )
    subject_ids = fields.One2many(
        comodel_name="benglish.subject",
        inverse_name="level_id",
        string="Asignaturas",
        help="Asignaturas que componen este nivel",
    )

    # Campos computados
    subject_count = fields.Integer(
        string="Número de Asignaturas", compute="_compute_subject_count", store=True
    )

    # Restricciones SQL
    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "El código del nivel debe ser único."),
        (
            "sequence_phase_unique",
            "UNIQUE(phase_id, sequence)",
            "La secuencia debe ser única dentro de la fase.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Genera el código automáticamente según el tipo de programa."""
        for vals in vals_list:
            if vals.get("code", "/") == "/":
                phase_id = vals.get("phase_id")
                if phase_id:
                    phase = self.env["benglish.phase"].browse(phase_id)
                    program_type = phase.program_id.program_type
                    if program_type == "bekids":
                        vals["code"] = (
                            self.env["ir.sequence"].next_by_code(
                                "benglish.level.bekids"
                            )
                            or "/"
                        )
                    elif program_type == "bteens":
                        vals["code"] = (
                            self.env["ir.sequence"].next_by_code(
                                "benglish.level.bteens"
                            )
                            or "/"
                        )
                    elif program_type == "benglish":
                        vals["code"] = (
                            self.env["ir.sequence"].next_by_code(
                                "benglish.level.benglish"
                            )
                            or "/"
                        )
                    else:
                        vals["code"] = (
                            f"LEVEL-{self.env['ir.sequence'].next_by_code('benglish.level') or '001'}"
                        )
        return super().create(vals_list)

    @api.depends("name", "phase_id.complete_name")
    def _compute_complete_name(self):
        """Calcula el nombre completo del nivel incluyendo la fase."""
        for level in self:
            if level.phase_id:
                level.complete_name = f"{level.phase_id.complete_name} / {level.name}"
            else:
                level.complete_name = level.name

    @api.depends("subject_ids")
    def _compute_subject_count(self):
        """Calcula el número de asignaturas asociadas."""
        for level in self:
            level.subject_count = len(level.subject_ids)

    @api.depends("phase_id.program_id")
    def _compute_plan_ids(self):
        """Calcula los planes que usan este nivel (todos los del programa)."""
        for level in self:
            if level.phase_id and level.phase_id.program_id:
                level.plan_ids = self.env["benglish.plan"].search(
                    [("program_id", "=", level.phase_id.program_id.id)]
                )
            else:
                level.plan_ids = False

    @api.constrains("code")
    def _check_code_format(self):
        """Valida el formato del código del nivel."""
        for level in self:
            if (
                level.code
                and not level.code.replace("_", "").replace("-", "").isalnum()
            ):
                raise ValidationError(
                    _(
                        "El código del nivel solo puede contener letras, números, guiones y guiones bajos."
                    )
                )

    def action_view_subjects(self):
        """Acción para ver las asignaturas del nivel."""
        self.ensure_one()
        return {
            "name": _("Asignaturas del Nivel"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.subject",
            "view_mode": "list,form",
            "domain": [("level_id", "=", self.id)],
            "context": {"default_level_id": self.id},
        }
