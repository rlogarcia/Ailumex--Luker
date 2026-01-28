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
    # Post-init hook removed to avoid programmatic creation of records (campuses, agendas, etc.)
    "data": [
        # Seguridad
        "security/security.xml",
        "security/teacher_security.xml",  # Seguridad para gestión de docentes
        # "security/crm_security.xml",  # Seguridad CRM - COMENTADO: archivo no existe
        "security/academic_history_security.xml",  # Seguridad para historial académico
        "security/ir.model.access.csv",
        # Secuencias
        "data/ir_sequence_data.xml",
        # Datos CRM - Pipelines y Automatizaciones
        # "data/crm_pipelines_data.xml",  # COMENTADO: archivo no existe
        # "data/crm_automations_data.xml",  # COMENTADO: archivo no existe
        # ============================================================
        # VISTAS Y ACCIONES (cargar en orden de dependencias)
        # ============================================================
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
        # "views/hr_employee_sales_views.xml",  # COMENTADO: archivo no existe
        # Vistas - Institucional (Coaches)
        "views/coach_views.xml",
        # Wizards base
        "views/wizards_views.xml",
        "views/freeze_request_wizard_views.xml",
        "wizards/generate_historical_progress_wizard_views.xml",
        # Vistas - Estados de Perfil y Congelamiento
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
        # Vistas - CRM
        # "views/crm_lead_views.xml",  # COMENTADO: archivo no existe
        # Vistas - Configuración
        "views/class_booking_settings_views.xml",
        "views/student_password_manager_views.xml",  # Gestión de contraseñas de estudiantes
        "views/teacher_password_manager_views.xml",  # Gestión de contraseñas de docentes
        # "views/portal_password_reset_template.xml",  # Modal de recuperación - DESACTIVADO: conflicto XML validador Odoo 18
        # MENÚS (DEBEN CARGARSE AL FINAL - dependen de todas las acciones)
        "views/menus.xml",
        # Datos operacionales
        "data/student_profile_states_base.xml",
        # "data/student_lifecycle_transitions.xml",  # Evitar duplicados en upgrade
        "data/student_moodle_user_data.xml",
        "data/coach_portal_email_template.xml",  # Plantilla email acceso portal coach
        "data/email_template_password_reset_simple.xml",  # Plantilla email OTP recuperación de contraseña
        # Estructura curricular
        # NOTE: Removed data files that create programs, plans, phases, levels, subjects, campuses and classrooms
        # to ensure the module does not load any hardcoded (quemado) academic structure on install.
        "data/automation_placement_test.xml",
        "data/automation_student_password_sync.xml",  # Sincronización automática gestor de contraseñas
        # "data/email_template_password_reset.xml",  # Template de email para recuperación de contraseña - TEMPORAL
        # Vistas Placement Test - DESACTIVADO TEMPORALMENTE
        # "views/placement_test_views.xml",
        # Menú Placement Test - DESACTIVADO TEMPORALMENTE
        # "views/placement_test_menu.xml",
        # Procesos automáticos (Cron Jobs)
        "data/cron_session_management.xml",  # Cierre automático de sesiones y limpieza de agenda
        "data/cron_agenda_state.xml",  # Actualización automática de estado de agendas a ejecutadas
        # "data/cron_password_reset_cleanup.xml",  # Limpieza de OTPs expirados - TEMPORAL
        # Acciones de servidor
        "data/server_actions_historical_progress.xml",  # Generar historial retroactivo
        "data/server_actions_password_manager.xml",  # Inicialización y sincronización gestor de contraseñas
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
