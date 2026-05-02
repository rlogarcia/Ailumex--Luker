# -*- coding: utf-8 -*-

from odoo import models, fields


class SurveyResponseAudio(models.Model):
    _name = 'survey.response.audio'
    _description = 'Audio de respuesta de encuesta'
    _order = 'id desc'

    id_response_line = fields.Many2one(
        comodel_name='survey.response.line',
        string='Línea de respuesta',
        required=True,
        ondelete='cascade'
    )

    id_response_header = fields.Many2one(
        comodel_name='survey.user_input',
        string='Aplicación',
        ondelete='cascade'
    )

    id_question = fields.Many2one(
        comodel_name='survey.question',
        string='Pregunta',
        ondelete='cascade'
    )

    id_adjunto = fields.Many2one(
        comodel_name='ir.attachment',
        string='Archivo de audio',
        required=True,
        ondelete='cascade'
    )

    nom_archivo = fields.Char(
        string='Nombre de archivo'
    )

    tipo_mime = fields.Char(
        string='Tipo MIME'
    )

    tam_archivo = fields.Integer(
        string='Tamaño'
    )

    def unlink(self):
        attachments = self.mapped('id_adjunto')
        res = super().unlink()
        if attachments:
            attachments.sudo().unlink()
        return res