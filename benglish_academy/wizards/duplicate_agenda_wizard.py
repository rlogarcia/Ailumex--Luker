# -*- coding: utf-8 -*-
"""
Wizard para Duplicación Inteligente de Agendas Académicas.

Este wizard permite duplicar una agenda académica completa con todas sus sesiones,
recalculando las fechas según los días de la semana y validando disponibilidad
de docentes y aulas en el nuevo periodo.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class DuplicateAgendaWizard(models.TransientModel):
    """
    Wizard para duplicar una agenda académica con recálculo inteligente de fechas.
    
    Características:
    - No usa copy() directo (evita conflictos de fechas)
    - Recalcula fechas por día de la semana
    - Valida disponibilidad de docentes y aulas
    - Permite omitir sesiones conflictivas o abortar
    - Crea agenda completamente nueva e independiente
    """

    _name = 'benglish.duplicate.agenda.wizard'
    _description = 'Wizard de Duplicación Inteligente de Agenda'

    # ==========================================
    # INFORMACIÓN DE AGENDA ORIGEN (READONLY)
    # ==========================================

    source_agenda_id = fields.Many2one(
        comodel_name='benglish.academic.agenda',
        string='Horario Origen',
        required=True,
        readonly=True,
        ondelete='cascade',
        help='Horario que se va a duplicar'
    )

    source_code = fields.Char(
        string='Código Origen',
        related='source_agenda_id.code',
        readonly=True
    )

    source_campus = fields.Char(
        string='Sede Origen',
        related='source_agenda_id.campus_id.name',
        readonly=True
    )

    source_date_start = fields.Date(
        string='Fecha Inicio Origen',
        related='source_agenda_id.date_start',
        readonly=True
    )

    source_date_end = fields.Date(
        string='Fecha Fin Origen',
        related='source_agenda_id.date_end',
        readonly=True
    )

    source_session_count = fields.Integer(
        string='Total Sesiones Origen',
        related='source_agenda_id.session_count',
        readonly=True
    )

    source_summary = fields.Text(
        string='Resumen de Agenda Origen',
        compute='_compute_source_summary',
        readonly=True,
        help='Resumen de días de la semana y distribución de sesiones'
    )

    # ==========================================
    # CONFIGURACIÓN DEL NUEVO PERIODO
    # ==========================================

    new_date_start = fields.Date(
        string='Nueva Fecha de Inicio',
        required=True,
        default=fields.Date.context_today,
        help='Fecha de inicio del nuevo periodo. Las sesiones se replicarán desde esta fecha.'
    )

    new_date_end = fields.Date(
        string='Nueva Fecha de Fin',
        required=True,
        help='Fecha de fin del nuevo periodo. Solo se crearán sesiones dentro de este rango.'
    )

    # Periodo académico (opcional, si existe en tu modelo)
    # new_academic_period_id = fields.Many2one(
    #     comodel_name='benglish.academic.period',
    #     string='Nuevo Periodo Académico',
    #     help='Periodo académico al que pertenecerá la nueva agenda (opcional)'
    # )

    # ==========================================
    # OPCIONES DE DUPLICACIÓN
    # ==========================================

    skip_conflicts = fields.Boolean(
        string='Omitir Sesiones con Conflictos',
        default=True,
        help=(
            'Si está marcado, las sesiones con conflictos de docente/aula se omitirán. '
            'Si no está marcado, el proceso se detendrá al encontrar el primer conflicto.'
        )
    )

    copy_published_state = fields.Boolean(
        string='Copiar Estado de Publicación',
        default=False,
        help=(
            'Si está marcado, las sesiones duplicadas mantendrán el estado de publicación '
            'de las sesiones originales.'
        )
    )

    validate_campus_schedule = fields.Boolean(
        string='Validar Horarios de Sede',
        default=True,
        help='Valida que los horarios estén dentro del rango permitido por la sede'
    )

    # ==========================================
    # CAMPOS COMPUTADOS PARA PREVISUALIZACIÓN
    # ==========================================

    estimated_sessions = fields.Integer(
        string='Sesiones Estimadas',
        compute='_compute_estimated_sessions',
        help='Número estimado de sesiones que se crearán (sin considerar conflictos)'
    )

    new_duration_days = fields.Integer(
        string='Duración Nueva Agenda (días)',
        compute='_compute_new_duration',
        help='Número de días del nuevo periodo'
    )

    weekdays_distribution = fields.Text(
        string='Distribución por Día',
        compute='_compute_weekdays_distribution',
        help='Muestra cuántas sesiones por día de la semana se crearán'
    )

    # ==========================================
    # MÉTODOS COMPUTADOS
    # ==========================================

    @api.depends('source_agenda_id', 'source_agenda_id.session_ids')
    def _compute_source_summary(self):
        """Genera resumen legible de la agenda origen."""
        for wizard in self:
            if not wizard.source_agenda_id:
                wizard.source_summary = ''
                continue

            agenda = wizard.source_agenda_id
            sessions = agenda.session_ids

            if not sessions:
                wizard.source_summary = '⚠️ La agenda origen no tiene sesiones programadas.'
                continue

            # Contar sesiones por día de la semana
            weekday_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            weekday_counts = {}

            for session in sessions:
                wd = session.weekday
                if wd not in weekday_counts:
                    weekday_counts[wd] = 0
                weekday_counts[wd] += 1

            summary_lines = [
                f"📅 Agenda: {agenda.code} - {agenda.campus_id.name}",
                f"📆 Periodo: {agenda.date_start} al {agenda.date_end}",
                f"🕐 Horario: {wizard._format_time(agenda.time_start)} - {wizard._format_time(agenda.time_end)}",
                f"📊 Total sesiones: {len(sessions)}",
                "",
                "Distribución por día de la semana:",
            ]

            for wd in sorted(weekday_counts.keys()):
                wd_int = int(wd)
                day_name = weekday_names[wd_int]
                count = weekday_counts[wd]
                summary_lines.append(f"  • {day_name}: {count} sesión(es)")

            wizard.source_summary = '\n'.join(summary_lines)

    @api.depends('new_date_start', 'new_date_end')
    def _compute_new_duration(self):
        """Calcula la duración del nuevo periodo."""
        for wizard in self:
            if wizard.new_date_start and wizard.new_date_end:
                delta = wizard.new_date_end - wizard.new_date_start
                wizard.new_duration_days = delta.days + 1
            else:
                wizard.new_duration_days = 0

    @api.depends('source_agenda_id', 'new_date_start', 'new_date_end')
    def _compute_estimated_sessions(self):
        """Estima cuántas sesiones se crearán (sin considerar conflictos)."""
        for wizard in self:
            if not all([wizard.source_agenda_id, wizard.new_date_start, wizard.new_date_end]):
                wizard.estimated_sessions = 0
                continue

            total = 0
            for session in wizard.source_agenda_id.session_ids:
                dates = wizard._calculate_new_dates_for_session(
                    session,
                    wizard.new_date_start,
                    wizard.new_date_end
                )
                total += len(dates)

            wizard.estimated_sessions = total

    @api.depends('source_agenda_id', 'new_date_start', 'new_date_end')
    def _compute_weekdays_distribution(self):
        """Muestra distribución estimada por día de la semana."""
        for wizard in self:
            if not all([wizard.source_agenda_id, wizard.new_date_start, wizard.new_date_end]):
                wizard.weekdays_distribution = ''
                continue

            weekday_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            weekday_counts = {}

            for session in wizard.source_agenda_id.session_ids:
                dates = wizard._calculate_new_dates_for_session(
                    session,
                    wizard.new_date_start,
                    wizard.new_date_end
                )
                wd = session.weekday
                if wd not in weekday_counts:
                    weekday_counts[wd] = 0
                weekday_counts[wd] += len(dates)

            if not weekday_counts:
                wizard.weekdays_distribution = 'No se crearán sesiones.'
                continue

            lines = ["Sesiones estimadas por día:"]
            for wd in sorted(weekday_counts.keys()):
                wd_int = int(wd)
                day_name = weekday_names[wd_int]
                count = weekday_counts[wd]
                lines.append(f"  • {day_name}: {count} sesión(es)")

            wizard.weekdays_distribution = '\n'.join(lines)

    # ==========================================
    # VALIDACIONES
    # ==========================================

    @api.constrains('new_date_start', 'new_date_end')
    def _check_new_dates(self):
        """Valida que las fechas del nuevo periodo sean coherentes."""
        for wizard in self:
            if wizard.new_date_end < wizard.new_date_start:
                raise ValidationError(
                    _('La fecha de fin debe ser posterior o igual a la fecha de inicio.')
                )

            # Validar que no exceda un rango razonable (ej: 1 año)
            delta = wizard.new_date_end - wizard.new_date_start
            if delta.days > 365:
                raise ValidationError(
                    _(
                        'El nuevo periodo no puede exceder 1 año de duración. '
                        'Duración actual: %s días.'
                    ) % delta.days
                )

    @api.constrains('source_agenda_id')
    def _check_source_has_sessions(self):
        """Valida que la agenda origen tenga sesiones para duplicar."""
        for wizard in self:
            if wizard.source_agenda_id and not wizard.source_agenda_id.session_ids:
                raise ValidationError(
                    _(
                        'La agenda origen "%s" no tiene sesiones programadas. '
                        'No hay nada que duplicar.'
                    ) % wizard.source_agenda_id.display_name
                )

    # ==========================================
    # MÉTODOS AUXILIARES
    # ==========================================

    def _format_time(self, time_float):
        """Convierte tiempo decimal a formato HH:MM."""
        hours = int(time_float)
        minutes = int((time_float - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    def _calculate_new_dates_for_session(self, original_session, new_start, new_end):
        """
        Calcula todas las fechas donde debe replicarse una sesión original.
        
        Args:
            original_session: Sesión original
            new_start: Fecha de inicio del nuevo periodo
            new_end: Fecha de fin del nuevo periodo
            
        Returns:
            list: Lista de fechas (date objects) donde crear la sesión
            
        Ejemplo:
            Si la sesión original era un lunes, retorna todos los lunes
            que existan entre new_start y new_end.
        """
        if not original_session.date:
            return []

        # Obtener día de la semana (0=Lunes, 6=Domingo)
        weekday = original_session.date.weekday()
        dates = []
        current = new_start

        # Ajustar al primer día de la semana correcto
        while current.weekday() != weekday and current <= new_end:
            current += timedelta(days=1)

        # Recopilar todas las fechas de ese día de la semana
        while current <= new_end:
            dates.append(current)
            current += timedelta(days=7)

        return dates

    def _check_teacher_availability(self, teacher_id, date, time_start, time_end, exclude_session_id=None):
        """
        Verifica si un docente está disponible en una fecha/hora específica.
        
        Args:
            teacher_id: ID del docente (hr.employee)
            date: Fecha a verificar
            time_start: Hora de inicio
            time_end: Hora de fin
            exclude_session_id: ID de sesión a excluir (para ediciones)
            
        Returns:
            tuple: (bool disponible, str motivo_conflicto)
        """
        if not teacher_id:
            return (True, None)

        domain = [
            ('teacher_id', '=', teacher_id),
            ('date', '=', date),
            ('state', '!=', 'cancelled'),
            '|',
            '&', ('time_start', '<', time_end), ('time_end', '>', time_start),
            '&', ('time_start', '>=', time_start), ('time_start', '<', time_end),
        ]

        if exclude_session_id:
            domain.append(('id', '!=', exclude_session_id))

        conflicting_sessions = self.env['benglish.academic.session'].search(domain, limit=1)

        if conflicting_sessions:
            session = conflicting_sessions[0]
            reason = _(
                'Docente ocupado en otra sesión: %s (%s - %s)'
            ) % (
                session.subject_id.name or 'Sin asignatura',
                self._format_time(session.time_start),
                self._format_time(session.time_end)
            )
            return (False, reason)

        return (True, None)

    def _check_classroom_availability(self, subcampus_id, date, time_start, time_end, exclude_session_id=None):
        """
        Verifica si un aula está disponible en una fecha/hora específica.
        
        Args:
            subcampus_id: ID del aula (benglish.subcampus)
            date: Fecha a verificar
            time_start: Hora de inicio
            time_end: Hora de fin
            exclude_session_id: ID de sesión a excluir
            
        Returns:
            tuple: (bool disponible, str motivo_conflicto)
        """
        if not subcampus_id:
            return (True, None)

        domain = [
            ('subcampus_id', '=', subcampus_id),
            ('date', '=', date),
            ('state', '!=', 'cancelled'),
            '|',
            '&', ('time_start', '<', time_end), ('time_end', '>', time_start),
            '&', ('time_start', '>=', time_start), ('time_start', '<', time_end),
        ]

        if exclude_session_id:
            domain.append(('id', '!=', exclude_session_id))

        conflicting_sessions = self.env['benglish.academic.session'].search(domain, limit=1)

        if conflicting_sessions:
            session = conflicting_sessions[0]
            reason = _(
                'Aula ocupada por otra sesión: %s (%s - %s)'
            ) % (
                session.subject_id.name or 'Sin asignatura',
                self._format_time(session.time_start),
                self._format_time(session.time_end)
            )
            return (False, reason)

        return (True, None)

    # ==========================================
    # ACCIÓN PRINCIPAL: DUPLICAR AGENDA
    # ==========================================

    def action_duplicate_agenda(self):
        """
        Acción principal que ejecuta la duplicación inteligente de la agenda.
        
        Proceso:
        1. Crea nueva agenda (sin copy())
        2. Para cada sesión original:
           a) Calcula nuevas fechas por día de la semana
           b) Valida disponibilidad de docente y aula
           c) Crea sesión o la omite según configuración
        3. Retorna vista de la nueva agenda con resumen de resultados
        """
        self.ensure_one()

        # Validación inicial
        if not self.source_agenda_id.session_ids:
            raise UserError(
                _('La agenda origen no tiene sesiones para duplicar.')
            )

        _logger.info(
            "Iniciando duplicación de agenda %s (%s sesiones)",
            self.source_agenda_id.code,
            len(self.source_agenda_id.session_ids)
        )

        # ==========================================
        # PASO 1: CREAR NUEVA AGENDA
        # ==========================================

        source = self.source_agenda_id

        new_agenda_vals = {
            'location_city': source.location_city,
            'campus_id': source.campus_id.id,
            'date_start': self.new_date_start,
            'date_end': self.new_date_end,
            'time_start': source.time_start,
            'time_end': source.time_end,
            'description': _(
                'Agenda duplicada desde %s (%s)\n'
                'Periodo original: %s al %s\n'
                'Duplicada el: %s por %s'
            ) % (
                source.code,
                source.display_name,
                source.date_start,
                source.date_end,
                fields.Date.today(),
                self.env.user.name
            ),
            'state': 'draft',
            'active': True,
            # El código se genera automáticamente por secuencia
        }

        # Si existe periodo académico, agregarlo
        # if self.new_academic_period_id:
        #     new_agenda_vals['academic_period_id'] = self.new_academic_period_id.id

        new_agenda = self.env['benglish.academic.agenda'].create(new_agenda_vals)

        _logger.info(
            "Nueva agenda creada: %s (ID: %s)",
            new_agenda.code,
            new_agenda.id
        )

        # ==========================================
        # PASO 2: DUPLICAR SESIONES
        # ==========================================

        created_sessions = self.env['benglish.academic.session']
        skipped_sessions = []
        
        for original_session in source.session_ids:
            # Calcular nuevas fechas para esta sesión
            new_dates = self._calculate_new_dates_for_session(
                original_session,
                self.new_date_start,
                self.new_date_end
            )

            if not new_dates:
                _logger.warning(
                    "No se encontraron fechas válidas para sesión %s (día: %s)",
                    original_session.id,
                    original_session.weekday
                )
                continue

            # Para cada fecha calculada, intentar crear sesión
            for new_date in new_dates:
                # ==========================================
                # VALIDAR DISPONIBILIDAD
                # ==========================================

                teacher_available, teacher_reason = self._check_teacher_availability(
                    original_session.teacher_id.id if original_session.teacher_id else None,
                    new_date,
                    original_session.time_start,
                    original_session.time_end
                )

                classroom_available, classroom_reason = self._check_classroom_availability(
                    original_session.subcampus_id.id if original_session.subcampus_id else None,
                    new_date,
                    original_session.time_start,
                    original_session.time_end
                )

                # Si hay conflictos, decidir qué hacer
                if not teacher_available or not classroom_available:
                    conflict_info = {
                        'original_session_id': original_session.id,
                        'original_date': original_session.date,
                        'new_date': new_date,
                        'time_start': original_session.time_start,
                        'time_end': original_session.time_end,
                        'subject': original_session.subject_id.name if original_session.subject_id else 'Sin asignatura',
                        'teacher_conflict': not teacher_available,
                        'classroom_conflict': not classroom_available,
                        'teacher_reason': teacher_reason,
                        'classroom_reason': classroom_reason,
                    }

                    if self.skip_conflicts:
                        skipped_sessions.append(conflict_info)
                        _logger.warning(
                            "Sesión omitida por conflicto: %s en %s - Razón: %s",
                            conflict_info['subject'],
                            new_date,
                            teacher_reason or classroom_reason
                        )
                        continue
                    else:
                        # Abortar todo el proceso
                        new_agenda.unlink()  # Eliminar agenda creada
                        raise UserError(
                            _(
                                'Conflicto detectado al duplicar sesión:\n\n'
                                '📅 Fecha: %s\n'
                                '🕐 Hora: %s - %s\n'
                                '📚 Asignatura: %s\n\n'
                                '❌ Motivo:\n%s\n\n'
                                'Active "Omitir Sesiones con Conflictos" para continuar '
                                'omitiendo las sesiones problemáticas.'
                            ) % (
                                new_date,
                                self._format_time(original_session.time_start),
                                self._format_time(original_session.time_end),
                                conflict_info['subject'],
                                teacher_reason or classroom_reason
                            )
                        )

                # ==========================================
                # CREAR SESIÓN
                # ==========================================

                session_vals = {
                    'agenda_id': new_agenda.id,
                    'date': new_date,
                    'time_start': original_session.time_start,
                    'time_end': original_session.time_end,
                    'subject_id': original_session.subject_id.id if original_session.subject_id else False,
                    'program_id': original_session.program_id.id if original_session.program_id else False,
                    'teacher_id': original_session.teacher_id.id if original_session.teacher_id else False,
                    'subcampus_id': original_session.subcampus_id.id if original_session.subcampus_id else False,
                    'delivery_mode': original_session.delivery_mode,
                    'session_type': original_session.session_type,
                    'max_capacity': original_session.max_capacity,
                    'meeting_link': original_session.meeting_link,
                    # NO copiar inscripciones (student_ids)
                    # NO copiar ID de sesión original
                }

                # Copiar estado de publicación si se solicita
                if self.copy_published_state:
                    session_vals['is_published'] = original_session.is_published
                    session_vals['state'] = original_session.state

                try:
                    new_session = self.env['benglish.academic.session'].create(session_vals)
                    created_sessions |= new_session
                    _logger.debug(
                        "Sesión creada: %s en %s",
                        new_session.subject_id.name if new_session.subject_id else 'N/A',
                        new_date
                    )
                except Exception as e:
                    _logger.error(
                        "Error al crear sesión: %s",
                        str(e)
                    )
                    if self.skip_conflicts:
                        skipped_sessions.append({
                            'original_session_id': original_session.id,
                            'new_date': new_date,
                            'subject': original_session.subject_id.name if original_session.subject_id else 'N/A',
                            'error': str(e)
                        })
                    else:
                        new_agenda.unlink()
                        raise

        # ==========================================
        # PASO 3: PREPARAR MENSAJE DE RESULTADO
        # ==========================================

        _logger.info(
            "Duplicación completada: %s sesiones creadas, %s omitidas",
            len(created_sessions),
            len(skipped_sessions)
        )

        # Crear mensaje detallado
        message_title = _('✅ Agenda Duplicada Exitosamente')
        message_lines = [
            _('Nueva agenda: %s') % new_agenda.code,
            _('Periodo: %s al %s') % (new_agenda.date_start, new_agenda.date_end),
            '',
            _('📊 Resumen de duplicación:'),
            _('  • Sesiones creadas: %s') % len(created_sessions),
        ]

        if skipped_sessions:
            message_lines.append(_('  • Sesiones omitidas: %s') % len(skipped_sessions))
            message_lines.append('')
            message_lines.append(_('⚠️ Sesiones omitidas por conflictos:'))
            
            # Limitar a 10 primeras sesiones omitidas para no saturar la notificación
            for i, skip_info in enumerate(skipped_sessions[:10]):
                if i >= 10:
                    message_lines.append(_('  ... y %s más') % (len(skipped_sessions) - 10))
                    break
                message_lines.append(
                    _('  • %s en %s: %s') % (
                        skip_info.get('subject', 'N/A'),
                        skip_info.get('new_date', 'N/A'),
                        skip_info.get('teacher_reason') or skip_info.get('classroom_reason') or skip_info.get('error', 'Error desconocido')
                    )
                )

        message_body = '\n'.join(message_lines)

        # Registrar en chatter de la nueva agenda
        new_agenda.message_post(
            body=message_body,
            subject=_('Agenda Duplicada'),
            message_type='notification'
        )

        # ==========================================
        # PASO 4: RETORNAR VISTA DE NUEVA AGENDA
        # ==========================================

        return {
            'type': 'ir.actions.act_window',
            'name': _('Agenda Duplicada: %s') % new_agenda.code,
            'res_model': 'benglish.academic.agenda',
            'res_id': new_agenda.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': {
                'default_notification': {
                    'type': 'success' if not skipped_sessions else 'warning',
                    'title': message_title,
                    'message': message_body,
                    'sticky': bool(skipped_sessions),
                }
            }
        }
