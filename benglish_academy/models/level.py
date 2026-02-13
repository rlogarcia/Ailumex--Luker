# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
from ..utils.normalizers import normalize_to_uppercase


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
        readonly=True,
        default="/",
        tracking=True,
        help="Código único identificador del nivel (generado automáticamente)",
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
        help="Fase a la que pertenece este nivel",
    )

    # Restricciones SQL
    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "El código del nivel debe ser único."),
        # NOTA: Se elimina la restricción de secuencia única para dar flexibilidad
        # El campo sequence es solo para ordenar, no necesita ser único
    ]

    def _next_unique_code(self, prefix, seq_code):
        env = self.env
        existing = self.search([("code", "ilike", f"{prefix}%")])
        seq = env["ir.sequence"].search([("code", "=", seq_code)], limit=1)

        if not existing:
            if seq:
                seq.number_next = 1
            return f"{prefix}1"

        max_n = 0
        for rec in existing:
            if not rec.code:
                continue
            m = re.search(r"(\d+)$", rec.code)
            if m:
                try:
                    n = int(m.group(1))
                except Exception:
                    n = 0
                if n > max_n:
                    max_n = n

        next_n = max_n + 1
        if seq and (not seq.number_next or seq.number_next <= next_n):
            seq.number_next = next_n + 1
        return f"{prefix}{next_n}"

    @api.model_create_multi
    def create(self, vals_list):
        """Genera el código automáticamente según el tipo de programa."""
        for vals in vals_list:
            # Normalizar nombre a MAYÚSCULAS
            if "name" in vals and vals["name"]:
                vals["name"] = normalize_to_uppercase(vals["name"])
            
            # Unified simple sequence for levels
            if vals.get("code", "/") == "/":
                vals["code"] = self._next_unique_code("N-", "benglish.level")
        return super().create(vals_list)

    def write(self, vals):
        """Sobrescribe write para normalizar datos a MAYÚSCULAS automáticamente."""
        if "name" in vals and vals["name"]:
            vals["name"] = normalize_to_uppercase(vals["name"])
        return super().write(vals)

    @api.depends("name", "phase_id.complete_name")
    def _compute_complete_name(self):
        """Calcula el nombre completo del nivel incluyendo la fase."""
        for level in self:
            if level.phase_id:
                level.complete_name = f"{level.phase_id.complete_name} / {level.name}"
            else:
                level.complete_name = level.name
