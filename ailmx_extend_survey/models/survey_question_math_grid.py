# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SurveyQuestionMathGrid(models.Model):
    """
    Extensión del modelo survey.question para soportar
    preguntas tipo GRID matemático.
    """
    _inherit = 'survey.question'

    # =============================
    # NUEVO TIPO DE PREGUNTA
    # =============================
    question_type = fields.Selection(
        selection_add=[
            ('math_grid', 'GRID matemático'),
        ],
        ondelete={
            'math_grid': 'set null',
        }
    )

    # =============================
    # CONFIGURACIÓN DEL GRID
    # =============================
    math_grid_rows = fields.Integer(
        string="Filas GRID matemático",
        default=2
    )

    math_grid_cols = fields.Integer(
        string="Columnas GRID matemático",
        default=3
    )

    math_grid_cell_ids = fields.One2many(
        comodel_name='survey.question.math.grid.cell',
        inverse_name='question_id',
        string='Celdas GRID matemático'
    )

    math_grid_total_cells = fields.Integer(
        string="Total de celdas",
        compute="_compute_math_total_cells"
    )

    # =============================
    # CÁLCULOS
    # =============================
    @api.depends('math_grid_rows', 'math_grid_cols')
    def _compute_math_total_cells(self):
        for rec in self:
            rec.math_grid_total_cells = rec.math_grid_rows * rec.math_grid_cols

    # =============================
    # VALIDACIONES
    # =============================
    @api.constrains('math_grid_rows', 'math_grid_cols')
    def _check_math_dimensions(self):
        for rec in self:
            if rec.question_type == 'math_grid':
                if rec.math_grid_rows <= 0:
                    raise ValidationError("Las filas deben ser mayores a 0.")
                if rec.math_grid_cols <= 0:
                    raise ValidationError("Las columnas deben ser mayores a 0.")

    # =============================
    # ACCIÓN ABRIR WIZARD
    # =============================
    def action_open_math_grid_wizard(self):
        self.ensure_one()

        if not self.id or isinstance(self.id, models.NewId):
            raise ValidationError(
                "Guarda la pregunta antes de editar la grilla."
            )

        return {
            'type': 'ir.actions.act_window',
            'name': 'Editar grilla matemática',
            'res_model': 'survey.question.math.grid.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_question_id': self.id,
            },
        }

    # =============================
    # ONCHANGE — SOLO LIMPIA CELDAS
    # =============================
    @api.onchange('math_grid_rows', 'math_grid_cols', 'question_type')
    def _onchange_regenerate_math_grid(self):
        for rec in self:
            if rec.question_type != 'math_grid':
                continue
            rec.math_grid_cell_ids = [(5, 0, 0)]