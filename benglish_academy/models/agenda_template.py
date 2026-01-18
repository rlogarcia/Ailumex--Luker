# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AgendaTemplate(models.Model):
    """
    Plantilla de agenda para publicar clases por tipo (Skill, B-check, Oral Test, etc.).
    """

    _name = "benglish.agenda.template"
    _description = "Plantilla de Agenda"
    _order = "program_id, sequence, name"
    _rec_name = "name"

    name = fields.Char(
        string="Nombre Interno",
        required=True,
        help="Nombre interno de la plantilla (ej: Skill 2 - Benglish)",
    )
    code = fields.Char(
        string="Código",
        required=True,
        help="Código técnico único por programa (ej: SKILL_2)",
    )
    sequence = fields.Integer(string="Secuencia", default=10)

    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        ondelete="restrict",
        help="Programa al que aplica la plantilla. Si está vacío, aplica a todos.",
    )

    active = fields.Boolean(string="Activo", default=True)

    subject_category = fields.Selection(
        selection=[
            ("bcheck", "B-check"),
            ("bskills", "B-skills"),
            ("oral_test", "Oral Test"),
            ("placement_test", "Placement Test"),
            ("master_class", "Master Class"),
            ("conversation_club", "Conversation Club"),
            ("other", "Otro"),
        ],
        string="Categoría",
        required=True,
        help="Categoría estructural para mapear asignaturas.",
    )

    skill_number = fields.Integer(
        string="Número de Skill",
        help="Número de Skill (1..6). Aplica solo para B-skills.",
    )

    mapping_mode = fields.Selection(
        selection=[
            ("per_unit", "Por unidad (Skills)"),
            ("pair", "Por pareja (B-check)"),
            ("block", "Por bloque (Oral Test)"),
            ("fixed", "Fijo"),
        ],
        string="Modo de Mapeo",
        default="per_unit",
        required=True,
        help="Regla principal de asignación de asignatura efectiva.",
    )

    pair_size = fields.Integer(
        string="Tamaño de Pareja",
        default=2,
        help="Tamaño de la pareja para B-checks.",
    )
    block_size = fields.Integer(
        string="Tamaño de Bloque",
        default=4,
        help="Tamaño del bloque para Oral Tests.",
    )

    alias_student = fields.Char(
        string="Alias Estudiante",
        required=True,
        help="Nombre visible para el estudiante (ej: Skill 2, B-check, Oral Test).",
    )

    allow_next_pending = fields.Boolean(
        string="Permitir siguiente pendiente",
        default=True,
        help="Si la unidad preferida ya fue atendida, buscar la siguiente pendiente.",
    )

    fixed_subject_id = fields.Many2one(
        comodel_name="benglish.subject",
        string="Asignatura Fija",
        ondelete="restrict",
        domain="[('program_id', '=', program_id)]",
        help="Asignatura fija cuando mapping_mode es 'fixed'.",
    )

    _sql_constraints = [
        (
            "code_program_unique",
            "UNIQUE(code, program_id)",
            "El código debe ser único por programa.",
        ),
    ]

    @api.constrains("mapping_mode", "skill_number")
    def _check_skill_number(self):
        for record in self:
            if record.mapping_mode == "per_unit" and record.subject_category == "bskills":
                if not record.skill_number or record.skill_number < 1:
                    raise ValidationError(
                        _("Debe definir el número de Skill para plantillas de B-skills.")
                    )

    @api.constrains("mapping_mode", "pair_size", "block_size")
    def _check_sizes(self):
        for record in self:
            if record.mapping_mode == "pair" and (record.pair_size or 0) < 2:
                raise ValidationError(
                    _("El tamaño de pareja debe ser >= 2 para B-check.")
                )
            if record.mapping_mode == "block" and (record.block_size or 0) < 2:
                raise ValidationError(
                    _("El tamaño de bloque debe ser >= 2 para Oral Test.")
                )

    @api.constrains("mapping_mode", "fixed_subject_id")
    def _check_fixed_subject(self):
        for record in self:
            if record.mapping_mode == "fixed" and not record.fixed_subject_id:
                raise ValidationError(
                    _("Debe definir una asignatura fija para plantillas 'fixed'.")
                )
