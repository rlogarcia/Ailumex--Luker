# -*- coding: utf-8 -*-
{
    'name': 'Luker API — PWA Offline',
    'version': '18.0.1.0.0',
    'summary': 'API REST para la App PWA offline-first de Fundación Luker.',
    'description': """
        Luker API — Capa HTTP para PWA
        ================================
        - Autenticación por dispositivo (token UUID)
        - Descarga de encuestas para uso offline
        - Descarga del perfil del participante
        - Sincronización de respuestas capturadas offline
        - Cola de reintento para sincronizaciones fallidas
    """,
    'category': 'Gestor Operativo',
    'author': 'AiLumex / Fundación Luker',
    'license': 'LGPL-3',
    'depends': [
        'gestor_operativo',
        'ailmx_extend_survey',
        'survey',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
