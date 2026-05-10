# -*- coding: utf-8 -*-
{
    'name': 'Operation Engine — SISPAR',
    'version': '18.0.1.0.0',
    'summary': 'Motor operativo SISPAR: campañas, ejecutores, asignaciones y tareas.',
    'category': 'Gestor Operativo',
    'author': 'AiLumex / Fundación Luker',
    'license': 'LGPL-3',
    'depends': [
        'gestor_operativo',
        'ailmx_extend_survey',
        'survey',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/operation_task_sequence.xml',
        'data/rol_data.xml',

        'views/rol_views.xml',
        'views/executor_views.xml',
        'views/hr_employee_inherit.xml',
        'views/campaign_views.xml',
        'views/assignment_views.xml',
        'views/task_views.xml',
        'views/survey_executor_inherit.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
