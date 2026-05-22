# -*- coding: utf-8 -*-
from odoo import models, fields


class SurveyBlockMessage(models.Model):
    _name = 'survey.block.message'
    _description = 'Mensaje de bloque de encuesta'

    survey_id = fields.Many2one(
        'survey.survey', string='Encuesta',
        required=True, ondelete='cascade',
    )
    titulo = fields.Char(string='Título')
    mensaje = fields.Html(string='Mensaje')
    orden = fields.Integer(string='Orden', default=10)
    activo = fields.Boolean(string='Activo', default=True)
