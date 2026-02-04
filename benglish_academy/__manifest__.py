# -*- coding: utf-8 -*-
{
    "name": "Benglish - Gestión Académica",
    "version": "18.0.1.6.0",
    "category": "Education",
    "summary": "Sistema de gestión académica para academia de inglés",
    "description": """
        Módulo de Gestión Académica para Benglish
        =============================================
        
        Funcionalidades principales:
        - Estructura académica: Programas, Planes, Fases, Niveles, Asignaturas
        - Gestión de prerrequisitos entre asignaturas
        - Gestión de sedes y multisedes
        - Programación de clases y horarios
        - Matrícula interna de estudiantes
        - Reemplazo de docentes
        - Reportes y agenda semanal
        - Publicación de agenda académica
        - Estados de perfil de estudiante
        - Congelamiento de matrículas
    """,
    "author": "Ailumex",
    "website": "https://www.benglish.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "base_automation",
        "contacts",
        "mail",
        "portal",
        "hr",
        "crm",
        "l10n_latam_base",  # Para tipos de documento (l10n_latam.identification.type)
    ],
    "data": [
        # Modelos - Registro explícito (DEBE ir ANTES de security)
        "data/model_elective_pool.xml",
        
        # Seguridad
        "security/security.xml",
        "security/teacher_security.xml",
        "security/academic_history_security.xml",
        "security/ir.model.access.csv",

        # VISTAS Y ACCIONES (solo vistas, sin carga de datos operativos)
        # Vistas - Diseño Curricular (acciones base)
        "views/program_views.xml",
        "views/plan_views.xml",
        "views/phase_views.xml",
        "views/level_views.xml",
        "views/subject_views.xml",
        # Vistas - Institucional
        "views/campus_views.xml",
        # Vistas - Empleados/Docentes
        "views/hr_employee_teacher_views.xml",
        # Vistas - Institucional (Coaches)
        "views/coach_views.xml",
        # Wizards base
        "views/wizards_views.xml",
        "views/freeze_request_wizard_views.xml",
        "wizards/generate_historical_progress_wizard_views.xml",
        # Server actions
        "data/server_actions_historical_progress.xml",
        "data/server_actions_password_manager.xml",
        "data/automation_student_password_sync.xml",
        "data/automation_placement_test.xml",
        "data/email_template_password_reset_simple.xml",
        # Cron jobs
        "data/cron_agenda_state.xml",
        "data/cron_password_reset_cleanup.xml",
        "data/cron_session_management.xml",
        # Vistas - Estados de Perfil y Congelamiento
        "data/student_profile_states_base.xml",
        "data/student_lifecycle_transitions.xml",
        "views/student_profile_state_views.xml",
        "views/freeze_reason_views.xml",
        "views/plan_freeze_config_views.xml",
        "views/student_freeze_period_views.xml",
        # Vistas - Transiciones de Estado
        "views/student_state_transition_views.xml",
        "views/student_lifecycle_transition_views.xml",
        "views/freeze_approval_preview_wizard_views.xml",
        "views/student_change_state_wizard_views.xml",
        "views/student_lifecycle_state_wizard_views.xml",
        # Vistas - Matrícula (definen action_enrollment, action_enrollment_kanban, etc.)
        "views/enrollment_views.xml",
        "views/enrollment_progress_views.xml",
        "views/enrollment_wizard_views.xml",
        # Vistas - Estudiantes (dependen de enrollment_views)
        "views/student_views.xml",
        "views/student_history_views.xml",
        "views/student_moodle_views.xml",
        "views/student_import_views.xml",
        "views/student_import_wizard_views.xml",
        "views/student_enrollment_import_wizard_views.xml",
        "views/portal_user_creation_wizard_views.xml",
        "views/student_actions.xml",
        "views/agenda_template_views.xml",
        "views/publish_session_wizard_views.xml",
        # Vistas - Programación Académica
        "views/course_views.xml",
        "views/group_views.xml",
        "views/teacher_replacement_log_views.xml",
        "views/class_session_views.xml",
        # Vistas - Agenda Académica (dependen de student_views)
        "views/academic_agenda_views.xml",
        "views/academic_session_views.xml",
        "views/session_enrollment_views.xml",
        "views/agenda_log_views.xml",
        "views/session_transfer_log_views.xml",
        "views/academic_history_views.xml",
        # Vistas - FASE 2: Pools de Electivas
        "views/elective_pool_views.xml",
        # Vistas - Configuración
        "views/class_booking_settings_views.xml",
        "views/student_password_manager_views.xml",
        "views/teacher_password_manager_views.xml",
        # MENÚS (DEBEN CARGARSE AL FINAL - dependen de todas las acciones)
        "views/menus.xml",
        # Secuencias simples para códigos (PRG-/P-/F-/N-/A-/SE-/AU-)
        "data/ir_sequence_data.xml",
        # Secuencia para Pool de Electivas (FASE 2)
        "data/ir_sequence_elective_pool.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "benglish_academy/static/src/xml/time_picker_widget.xml",
            "benglish_academy/static/src/js/time_picker_widget.js",
            "benglish_academy/static/src/css/time_picker_widget.css",
        ],
        "web.assets_web": [
            "benglish_academy/static/src/xml/time_picker_widget.xml",
            "benglish_academy/static/src/js/time_picker_widget.js",
            "benglish_academy/static/src/css/time_picker_widget.css",
        ],
    },
    "demo": [],
    "installable": True,
    "application": True,
    "auto_install": False,
}
