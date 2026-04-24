# -*- coding: utf-8 -*-

from odoo import models, fields


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    conditional_block_message = fields.Char(
        string='Mensaje de bloqueo condicional'
    )