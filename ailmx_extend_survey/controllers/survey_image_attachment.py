# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class SurveyImageAttachmentController(http.Controller):

    @http.route(
        '/ailmx/survey/upload_image',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def upload_image(self, **post):
        try:
            token = post.get('token')
            question_id = post.get('question_id')
            image_file = request.httprequest.files.get('image_file')

            if not token:
                return request.make_json_response({
                    'success': False,
                    'error': 'No se recibió token de aplicación.'
                })

            if not question_id:
                return request.make_json_response({
                    'success': False,
                    'error': 'No se recibió question_id.'
                })

            if not image_file:
                return request.make_json_response({
                    'success': False,
                    'error': 'No se recibió archivo de imagen.'
                })

            user_input = request.env['survey.user_input'].sudo().search([
                ('access_token', '=', token)
            ], limit=1)

            if not user_input:
                return request.make_json_response({
                    'success': False,
                    'error': 'No se encontró la aplicación asociada al token.'
                })

            attachment = request.env['ir.attachment'].sudo().create({
                'name': image_file.filename,
                'datas': http.base64.b64encode(image_file.read()),
                'res_model': 'survey.user_input',
                'res_id': user_input.id,
                'mimetype': image_file.mimetype,
                'type': 'binary',
            })

            return request.make_json_response({
                'success': True,
                'attachment_id': attachment.id,
                'filename': attachment.name,
            })

        except Exception as error:
            return request.make_json_response({
                'success': False,
                'error': str(error),
            })