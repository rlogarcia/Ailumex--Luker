# -*- coding: utf-8 -*-
from odoo import models, fields


class SurveyQuestionReadingGridCell(models.Model):
    _name = 'survey.question.reading.grid.cell'
    _description = 'Celda de GRID de lectura'

    question_id = fields.Many2one(
        comodel_name='survey.question',
        string='Pregunta',
        required=True,
        ondelete='cascade',
    )
    fila = fields.Integer(string='Fila', default=0)
    columna = fields.Integer(string='Columna', default=0)
    valor = fields.Char(string='Valor', default='')
    es_encabezado = fields.Boolean(string='Es encabezado', default=False)
