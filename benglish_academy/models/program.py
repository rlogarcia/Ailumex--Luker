# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AcademicProgram(models.Model):
    """
    Modelo para gestionar los Programas Académicos.
    Un programa representa el nivel más alto de la estructura académica (ej: Programa de Inglés General).
    """

    _name = "benglish.program"
    _description = "Programa Académico"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"
    _rec_name = "name"

    # Campos básicos
    name = fields.Char(
        string="Nombre del Programa",
        required=True,
        tracking=True,
        help="Nombre completo del programa académico",
    )
    code = fields.Char(
        string="Código",
        required=True,
        copy=False,
        default="/",
        tracking=True,
        help="Código único identificador del programa (generado automáticamente o manual)",
    )
    program_type = fields.Selection(
        selection=[
            ("bekids", "Bekids"),
            ("bteens", "B teens"),
            ("benglish", "Benglish"),
            ("other", "Otro"),
        ],
        string="Tipo de Programa",
        required=True,
        default="other",
        tracking=True,
        help="Tipo de programa para generación automática de código",
    )
    sequence = fields.Integer(
        string="Secuencia", default=10, help="Orden de visualización"
    )
    description = fields.Text(
        string="Descripción", help="Descripción detallada del programa académico"
    )

    # Estado
    active = fields.Boolean(
        string="Activo",
        default=True,
        tracking=True,
        help="Si está inactivo, el programa no estará disponible para nuevas operaciones",
    )

    # Relaciones
    plan_ids = fields.One2many(
        comodel_name="benglish.plan",
        inverse_name="program_id",
        string="Planes de Estudio",
        help="Planes de estudio asociados a este programa",
    )

    # Campos computados
    plan_count = fields.Integer(
        string="Número de Planes", compute="_compute_plan_count", store=True
    )

    # Restricciones SQL
    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "El código del programa debe ser único."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Genera el código automáticamente según el tipo de programa."""
        for vals in vals_list:
            if vals.get("code", "/") == "/":
                program_type = vals.get("program_type", "other")
                if program_type == "bekids":
                    vals["code"] = (
                        self.env["ir.sequence"].next_by_code("benglish.program.bekids")
                        or "/"
                    )
                elif program_type == "bteens":
                    vals["code"] = (
                        self.env["ir.sequence"].next_by_code("benglish.program.bteens")
                        or "/"
                    )
                elif program_type == "benglish":
                    vals["code"] = (
                        self.env["ir.sequence"].next_by_code(
                            "benglish.program.benglish"
                        )
                        or "/"
                    )
                else:
                    vals["code"] = (
                        f"PROG-{self.env['ir.sequence'].next_by_code('benglish.program') or '001'}"
                    )
        return super().create(vals_list)

    @api.depends("plan_ids")
    def _compute_plan_count(self):
        """Calcula el número de planes de estudio asociados."""
        for program in self:
            program.plan_count = len(program.plan_ids)

    @api.constrains("code")
    def _check_code_format(self):
        """Valida el formato del código del programa."""
        for program in self:
            if (
                program.code
                and not program.code.replace("_", "").replace("-", "").isalnum()
            ):
                raise ValidationError(
                    _(
                        "El código del programa solo puede contener letras, números, guiones y guiones bajos."
                    )
                )

    def action_view_plans(self):
        """Acción para ver los planes de estudio del programa."""
        self.ensure_one()
        return {
            "name": _("Planes de Estudio"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.plan",
            "view_mode": "list,form",
            "domain": [("program_id", "=", self.id)],
            "context": {"default_program_id": self.id},
        }
