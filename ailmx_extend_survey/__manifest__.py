# Archivo que Odoo va a leer para saber su nombre y características
{
    'name': 'Ailmx Extend Survey',
    'version': '18.0.1.0.0',
    'summary': 'Extend Survey Module',
    'author': 'AiLumex',
    'category': 'Customizations',
    'depends': ['survey'], # Lista de modulos que deben estar instalados antes de este
    'data': [ # Aquí se van a cargar los tipos de pregunta al instalar el 
        # PERMISOS
        'security/ir.model.access.csv',

        # VISTAS
        'views/survey_question_type_views.xml',
        'views/data_element_views.xml',
        'views/survey_question_extension_views.xml',
        'views/survey_response_line_views.xml',
        'views/participant_views.xml',
        'views/survey_form_inherit.xml',
        'views/menu_extensions.xml',

        # DATOS INICIALES
        'data/survey_question_type_data.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False, # No se instala automáticamente cuando se instala Survey
    'post_init_hook': 'post_init_hook', # Se ejecuta después de instalar o actualizar el módulo
}