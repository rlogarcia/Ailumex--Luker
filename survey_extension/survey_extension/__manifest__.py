# -*- coding: utf-8 -*-
{
    # ============================================================
    # METADATA
    # ============================================================
    "name": "Survey Extension",
    "summary": "Extiende Encuestas con público objetivo, ranking, dashboards y segmentación por región y tipo.",
    "version": "1.5.0",
    "category": "Surveys",
    "author": "Your Company",
    "website": "https://www.example.com",
    "license": "LGPL-3",

    # ============================================================
    # DEPENDENCIAS
    # ============================================================
    # Nota: 'survey' ya trae web/views necesarias. No añadimos más.
    "depends": [
        "base",
        "survey",
    ],

    # ============================================================
    # DATA (ORDEN IMPORTANTE)
    # 1) Seguridad primero
    # 2) Data (secuencias, crons, catálogos…)
    # 3) Vistas/acciones (incluye la ACCIÓN de Dispositivos)
    # 4) Menús (último, para que ya existan acciones y vistas)
    # ============================================================
    "data": [
        # --- Seguridad ---
        "security/ir.model.access.csv",

        # --- Data inicial / técnica ---
        "data/audience_categories.xml",
        "data/question_categories.xml",
        "data/survey_sequence.xml",
        "data/survey_trash_cron.xml",
        "data/survey_regions.xml",

        # --- Vistas y acciones (UI) ---
        # IMPORTANTE: Los wizards deben cargarse ANTES de las vistas que los referencian
        "views/survey_edit_question_title_wizard_views.xml",
        "views/survey_version_wizard_views.xml",
        "views/survey_code_selection_wizard_views.xml",
        "views/survey_assign_device_wizard_views.xml",
        
        # Dispositivos: define vistas + acción (action_survey_device)
        # DEBE ir DESPUÉS del wizard porque lo referencia
        "views/survey_device_views.xml",

        # Herencias / vistas existentes del módulo
        "views/survey_user_input_inherit_views.xml",
        "views/survey_user_input_segmentation_views.xml",
        "views/survey_survey_inherit_views.xml",
        "views/survey_ranking_dashboard_views.xml",
        "views/survey_region_views.xml",
        "views/report_survey_summary.xml",
        "views/survey_key_counter_views.xml",
        "views/survey_templates.xml",
        "views/survey_scoring_templates.xml",
        "views/survey_calificacion_average_views.xml",
        "views/survey_question_inherit_views.xml",
        
        # --- Vistas WPM (Palabras Por Minuto) ---
        "views/survey_wpm_question_views.xml",
        "views/survey_wpm_templates.xml",
        "views/survey_user_input_line_views.xml",

        # --- Menús (DEBE cargarse ANTES de las vistas que lo referencian) ---
        "views/survey_extension_menu.xml",
        
        # --- Vistas que dependen de los menús ---
        "views/survey_trash_views.xml",
    ],

    # ============================================================
    # ASSETS (FRONTEND/BACKEND)
    # Mantengo exactamente tus rutas y agrego comentarios.
    # OJO: verifica que los nombres de archivo coincidan 1:1 con /static/src/js/
    # ============================================================
    "assets": {
        # Recursos que carga el frontend público de encuestas (widgets JS/SCSS)
        "survey.survey_assets": [
            "survey_extension/static/src/js/survey_conditional_questions.js",
            "survey_extension/static/src/js/survey_answer_attachments.js",
            "survey_extension/static/src/js/survey_wpm_questions.js",
            # Sistema de cronómetro
            "survey_extension/static/src/js/survey_timer.js",
            "survey_extension/static/src/css/survey_timer.css",
            "survey_extension/static/src/scss/survey_extension.scss",
        ],
        # Backend (vistas Odoo / dashboards)
        "web.assets_backend": [
            "survey_extension/static/src/js/survey_ranking_graphs.js",
            "survey_extension/static/src/scss/survey_ranking_dashboard.scss",
        ],
        # Dejamos definidas aunque vacías (como ya las tenías)
        "web.assets_frontend": [],
        "web.assets_tests": [],
    },

    # ============================================================
    # CONFIG
    # ============================================================
    "application": False,
    "installable": True,

    # ============================================================
    # HOOKS (ya definidos en tu hooks.py)
    # ============================================================
    "pre_init_hook": "migrate_version_year_to_char",
    "post_init_hook": "post_init_hook",
}
