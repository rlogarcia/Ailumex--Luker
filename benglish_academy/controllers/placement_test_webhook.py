# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class PlacementTestWebhook(http.Controller):
    """
    Controlador para recibir resultados del Campus Virtual (LMS)
    
    Endpoint: POST /benglish/placement_test/lms_result
    
    Payload esperado:
    {
        "student_code": "EST-2025-123",
        "lms_score": 85,
        "grammar_score": 90,
        "listening_score": 80,
        "reading_score": 85,
        "test_date": "2025-01-15",
        "token": "secret_token_xyz"
    }
    """
    
    @http.route('/benglish/placement_test/lms_result', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_lms_result(self, **kwargs):
        """
        Recibe resultado del LMS y lo registra en el Placement Test correspondiente
        """
        try:
            # 1. VALIDAR TOKEN DE SEGURIDAD
            expected_token = request.env['ir.config_parameter'].sudo().get_param(
                'benglish.lms_webhook_token'
            )
            
            provided_token = kwargs.get('token')
            
            if not expected_token:
                _logger.warning("LMS webhook token no configurado en sistema")
                return {
                    'status': 'error',
                    'message': 'Sistema no configurado para recibir resultados LMS. Contacte al administrador.'
                }
            
            if provided_token != expected_token:
                _logger.warning(f"Token LMS inválido recibido: {provided_token}")
                return {
                    'status': 'error',
                    'message': 'Token de autenticación inválido'
                }
            
            # 2. EXTRAER DATOS
            student_code = kwargs.get('student_code')
            lms_score = kwargs.get('lms_score')
            grammar_score = kwargs.get('grammar_score', 0)
            listening_score = kwargs.get('listening_score', 0)
            reading_score = kwargs.get('reading_score', 0)
            
            if not student_code:
                return {'status': 'error', 'message': 'student_code es requerido'}
            
            if lms_score is None:
                return {'status': 'error', 'message': 'lms_score es requerido'}
            
            # 3. BUSCAR ESTUDIANTE
            student = request.env['benglish.student'].sudo().search([
                ('code', '=', student_code)
            ], limit=1)
            
            if not student:
                _logger.error(f"Estudiante no encontrado con código: {student_code}")
                return {
                    'status': 'error',
                    'message': f'Estudiante {student_code} no encontrado en el sistema'
                }
            
            # 4. BUSCAR PLACEMENT TEST PENDIENTE (último sin LMS)
            history = request.env['benglish.placement.test.prospect'].sudo().search([
                ('prospect_name', '=', student.name),
                ('lms_score', '=', 0),
                ('placement_status', 'in', ['pending_oral', 'pending_lms'])
            ], limit=1, order='test_date desc')
            
            if not history:
                _logger.error(
                    f"No se encontró Placement Test pendiente para estudiante {student_code}"
                )
                return {
                    'status': 'error',
                    'message': f'No hay Placement Test pendiente de resultado LMS para {student.name}'
                }
            
            # 5. REGISTRAR RESULTADO LMS
            history.write({
                'lms_score': lms_score,
                'lms_grammar_score': grammar_score,
                'lms_listening_score': listening_score,
                'lms_reading_score': reading_score,
                'lms_received_date': http.request.env.context.get('tz') or 'UTC',
                'placement_status': 'pending_decision'
            })
            
            _logger.info(
                f"✓ Resultado LMS registrado para {student.name} (código: {student_code}): "
                f"Score={lms_score}%, Grammar={grammar_score}%, "
                f"Listening={listening_score}%, Reading={reading_score}%"
            )
            
            # 6. INTENTAR CONSOLIDACIÓN AUTOMÁTICA
            try:
                history._auto_consolidate_placement_test()
            except Exception as e:
                _logger.warning(f"No se pudo auto-consolidar Placement Test: {str(e)}")
            
            # 7. RETORNAR ÉXITO
            return {
                'status': 'success',
                'message': 'Resultado LMS registrado correctamente',
                'data': {
                    'student_code': student_code,
                    'student_name': student.name,
                    'lms_score': lms_score,
                    'final_score': history.final_score,
                    'phase_suggested': history.phase_assigned_id.name if history.phase_assigned_id else None
                }
            }
        
        except Exception as e:
            _logger.error(f"Error procesando resultado LMS: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Error interno del servidor: {str(e)}'
            }
    
    @http.route('/benglish/placement_test/health', type='http', auth='public', methods=['GET'])
    def health_check(self):
        """Endpoint para verificar que el webhook está activo"""
        return request.make_response(
            json.dumps({
                'status': 'ok',
                'service': 'Benglish Placement Test Webhook',
                'version': '1.0'
            }),
            headers=[('Content-Type', 'application/json')]
        )
