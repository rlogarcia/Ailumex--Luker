# -*- coding: utf-8 -*-

from odoo import models, fields


class SurveyQuestionReadingGridCell(models.Model):
    """
    Cada registro representa una celda del GRID lectura.
    """
    _name = 'survey.question.reading.grid.cell'
    _description = 'Celda de GRID lectura'
    _order = 'row_index, col_index, id'

    question_id = fields.Many2one(
        'survey.question',
        string='Pregunta',
        required=True,
        ondelete='cascade'
    )
    # Pregunta a la que pertenece la celda.

    row_index = fields.Integer(
        string='Fila',
        required=True
    )
    # Fila de la celda.

    col_index = fields.Integer(
        string='Columna',
        required=True
    )
    # Columna de la celda.

    cell_value = fields.Char(
        string='Contenido'
    )
    # Texto visible en esa celda.