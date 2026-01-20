# -*- coding: utf-8 -*-
"""Controlador REST para sincronización de sesiones con portales."""

import json
from datetime import datetime, timedelta
from odoo import http, fields, _
from odoo.http import request, Response


class PortalSyncController(http.Controller):
    """API REST para exportar sesiones publicadas a portales externos."""

    @http.route('/api/v1/sessions/published', type='http', auth='public', methods=['GET'], csrf=False)
    def get_published_sessions(self, **kwargs):
        """
        Endpoint para obtener sesiones publicadas.
        
        Parámetros query string opcionales:
        - campus_id: Filtrar por sede (ID)
        - start_date: Fecha inicio (YYYY-MM-DD)
        - end_date: Fecha fin (YYYY-MM-DD)
        - subject_id: Filtrar por asignatura (ID)
        - format: json (default) o csv
        - api_key: Clave de autenticación (requerida en producción)
        """
        # Validar API key (básico, mejorar en producción con OAuth2)
        api_key = kwargs.get('api_key')
        if not self._validate_api_key(api_key):
            return Response(
                json.dumps({'error': 'Invalid or missing API key'}),
                status=401,
                content_type='application/json'
            )
        
        # Construir dominio de búsqueda
        domain = [('is_published', '=', True), ('state', '!=', 'cancelled')]
        
        if kwargs.get('campus_id'):
            try:
                domain.append(('campus_id', '=', int(kwargs['campus_id'])))
            except ValueError:
                pass
        
        if kwargs.get('subject_id'):
            try:
                domain.append(('subject_id', '=', int(kwargs['subject_id'])))
            except ValueError:
                pass
        
        if kwargs.get('start_date'):
            try:
                start_dt = fields.Datetime.to_datetime(datetime.strptime(kwargs['start_date'], '%Y-%m-%d'))
                domain.append(('start_datetime', '>=', start_dt))
            except ValueError:
                pass
        
        if kwargs.get('end_date'):
            try:
                end_dt = fields.Datetime.to_datetime(datetime.strptime(kwargs['end_date'], '%Y-%m-%d'))
                domain.append(('start_datetime', '<=', end_dt))
            except ValueError:
                pass
        
        # Buscar sesiones
        Session = request.env['benglish.class.session'].sudo()
        sessions = Session.search(domain, order='start_datetime asc')
        
        # Formato de respuesta
        output_format = kwargs.get('format', 'json').lower()
        
        if output_format == 'csv':
            return self._export_csv(sessions)
        else:
            return self._export_json(sessions)

    def _validate_api_key(self, api_key):
        """Valida la clave API (implementación básica)."""
        # MODO DESARROLLO: Permitir acceso sin API key
        # Para producción, configurar la clave en Configuración > Parámetros técnicos:
        # - benglish.api.allow_no_key = False
        # - benglish.api.key = tu_clave_secreta
        
        # Si no viene por query param, intentar leer header Authorization: Bearer <token>
        if not api_key:
            try:
                auth_header = request.httprequest.headers.get('Authorization')
            except Exception:
                auth_header = None
            if auth_header and auth_header.startswith('Bearer '):
                api_key = auth_header.split(' ', 1)[1].strip()

        # Si aún no hay api_key, permitir en desarrollo (por defecto True)
        if not api_key:
            allow_no_key = request.env['ir.config_parameter'].sudo().get_param('benglish.api.allow_no_key', 'True')
            return allow_no_key == 'True'

        # Comparar con clave almacenada en configuración
        valid_key = request.env['ir.config_parameter'].sudo().get_param('benglish.api.key', '')
        return api_key == valid_key

    def _export_json(self, sessions):
        """Exporta sesiones en formato JSON."""
        data = {
            'status': 'success',
            'count': len(sessions),
            'timestamp': fields.Datetime.now().isoformat(),
            'sessions': []
        }
        
        for session in sessions:
            session_data = {
                'id': session.id,
                'name': session.display_name,
                'subject': {
                    'id': session.subject_id.id,
                    'name': session.subject_id.name,
                } if session.subject_id else None,
                'campus': {
                    'id': session.campus_id.id,
                    'name': session.campus_id.name,
                    'code': session.campus_id.code,
                },
                'subcampus': {
                    'id': session.subcampus_id.id,
                    'name': session.subcampus_id.name,
                } if session.subcampus_id else None,
                'teacher': {
                    'id': session.teacher_id.id,
                    'name': session.teacher_id.name,
                } if session.teacher_id else None,
                'coach': {
                    'id': session.coach_id.id,
                    'name': session.coach_id.name,
                } if session.coach_id else None,
                'schedule': {
                    'start_datetime': session.start_datetime.isoformat() if session.start_datetime else None,
                    'end_datetime': session.end_datetime.isoformat() if session.end_datetime else None,
                    'duration_hours': session.duration_hours,
                },
                'delivery': {
                    'mode': session.delivery_mode,
                    'meeting_link': session.meeting_link,
                    'meeting_platform': session.meeting_platform,
                },
                'session_type': session.session_type,
                'state': session.state,
                'published_at': session.published_at.isoformat() if session.published_at else None,
            }
            data['sessions'].append(session_data)
        
        return Response(
            json.dumps(data, ensure_ascii=False, indent=2),
            status=200,
            content_type='application/json; charset=utf-8'
        )

    def _export_csv(self, sessions):
        """Exporta sesiones en formato CSV."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Encabezados
        writer.writerow([
            'ID', 'Nombre', 'Asignatura', 'Sede', 'Aula',
            'Docente', 'Inicio', 'Fin', 'Duración (hrs)', 'Modalidad',
            'Enlace', 'Estado', 'Publicado'
        ])
        
        # Datos
        for session in sessions:
            writer.writerow([
                session.id,
                session.display_name,
                session.subject_id.name if session.subject_id else '',
                session.campus_id.name if session.campus_id else '',
                session.subcampus_id.name if session.subcampus_id else '',
                session.teacher_id.name if session.teacher_id else '',
                session.start_datetime.strftime('%Y-%m-%d %H:%M') if session.start_datetime else '',
                session.end_datetime.strftime('%Y-%m-%d %H:%M') if session.end_datetime else '',
                session.duration_hours,
                session.delivery_mode,
                session.meeting_link or '',
                session.state,
                session.published_at.strftime('%Y-%m-%d %H:%M') if session.published_at else '',
            ])
        
        csv_data = output.getvalue()
        output.close()
        
        return Response(
            csv_data,
            status=200,
            content_type='text/csv; charset=utf-8',
            headers=[
                ('Content-Disposition', 'attachment; filename="sessions_published.csv"')
            ]
        )

    @http.route('/api/v1/sessions/stats', type='http', auth='public', methods=['GET'], csrf=False)
    def get_session_stats(self, **kwargs):
        """
        Endpoint para obtener estadísticas de sesiones publicadas.
        
        Parámetros query string opcionales:
        - campus_id: Filtrar por sede
        - api_key: Clave de autenticación
        """
        api_key = kwargs.get('api_key')
        if not self._validate_api_key(api_key):
            return Response(
                json.dumps({'error': 'Invalid or missing API key'}),
                status=401,
                content_type='application/json'
            )
        
        Session = request.env['benglish.class.session'].sudo()
        
        domain = [('is_published', '=', True)]
        if kwargs.get('campus_id'):
            try:
                domain.append(('campus_id', '=', int(kwargs['campus_id'])))
            except ValueError:
                pass
        
        stats = {
            'status': 'success',
            'timestamp': fields.Datetime.now().isoformat(),
            'total_published': Session.search_count(domain),
            'by_state': {
                'planned': Session.search_count(domain + [('state', '=', 'planned')]),
                'in_progress': Session.search_count(domain + [('state', '=', 'in_progress')]),
                'done': Session.search_count(domain + [('state', '=', 'done')]),
            },
            'by_mode': {
                'presential': Session.search_count(domain + [('delivery_mode', '=', 'presential')]),
                'virtual': Session.search_count(domain + [('delivery_mode', '=', 'virtual')]),
                'hybrid': Session.search_count(domain + [('delivery_mode', '=', 'hybrid')]),
            }
        }
        
        return Response(
            json.dumps(stats, ensure_ascii=False, indent=2),
            status=200,
            content_type='application/json; charset=utf-8'
        )
    # http://localhost:8071/api/v1/sessions/published?format=json