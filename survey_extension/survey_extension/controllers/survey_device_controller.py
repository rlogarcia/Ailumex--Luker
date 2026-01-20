# -*- coding: utf-8 -*-
"""
Archivo: survey_device_controller.py
Propósito: Controlador para manejar captura de información de dispositivo
"""

import json
import logging
from odoo import http
from odoo.http import request
from odoo.addons.survey.controllers.main import Survey

_logger = logging.getLogger(__name__)


class SurveyDeviceController(Survey):
    """Extiende el controlador de encuestas para capturar información de dispositivo."""

    @http.route()
    def survey_submit(self, survey_token, **post):
        """
        Override del método survey_submit para:
        1. Capturar información de dispositivo
        2. Procesar campos WPM correctamente (agrupándolos por question_id)
        """
        # Obtener la participación actual
        access_data = self._get_access_data(survey_token)
        if access_data['validity_code'] is not True:
            return super().survey_submit(survey_token, **post)
        
        user_input_sudo = access_data['user_input_sudo']
        
        # Capturar información de dispositivo si está presente en el POST
        if 'x_device_id' in post and post['x_device_id']:
            try:
                user_input_sudo.write({
                    'x_device_id': post['x_device_id'],
                    'x_device_type': post.get('x_device_type', 'other'),
                    'x_device_info': post.get('x_device_info', ''),
                })
                _logger.info(
                    'Device info captured for survey %s: device_id=%s, type=%s',
                    user_input_sudo.survey_id.title,
                    post['x_device_id'],
                    post.get('x_device_type', 'other')
                )
            except Exception as e:
                _logger.warning('Error capturing device info: %s', str(e))
        
        # Procesar campos WPM: agrupar campos dispersos en diccionarios
        # Los campos vienen como: {question_id}_wpm_time, {question_id}_wpm_words, etc.
        # Necesitamos convertirlos a: {question_id: {'wpm_time': ..., 'wpm_words': ...}}
        processed_post = dict(post)
        wpm_data = {}  # {question_id: {wpm_field: value}}
        
        # Identificar y agrupar campos WPM
        keys_to_remove = []
        for key, value in post.items():
            if '_wpm_' in key:
                try:
                    # Formato: {question_id}_wpm_{field}
                    # Ejemplo: 123_wpm_time, 123_wpm_words, etc.
                    parts = key.split('_wpm_')
                    if len(parts) == 2:
                        question_id = parts[0]
                        wpm_field = 'wpm_' + parts[1]  # wpm_time, wpm_words, etc.
                        
                        if question_id not in wpm_data:
                            wpm_data[question_id] = {}
                        
                        wpm_data[question_id][wpm_field] = value
                        keys_to_remove.append(key)
                except Exception as e:
                    _logger.warning(f'Error parsing WPM field {key}: {e}')
        
        # Remover campos WPM individuales del POST
        for key in keys_to_remove:
            processed_post.pop(key, None)
        
        # Agregar datos WPM agrupados al POST
        for question_id, wpm_fields in wpm_data.items():
            processed_post[question_id] = wpm_fields
            _logger.debug(f'WPM data for question {question_id}: {wpm_fields}')
        
        # Continuar con el procesamiento normal usando el POST procesado
        return super().survey_submit(survey_token, **processed_post)

    @http.route()
    def survey_start(self, *args, **kwargs):
        """
        Override del método survey_start para validar restricciones de dispositivo
        antes de iniciar la encuesta.
        """
        response = super().survey_start(*args, **kwargs)
        
        # Si hay restricción por dispositivo, validar
        survey_sudo = kwargs.get('survey_sudo')
        if survey_sudo and survey_sudo.x_restrict_by_device:
            device_id = request.httprequest.cookies.get('odoo_survey_device_uuid')
            if device_id:
                # Verificar si este dispositivo ya respondió
                existing = request.env['survey.user_input'].sudo().search([
                    ('survey_id', '=', survey_sudo.id),
                    ('x_device_id', '=', device_id),
                    ('state', '!=', 'new'),
                ], limit=1)
                
                if existing:
                    # Redirigir a página de error o mostrar mensaje
                    return request.render('survey_extension.survey_device_already_used', {
                        'survey': survey_sudo,
                        'previous_date': existing.create_date,
                    })
        
        return response

    @http.route(
        '/survey/check_device/<int:survey_id>',
        type='json',
        auth='public',
        website=True,
        csrf=False
    )
    def check_device_restriction(self, survey_id, device_id, **kwargs):
        """
        Endpoint AJAX para verificar si un dispositivo puede participar en la encuesta.
        
        :param int survey_id: ID de la encuesta
        :param str device_id: UUID del dispositivo
        :return dict: {'allowed': bool, 'message': str}
        """
        survey = request.env['survey.survey'].sudo().browse(survey_id)
        
        if not survey.exists():
            return {
                'allowed': False,
                'message': 'Encuesta no encontrada'
            }
        
        # Si no hay restricción, permitir
        if not survey.x_restrict_by_device:
            return {
                'allowed': True,
                'message': 'Sin restricciones'
            }
        
        # Verificar si el dispositivo ya participó
        existing = request.env['survey.user_input'].sudo().search([
            ('survey_id', '=', survey_id),
            ('x_device_id', '=', device_id),
            ('state', '!=', 'new'),
        ], limit=1)
        
        if existing:
            return {
                'allowed': False,
                'message': f'Este dispositivo ya respondió el {existing.create_date.strftime("%d/%m/%Y a las %H:%M")}',
                'previous_date': existing.create_date.isoformat(),
            }
        
        return {
            'allowed': True,
            'message': 'Dispositivo autorizado'
        }

    @http.route(
        '/survey/device_stats/<int:survey_id>',
        type='json',
        auth='user',
        website=True
    )
    def get_device_statistics(self, survey_id, **kwargs):
        """
        Obtiene estadísticas de dispositivos para una encuesta.
        
        :param int survey_id: ID de la encuesta
        :return dict: Estadísticas de dispositivos
        """
        survey = request.env['survey.survey'].browse(survey_id)
        
        if not survey.exists():
            return {'error': 'Encuesta no encontrada'}
        
        # Estadísticas por tipo de dispositivo
        device_stats = request.env['survey.user_input'].read_group(
            [('survey_id', '=', survey_id), ('x_device_type', '!=', False)],
            ['x_device_type'],
            ['x_device_type']
        )
        
        # Dispositivos únicos
        unique_devices = request.env['survey.user_input'].search([
            ('survey_id', '=', survey_id),
            ('x_device_id', '!=', False)
        ]).mapped('x_device_id')
        
        return {
            'total_participations': len(unique_devices),
            'unique_devices': len(set(unique_devices)),
            'device_types': [
                {
                    'type': stat['x_device_type'],
                    'count': stat['x_device_type_count']
                }
                for stat in device_stats
            ]
        }
