# -*- coding: utf-8 -*-

from odoo import models, fields


class SurveyResponseAudio(models.Model):
    _name = 'survey.response.audio'
    _description = 'Audio de respuesta de encuesta'
    _order = 'id desc'

    response_line_id = fields.Many2one(
        comodel_name='survey.response.line',
        string='Línea de respuesta',
        required=True,
        ondelete='cascade'
    )

    response_header_id = fields.Many2one(
        comodel_name='survey.user_input',
        string='Aplicación',
        ondelete='cascade'
    )

    question_id = fields.Many2one(
        comodel_name='survey.question',
        string='Pregunta',
        ondelete='cascade'
    )

    attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string='Archivo de audio',
        required=True,
        ondelete='cascade'
    )

    filename = fields.Char(
        string='Nombre de archivo'
    )

    mimetype = fields.Char(
        string='Tipo MIME'
    )

    file_size = fields.Integer(
        string='Tamaño'
    )

    def unlink(self):
        attachments = self.mapped('attachment_id')
        res = super().unlink()
        if attachments:
            attachments.sudo().unlink()
        return res