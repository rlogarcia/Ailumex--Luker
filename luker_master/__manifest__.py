# -*- coding: utf-8 -*-
{
    'name': 'Gestor Operativo — Plataforma Luker',
    'version': '18.0.3.0.0',
    'summary': 'Gestión operativa de participantes, contexto organizacional, carga masiva SIMAT y resultados.',
    'description': """
        Gestor Operativo — Plataforma Luker
        =====================================
        - Participantes vinculados a Contactos (res.partner)
        - Tipos de identificación del localizador latinoamericano (l10n_latam)
        - Contexto organizacional vinculado a Empresas (res.partner)
        - Caracterización dinámica con vigencias
        - Carga masiva SIMAT con conciliación, mapeo de columnas y trazabilidad completa
        - Resultados vinculados a Encuestas (survey.user_input)
        - Ficha 360° del participante
    """,
    'category': 'Luker',
    'author': 'Fundación Luker',
    'website': 'https://www.fundacionluker.org.co',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'web',
        'contacts',
        'survey',
        'l10n_latam_base',
    ],
    'data': [
        # Security
        'security/luker_groups.xml',
        'security/ir.model.access.csv',

        # Data inicial
        'data/participant_type_data.xml',
        'data/attribute_definition_data.xml',

        # Views
        'views/participant_type_views.xml',
        'views/organization_views.xml',
        'views/participant_views.xml',
        'views/attribute_definition_views.xml',
        'views/application_result_views.xml',
        'views/dashboard_views.xml',

        # Acción de carga masiva (antes que el wizard y el menú)
        'views/participant_import_action.xml',

        # Wizard
        'views/participant_import_wizard_views.xml',

        # Menus (siempre al final)
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'luker_master/static/src/scss/luker_master.scss',
        ],
    },
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 10,
}
