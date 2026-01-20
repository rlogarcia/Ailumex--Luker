# -*- coding: utf-8 -*-
{
    'name': 'Portal del Coach',
    'version': '2.0.0',
    'category': 'Website',
    'summary': 'Portal web para coaches - Integrado con Horarios Académicos',
    'description': """
        Portal del Coach - Versión 2.0
        ===============================
        
        Modificado para integrarse con el módulo benglish_academy:
        - Usa benglish.academic.session en lugar de benglish.class.session
        - Muestra solo sesiones publicadas (is_published=True)
        - Filtra por teacher_id (hr.employee) del coach logueado
        - Refleja los cambios editados en tiempo real
        - Visualización idéntica al gestor académico
        
        Características:
        - Dashboard con próximas sesiones
        - Horario semanal con navegación
        - Vista de horarios académicos
        - Vista de programas y asignaturas
        - Detalle de sesiones con estudiantes inscritos
        - Perfil del coach
    """,
    'author': 'B English Academy',
    'depends': [
        'base',
        'portal',
        'website',
        'benglish_academy',  # Dependencia del módulo académico
        'hr',
    ],
    'data': [
        # Vistas backend
        #'views/coach_hr_views.xml',
        # Templates frontend
        'views/portal_coach_templates.xml',
        'views/portal_agenda_templates.xml',
        'views/portal_session_detail_template.xml',
        'views/portal_history_template.xml',
        'views/change_password_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'portal_coach/static/src/css/portal_coach.css',
            'portal_coach/static/src/js/portal_coach.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
