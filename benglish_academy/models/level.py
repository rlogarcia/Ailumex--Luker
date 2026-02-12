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
        help="Fase a la que pertenece este nivel (compartida por todos los planes del programa)",
    )
    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        related="phase_id.program_id",
        store=True,
        help="Programa asociado (a través de la fase)",
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

    @api.depends("subject_ids")
    def _compute_subject_count(self):
        """Calcula el número de asignaturas asociadas."""
        for level in self:
            level.subject_count = len(level.subject_ids)

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

    def compute_max_unit_from_subjects(self):
        """
        Calcula y escribe `max_unit` a partir de las asignaturas activas del nivel.
        Si no hay asignaturas con `unit_number > 0`, deja `max_unit` en 0.
        """
        Subject = self.env["benglish.subject"].sudo()
        for level in self:
            subjects = Subject.search(
                [("level_id", "=", level.id), ("active", "=", True), ("unit_number", ">", 0)]
            )
            if subjects:
                max_unit = max(subjects.mapped("unit_number"))
            else:
                max_unit = 0
            if level.max_unit != max_unit:
                level.write({"max_unit": max_unit})

    @api.model
    def fill_missing_max_units(self):
        """
        Helper para poblar `max_unit` en todos los niveles que actualmente tienen 0.
        - Calcula `max_unit` desde asignaturas del nivel.
        - Si no encuentra asignaturas con unit_number en el nivel, intenta inferir
          desde asignaturas del plan/phase/program asociadas.

        Devuelve una acción cliente que notifica cuántos niveles se actualizaron.
        """
        Level = self.sudo()
        levels = Level.search([("max_unit", "=", 0)])
        updated = 0
        Subject = self.env["benglish.subject"].sudo()

        for lvl in levels:
            # 1) Intentar desde asignaturas del mismo nivel
            subjects = Subject.search(
                [("level_id", "=", lvl.id), ("active", "=", True), ("unit_number", ">", 0)]
            )
            if subjects:
                max_u = max(subjects.mapped("unit_number"))
                if max_u and lvl.max_unit != max_u:
                    lvl.write({"max_unit": max_u})
                    updated += 1
                    continue

            # 2) Intentar desde la fase / programa: buscar asignaturas en niveles de la misma fase
            if lvl.phase_id:
                phase_levels = Level.search([("phase_id", "=", lvl.phase_id.id)])
                subj_phase = Subject.search(
                    [("level_id", "in", phase_levels.ids), ("active", "=", True), ("unit_number", ">", 0)]
                )
                if subj_phase:
                    # tomar el máximo unit_number encontrado en la fase
                    max_u = max(subj_phase.mapped("unit_number"))
                    if max_u and lvl.max_unit != max_u:
                        lvl.write({"max_unit": max_u})
                        updated += 1
                        continue

            # 3) Intentar desde planes asociados al programa
            if lvl.phase_id and lvl.phase_id.program_id:
                program = lvl.phase_id.program_id
                subj_prog = Subject.search(
                    [("program_id", "=", program.id), ("active", "=", True), ("unit_number", ">", 0)]
                )
                if subj_prog:
                    max_u = max(subj_prog.mapped("unit_number"))
                    if max_u and lvl.max_unit != max_u:
                        lvl.write({"max_unit": max_u})
                        updated += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Población de max_unit",
                "message": _("Se actualizaron %d niveles") % updated,
                "type": "success",
                "sticky": False,
            },
        }
