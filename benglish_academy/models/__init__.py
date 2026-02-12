# -*- coding: utf-8 -*-

from . import res_config_settings
from . import session_sync_mixin
from . import program
from . import plan
from . import commercial_plan  # NUEVO: Plan Comercial (Feb 2026)
from . import commercial_plan_line  # NUEVO: Líneas del Plan Comercial
from . import student_commercial_progress  # NUEVO: Progreso dinámico del estudiante
from . import phase
from . import level
from . import subject
from . import campus
from . import hr_employee  # Necesario para meeting_link en subcampus
from . import crm_lead  # Extensión de CRM para validaciones comerciales
from . import subcampus
from . import course
from . import group
from . import coach
from . import class_type
from . import class_session
from . import teacher_replacement_log
from . import student
from . import student_password_manager
from . import teacher_password_manager
from . import benglish_password_reset
from . import enrollment
from . import enrollment_progress
from . import student_profile_state
from . import student_state_history
from . import student_lifecycle_transition
from . import student_lifecycle_history
from . import student_edit_history
from . import freeze_reason
from . import plan_freeze_config
from . import student_freeze_period
from . import student_state_transition
from . import student_moodle
from . import student_import_batch
from . import student_import_line
from . import student_import_log
from . import academic_agenda
from . import academic_session
from . import elective_pool  # FASE 2: Pools de electivas por fase
from . import plan_requirement  # Requisitos académicos por nivel y plan
from . import plan_requirement_option  # Opciones para requisitos CHOICE
from . import student_requirement_status  # Estado de requisitos del estudiante
from . import student_compliance  # Cumplimiento académico del estudiante
from . import class_execution  # Clase ejecutada y asistencia
from . import academic_history
from . import academic_period  # NUEVO: Periodo Académico (Feb 2026)
from . import placement_test
from . import placement_test_prospect
from . import subject_session_tracking
from . import agenda_log
from . import session_transfer_log
from . import session_enrollment
from . import res_partner
from . import academic_settings
