# Archivo que Odoo va a leer para saber su nombre y características
{
    'name': 'Ailmx Extend Survey',
    'license': 'LGPL-3',
    'version': '18.0.1.0.0',
    'summary': 'Extend Survey Module',
    'author': 'AiLumex',
    'category': 'Customizations',
    'depends': ['survey', 'web'], # Lista de modulos que deben estar instalados antes de este
    'data': [ # Aquí se van a cargar los tipos de pregunta al instalar el 
    
        # PERMISOS
        'security/ir.model.access.csv',

        # VISTAS
        'views/survey_question_type_views.xml',
        'views/data_element_views.xml',
        'views/survey_question_extension_views.xml',
        'views/survey_question_reading_grid_wizard_views.xml',
        'views/survey_question_reading_grid_views.xml',
        'views/survey_response_line_views.xml',
        'views/participant_views.xml',
        'views/survey_form_inherit.xml',
        'views/survey_application_views.xml',
        'views/menu_extensions.xml',
        'views/survey_question_timer_templates.xml',
        'views/survey_question_image_templates.xml',
        'views/survey_question_reading_grid_templates.xml',
        'views/menu_cleanup.xml',

        # DATOS INICIALES
        'data/survey_question_type_data.xml',
        'data/survey_sequence_data.xml',
        'data/participant_sequence_data.xml',
    ],
    'assets': {
        # Bundle para la parte administrativa (Backend)
        'web.assets_backend': [
            'ailmx_extend_survey/static/src/css/survey_style.css',
            'ailmx_extend_survey/static/src/css/participant_style.css',

            # Widget wizard GRID lectura
            'ailmx_extend_survey/static/src/css/reading_grid_wizard.css',
            'ailmx_extend_survey/static/src/xml/reading_grid_wizard_widget.xml',
            'ailmx_extend_survey/static/src/js/reading_grid_wizard_widget.js',
        ],

        # Bundle para la parte pública (Frontend)
        'web.assets_frontend': [
            'ailmx_extend_survey/static/src/css/survey_timer.css',
            'ailmx_extend_survey/static/src/css/survey_reading_grid.css',
            'ailmx_extend_survey/static/src/js/survey_timer.js',
            'ailmx_extend_survey/static/src/js/survey_reading_grid.js',
        ],
        
        # Las encuestas públicas usan este bundle minimal
        'web.assets_frontend_minimal': [
            'ailmx_extend_survey/static/src/css/survey_timer.css',
            'ailmx_extend_survey/static/src/css/survey_reading_grid.css',
            'ailmx_extend_survey/static/src/js/survey_timer.js',
            'ailmx_extend_survey/static/src/js/survey_reading_grid.js',
        ],

        # Bundle de encuestas — Odoo 18 usa este para el frontend de surveys
        'survey.survey_assets': [
            'ailmx_extend_survey/static/src/css/survey_timer.css',
            'ailmx_extend_survey/static/src/css/survey_reading_grid.css',
            'ailmx_extend_survey/static/src/js/survey_timer.js',
            'ailmx_extend_survey/static/src/js/survey_reading_grid.js',
        ],

    },
    'installable': True,
    'application': False,
    'auto_install': False, # No se instala automáticamente cuando se instala Survey
    'post_init_hook': 'post_init_hook', # Se ejecuta después de instalar o actualizar el módulo
}