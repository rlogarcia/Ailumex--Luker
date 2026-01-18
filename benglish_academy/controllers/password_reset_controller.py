# -*- coding: utf-8 -*-
"""
Controlador HTTP para gestionar la recuperación de contraseña
Endpoints para request OTP, verify OTP y reset password
"""

from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class PasswordResetController(http.Controller):
    
    @http.route('/benglish/password/request_otp', type='json', auth='public', methods=['POST'], csrf=False)
    def request_otp(self, identification='', identification_type='', **kwargs):
        """
        Endpoint para solicitar un código OTP
        
        Parámetros esperados:
            - identification: Número de identificación
            - identification_type: Tipo de identificación (opcional)
        
        Retorna JSON con success, message y email ofuscado
        """
        try:
            identification = identification.strip() if identification else ''
            
            # Validar entrada
            if not identification:
                return {
                    'success': False,
                    'message': 'Por favor, ingresa tu número de identificación.'
                }
            
            # Obtener información de la petición
            request_info = {
                'ip_address': request.httprequest.remote_addr,
                'user_agent': request.httprequest.user_agent.string if request.httprequest.user_agent else None
            }
            
            # Llamar al modelo para crear el OTP
            PasswordReset = request.env['benglish.password.reset'].sudo()
            result = PasswordReset.create_otp_request(
                identification=identification,
                identification_type=identification_type,
                request_info=request_info
            )
            
            return result
            
        except Exception as e:
            _logger.error(f"Error en request_otp endpoint: {str(e)}")
            return {
                'success': False,
                'message': 'Ocurrió un error al procesar tu solicitud. Por favor, intenta nuevamente.'
            }
    
    @http.route('/benglish/password/verify_otp', type='json', auth='public', methods=['POST'], csrf=False)
    def verify_otp(self, identification='', otp_code='', **kwargs):
        """
        Endpoint para verificar el código OTP
        
        Parámetros esperados:
            - identification: Número de identificación
            - otp_code: Código OTP de 6 dígitos
        
        Retorna JSON con success, message y reset_token
        """
        try:
            identification = identification.strip() if identification else ''
            otp_code = otp_code.strip() if otp_code else ''
            
            # Validar entrada
            if not identification:
                return {
                    'success': False,
                    'message': 'Por favor, ingresa tu número de identificación.'
                }
            
            if not otp_code:
                return {
                    'success': False,
                    'message': 'Por favor, ingresa el código OTP.'
                }
            
            if len(otp_code) != 6 or not otp_code.isdigit():
                return {
                    'success': False,
                    'message': 'El código debe ser de 6 dígitos.'
                }
            
            # Llamar al modelo para verificar el OTP
            PasswordReset = request.env['benglish.password.reset'].sudo()
            result = PasswordReset.verify_otp(
                identification=identification,
                otp_code=otp_code
            )
            
            return result
            
        except Exception as e:
            _logger.error(f"Error en verify_otp endpoint: {str(e)}")
            return {
                'success': False,
                'message': 'Ocurrió un error al verificar el código. Por favor, intenta nuevamente.'
            }
    
    @http.route('/benglish/password/reset', type='json', auth='public', methods=['POST'], csrf=False)
    def reset_password(self, identification='', reset_token='', new_password='', confirm_password='', **kwargs):
        """
        Endpoint para resetear la contraseña
        
        Parámetros esperados:
            - identification: Número de identificación
            - reset_token: Token de reseteo obtenido tras verificar OTP
            - new_password: Nueva contraseña
            - confirm_password: Confirmación de la nueva contraseña
        
        Retorna JSON con success y message
        """
        try:
            identification = identification.strip() if identification else ''
            reset_token = reset_token.strip() if reset_token else ''
            
            # Validar entrada
            if not identification:
                return {
                    'success': False,
                    'message': 'Por favor, ingresa tu número de identificación.'
                }
            
            if not reset_token:
                return {
                    'success': False,
                    'message': 'Token de reseteo inválido. Por favor, inicia el proceso nuevamente.'
                }
            
            if not new_password:
                return {
                    'success': False,
                    'message': 'Por favor, ingresa tu nueva contraseña.'
                }
            
            if len(new_password) < 6:
                return {
                    'success': False,
                    'message': 'La contraseña debe tener al menos 6 caracteres.'
                }
            
            if new_password != confirm_password:
                return {
                    'success': False,
                    'message': 'Las contraseñas no coinciden.'
                }
            
            # Llamar al modelo para resetear la contraseña
            PasswordReset = request.env['benglish.password.reset'].sudo()
            result = PasswordReset.reset_password(
                identification=identification,
                reset_token=reset_token,
                new_password=new_password
            )
            
            return result
            
        except Exception as e:
            _logger.error(f"Error en reset_password endpoint: {str(e)}")
            return {
                'success': False,
                'message': 'Ocurrió un error al cambiar la contraseña. Por favor, intenta nuevamente.'
            }
    
    @http.route('/benglish/password/check_cooldown', type='json', auth='public', methods=['POST'], csrf=False)
    def check_cooldown(self, identification='', **kwargs):
        """
        Endpoint para verificar el cooldown antes de permitir reenvío
        
        Parámetros esperados:
            - identification: Número de identificación
        
        Retorna JSON con can_resend y seconds_remaining
        """
        try:
            from datetime import datetime, timedelta
            
            identification = identification.strip() if identification else ''
            
            if not identification:
                return {
                    'can_resend': False,
                    'seconds_remaining': 0,
                    'message': 'Identificación requerida.'
                }
            
            # Buscar usuario
            user = request.env['res.users'].sudo().search([
                ('login', '=', identification),
                ('active', '=', True)
            ], limit=1)
            
            if not user:
                # No revelar si el usuario existe
                return {
                    'can_resend': True,
                    'seconds_remaining': 0
                }
            
            # Buscar último OTP
            PasswordReset = request.env['benglish.password.reset'].sudo()
            COOLDOWN_SECONDS = 60
            
            last_request = PasswordReset.search([
                ('user_id', '=', user.id),
                ('create_date', '>', datetime.now() - timedelta(seconds=COOLDOWN_SECONDS))
            ], limit=1)
            
            if last_request:
                time_elapsed = (datetime.now() - last_request.create_date).total_seconds()
                seconds_remaining = int(COOLDOWN_SECONDS - time_elapsed)
                
                return {
                    'can_resend': False,
                    'seconds_remaining': max(0, seconds_remaining),
                    'message': f'Debes esperar {seconds_remaining} segundos antes de solicitar un nuevo código.'
                }
            
            return {
                'can_resend': True,
                'seconds_remaining': 0
            }
            
        except Exception as e:
            _logger.error(f"Error en check_cooldown endpoint: {str(e)}")
            return {
                'can_resend': True,
                'seconds_remaining': 0
            }
