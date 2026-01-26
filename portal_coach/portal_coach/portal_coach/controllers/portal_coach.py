# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import fields, http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from collections import OrderedDict
import pytz
import json
import base64
import logging

_logger = logging.getLogger(__name__)


class PortalCoachController(CustomerPortal):
    """
    Controlador del Portal del Coach
    Modificado para usar benglish.academic.session en lugar de benglish.class.session
    Solo muestra sesiones publicadas (is_published=True)
    """

    def _get_coach(self):
        """
        Obtiene el coach asociado al usuario logueado
        Busca primero en benglish.coach, si no existe busca en hr.employee
        """
        # Opción A: Buscar en benglish.coach
        coach = request.env['benglish.coach'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        
        if coach:
            return coach
        
        # Opción B: Si no existe coach, crear uno "virtual" desde hr.employee
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.user.id),
            ('is_teacher', '=', True)
        ], limit=1)
        
        if employee:
            # Retornar un objeto similar a coach pero usando datos del employee
            return type('obj', (object,), {
                'id': employee.id,
                'name': employee.name,
                'code': employee.identification_id or f'EMP-{employee.id}',
                'email': employee.work_email,
                'phone': employee.work_phone,
                'employee_id': employee,
                'meeting_link': employee.meeting_link,
                'meeting_id': employee.meeting_id,
                'exists': lambda: True,
            })()
        
        return None

    def _get_coach_employee(self, coach):
        """
        Obtiene el hr.employee asociado al coach
        Las sesiones académicas se asignan por teacher_id (hr.employee)
        """
        if not coach:
            return None
        
        # Si coach tiene employee_id, usarlo
        if hasattr(coach, 'employee_id') and coach.employee_id:
            return coach.employee_id
        
        # Si coach ES el employee (caso virtual), retornarlo directamente
        if hasattr(coach, '__class__') and coach.__class__.__name__ == 'obj':
            return coach.employee_id
        
        return None

    def _get_published_sessions(self, teacher_id, additional_domain=None):
        """
        Obtiene las sesiones académicas publicadas para un docente
        
        Args:
            teacher_id: ID del hr.employee (docente)
            additional_domain: Lista de tuplas con condiciones adicionales
            
        Returns:
            Recordset de benglish.academic.session
        """
        if not teacher_id:
            return request.env['benglish.academic.session'].sudo()
        
        domain = [
            ('teacher_id', '=', teacher_id.id),
            ('is_published', '=', True),  # Solo sesiones publicadas
            ('active', '=', True),
            ('state', '!=', 'done'),  # Excluir sesiones terminadas
        ]
        
        if additional_domain:
            domain.extend(additional_domain)
        
        return request.env['benglish.academic.session'].sudo().search(
            domain,
            order='date asc, time_start asc'
        )

    @http.route(['/my/coach', '/my/coach/home'], type='http', auth='user', website=True)
    def portal_coach_home(self, week_offset=0, **kwargs):
        """Dashboard principal del coach con navegación de semanas"""
        # Convertir week_offset a entero
        try:
            week_offset = int(week_offset)
        except:
            week_offset = 0
        
        # Debug: Información del usuario actual
        current_user = request.env.user
        debug_info = {
            'user_id': current_user.id,
            'user_name': current_user.name,
            'user_login': current_user.login,
        }
        
        # Intentar obtener coach
        coach = self._get_coach()
        
        if not coach:
            # Buscar información adicional para debug
            coach_record = request.env['benglish.coach'].sudo().search([
                ('user_id', '=', current_user.id)
            ], limit=1)
            
            employee_record = request.env['hr.employee'].sudo().search([
                ('user_id', '=', current_user.id)
            ], limit=1)
            
            debug_info.update({
                'coach_exists': bool(coach_record),
                'coach_id': coach_record.id if coach_record else None,
                'employee_exists': bool(employee_record),
                'employee_id': employee_record.id if employee_record else None,
                'employee_name': employee_record.name if employee_record else None,
                'is_teacher': employee_record.is_teacher if employee_record else False,
            })
            
            return request.render('portal_coach.coach_not_found', {
                'debug_info': debug_info,
                'error_message': 'No se encontró un coach o empleado docente asociado a tu usuario.',
            })

        teacher = self._get_coach_employee(coach)
        if not teacher:
            debug_info.update({
                'coach_found': True,
                'coach_has_employee': hasattr(coach, 'employee_id'),
                'employee_id_value': coach.employee_id.id if hasattr(coach, 'employee_id') and coach.employee_id else None,
            })
            
            return request.render('portal_coach.coach_not_found', {
                'debug_info': debug_info,
                'error_message': 'El coach no tiene un empleado (hr.employee) asociado.',
            })

        today = fields.Date.today()
        now = datetime.now()
        
        # Convertir fecha a datetime para comparación
        today_start = datetime.combine(today, datetime.min.time())
        
        # MODIFICADO: Calcular semana con offset
        base_week_start = today - timedelta(days=today.weekday())
        week_start = base_week_start + timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=6)

        # Próxima sesión
        next_session = self._get_published_sessions(
            teacher,
            [
                ('date', '>=', today),
                '|',
                ('date', '>', today),
                ('time_start', '>=', now.hour + now.minute / 60.0),
            ]
        )
        next_session = next_session[:1] if next_session else False

        # Sesiones de esta semana
        week_sessions = self._get_published_sessions(
            teacher,
            [
                ('date', '>=', week_start),
                ('date', '<=', week_end),
            ]
        )

        # Próximas 5 sesiones
        upcoming_sessions = self._get_published_sessions(
            teacher,
            [
                ('date', '>=', today),
            ]
        )[:5]

        # Grupos activos (si aplica - esto depende de si hay relación con grupos)
        # Por ahora lo dejamos en 0 ya que academic_session no tiene grupos
        active_groups_count = 0

        values = {
            'coach': coach,
            'teacher': teacher,
            'next_session': next_session,
            'week_sessions': week_sessions,
            'upcoming_sessions': upcoming_sessions,
            'active_groups_count': active_groups_count,
            'week_sessions_count': len(week_sessions),
            'week_offset': week_offset,  # AGREGADO: Pasar offset al template
            'page_name': 'coach_dashboard',
        }

        return request.render('portal_coach.coach_dashboard', values)

    @http.route(['/my/coach/agenda'], type='http', auth='user', website=True)
    def portal_coach_agenda(self, start=None, **kwargs):
        """
        Vista de agenda semanal del coach
        Muestra solo sesiones publicadas (is_published=True)
        Refleja exactamente como se ve en el gestor académico
        """
        coach = self._get_coach()
        if not coach:
            return request.redirect('/my/coach')

        teacher = self._get_coach_employee(coach)
        if not teacher:
            return request.redirect('/my/coach')

        # Determinar rango de fechas
        if start:
            try:
                start_date = datetime.strptime(start, '%Y-%m-%d').date()
            except:
                start_date = fields.Date.today()
        else:
            # Inicio de esta semana (lunes)
            today = fields.Date.today()
            start_date = today - timedelta(days=today.weekday())

        end_date = start_date + timedelta(days=6)

        # Obtener sesiones de la semana
        week_sessions = self._get_published_sessions(
            teacher,
            [
                ('date', '>=', start_date),
                ('date', '<=', end_date),
            ]
        )

        # Organizar por día - FORMATO COMPATIBLE CON TEMPLATE
        days = []
        sessions_by_day = []  # Lista de tuplas (fecha, sesiones)
        today = fields.Date.today()
        
        for i in range(7):
            day_date = start_date + timedelta(days=i)
            day_sessions = week_sessions.filtered(lambda s: s.date == day_date)
            
            # Para template viejo (por si acaso)
            days.append({
                'date': day_date,
                'weekday': day_date.strftime('%A'),
                'day_number': day_date.day,
                'sessions': day_sessions,
                'is_today': day_date == fields.Date.today(),
            })
            
            # Para template nuevo (formato tupla)
            sessions_by_day.append((day_date, day_sessions))

        # Calcular estadísticas
        total_sessions = len(week_sessions)
        unique_subjects = week_sessions.mapped('subject_id')
        unique_subjects_count = len(unique_subjects)
        unique_agendas = week_sessions.mapped('agenda_id')
        unique_agendas_count = len(unique_agendas)
        
        # Calcular número de semana
        week_number = start_date.isocalendar()[1]

        # Navegación - FORMATO CORRECTO
        prev_week_start = (start_date - timedelta(days=7)).strftime('%Y-%m-%d')
        next_week_start = (start_date + timedelta(days=7)).strftime('%Y-%m-%d')

        values = {
            'coach': coach,
            'teacher': teacher,
            'days': days,
            'sessions_by_day': sessions_by_day,  # AGREGADO
            'today': today,  # AGREGADO
            'week_start': start_date,
            'week_end': end_date,
            'start_date': start_date,  # Compatibilidad con template
            'end_date': end_date,      # Compatibilidad con template
            'week_number': week_number,  # AGREGADO
            'total_sessions': total_sessions,  # AGREGADO
            'unique_subjects_count': unique_subjects_count,  # AGREGADO
            'unique_agendas_count': unique_agendas_count,  # AGREGADO
            'prev_week': prev_week_start,
            'next_week': next_week_start,
            'prev_week_start': prev_week_start,  # AGREGADO
            'next_week_start': next_week_start,  # AGREGADO
            'page_name': 'coach_agenda',
        }

        return request.render('portal_coach.coach_agenda', values)

    @http.route(['/my/coach/profile'], type='http', auth='user', website=True)
    def portal_coach_profile(self, **kwargs):
        """Perfil del coach"""
        coach = self._get_coach()
        if not coach:
            return request.redirect('/my/coach')

        teacher = self._get_coach_employee(coach)
        
        # Obtener estadísticas
        if teacher:
            all_sessions = self._get_published_sessions(teacher)
            total_sessions = len(all_sessions)
            future_sessions = len(all_sessions.filtered(
                lambda s: s.date >= fields.Date.today()
            ))
        else:
            total_sessions = 0
            future_sessions = 0

        values = {
            'coach': coach,
            'teacher': teacher,
            'total_sessions': total_sessions,
            'future_sessions': future_sessions,
            'page_name': 'coach_profile',
        }

        return request.render('portal_coach.coach_profile', values)

    @http.route(['/my/coach/session/<int:session_id>'], type='http', auth='user', website=True)
    def portal_coach_session_detail(self, session_id, **kwargs):
        """
        Detalle de una sesión específica
        Solo muestra si la sesión está publicada y pertenece al coach
        """
        coach = self._get_coach()
        if not coach:
            return request.redirect('/my/coach')

        teacher = self._get_coach_employee(coach)
        if not teacher:
            return request.redirect('/my/coach')

        # Buscar la sesión
        session = request.env['benglish.academic.session'].sudo().search([
            ('id', '=', session_id),
            ('teacher_id', '=', teacher.id),
            ('is_published', '=', True),
            ('active', '=', True),
        ], limit=1)

        if not session:
            return request.redirect('/my/coach/agenda')

        # Obtener inscripciones (estudiantes)
        enrollments = session.enrollment_ids
        
        # Verificar si todos los estudiantes tienen asistencia marcada
        pending_attendance = enrollments.filtered(
            lambda e: e.state not in ['attended', 'absent']
        )
        attendance_complete = len(pending_attendance) == 0

        values = {
            'coach': coach,
            'teacher': teacher,
            'session': session,
            'enrollments': enrollments,
            'attendance_complete': attendance_complete,
            'pending_count': len(pending_attendance),
            'page_name': 'session_detail',
        }

        return request.render('portal_coach.session_detail', values)

    # ========================================
    # RUTAS PARA GESTIÓN DE ASISTENCIA
    # ========================================

    @http.route(['/my/coach/session/<int:session_id>/mark_attendance'], 
                type='json', auth='user', methods=['POST'], csrf=False)
    def mark_attendance(self, session_id, enrollment_id, status, **kwargs):
        """
        Marca la asistencia de un estudiante
        
        Args:
            session_id: ID de la sesión
            enrollment_id: ID de la inscripción
            status: 'attended' o 'absent'
        
        Returns:
            JSON con resultado de la operación
        """
        try:
            # Verificar que el coach es dueño de la sesión
            coach = self._get_coach()
            if not coach:
                return {'success': False, 'error': 'No autorizado'}

            teacher = self._get_coach_employee(coach)
            if not teacher:
                return {'success': False, 'error': 'No autorizado'}

            # Buscar la sesión
            session = request.env['benglish.academic.session'].sudo().search([
                ('id', '=', session_id),
                ('teacher_id', '=', teacher.id),
            ], limit=1)

            if not session:
                return {'success': False, 'error': 'Sesión no encontrada'}

            # Buscar la inscripción
            enrollment = request.env['benglish.session.enrollment'].sudo().search([
                ('id', '=', enrollment_id),
                ('session_id', '=', session_id),
            ], limit=1)

            if not enrollment:
                return {'success': False, 'error': 'Inscripción no encontrada'}

            # Marcar asistencia usando write() para disparar hooks de sincronización
            if status == 'attended':
                enrollment.write({'state': 'attended'})
            elif status == 'absent':
                enrollment.write({'state': 'absent'})
            else:
                return {'success': False, 'error': 'Estado inválido'}

            return {
                'success': True,
                'enrollment_id': enrollment_id,
                'status': enrollment.state,
                'student_name': enrollment.student_id.name
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/my/coach/session/<int:session_id>/upload_session_files', type='http', auth='user', methods=['POST'], website=True, csrf=False)
    def upload_session_files(self, session_id, **post):
        """
        Sube archivos relacionados con una sesión
        Se usa cuando el coach selecciona "Materiales" y adjunta archivos
        
        Args:
            session_id: ID de la sesión
            post: Datos del POST incluyendo archivos
            
        Returns:
            JSON con resultado del upload
        """
        try:
            coach = self._get_coach()
            if not coach:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'No autorizado'}),
                    headers=[('Content-Type', 'application/json')]
                )

            teacher = self._get_coach_employee(coach)
            if not teacher:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'No autorizado'}),
                    headers=[('Content-Type', 'application/json')]
                )

            session = request.env['benglish.academic.session'].sudo().search([
                ('id', '=', session_id),
                ('teacher_id', '=', teacher.id),
            ], limit=1)

            if not session:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Sesión no encontrada'}),
                    headers=[('Content-Type', 'application/json')]
                )

            # Procesar archivos subidos
            uploaded_files = []
            file_count = 0
            
            # Los archivos vienen en request.httprequest.files
            for key in request.httprequest.files:
                file = request.httprequest.files[key]
                
                if file and file.filename:
                    # Leer contenido del archivo
                    file_content = file.read()
                    
                    # Crear attachment
                    attachment = request.env['ir.attachment'].sudo().create({
                        'name': file.filename,
                        'datas': base64.b64encode(file_content),
                        'res_model': 'benglish.academic.session',
                        'res_id': session.id,
                        'type': 'binary',
                        'description': f'Material de sesión - Subido por {coach.name}',
                    })
                    
                    uploaded_files.append({
                        'id': attachment.id,
                        'name': attachment.name,
                        'size': len(file_content),
                    })
                    file_count += 1
                    
                    _logger.info(f"Archivo '{file.filename}' subido para sesión {session_id} - Attachment ID: {attachment.id}")
            
            if file_count == 0:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'No se recibieron archivos'}),
                    headers=[('Content-Type', 'application/json')]
                )
            
            return request.make_response(
                json.dumps({
                    'success': True,
                    'message': f'{file_count} archivo(s) subido(s) correctamente',
                    'files': uploaded_files,
                    'count': file_count
                }),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.error(f"Error al subir archivos para sesión {session_id}: {str(e)}")
            return request.make_response(
                json.dumps({'success': False, 'error': str(e)}),
                headers=[('Content-Type', 'application/json')]
            )

    @http.route('/my/coach/session/<int:session_id>/get_session_observations', type='json', auth='user', methods=['POST'], website=True, csrf=False)
    @http.route('/my/coach/session/<int:session_id>/save_session_observations', type='json', auth='user', methods=['POST'], website=True, csrf=False)
    def save_session_observations(self, session_id, novedad_observations=None, novedad_type=None, **kwargs):
        """
        Guarda las observaciones de una sesión
        
        Args:
            session_id: ID de la sesión
            novedad_observations: Observaciones de novedad
            novedad_type: Tipo de novedad
            
        Returns:
            JSON con resultado
        """
        try:
            coach = self._get_coach()
            if not coach:
                return {'success': False, 'error': 'No autorizado'}

            teacher = self._get_coach_employee(coach)
            if not teacher:
                return {'success': False, 'error': 'No autorizado'}

            session = request.env['benglish.academic.session'].sudo().search([
                ('id', '=', session_id),
                ('teacher_id', '=', teacher.id),
            ], limit=1)

            if not session:
                return {'success': False, 'error': 'Sesión no encontrada'}

            # Por ahora, las observaciones se guardan al terminar la sesión
            # Esta ruta solo retorna success
            _logger.info(f"Observaciones guardadas temporalmente para sesión {session_id}")
            
            return {
                'success': True,
                'message': 'Observaciones guardadas'
            }

        except Exception as e:
            _logger.error(f"Error al guardar observaciones de sesión {session_id}: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_session_observations(self, session_id, **kwargs):
        """
        Obtiene las observaciones generales guardadas de una sesión
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            JSON con las observaciones
        """
        try:
            coach = self._get_coach()
            if not coach:
                return {'success': False, 'error': 'No autorizado'}

            teacher = self._get_coach_employee(coach)
            if not teacher:
                return {'success': False, 'error': 'No autorizado'}

            session = request.env['benglish.academic.session'].sudo().search([
                ('id', '=', session_id),
                ('teacher_id', '=', teacher.id),
            ], limit=1)

            if not session:
                return {'success': False, 'error': 'Sesión no encontrada'}

            # Por ahora, las observaciones se guardarán en un campo personalizado
            # Si no existe el campo, devolvemos vacío
            observations = session.general_observations if hasattr(session, 'general_observations') else ''
            
            return {
                'success': True,
                'observations': observations or ''
            }

        except Exception as e:
            _logger.error(f"Error al obtener observaciones de sesión {session_id}: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/my/coach/session/<int:session_id>/get_session_files', type='json', auth='user', methods=['POST'], website=True, csrf=False)
    def get_session_files(self, session_id, **kwargs):
        """
        Obtiene los archivos adjuntos de una sesión
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            JSON con la lista de archivos
        """
        try:
            coach = self._get_coach()
            if not coach:
                return {'success': False, 'error': 'No autorizado'}

            teacher = self._get_coach_employee(coach)
            if not teacher:
                return {'success': False, 'error': 'No autorizado'}

            session = request.env['benglish.academic.session'].sudo().search([
                ('id', '=', session_id),
                ('teacher_id', '=', teacher.id),
            ], limit=1)

            if not session:
                return {'success': False, 'error': 'Sesión no encontrada'}

            # Obtener attachments relacionados con la sesión
            attachments = request.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'benglish.academic.session'),
                ('res_id', '=', session.id),
            ])
            
            files = []
            for att in attachments:
                files.append({
                    'id': att.id,
                    'name': att.name,
                    'size': len(base64.b64decode(att.datas)) if att.datas else 0,
                    'url': f'/web/content/{att.id}?download=true',
                    'mimetype': att.mimetype or 'application/octet-stream',
                })
            
            return {
                'success': True,
                'files': files,
                'count': len(files)
            }

        except Exception as e:
            _logger.error(f"Error al obtener archivos de sesión {session_id}: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route(['/my/coach/session/<int:session_id>/start'], 
                type='json', auth='user', methods=['POST'], csrf=False)
    def start_session(self, session_id, **kwargs):
        """
        Inicia una sesión (cambia estado a 'started')
        """
        try:
            coach = self._get_coach()
            if not coach:
                return {'success': False, 'error': 'No autorizado'}

            teacher = self._get_coach_employee(coach)
            if not teacher:
                return {'success': False, 'error': 'No autorizado'}

            session = request.env['benglish.academic.session'].sudo().search([
                ('id', '=', session_id),
                ('teacher_id', '=', teacher.id),
            ], limit=1)

            if not session:
                return {'success': False, 'error': 'Sesión no encontrada'}

            if session.state not in ['draft', 'active', 'with_enrollment']:
                return {'success': False, 'error': 'Solo se pueden iniciar sesiones en borrador o activas'}

            session.state = 'started'

            return {
                'success': True,
                'state': session.state,
                'message': 'Clase iniciada correctamente'
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(['/my/coach/session/<int:session_id>/finish'], 
                type='json', auth='user', methods=['POST'], csrf=False)
    @http.route('/my/coach/session/<int:session_id>/finish', type='json', auth='user', methods=['POST'], website=True)
    def finish_session(self, session_id, novedad_type=None, observaciones=None, **kwargs):
        """
        Finaliza una sesión (cambia estado a 'done')
        Valida que todos los estudiantes tengan asistencia marcada
        Crea registros en benglish.academic.history para cada estudiante
        
        Args:
            session_id: ID de la sesión
            novedad_type: Tipo de novedad ('aplazada', 'materiales', None para sin novedad)
            observaciones: Observaciones de la sesión
        """
        try:
            coach = self._get_coach()
            if not coach:
                return {'success': False, 'error': 'No autorizado'}

            teacher = self._get_coach_employee(coach)
            if not teacher:
                return {'success': False, 'error': 'No autorizado'}

            session = request.env['benglish.academic.session'].sudo().search([
                ('id', '=', session_id),
                ('teacher_id', '=', teacher.id),
            ], limit=1)

            if not session:
                return {'success': False, 'error': 'Sesión no encontrada'}

            if session.state != 'started':
                return {'success': False, 'error': 'Solo se pueden finalizar sesiones iniciadas'}

            # Verificar que todos tengan asistencia marcada
            pending = session.enrollment_ids.filtered(
                lambda e: e.state not in ['attended', 'absent', 'cancelled']
            )

            if pending:
                return {
                    'success': False, 
                    'error': f'Hay {len(pending)} estudiantes sin asistencia marcada'
                }

            # ==============================================
            # DETERMINAR TIPO DE NOVEDAD PARA LA BITÁCORA
            # ==============================================
            
            # Mapeo de novedades del portal → bitácora académica
            # El campo 'novedad' en benglish.academic.history tiene estas opciones:
            # - "normal" (por defecto)
            # - "retraso", "salida_temprana", "comportamiento", "participacion_destacada", "otro"
            
            novedad_value = 'normal'  # Por defecto
            notes_text = observaciones or ''
            
            if novedad_type:
                if novedad_type == 'aplazada':
                    novedad_value = 'otro'
                    prefix = 'CLASE APLAZADA'
                    notes_text = f'{prefix}: {observaciones}' if observaciones else prefix
                    
                elif novedad_type == 'materiales':
                    novedad_value = 'otro'
                    prefix = 'MATERIALES SUBIDOS'
                    notes_text = f'{prefix}: {observaciones}' if observaciones else prefix
            
            # ==============================================
            # CREAR REGISTROS EN BITÁCORA ACADÉMICA
            # ==============================================
            
            _logger.info(f"Creando registros de bitácora para sesión {session.id} con novedad '{novedad_value}'")
            
            try:
                for enrollment in session.enrollment_ids:
                    # Solo crear registro si el estudiante asistió
                    if enrollment.state == 'attended':
                        
                        # Buscar si ya existe un registro (por si acaso)
                        existing = request.env['benglish.academic.history'].sudo().search([
                            ('session_id', '=', session.id),
                            ('student_id', '=', enrollment.student_id.id),
                        ], limit=1)
                        
                        if existing:
                            _logger.warning(f"Ya existe registro de bitácora para estudiante {enrollment.student_id.id} en sesión {session.id}")
                            continue
                        
                        # Obtener nota del tracking si existe
                        grade = False
                        tracking = request.env['benglish.subject.session.tracking'].sudo().search([
                            ('session_id', '=', session.id),
                            ('student_id', '=', enrollment.student_id.id),
                        ], limit=1)
                        
                        if tracking and tracking.grade:
                            grade = tracking.grade
                        
                        # Preparar datos para el registro de bitácora
                        history_vals = {
                            # Relaciones principales
                            'student_id': enrollment.student_id.id,
                            'session_id': session.id,
                            'enrollment_id': enrollment.id,
                            
                            # Datos de la sesión (denormalizados)
                            'session_date': session.date,
                            'session_time_start': session.time_start,
                            'session_time_end': session.time_end,
                            'program_id': session.program_id.id,
                            'plan_id': session.plan_id.id if session.plan_id else False,
                            'level_id': session.level_id.id,
                            'subject_id': session.subject_id.id,
                            'teacher_id': session.teacher_id.id,
                            'campus_id': session.campus_id.id,
                            'group_id': session.group_id.id if session.group_id else False,
                            'modality': session.modality,
                            'session_code': session.complete_code,
                            
                            # Estado de asistencia
                            'attendance_status': 'attended',  # Solo creamos para los que asistieron
                            
                            # Novedad y observaciones
                            'novedad': novedad_value,
                            'notes': notes_text,
                            
                            # Calificación (si existe)
                            'grade': grade if grade else False,
                        }
                        
                        # Crear registro en bitácora
                        history_record = request.env['benglish.academic.history'].sudo().create(history_vals)
                        _logger.info(f"Creado registro de bitácora ID {history_record.id} para estudiante {enrollment.student_id.name}")
                
                _logger.info(f"Registros de bitácora creados exitosamente para sesión {session.id}")
                
            except Exception as e:
                _logger.error(f"Error al crear registros de bitácora: {str(e)}")
                # No bloqueamos la finalización de la sesión por errores en bitácora
                # pero registramos el error

            # ==============================================
            # FINALIZAR SESIÓN
            # ==============================================
            
            session.state = 'done'
            
            return {
                'success': True,
                'state': session.state,
                'message': 'Clase terminada correctamente y registrada en bitácora'
            }

        except Exception as e:
            _logger.error(f"Error al finalizar sesión: {str(e)}")
            return {'success': False, 'error': str(e)}


    @http.route('/my/coach/session/<int:session_id>/save_grade', type='json', auth='user', methods=['POST'], website=True)
    def save_grade(self, session_id, enrollment_id, grade, **kwargs):
        """
        Guarda la nota/calificación de un estudiante en benglish.subject.session.tracking
        
        Parámetros:
            - session_id: ID de la sesión
            - enrollment_id: ID del enrollment del estudiante
            - grade: Nota (0-100)
            
        Retorna:
            {
                'success': True/False,
                'message': 'Mensaje de resultado',
                'grade': nota guardada
            }
        """
        try:
            # Obtener coach del usuario actual
            coach = request.env['benglish.coach'].sudo().search([
                ('user_id', '=', request.env.user.id)
            ], limit=1)
            
            # Validar sesión
            session = request.env['benglish.academic.session'].sudo().browse(session_id)
            if not session.exists():
                return {'success': False, 'message': 'Sesión no encontrada'}
            
            # Validar enrollment
            enrollment = request.env['benglish.session.enrollment'].sudo().browse(enrollment_id)
            if not enrollment.exists():
                return {'success': False, 'message': 'Inscripción no encontrada'}
            
            # Validar que el enrollment pertenece a esta sesión
            if enrollment.session_id.id != session_id:
                return {'success': False, 'message': 'Inscripción no pertenece a esta sesión'}
            
            # Validar que la sesión esté iniciada
            if session.state not in ['started', 'done']:
                return {'success': False, 'message': 'Solo se puede guardar notas en sesiones iniciadas'}
            
            # VALIDAR QUE LA ASIGNATURA SEA EVALUABLE
            if not session.subject_id.evaluable:
                return {'success': False, 'message': 'Esta asignatura no es calificable'}
            
            # Validar que el estudiante asistió
            if enrollment.state != 'attended':
                return {'success': False, 'message': 'Solo se puede calificar estudiantes que asistieron'}
            
            # Validar rango de nota (0-100 según el modelo)
            try:
                grade_float = float(grade)
                if grade_float < 0 or grade_float > 100:
                    return {'success': False, 'message': 'La nota debe estar entre 0 y 100'}
                # Redondear a 2 decimales
                grade_float = round(grade_float, 2)
            except (ValueError, TypeError):
                return {'success': False, 'message': 'Nota inválida'}
            
            # Buscar o crear registro en subject_session_tracking
            # Buscar por student_id + subject_id (constraint único)
            tracking = request.env['benglish.subject.session.tracking'].sudo().search([
                ('student_id', '=', enrollment.student_id.id),
                ('subject_id', '=', session.subject_id.id),
            ], limit=1)
            
            if tracking:
                # Actualizar tracking existente
                tracking.write({
                    'session_id': session_id,
                    'session_code': session.session_code if hasattr(session, 'session_code') else False,
                    'attended': True,  # Si está calificando, asistió
                    'grade': grade_float,
                    'teacher_id': coach.id if coach else False,  # benglish.coach
                    'state': 'registered',
                })
            else:
                # Crear nuevo tracking
                tracking = request.env['benglish.subject.session.tracking'].sudo().create({
                    'student_id': enrollment.student_id.id,
                    'subject_id': session.subject_id.id,
                    'session_id': session_id,
                    'session_code': session.session_code if hasattr(session, 'session_code') else False,
                    'phase_id': session.subject_id.phase_id.id if session.subject_id.phase_id else False,
                    'level_id': session.subject_id.level_id.id if session.subject_id.level_id else False,
                    'attended': True,
                    'grade': grade_float,
                    'teacher_id': coach.id if coach else False,  # benglish.coach
                    'state': 'registered',
                })
            
            _logger.info(f"Nota guardada: Session={session_id}, Student={enrollment.student_id.name}, Grade={grade_float}")
            
            return {
                'success': True,
                'message': f'Nota {grade_float} guardada correctamente',
                'grade': grade_float,
            }
            
        except Exception as e:
            _logger.error(f"Error al guardar nota: {str(e)}")
            return {
                'success': False,
                'message': f'Error al guardar nota: {str(e)}'
            }
    
    
    @http.route('/my/coach/session/<int:session_id>/save_observation', type='json', auth='user', methods=['POST'], website=True)
    def save_observation(self, session_id, enrollment_id, observation, **kwargs):
        """
        Guarda la observación de un estudiante en benglish.subject.session.tracking
        
        Parámetros:
            - session_id: ID de la sesión
            - enrollment_id: ID del enrollment del estudiante
            - observation: Texto de observación
            
        Retorna:
            {
                'success': True/False,
                'message': 'Mensaje de resultado'
            }
        """
        try:
            # Obtener coach del usuario actual
            coach = request.env['benglish.coach'].sudo().search([
                ('user_id', '=', request.env.user.id)
            ], limit=1)
            
            # Validar sesión
            session = request.env['benglish.academic.session'].sudo().browse(session_id)
            if not session.exists():
                return {'success': False, 'message': 'Sesión no encontrada'}
            
            # Validar enrollment
            enrollment = request.env['benglish.session.enrollment'].sudo().browse(enrollment_id)
            if not enrollment.exists():
                return {'success': False, 'message': 'Inscripción no encontrada'}
            
            # Validar que el enrollment pertenece a esta sesión
            if enrollment.session_id.id != session_id:
                return {'success': False, 'message': 'Inscripción no pertenece a esta sesión'}
            
            # Validar que la sesión esté iniciada
            if session.state not in ['started', 'done']:
                return {'success': False, 'message': 'Solo se puede guardar observaciones en sesiones iniciadas'}
            
            # Limpiar observación
            observation_text = observation.strip() if observation else ''
            
            # Buscar o crear registro en subject_session_tracking
            # Buscar por student_id + subject_id (constraint único)
            tracking = request.env['benglish.subject.session.tracking'].sudo().search([
                ('student_id', '=', enrollment.student_id.id),
                ('subject_id', '=', session.subject_id.id),
            ], limit=1)
            
            if tracking:
                # Actualizar tracking existente
                tracking.write({
                    'session_id': session_id,
                    'session_code': session.session_code if hasattr(session, 'session_code') else False,
                    'notes': observation_text,
                    'teacher_id': coach.id if coach else False,
                    'state': 'registered',
                })
            else:
                # Crear nuevo tracking
                tracking = request.env['benglish.subject.session.tracking'].sudo().create({
                    'student_id': enrollment.student_id.id,
                    'subject_id': session.subject_id.id,
                    'session_id': session_id,
                    'session_code': session.session_code if hasattr(session, 'session_code') else False,
                    'phase_id': session.subject_id.phase_id.id if session.subject_id.phase_id else False,
                    'level_id': session.subject_id.level_id.id if session.subject_id.level_id else False,
                    'attended': enrollment.state == 'attended',
                    'notes': observation_text,
                    'teacher_id': coach.id if coach else False,
                    'state': 'registered',
                })
            
            # También actualizar las notas en el enrollment
            enrollment.write({
                'notes': observation_text,
            })
            
            _logger.info(f"Observación guardada: Session={session_id}, Student={enrollment.student_id.name}")
            
            return {
                'success': True,
                'message': 'Observación guardada correctamente',
            }
            
        except Exception as e:
            _logger.error(f"Error al guardar observación: {str(e)}")
            return {
                'success': False,
                'message': f'Error al guardar observación: {str(e)}'
            }
    
    
    @http.route('/my/coach/session/<int:session_id>/get_student_data', type='json', auth='user', methods=['POST'], website=True)
    def get_student_data(self, session_id, **kwargs):
        """
        Obtiene los datos guardados de todos los estudiantes de una sesión.
        Útil para cargar datos existentes cuando el coach abre la sesión.
        
        Retorna:
            {
                'success': True/False,
                'data': {
                    enrollment_id: {
                        'grade': nota,
                        'observation': observación,
                        'attendance': estado
                    },
                    ...
                }
            }
        """
        try:
            # Obtener sesión
            session = request.env['benglish.academic.session'].sudo().browse(session_id)
            if not session.exists():
                return {'success': False, 'message': 'Sesión no encontrada'}
            
            # Obtener todos los enrollments de esta sesión
            enrollments = request.env['benglish.session.enrollment'].sudo().search([
                ('session_id', '=', session_id)
            ])
            
            # Construir diccionario de datos
            data = {}
            for enrollment in enrollments:
                # Buscar tracking por student_id + subject_id
                tracking = request.env['benglish.subject.session.tracking'].sudo().search([
                    ('student_id', '=', enrollment.student_id.id),
                    ('subject_id', '=', session.subject_id.id),
                ], limit=1)
                
                data[enrollment.id] = {
                    'grade': tracking.grade if tracking else None,
                    'observation': tracking.notes if tracking else (enrollment.notes or ''),
                    'attendance': enrollment.state,
                }
            
            return {
                'success': True,
                'data': data,
            }
            
        except Exception as e:
            _logger.error(f"Error al obtener datos de estudiantes: {str(e)}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
        
    @http.route('/my/coach/change_password', type='http', auth='user', website=True)
    def coach_change_password(self, **kw):
        """
        Página personalizada para cambiar contraseña del coach
        """
        values = {
            'page_name': 'change_password',
            'error': kw.get('error'),
            'success': kw.get('success'),
        }
        return request.render('portal_coach.change_password_template', values)


    @http.route(
        '/my/coach/change_password/submit',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
        csrf=True
    )
    def coach_change_password_submit(self, old_password, new_password, confirm_password, **kw):
        """
        Procesa el cambio de contraseña
        """
        user = request.env.user

        # Validar que las contraseñas coincidan
        if new_password != confirm_password:
            return request.redirect('/my/coach/change_password?error=no_match')

        # Validar longitud mínima
        if len(new_password) < 8:
            return request.redirect('/my/coach/change_password?error=too_short')

        try:
            # Verificar contraseña actual
            request.env['res.users'].sudo().browse(user.id)._check_credentials(
                old_password, {'interactive': True}
            )

            # Cambiar contraseña
            user.sudo().write({'password': new_password})

            return request.redirect('/my/coach?success=password_changed')

        except Exception as e:
            _logger.error(f"Error al cambiar contraseña: {str(e)}")
            return request.redirect('/my/coach/change_password?error=wrong_password')

    @http.route(['/my/coach/history'], type='http', auth='user', website=True)
    def portal_coach_history(self, page=1, search=None, **kwargs):
        """
        Vista de historial de clases dictadas (estado 'done')
        Muestra todas las sesiones finalizadas con paginación y búsqueda
        """
        coach = self._get_coach()
        if not coach:
            return request.redirect('/my/coach')

        teacher = self._get_coach_employee(coach)
        if not teacher:
            return request.redirect('/my/coach')

        # Convertir página a entero
        try:
            page = int(page)
        except:
            page = 1

        # Configuración de paginación
        sessions_per_page = 20
        offset = (page - 1) * sessions_per_page

        # Dominio base: sesiones terminadas
        domain = [
            ('teacher_id', '=', teacher.id),
            ('state', '=', 'done'),
            ('active', '=', True),
        ]

        # Agregar búsqueda si existe
        if search:
            domain.extend([
                '|', '|', '|',
                ('subject_id.name', 'ilike', search),
                ('subject_id.code', 'ilike', search),
                ('program_id.name', 'ilike', search),
                ('agenda_id.name', 'ilike', search),
            ])

        # Obtener sesiones
        Session = request.env['benglish.academic.session'].sudo()
        total_sessions = Session.search_count(domain)
        sessions = Session.search(
            domain,
            limit=sessions_per_page,
            offset=offset,
            order='date desc, time_start desc'
        )

        # Calcular paginación
        total_pages = (total_sessions + sessions_per_page - 1) // sessions_per_page

        # Estadísticas
        all_done_sessions = Session.search([('teacher_id', '=', teacher.id), ('state', '=', 'done')])
        unique_subjects = len(all_done_sessions.mapped('subject_id'))
        unique_programs = len(all_done_sessions.mapped('program_id'))
        total_students_taught = sum(session.enrolled_count for session in all_done_sessions)

        values = {
            'coach': coach,
            'teacher': teacher,
            'sessions': sessions,
            'total_sessions': total_sessions,
            'unique_subjects': unique_subjects,
            'unique_programs': unique_programs,
            'total_students_taught': total_students_taught,
            'page': page,
            'total_pages': total_pages,
            'search': search or '',
            'page_name': 'coach_history',
        }

        return request.render('portal_coach.coach_history', values)

    @http.route(['/my/coach/history/clear'], type='json', auth='user', methods=['POST'], csrf=False)
    def clear_coach_history(self, **kwargs):
        """
        Limpia el historial de clases (marca como inactive)
        """
        try:
            coach = self._get_coach()
            if not coach:
                return {'success': False, 'error': 'No autorizado'}

            teacher = self._get_coach_employee(coach)
            if not teacher:
                return {'success': False, 'error': 'No autorizado'}

            # Buscar todas las sesiones terminadas
            sessions = request.env['benglish.academic.session'].sudo().search([
                ('teacher_id', '=', teacher.id),
                ('state', '=', 'done'),
                ('active', '=', True),
            ])

            # Marcar como inactivas
            sessions.write({'active': False})

            return {
                'success': True,
                'message': f'{len(sessions)} clases eliminadas del historial',
                'count': len(sessions)
            }

        except Exception as e:
            _logger.error(f"Error al limpiar historial: {str(e)}")
            return {'success': False, 'error': str(e)}



    # ========================================
    # DATOS PERSONALES DEL COACH
    # ========================================
    
@http.route(['/my/coach/profile'], type='http', auth='user', website=True)
def coach_profile(self, success=None, **kwargs):
        """
        Página de perfil del coach con todos sus datos personales
        Permite ver y editar la información
        """
        coach = self._get_coach()
        if not coach:
            return request.redirect('/my')

        teacher = self._get_coach_employee(coach)

        # Obtener países y estados para los selectores
        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])
        programs = request.env['benglish.program'].sudo().search([])
        levels = request.env['benglish.level'].sudo().search([])
        campuses = request.env['benglish.campus'].sudo().search([])
        
        values = {
            'page_name': 'coach_profile',
            'coach': coach,
            'teacher': teacher,
            'countries': countries,
            'states': states,
            'programs': programs,
            'levels': levels,
            'campuses': campuses,
            'success': success,
        }
        
        return request.render('portal_coach.coach_profile_template', values)

@http.route(['/my/coach/profile/update'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
def coach_profile_update(self, **post):
        """
        Actualiza los datos personales del coach
        Solo permite actualizar campos que el coach puede modificar
        """
        try:
            coach = self._get_coach()
            if not coach:
                return request.redirect('/my')

            # Campos que el coach PUEDE modificar
            update_vals = {}
            
            # Información de contacto
            if post.get('phone'):
                update_vals['phone'] = post.get('phone')
            if post.get('email'):
                update_vals['email'] = post.get('email')
            if 'street' in post:
                update_vals['street'] = post.get('street') or False
            if 'street2' in post:
                update_vals['street2'] = post.get('street2') or False
            if 'city' in post:
                update_vals['city'] = post.get('city') or False
            if 'zip' in post:
                update_vals['zip'] = post.get('zip') or False
            
            # Estado y país
            if post.get('state_id'):
                update_vals['state_id'] = int(post.get('state_id'))
            elif 'state_id' in post:
                update_vals['state_id'] = False
                
            if post.get('country_id'):
                update_vals['country_id'] = int(post.get('country_id'))
            
            # Información personal
            if post.get('birth_date'):
                update_vals['birth_date'] = post.get('birth_date')
            elif 'birth_date' in post:
                update_vals['birth_date'] = False
                
            if 'identification_number' in post:
                update_vals['identification_number'] = post.get('identification_number') or False
            
            # Información académica
            if 'specialization' in post:
                update_vals['specialization'] = post.get('specialization') or False
            if post.get('experience_years'):
                try:
                    update_vals['experience_years'] = int(post.get('experience_years'))
                except ValueError:
                    pass
            
            # Actualizar el coach
            if update_vals:
                coach.sudo().write(update_vals)
                _logger.info(f"Coach {coach.code} actualizó sus datos personales")

            return request.redirect('/my/coach/profile?success=1')

        except Exception as e:
            _logger.error(f"Error al actualizar datos del coach: {str(e)}")
            return request.redirect('/my/coach/profile?success=0')

@http.route('/my/coach/change_password', type='http', auth='user', website=True)
def coach_change_password(self, **kw):
        """
        Página personalizada para cambiar contraseña del coach
        """
        values = {
            'page_name': 'change_password',
            'error': kw.get('error'),
            'success': kw.get('success'),
        }
        return request.render('portal_coach.change_password_template', values)
    
@http.route('/my/coach/change_password/submit', type='http', auth='user', methods=['POST'], website=True, csrf=True)
def coach_change_password_submit(self, old_password, new_password, confirm_password, **kw):
        """
        Procesa el cambio de contraseña
        """
        user = request.env.user
        
        # Validar que las contraseñas coincidan
        if new_password != confirm_password:
            return request.redirect('/my/coach/change_password?error=no_match')
        
        # Validar longitud mínima
        if len(new_password) < 8:
            return request.redirect('/my/coach/change_password?error=too_short')
        
        # Intentar cambiar la contraseña
        try:
            # Verificar contraseña actual
            request.env['res.users'].sudo().browse(user.id)._check_credentials(old_password, {'interactive': True})
            
            # Cambiar contraseña
            user.sudo().write({'password': new_password})
            
            # Redirigir al portal con mensaje de éxito
            return request.redirect('/my/coach?success=password_changed')
            
        except Exception as e:
            _logger.error(f"Error al cambiar contraseña: {str(e)}")
            return request.redirect('/my/coach/change_password?error=wrong_password')
        
@http.route('/my/coach/session/<int:session_id>/delete_session_file',type='json', auth='user', methods=['POST'], website=True, csrf=False)
def delete_session_file(self, session_id, file_id, **kwargs):
            """
            Elimina un archivo adjunto de una sesión
            """
            try:
                coach = self._get_coach()
                if not coach:
                    return {'success': False, 'message': 'No autorizado'}

                teacher = self._get_coach_employee(coach)
                if not teacher:
                    return {'success': False, 'message': 'No autorizado'}

                session = request.env['benglish.academic.session'].sudo().search([
                    ('id', '=', session_id),
                    ('teacher_id', '=', teacher.id),
                ], limit=1)

                if not session:
                    return {'success': False, 'message': 'Sesión no encontrada'}

                attachment = request.env['ir.attachment'].sudo().browse(file_id)
                if not attachment.exists():
                    return {'success': False, 'message': 'Archivo no encontrado'}

                if attachment.res_model != 'benglish.academic.session' or attachment.res_id != session.id:
                    return {'success': False, 'message': 'Archivo no pertenece a esta sesión'}

                attachment.unlink()

                _logger.info(f"Archivo {file_id} eliminado de sesión {session_id}")

                return {
                    'success': True,
                    'message': 'Archivo eliminado correctamente'
                }

            except Exception as e:
                _logger.error(f"Error al eliminar archivo {file_id} de sesión {session_id}: {str(e)}")
                return {
                    'success': False,
                    'message': str(e)
                }