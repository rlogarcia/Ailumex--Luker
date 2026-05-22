# -*- coding: utf-8 -*-
from odoo import models, fields


class SurveyQuestionAnswer(models.Model):
    _inherit = 'survey.question.answer'

    flg_is_correct = fields.Boolean(
        string='Es respuesta correcta',
        default=False,
        help='Marca esta opción como la respuesta correcta.',
    )
    valor_puntaje = fields.Float(
        string='Valor puntaje',
        default=0.0,
        help='Puntaje asignado a esta opción cuando es seleccionada.',
    )
