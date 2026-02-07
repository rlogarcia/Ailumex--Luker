# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import re
from odoo.exceptions import ValidationError
from ..utils.normalizers import normalize_to_uppercase


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
        readonly=True,
        default="/",
        tracking=True,
        help="Código único identificador del programa (generado automáticamente)",
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

    def _next_unique_code(self, prefix, seq_code):
        """Calcula el siguiente código libre con prefijo.

        Lógica:
        - Si no hay registros existentes con el prefijo, forzar inicio en 1 y ajustar la secuencia.
        - Si hay registros, tomar el mayor sufijo numérico y devolver prefix+(max+1), y ajustar la secuencia si hace falta.
        """
        env = self.env
        # Buscar registros existentes con el prefijo
        existing = self.search([("code", "ilike", f"{prefix}%")])
        seq = env["ir.sequence"].search([("code", "=", seq_code)], limit=1)

        if not existing:
            # No hay códigos existentes: iniciar desde 1
            if seq:
                seq.number_next = 1
            return f"{prefix}1"

        # Si hay existentes, calcular el mayor sufijo numérico
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
        # Ajustar secuencia para evitar que next_by_code genere un número menor
        if seq and (not seq.number_next or seq.number_next <= next_n):
            seq.number_next = next_n + 1

        return f"{prefix}{next_n}"

    @api.model_create_multi
    def create(self, vals_list):
        """Genera el código automáticamente según el tipo de programa, evitando colisiones."""
        for vals in vals_list:
            # Normalizar nombre a MAYÚSCULAS
            if "name" in vals and vals["name"]:
                vals["name"] = normalize_to_uppercase(vals["name"])
            
            # If no manual code provided, use unified simple sequence but ensure uniqueness
            if vals.get("code", "/") == "/":
                vals["code"] = self._next_unique_code("PRG-", "benglish.program")
        return super().create(vals_list)

    def write(self, vals):
        """Sobrescribe write para normalizar datos a MAYÚSCULAS automáticamente."""
        if "name" in vals and vals["name"]:
            vals["name"] = normalize_to_uppercase(vals["name"])
        return super().write(vals)

    @api.depends("plan_ids")
    def _compute_plan_count(self):
        """Calcula el número de planes de estudio asociados."""
        for program in self:
            program.plan_count = len(program.plan_ids)

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
