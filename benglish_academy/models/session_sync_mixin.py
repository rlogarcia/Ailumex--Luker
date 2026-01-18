# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class SessionSyncMixin(models.AbstractModel):
    """
    Mixin para sincronizar sesiones académicas con el portal del estudiante.
    
    Este mixin proporciona funcionalidad para:
    - Limpiar agenda del portal cuando una sesión se marca como 'dictada' o 'cancelada'
    - Mover registros al historial académico cuando corresponda
    - Registrar ausencias en el historial
    - Manejar estados de asistencia pendiente
    """
    
    _name = "benglish.session.sync.mixin"
    _description = "Mixin de Sincronización de Sesiones"
    
    def _sync_session_to_portal_on_state_change(self, old_state, new_state):
        """
        Sincroniza el estado de la sesión con la agenda del portal del estudiante.
        
        Cuando una sesión cambia a 'done' o 'cancelled', limpia las líneas de agenda
        correspondientes del portal y mueve los registros al historial si corresponde.
        
        Args:
            old_state (str): Estado anterior de la sesión
            new_state (str): Nuevo estado de la sesión
        """
        self.ensure_one()
        
        # Solo procesar si el estado cambió a 'done' o 'cancelled'
        if new_state not in ['done', 'cancelled']:
            return
        
        _logger.info(
            f"[SYNC] Session {self.id} state changed from '{old_state}' to '{new_state}'. "
            f"Starting portal agenda cleanup."
        )
        
        # Buscar todas las líneas de agenda del portal que referencian esta sesión
        AgendaLine = self.env['portal.student.weekly.plan.line'].sudo()
        agenda_lines = AgendaLine.search([('session_id', '=', self.id)])
        
        if not agenda_lines:
            _logger.info(
                f"[SYNC] No agenda lines found for Session {self.id}. Nothing to sync."
            )
            return
        
        _logger.info(
            f"[SYNC] Found {len(agenda_lines)} agenda line(s) for Session {self.id}. "
            f"Processing each line..."
        )
        
        # Procesar cada línea de agenda
        for line in agenda_lines:
            # El estudiante está en plan_id.student_id
            student = line.plan_id.student_id if line.plan_id else False
            if not student:
                _logger.warning(
                    f"[SYNC] Agenda line {line.id} has no student (plan={line.plan_id}). Skipping."
                )
                continue
            
            # Buscar la inscripción del estudiante en esta sesión
            enrollment = self._get_enrollment_for_student(student)
            
            if enrollment:
                # Procesar según el estado de asistencia
                if new_state == 'done':
                    if enrollment.state == 'attended':
                        self._move_to_academic_history(student, enrollment, line)
                    elif enrollment.state == 'absent':
                        self._register_absence_in_history(student, enrollment, line)
                    else:  # pending o confirmed
                        self._mark_as_pending_confirmation(student, enrollment, line)
                
                # Eliminar la línea de la agenda del portal
                _logger.info(
                    f"[SYNC] Removing agenda line {line.id} for Student={student.name}, "
                    f"Session={self.id}"
                )
                line.unlink()
            else:
                _logger.warning(
                    f"[SYNC] No enrollment found for Student={student.id} in Session={self.id}. "
                    f"Removing agenda line anyway."
                )
                line.unlink()
    
    def _get_enrollment_for_student(self, student):
        """
        Busca la inscripción del estudiante en esta sesión.
        
        Args:
            student (benglish.student): Estudiante
            
        Returns:
            benglish.session.enrollment: Inscripción encontrada o False
        """
        self.ensure_one()
        Enrollment = self.env['benglish.session.enrollment'].sudo()
        return Enrollment.search([
            ('session_id', '=', self.id),
            ('student_id', '=', student.id)
        ], limit=1)
    
    def _move_to_academic_history(self, student, enrollment, agenda_line):
        """
        Mueve la sesión completada al historial académico del estudiante.
        
        Esta función se llama cuando:
        - La sesión está en estado 'done'
        - El estudiante tiene asistencia marcada como 'attended'
        
        Args:
            student (benglish.student): Estudiante
            enrollment (benglish.session.enrollment): Inscripción del estudiante
            agenda_line (portal.student.weekly.plan.line): Línea de agenda a procesar
        """
        self.ensure_one()
        
        _logger.info(
            f"[SYNC] Moving to history: Student={student.name}, Session={self.id}, "
            f"Attendance=attended"
        )
        
        # El historial debería haber sido creado por el método action_mark_done
        # o por _sync_to_academic_history en session_enrollment
        # Aquí solo verificamos que exista
        History = self.env['benglish.academic.history'].sudo()
        existing_history = History.search([
            ('student_id', '=', student.id),
            ('session_id', '=', self.id),
            ('enrollment_id', '=', enrollment.id)
        ], limit=1)
        
        if existing_history:
            _logger.info(
                f"[SYNC] History record already exists for Student={student.id}, "
                f"Session={self.id}. No need to create."
            )
        else:
            _logger.warning(
                f"[SYNC] No history record found for attended session. "
                f"This should have been created by action_mark_done or _sync_to_academic_history."
            )
        
        # Notificar al estudiante (opcional)
        student.message_post(
            body=_(
                "Clase completada: %(subject)s - %(date)s<br/>"
                "Estado: Asistió"
            ) % {
                'subject': self.subject_id.name if hasattr(self, 'subject_id') and self.subject_id else 'N/A',
                'date': self.date if hasattr(self, 'date') else 'N/A',
            },
            subject=_("Clase Completada")
        )
    
    def _register_absence_in_history(self, student, enrollment, agenda_line):
        """
        Registra la ausencia del estudiante en el historial académico.
        
        Args:
            student (benglish.student): Estudiante
            enrollment (benglish.session.enrollment): Inscripción del estudiante
            agenda_line (portal.student.weekly.plan.line): Línea de agenda a procesar
        """
        self.ensure_one()
        
        _logger.info(
            f"[SYNC] Registering absence: Student={student.name}, Session={self.id}"
        )
        
        # El historial de ausencia debería haber sido creado por _sync_to_academic_history
        History = self.env['benglish.academic.history'].sudo()
        existing_history = History.search([
            ('student_id', '=', student.id),
            ('session_id', '=', self.id),
            ('enrollment_id', '=', enrollment.id)
        ], limit=1)
        
        if existing_history:
            _logger.info(
                f"[SYNC] Absence history record already exists for Student={student.id}, "
                f"Session={self.id}."
            )
        else:
            _logger.warning(
                f"[SYNC] No history record found for absent session. "
                f"This should have been created by _sync_to_academic_history."
            )
    
    def _mark_as_pending_confirmation(self, student, enrollment, agenda_line):
        """
        Marca la sesión como pendiente de confirmación de asistencia.
        
        Args:
            student (benglish.student): Estudiante
            enrollment (benglish.session.enrollment): Inscripción del estudiante
            agenda_line (portal.student.weekly.plan.line): Línea de agenda a procesar
        """
        self.ensure_one()
        
        _logger.info(
            f"[SYNC] Session completed but attendance not confirmed: "
            f"Student={student.name}, Session={self.id}, "
            f"Enrollment State={enrollment.state}"
        )
        
        # Notificar que se necesita confirmar asistencia
        self.message_post(
            body=_(
                "Sesión completada pero asistencia no confirmada para estudiante: %(student)s<br/>"
                "Estado de inscripción: %(state)s<br/>"
                "Por favor confirmar asistencia."
            ) % {
                'student': student.name,
                'state': enrollment.state,
            },
            subject=_("Asistencia Pendiente")
        )
    
    @api.model
    def _cron_cleanup_orphan_agenda_lines(self):
        """
        Tarea programada (cron) para limpiar líneas huérfanas de agenda.
        
        Busca líneas de agenda del portal cuyas sesiones están en estado 'done' o 'cancelled'
        y las procesa/elimina. Esta es una red de seguridad en caso de que la sincronización
        en tiempo real falle.
        
        Se recomienda ejecutar diariamente (ej: 2:00 AM).
        """
        _logger.info("[CRON] Starting orphan agenda lines cleanup...")
        
        AgendaLine = self.env['portal.student.weekly.plan.line'].sudo()
        
        # Buscar líneas de agenda cuyas sesiones están completadas o canceladas
        # y que tienen fecha anterior a hace 24 horas (para evitar procesamiento prematuro)
        cutoff_date = fields.Datetime.now() - timedelta(hours=24)
        
        orphan_lines = AgendaLine.search([
            ('session_id', '!=', False),
            ('session_id.state', 'in', ['done', 'cancelled']),
            ('session_id.end_datetime', '<', cutoff_date)
        ])
        
        if not orphan_lines:
            _logger.info("[CRON] No orphan agenda lines found. Cleanup complete.")
            return
        
        _logger.info(
            f"[CRON] Found {len(orphan_lines)} orphan agenda line(s). Processing..."
        )
        
        processed = 0
        errors = 0
        
        for line in orphan_lines:
            try:
                session = line.session_id
                # El estudiante está en plan_id.student_id
                student = line.plan_id.student_id if line.plan_id else False
                
                if not session or not student:
                    _logger.warning(
                        f"[CRON] Agenda line {line.id} missing session or student. "
                        f"Deleting anyway."
                    )
                    line.unlink()
                    processed += 1
                    continue
                
                # Buscar inscripción
                enrollment = session._get_enrollment_for_student(student)
                
                if enrollment and session.state == 'done':
                    # Asegurarse de que el historial está creado
                    if enrollment.state in ['attended', 'absent']:
                        enrollment._sync_to_academic_history()
                
                # Eliminar línea de agenda
                line.unlink()
                processed += 1
                
            except Exception as e:
                _logger.error(
                    f"[CRON] Error processing agenda line {line.id}: {str(e)}",
                    exc_info=True
                )
                errors += 1
        
        _logger.info(
            f"[CRON] Cleanup complete. Processed: {processed}, Errors: {errors}"
        )
