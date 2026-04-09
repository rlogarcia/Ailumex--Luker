# -*- coding: utf-8 -*-

from odoo import models, fields


class SurveyQuestionMathGridCell(models.Model):
    """
    Cada registro representa una celda del GRID matemático.
    Tiene valor visible (cell_value) y valor correcto (correct_value)
    para poder evaluar la respuesta del participante.
    """
    _name = 'survey.question.math.grid.cell'
    _description = 'Celda de GRID matemático'
    _order = 'row_index, col_index, id'

    question_id = fields.Many2one(
        'survey.question',
        string='Pregunta',
        required=True,
        ondelete='cascade'
    )

    row_index = fields.Integer(
        string='Fila',
        required=True
    )

    col_index = fields.Integer(
        string='Columna',
        required=True
    )

    cell_value = fields.Char(
        string='Contenido visible'
    )

    correct_value = fields.Char(
        string='Valor correcto'
    )