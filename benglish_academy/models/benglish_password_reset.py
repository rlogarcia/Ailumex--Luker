# -*- coding: utf-8 -*-
"""
Modelo para gestionar la recuperación de contraseña mediante OTP
Almacena códigos OTP hasheados con expiración y control de intentos
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import secrets
import hashlib
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class BenglishPasswordReset(models.Model):
    _name = 'benglish.password.reset'
    _description = 'Password Reset OTP Management'
    _order = 'create_date desc'
    
    # Configuración de seguridad
    OTP_LENGTH = 6
    OTP_VALIDITY_MINUTES = 10
    MAX_ATTEMPTS = 5
    RESEND_COOLDOWN_SECONDS = 60
    
    user_id = fields.Many2one('res.users', string='Usuario', required=True, ondelete='cascade', index=True)
    identification = fields.Char(string='Número de Identificación', required=True, index=True)
    otp_hash = fields.Char(string='OTP Hash', required=True)
    expiration_date = fields.Datetime(string='Fecha de Expiración', required=True, index=True)
    attempts = fields.Integer(string='Intentos de Validación', default=0)
    is_used = fields.Boolean(string='Usado', default=False, index=True)
    is_blocked = fields.Boolean(string='Bloqueado', default=False)
    user_role = fields.Selection([
        ('admin', 'Administrador'),
        ('teacher', 'Profesor'),
        ('student', 'Estudiante'),
        ('other', 'Otro')
    ], string='Rol del Usuario', required=True)
    ip_address = fields.Char(string='Dirección IP')
    user_agent = fields.Char(string='User Agent')
    
    @api.model
    def _generate_otp(self):
        """Genera un OTP de 6 dígitos aleatorios"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(self.OTP_LENGTH)])
    
    @api.model
    def _hash_otp(self, otp):
        """Hashea el OTP usando SHA256"""
        return hashlib.sha256(otp.encode('utf-8')).hexdigest()
    
    @api.model
    def _verify_otp(self, otp_hash, otp_input):
        """Verifica si el OTP ingresado coincide con el hash"""
        return otp_hash == self._hash_otp(otp_input)
    
    @api.model
    def _determine_user_role(self, user):
        """Determina el rol del usuario para auditoría"""
        if user.has_group('base.group_system') or user.has_group('base.group_erp_manager'):
            return 'admin'
        
        # Usuario portal (puede ser coach o estudiante)
        if user.has_group('base.group_portal'):
            # Verificar si es coach
            coach = self.env['benglish.coach'].sudo().search([
                ('user_id', '=', user.id),
                ('active', '=', True)
            ], limit=1)
            if coach:
                return 'teacher'
            
            # Verificar si es empleado con acceso portal (coach sin registro en benglish.coach)
            employee = self.env['hr.employee'].sudo().search([
                ('user_id', '=', user.id),
                ('is_teacher', '=', True),
                ('active', '=', True)
            ], limit=1)
            if employee:
                return 'teacher'
            
            # Verificar si es estudiante
            student = self.env['benglish.student'].sudo().search([
                ('user_id', '=', user.id),
                ('active', '=', True)
            ], limit=1)
            if student:
                return 'student'
        
        return 'other'
    
    @api.model
    def _find_user_by_identification(self, identification):
        """
        Busca un usuario de Odoo por su número de identificación.
        Busca en TODOS los usuarios (internos, portal, coaches, estudiantes).
        
        Args:
            identification: Número de identificación a buscar
            
        Returns:
            tuple: (usuario encontrado o False, partner con identificación o False, empleado o False)
        """
        import re
        
        # Normalizar el número de identificación (remover espacios, guiones, etc.)
        normalized_id = re.sub(r"[^0-9a-zA-Z]", "", identification or "")
        
        if not normalized_id:
            return (False, False, False)
        
        _logger.info(f"🔍 Buscando usuario con identificación: {identification}")
        
        # MÉTODO 1: Buscar por login directo (número de identificación)
        user = self.env['res.users'].sudo().search([
            ('login', '=', identification),
            ('active', '=', True)
        ], limit=1)
        
        if user:
            _logger.info(f"✅ Usuario encontrado por login: {user.login} - {user.name}")
            return (user, False, False)
        
        # MÉTODO 2: Buscar en empleados por identification_id
        _logger.info(f"🔍 Buscando en empleados por identification_id...")
        employee = self.env['hr.employee'].sudo().search([
            ('identification_id', '=', identification),
            ('active', '=', True)
        ], limit=1)
        
        _logger.info(f"   Encontrados {1 if employee else 0} empleados por identification_id")
        
        if employee:
            _logger.info(f"   Empleado encontrado: {employee.name} (ID: {employee.id}) - user_id: {employee.user_id.id if employee.user_id else 'No tiene'}")
            if employee.user_id:
                _logger.info(f"✅ Usuario encontrado por identification_id de empleado: {employee.name}")
                return (employee.user_id, False, employee)
            else:
                _logger.warning(f"   ⚠️ Empleado {employee.name} no tiene usuario asociado")
        
        # MÉTODO 3: Buscar en empleados por ssnid
        _logger.info(f"🔍 Buscando en empleados por ssnid...")
        employee = self.env['hr.employee'].sudo().search([
            ('ssnid', '=', identification),
            ('active', '=', True)
        ], limit=1)
        
        if employee and employee.user_id:
            _logger.info(f"✅ Usuario encontrado por ssnid de empleado: {employee.name}")
            return (employee.user_id, False, employee)
        
        # MÉTODO 4: Buscar por número de identificación del partner (VAT o ref)
        _logger.info(f"🔍 Buscando en partners por VAT...")
        # Primero buscar por VAT
        partners = self.env['res.partner'].sudo().search([
            ('vat', '=', identification)
        ])
        
        _logger.info(f"   Encontrados {len(partners)} partners por VAT")
        
        # Si no encuentra por VAT, buscar por ref (campo de referencia/identificación)
        if not partners:
            _logger.info(f"🔍 Buscando en partners por ref...")
            partners = self.env['res.partner'].sudo().search([
                ('ref', '=', identification)
            ])
            _logger.info(f"   Encontrados {len(partners)} partners por ref")
        
        for partner in partners:
            _logger.info(f"   Partner encontrado: {partner.name} (ID: {partner.id})")
            # Buscar usuario asociado al partner
            user = self.env['res.users'].sudo().search([
                ('partner_id', '=', partner.id),
                ('active', '=', True)
            ], limit=1)
            
            if user:
                _logger.info(f"✅ Usuario encontrado por partner (VAT/ref): {user.name}")
                return (user, partner, False)
            else:
                _logger.warning(f"   ⚠️ Partner {partner.name} no tiene usuario asociado")
                # Buscar si existe un usuario con ese email del partner
                if partner.email:
                    _logger.info(f"   🔍 Buscando usuario con login = {partner.email}")
                    user_by_email = self.env['res.users'].sudo().search([
                        ('login', '=', partner.email),
                        ('active', '=', True)
                    ], limit=1)
                    if user_by_email:
                        _logger.info(f"✅ Usuario encontrado por email del partner: {user_by_email.name}")
                        return (user_by_email, partner, False)
                    else:
                        _logger.warning(f"   ⚠️ No existe usuario con login {partner.email}")
                else:
                    _logger.warning(f"   ⚠️ Partner {partner.name} no tiene email configurado")
        
        # MÉTODO 5: Buscar en estudiantes por número de documento
        student = self.env['benglish.student'].sudo().search([
            ('student_id_number', '=', identification),
            ('active', '=', True)
        ], limit=1)
        
        if student and student.user_id:
            _logger.info(f"✅ Usuario encontrado por estudiante: {student.name}")
            return (student.user_id, False, False)
        
        _logger.warning(f"❌ No se encontró usuario con identificación: {identification}")
        return (False, False, False)
    
    @api.model
    def create_otp_request(self, identification, identification_type=None, request_info=None):
        """
        Crea una nueva solicitud de OTP para CUALQUIER usuario de Odoo.
        Funciona con: estudiantes, coaches, empleados, administradores, cualquier usuario.
        
        Args:
            identification: Número de identificación del usuario
            identification_type: Tipo de identificación (CC/TI) - opcional
            request_info: Diccionario con ip_address y user_agent
            
        Returns:
            dict: Resultado con success, message y email (ofuscado)
        """
        try:
            # Buscar usuario por número de identificación (cualquier usuario)
            user, partner_with_id, employee_with_id = self._find_user_by_identification(identification)
            
            if not user:
                # No revelar si el usuario existe o no (seguridad)
                _logger.info(f"⚠️ Intento de recuperación para identificación inexistente: {identification}")
                return {
                    'success': True,  # Siempre retorna True para no enumerar usuarios
                    'message': 'Si existe una cuenta asociada a esta identificación, recibirás un código en tu correo electrónico.',
                    'email': None
                }
            
            # Verificar que el usuario tenga email
            # PRIORIDAD: 1) email del empleado con identificación, 2) email del partner con identificación, 3) email del usuario
            if employee_with_id and employee_with_id.work_email:
                email = employee_with_id.work_email
                _logger.info(f"📧 Usando email del empleado: {email}")
            elif partner_with_id and partner_with_id.email:
                email = partner_with_id.email
                _logger.info(f"📧 Usando email del partner con identificación: {email}")
            else:
                email = user.email or user.partner_id.email
                _logger.info(f"📧 Usando email del usuario: {email}")
            if not email:
                _logger.warning(f"Usuario {user.login} sin email configurado")
                return {
                    'success': True,  # No revelar que no tiene email
                    'message': 'Si existe una cuenta asociada a esta identificación, recibirás un código en tu correo electrónico.',
                    'email': None
                }
            
            # Verificar cooldown de reenvío (rate limit)
            last_request = self.search([
                ('user_id', '=', user.id),
                ('create_date', '>', fields.Datetime.now() - timedelta(seconds=self.RESEND_COOLDOWN_SECONDS))
            ], limit=1)
            
            if last_request:
                time_remaining = int(self.RESEND_COOLDOWN_SECONDS - (datetime.now() - last_request.create_date).total_seconds())
                return {
                    'success': False,
                    'message': f'Debes esperar {time_remaining} segundos antes de solicitar un nuevo código.',
                    'email': None
                }
            
            # Invalidar OTPs anteriores no usados
            old_otps = self.search([
                ('user_id', '=', user.id),
                ('is_used', '=', False)
            ])
            old_otps.write({'is_used': True})
            
            # Generar nuevo OTP
            otp = self._generate_otp()
            otp_hash = self._hash_otp(otp)
            
            # Determinar rol del usuario
            user_role = self._determine_user_role(user)
            
            # Crear registro de OTP
            otp_record = self.create({
                'user_id': user.id,
                'identification': identification,
                'otp_hash': otp_hash,
                'expiration_date': fields.Datetime.now() + timedelta(minutes=self.OTP_VALIDITY_MINUTES),
                'user_role': user_role,
                'ip_address': request_info.get('ip_address') if request_info else None,
                'user_agent': request_info.get('user_agent') if request_info else None,
            })
            
            # Enviar email con OTP
            self._send_otp_email(user, otp, email)
            
            # Ofuscar email para mostrar al usuario
            email_parts = email.split('@')
            if len(email_parts) == 2:
                local = email_parts[0]
                domain = email_parts[1]
                if len(local) > 3:
                    ofuscated_email = f"{local[:2]}***{local[-1]}@{domain}"
                else:
                    ofuscated_email = f"{local[0]}***@{domain}"
            else:
                ofuscated_email = "***"
            
            _logger.info(f"OTP generado para usuario {user.login} (rol: {user_role})")
            
            return {
                'success': True,
                'message': 'Si existe una cuenta asociada a esta identificación, recibirás un código en tu correo electrónico.',
                'email': ofuscated_email,
                'otp_id': otp_record.id  # Solo para debugging, no exponer en producción
            }
            
        except Exception as e:
            _logger.error(f"Error al crear OTP request: {str(e)}")
            return {
                'success': False,
                'message': 'Ocurrió un error al procesar tu solicitud. Por favor, contacta con soporte.',
                'email': None
            }
    
    @api.model
    def verify_otp(self, identification, otp_code):
        """
        Verifica el código OTP ingresado por el usuario
        
        Args:
            identification: Número de identificación del usuario
            otp_code: Código OTP de 6 dígitos
            
        Returns:
            dict: Resultado con success, message y reset_token (si válido)
        """
        try:
            # Buscar el OTP más reciente no usado
            otp_record = self.search([
                ('identification', '=', identification),
                ('is_used', '=', False),
                ('is_blocked', '=', False)
            ], order='create_date desc', limit=1)
            
            if not otp_record:
                return {
                    'success': False,
                    'message': 'No hay una solicitud de recuperación activa para esta identificación.',
                    'reset_token': None
                }
            
            # Verificar si está bloqueado por intentos
            if otp_record.attempts >= self.MAX_ATTEMPTS:
                otp_record.write({'is_blocked': True})
                return {
                    'success': False,
                    'message': 'Has superado el número máximo de intentos. Solicita un nuevo código.',
                    'reset_token': None
                }
            
            # Verificar expiración
            if fields.Datetime.now() > otp_record.expiration_date:
                return {
                    'success': False,
                    'message': 'El código ha expirado. Solicita un nuevo código.',
                    'expired': True,
                    'reset_token': None
                }
            
            # Incrementar intentos
            otp_record.write({'attempts': otp_record.attempts + 1})
            
            # Verificar el OTP
            if not self._verify_otp(otp_record.otp_hash, otp_code):
                attempts_left = self.MAX_ATTEMPTS - otp_record.attempts
                if attempts_left > 0:
                    return {
                        'success': False,
                        'message': f'Código incorrecto. Te quedan {attempts_left} intentos.',
                        'reset_token': None
                    }
                else:
                    otp_record.write({'is_blocked': True})
                    return {
                        'success': False,
                        'message': 'Has superado el número máximo de intentos. Solicita un nuevo código.',
                        'reset_token': None
                    }
            
            # OTP válido - generar token de reseteo
            reset_token = secrets.token_urlsafe(32)
            otp_record.write({
                'is_used': True,
                'otp_hash': reset_token  # Reutilizamos el campo para guardar el token de reseteo
            })
            
            _logger.info(f"OTP verificado exitosamente para usuario {otp_record.user_id.login}")
            
            return {
                'success': True,
                'message': 'Código verificado correctamente. Ahora puedes cambiar tu contraseña.',
                'reset_token': reset_token,
                'user_id': otp_record.user_id.id
            }
            
        except Exception as e:
            _logger.error(f"Error al verificar OTP: {str(e)}")
            return {
                'success': False,
                'message': 'Ocurrió un error al verificar el código. Por favor, intenta nuevamente.',
                'reset_token': None
            }
    
    @api.model
    def reset_password(self, identification, reset_token, new_password):
        """
        Cambia la contraseña del usuario usando el token de reseteo
        
        Args:
            identification: Número de identificación del usuario
            reset_token: Token de reseteo generado tras verificar OTP
            new_password: Nueva contraseña
            
        Returns:
            dict: Resultado con success y message
        """
        try:
            # Buscar el registro con el token de reseteo
            otp_record = self.search([
                ('identification', '=', identification),
                ('is_used', '=', True),
                ('otp_hash', '=', reset_token)  # El token está guardado en otp_hash
            ], order='create_date desc', limit=1)
            
            if not otp_record:
                return {
                    'success': False,
                    'message': 'Token de reseteo inválido o expirado. Por favor, inicia el proceso nuevamente.'
                }
            
            # Verificar que no haya pasado mucho tiempo desde la verificación (15 minutos)
            time_since_verification = (datetime.now() - otp_record.write_date).total_seconds()
            if time_since_verification > 900:  # 15 minutos
                return {
                    'success': False,
                    'message': 'La sesión de reseteo ha expirado. Por favor, inicia el proceso nuevamente.'
                }
            
            # Validar la nueva contraseña
            if not new_password or len(new_password) < 6:
                return {
                    'success': False,
                    'message': 'La contraseña debe tener al menos 6 caracteres.'
                }
            
            # Cambiar la contraseña
            user = otp_record.user_id
            user.sudo().write({'password': new_password})
            
            # Invalidar el token (cambiar el hash para que no se pueda reutilizar)
            otp_record.write({'otp_hash': 'USED'})
            
            _logger.info(f"Contraseña cambiada exitosamente para usuario {user.login}")
            
            return {
                'success': True,
                'message': 'Contraseña actualizada correctamente. Ya puedes iniciar sesión con tu nueva contraseña.'
            }
            
        except Exception as e:
            _logger.error(f"Error al resetear contraseña: {str(e)}")
            return {
                'success': False,
                'message': 'Ocurrió un error al cambiar la contraseña. Por favor, intenta nuevamente.'
            }
    
    def _send_otp_email(self, user, otp, email):
        """
        Envía el email con el código OTP al usuario
        
        Utiliza el subsistema de mail de Odoo de forma robusta:
        1. Busca el template configurado
        2. Si no existe, crea un email básico pero funcional
        3. Usa IrMailServer para envío directo con manejo de errores
        
        Args:
            user: Registro res.users
            otp: Código OTP de 6 dígitos
            email: Email destinatario
            
        Returns:
            bool: True si se envió exitosamente, False en caso contrario
        """
        try:
            IrMailServer = self.env['ir.mail_server'].sudo()
            
            # Obtener el servidor de correo saliente (opcional, para mejorar envío)
            mail_server = IrMailServer.search([], limit=1, order='sequence')
            if not mail_server:
                _logger.warning("No hay servidor de correo saliente configurado - se usará configuración por defecto")
            
            # SOLUCIÓN ROBUSTA: Enviar correo directamente sin depender del template
            # Esto evita problemas con templates en la BD que no se actualizan
            _logger.info("Enviando email OTP con método robusto directo")
            
            # Obtener email_from del servidor de correo o de la compañía
            company = self.env.company
            email_from = company.email or 'noreply@benglishacademy.com'
            
            # Si hay servidor configurado, usar su email
            try:
                mail_server = IrMailServer.search([], limit=1)
                if mail_server and mail_server.smtp_user:
                    email_from = mail_server.smtp_user
            except:
                pass
            # Si hay servidor configurado, usar su email
            try:
                mail_server = IrMailServer.search([], limit=1)
                if mail_server and mail_server.smtp_user:
                    email_from = mail_server.smtp_user
            except:
                pass
            
            # Crear email HTML atractivo y profesional con colores azules del portal
            body_html = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background-color: #1e40af; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
                        <h1 style="margin: 0;">🔐 Recuperación de Contraseña</h1>
                    </div>
                    <div style="background-color: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; border-radius: 0 0 10px 10px;">
                        <p style="font-size: 16px;">Hola <strong>{user.name}</strong>,</p>
                        
                        <p>Has solicitado recuperar tu contraseña para acceder al portal de <strong>Benglish</strong>.</p>
                        
                        <p>Tu código de verificación es:</p>
                        
                        <div style="background-color: #1e40af; padding: 25px; text-align: center; border-radius: 8px; margin: 25px 0;">
                            <p style="margin: 0; font-size: 42px; font-weight: bold; color: white; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                                {otp}
                            </p>
                        </div>
                        
                        <div style="background-color: #dbeafe; border-left: 4px solid #1e40af; padding: 15px; margin: 20px 0; border-radius: 4px;">
                            <p style="margin: 0; color: #1e3a8a;"><strong>⏰ Importante:</strong> Este código es válido por <strong>{self.OTP_VALIDITY_MINUTES} minutos</strong>.</p>
                        </div>
                        
                        <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                            Si no solicitaste este código, puedes ignorar este mensaje.<br/>
                            Tu cuenta permanece segura.
                        </p>
                        
                        <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;"/>
                        
                        <p style="font-size: 12px; color: #9ca3af; text-align: center;">
                            <strong>Benglish</strong><br/>
                            Este es un correo automático, por favor no respondas a este mensaje.
                        </p>
                    </div>
                </div>
            """
            
            # Crear el mail directamente
            mail_values = {
                'subject': 'Código de recuperación de contraseña - Benglish',
                'email_from': email_from,
                'email_to': email,
                'body_html': body_html,
                'auto_delete': True,
            }
            
            # Si hay servidor de correo configurado, asignarlo
            try:
                if mail_server:
                    mail_values['mail_server_id'] = mail_server.id
            except:
                pass
            
            # Crear y enviar el correo
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send(raise_exception=True)
            
            _logger.info(f"Email OTP enviado exitosamente a {email}")
            return True
            
        except Exception as e:
            _logger.error(f"Error al enviar email OTP: {str(e)}", exc_info=True)
            # No hacer raise para no bloquear el flujo, el usuario verá el mensaje genérico
            return False
    
    @api.model
    def cleanup_expired_otps(self):
        """
        Limpia OTPs expirados (más de 24 horas)
        Se puede ejecutar mediante cron job
        """
        expiration_limit = fields.Datetime.now() - timedelta(hours=24)
        expired_otps = self.search([
            ('create_date', '<', expiration_limit)
        ])
        count = len(expired_otps)
        expired_otps.unlink()
        _logger.info(f"Limpieza de OTPs: {count} registros eliminados")
        return count
