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
        string="Planes de Estudio (Legacy)",
        help="Planes de estudio asociados a este programa (modelo legacy)",
    )

    commercial_plan_ids = fields.One2many(
        comodel_name="benglish.commercial.plan",
        inverse_name="program_id",
        string="Planes Comerciales",
        help="Planes comerciales asociados a este programa (nuevo modelo Feb 2026)",
    )

    # Campos computados
    plan_count = fields.Integer(
        string="Planes (Legacy)", compute="_compute_plan_count", store=False
    )

    commercial_plan_count = fields.Integer(
        string="Planes Comerciales", compute="_compute_commercial_plan_count", store=False
    )

    # Restricciones SQL
    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "El código del programa debe ser único."),
    ]

    def _next_unique_code(self, prefix, seq_code):
        """Calcula el siguiente código libre con prefijo, reutilizando huecos.

        Lógica:
        - Busca el primer número disponible (hueco) entre los existentes.
        - Si no hay huecos, usa el siguiente número después del máximo.
        """
        env = self.env
        import re
        
        # Buscar registros existentes con el prefijo
        existing = self.search([("code", "=like", f"{prefix}%")])
        
        if not existing:
            return f"{prefix}1"
        
        # Obtener todos los números usados
        used_numbers = set()
        for rec in existing:
            if rec.code:
                m = re.search(r"(\d+)$", rec.code)
                if m:
                    try:
                        used_numbers.add(int(m.group(1)))
                    except ValueError:
                        pass
        
        if not used_numbers:
            return f"{prefix}1"
        
        # Buscar primer hueco
        for num in range(1, max(used_numbers) + 2):
            if num not in used_numbers:
                return f"{prefix}{num}"
        
        # No debería llegar aquí, pero por seguridad
        return f"{prefix}{max(used_numbers) + 1}"

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
        """Calcula el número de planes de estudio asociados (legacy)."""
        for program in self:
            program.plan_count = len(program.plan_ids)

    @api.depends("commercial_plan_ids")
    def _compute_commercial_plan_count(self):
        """Calcula el número de planes comerciales asociados."""
        for program in self:
            program.commercial_plan_count = len(program.commercial_plan_ids)

    def action_view_plans(self):
        """Acción para ver los planes de estudio del programa (legacy)."""
        self.ensure_one()
        return {
            "name": _("Planes de Estudio (Legacy)"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.plan",
            "view_mode": "list,form",
            "domain": [("program_id", "=", self.id)],
            "context": {"default_program_id": self.id},
        }

    def action_view_commercial_plans(self):
        """Acción para ver los planes comerciales del programa."""
        self.ensure_one()
        return {
            "name": _("Planes Comerciales - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "benglish.commercial.plan",
            "view_mode": "list,form",
            "domain": [("program_id", "=", self.id)],
            "context": {"default_program_id": self.id},
        }
