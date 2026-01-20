# -*- coding: utf-8 -*-
"""Wizard para generar sesiones de clase masivamente según horario del grupo."""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import calendar


class GenerateSessionsWizard(models.TransientModel):
    """
    Wizard para generar sesiones de clase automáticamente.
    Permite definir días de la semana, hora inicio/fin y generar
    todas las sesiones para un periodo determinado.
    """
    _name = 'benglish.generate.sessions.wizard'
    _description = 'Asistente de Generación de Sesiones'

    # GRUPO BASE 
    group_id = fields.Many2one(
        comodel_name='benglish.group',
        string='Grupo',
        required=True,
        help='Grupo para el cual se generarán las sesiones'
    )
    group_name = fields.Char(
        string='Nombre del Grupo',
        related='group_id.name',
        readonly=True
    )
    campus_id = fields.Many2one(
        comodel_name='benglish.campus',
        string='Sede',
        related='group_id.campus_id',
        readonly=True
    )
    subcampus_id = fields.Many2one(
        comodel_name='benglish.subcampus',
        string='Aula',
        related='group_id.subcampus_id',
        readonly=True
    )
    teacher_id = fields.Many2one(
        comodel_name='res.users',
        string='Docente',
        related='group_id.teacher_id',
        readonly=True
    )
    coach_id = fields.Many2one(
        comodel_name='benglish.coach',
        string='Coach',
        related='group_id.coach_id',
        readonly=True
    )
    delivery_mode = fields.Selection(
        string='Modalidad',
        related='group_id.delivery_mode',
        readonly=True
    )
    
    # PERIODO 
    date_start = fields.Date(
        string='Fecha de Inicio',
        required=True,
        default=fields.Date.context_today,
        help='Fecha desde la cual comenzar a generar sesiones'
    )
    date_end = fields.Date(
        string='Fecha de Fin',
        required=True,
        help='Fecha hasta la cual generar sesiones'
    )
    weeks_count = fields.Integer(
        string='Semanas',
        compute='_compute_weeks_count',
        help='Número de semanas del periodo'
    )
    
    #  HORARIO
    # Días de la semana (0=Lunes, 6=Domingo)
    monday = fields.Boolean(string='Lunes', default=True)
    tuesday = fields.Boolean(string='Martes', default=False)
    wednesday = fields.Boolean(string='Miércoles', default=True)
    thursday = fields.Boolean(string='Jueves', default=False)
    friday = fields.Boolean(string='Viernes', default=True)
    saturday = fields.Boolean(string='Sábado', default=False)
    sunday = fields.Boolean(string='Domingo', default=False)
    
    # Horario (en formato float: 8.5 = 8:30)
    time_start = fields.Float(
        string='Hora de Inicio',
        required=True,
        default=8.0,
        help='Hora de inicio de cada sesión (ej: 8.5 = 8:30)'
    )
    time_end = fields.Float(
        string='Hora de Fin',
        required=True,
        default=10.0,
        help='Hora de fin de cada sesión (ej: 10.0 = 10:00)'
    )
    time_start_display = fields.Char(
        string='Inicio',
        compute='_compute_time_display'
    )
    time_end_display = fields.Char(
        string='Fin',
        compute='_compute_time_display'
    )
    
    # CONFIGURACIÓN 
    session_type = fields.Selection(
        selection=[
            ('regular', 'Clase regular'),
            ('makeup', 'Clase de recuperación'),
            ('evaluation', 'Evaluación'),
        ],
        string='Tipo de Sesión',
        default='regular',
        required=True
    )
    auto_publish = fields.Boolean(
        string='Publicar Automáticamente',
        default=False,
        help='Si está marcado, las sesiones se publicarán automáticamente'
    )
    skip_conflicts = fields.Boolean(
        string='Omitir Conflictos',
        default=True,
        help='Si hay conflictos de horario, omite esas fechas y continúa'
    )
    
    # PREVIEW 
    sessions_to_create = fields.Integer(
        string='Sesiones a Crear',
        compute='_compute_sessions_preview',
        help='Número de sesiones que se crearán'
    )
    preview_dates = fields.Text(
        string='Vista Previa de Fechas',
        compute='_compute_sessions_preview',
        help='Lista de fechas donde se crearán sesiones'
    )
    conflict_warning = fields.Text(
        string='Advertencia de Conflictos',
        compute='_compute_sessions_preview'
    )
    
    #  MÉTODOS COMPUTADOS 
    
    @api.depends('date_start', 'date_end')
    def _compute_weeks_count(self):
        """Calcula el número de semanas del periodo."""
        for wizard in self:
            if wizard.date_start and wizard.date_end:
                delta = wizard.date_end - wizard.date_start
                wizard.weeks_count = max(1, delta.days // 7)
            else:
                wizard.weeks_count = 0
    
    @api.depends('time_start', 'time_end')
    def _compute_time_display(self):
        """Convierte horas float a formato HH:MM."""
        for wizard in self:
            wizard.time_start_display = self._float_to_time_str(wizard.time_start)
            wizard.time_end_display = self._float_to_time_str(wizard.time_end)
    
    def _float_to_time_str(self, float_time):
        """Convierte float a string de tiempo (8.5 -> '08:30')."""
        hours = int(float_time)
        minutes = int((float_time - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"
    
    @api.depends('date_start', 'date_end', 'monday', 'tuesday', 'wednesday', 
                 'thursday', 'friday', 'saturday', 'sunday', 'group_id',
                 'time_start', 'time_end')
    def _compute_sessions_preview(self):
        """Calcula preview de sesiones a crear y detecta conflictos."""
        for wizard in self:
            dates = wizard._get_session_dates()
            wizard.sessions_to_create = len(dates)
            
            if dates:
                # Mostrar primeras 10 y últimas 5
                preview_lines = []
                day_names = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
                
                for i, date in enumerate(dates[:10]):
                    day_name = day_names[date.weekday()]
                    preview_lines.append(f"• {day_name} {date.strftime('%d/%m/%Y')}")
                
                if len(dates) > 15:
                    preview_lines.append(f"... ({len(dates) - 15} fechas más) ...")
                    for date in dates[-5:]:
                        day_name = day_names[date.weekday()]
                        preview_lines.append(f"• {day_name} {date.strftime('%d/%m/%Y')}")
                elif len(dates) > 10:
                    for date in dates[10:]:
                        day_name = day_names[date.weekday()]
                        preview_lines.append(f"• {day_name} {date.strftime('%d/%m/%Y')}")
                
                wizard.preview_dates = '\n'.join(preview_lines)
            else:
                wizard.preview_dates = 'No hay fechas seleccionadas'
            
            # Detectar conflictos
            conflicts = wizard._detect_conflicts(dates)
            if conflicts:
                wizard.conflict_warning = f"⚠️ {len(conflicts)} CONFLICTOS detectados:\n" + '\n'.join(conflicts[:5])
                if len(conflicts) > 5:
                    wizard.conflict_warning += f"\n... y {len(conflicts) - 5} más."
            else:
                wizard.conflict_warning = False
    
    #  MÉTODOS AUXILIARES 
    
    def _get_selected_weekdays(self):
        """Retorna lista de días de la semana seleccionados (0=Lunes)."""
        self.ensure_one()
        days = []
        if self.monday: days.append(0)
        if self.tuesday: days.append(1)
        if self.wednesday: days.append(2)
        if self.thursday: days.append(3)
        if self.friday: days.append(4)
        if self.saturday: days.append(5)
        if self.sunday: days.append(6)
        return days
    
    def _get_session_dates(self):
        """Genera lista de fechas donde se crearán sesiones."""
        self.ensure_one()
        if not self.date_start or not self.date_end:
            return []
        
        selected_days = self._get_selected_weekdays()
        if not selected_days:
            return []
        
        dates = []
        current = self.date_start
        while current <= self.date_end:
            if current.weekday() in selected_days:
                dates.append(current)
            current += timedelta(days=1)
        
        return dates
    
    def _detect_conflicts(self, dates):
        """Detecta conflictos de horario para las fechas dadas."""
        self.ensure_one()
        if not self.group_id or not dates:
            return []
        
        conflicts = []
        Session = self.env['benglish.class.session']
        
        for date in dates[:20]:  # Limitamos a 20 para performance
            # Convertir fecha y hora a datetime
            start_dt = datetime.combine(date, datetime.min.time())
            start_dt = start_dt.replace(
                hour=int(self.time_start),
                minute=int((self.time_start % 1) * 60)
            )
            end_dt = start_dt.replace(
                hour=int(self.time_end),
                minute=int((self.time_end % 1) * 60)
            )
            
            # Buscar conflictos por asignatura y sede
            domain = [
                ('state', '!=', 'cancelled'),
                ('start_datetime', '<', end_dt),
                ('end_datetime', '>', start_dt),
            ]
            
            # Conflicto de asignatura en la misma sede (mismo grupo implícito)
            if Session.search_count(domain + [('subject_id', '=', self.group_id.subject_id.id), ('campus_id', '=', self.campus_id.id)]):
                conflicts.append(f"• {date.strftime('%d/%m/%Y')}: Ya existe sesión de esta asignatura en esta sede")
                continue
            
            # Conflicto de docente
            if self.teacher_id and Session.search_count(domain + [('teacher_id', '=', self.teacher_id.id)]):
                conflicts.append(f"• {date.strftime('%d/%m/%Y')}: Docente ocupado")
                continue
            
            # Conflicto de aula
            if self.subcampus_id and Session.search_count(domain + [('subcampus_id', '=', self.subcampus_id.id)]):
                conflicts.append(f"• {date.strftime('%d/%m/%Y')}: Aula ocupada")
        
        return conflicts
    
    #  VALIDACIONES
    
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        """Valida que las fechas sean correctas."""
        for wizard in self:
            if wizard.date_start and wizard.date_end:
                if wizard.date_end < wizard.date_start:
                    raise ValidationError(_('La fecha de fin debe ser posterior a la fecha de inicio.'))
    
    @api.constrains('time_start', 'time_end')
    def _check_times(self):
        """Valida que las horas sean correctas."""
        for wizard in self:
            if wizard.time_start >= wizard.time_end:
                raise ValidationError(_('La hora de fin debe ser posterior a la hora de inicio.'))
            if wizard.time_start < 0 or wizard.time_start > 23.99:
                raise ValidationError(_('La hora de inicio debe estar entre 0 y 24.'))
            if wizard.time_end < 0 or wizard.time_end > 23.99:
                raise ValidationError(_('La hora de fin debe estar entre 0 y 24.'))
    
    @api.onchange('group_id')
    def _onchange_group_id(self):
        """Precarga fechas del grupo si existen."""
        if self.group_id:
            if self.group_id.start_date:
                self.date_start = self.group_id.start_date
            if self.group_id.end_date:
                self.date_end = self.group_id.end_date
    
    #  ACCIÓN PRINCIPAL 
    
    def action_generate_sessions(self):
        """Genera las sesiones de clase."""
        self.ensure_one()
        
        # Validaciones
        if not self.group_id:
            raise UserError(_('Debe seleccionar un grupo.'))
        
        selected_days = self._get_selected_weekdays()
        if not selected_days:
            raise UserError(_('Debe seleccionar al menos un día de la semana.'))
        
        dates = self._get_session_dates()
        if not dates:
            raise UserError(_('No hay fechas válidas para generar sesiones.'))
        
        # Crear sesiones
        Session = self.env['benglish.class.session']
        created_count = 0
        skipped_count = 0
        errors = []
        
        for date in dates:
            # Construir datetime de inicio y fin
            start_dt = datetime.combine(date, datetime.min.time())
            start_dt = start_dt.replace(
                hour=int(self.time_start),
                minute=int((self.time_start % 1) * 60)
            )
            end_dt = start_dt.replace(
                hour=int(self.time_end),
                minute=int((self.time_end % 1) * 60)
            )
            
            # Verificar conflictos
            conflict_domain = [
                ('state', '!=', 'cancelled'),
                ('start_datetime', '<', end_dt),
                ('end_datetime', '>', start_dt),
            ]
            
            has_conflict = False
            
            # Conflicto de asignatura en la sede
            if Session.search_count(conflict_domain + [('subject_id', '=', self.group_id.subject_id.id), ('campus_id', '=', self.campus_id.id)]):
                has_conflict = True
            
            # Conflicto de docente
            if not has_conflict and self.teacher_id:
                if Session.search_count(conflict_domain + [('teacher_id', '=', self.teacher_id.id)]):
                    has_conflict = True
            
            # Conflicto de aula
            if not has_conflict and self.subcampus_id:
                if Session.search_count(conflict_domain + [('subcampus_id', '=', self.subcampus_id.id)]):
                    has_conflict = True
            
            if has_conflict:
                if self.skip_conflicts:
                    skipped_count += 1
                    continue
                else:
                    raise UserError(_(
                        'Conflicto detectado para la fecha %s. '
                        'Active "Omitir Conflictos" para continuar.'
                    ) % date.strftime('%d/%m/%Y'))
            
            # Crear sesión
            try:
                vals = {
                    'subject_id': self.group_id.subject_id.id,
                    'campus_id': self.campus_id.id,
                    'subcampus_id': self.subcampus_id.id if self.subcampus_id else False,
                    'teacher_id': self.teacher_id.id if self.teacher_id else False,
                    'coach_id': self.coach_id.id if self.coach_id else False,
                    'start_datetime': start_dt,
                    'end_datetime': end_dt,
                    'session_type': self.session_type,
                    'delivery_mode': self.delivery_mode or 'presential',
                    'state': 'planned',
                }
                
                # Heredar meeting_link si es virtual/híbrido
                if self.delivery_mode in ('virtual', 'hybrid') and self.group_id.meeting_link:
                    vals['meeting_link'] = self.group_id.meeting_link
                    vals['meeting_platform'] = self.group_id.meeting_platform
                
                session = Session.create(vals)
                
                # Publicar si está configurado
                if self.auto_publish:
                    session.action_publish()
                
                created_count += 1
                
            except Exception as e:
                errors.append(f"Error en {date.strftime('%d/%m/%Y')}: {str(e)}")
        
        # Mensaje de resultado
        message_parts = [f"✅ {created_count} sesiones creadas exitosamente."]
        
        if skipped_count > 0:
            message_parts.append(f"⚠️ {skipped_count} sesiones omitidas por conflictos.")
        
        if errors:
            message_parts.append(f"❌ {len(errors)} errores: " + '; '.join(errors[:3]))
        
        # Registrar en el chatter del grupo
        self.group_id.message_post(
            body=_('<strong>🗓️ Generación Masiva de Sesiones</strong><br/>'
                   'Se generaron <strong>%d sesiones</strong> desde %s hasta %s.<br/>'
                   'Horario: %s - %s<br/>'
                   'Tipo: %s%s') % (
                created_count,
                self.date_start.strftime('%d/%m/%Y'),
                self.date_end.strftime('%d/%m/%Y'),
                self.time_start_display,
                self.time_end_display,
                dict(self._fields['session_type'].selection).get(self.session_type),
                f'<br/>Omitidas por conflicto: {skipped_count}' if skipped_count else ''
            ),
            message_type='notification',
            subtype_xmlid='mail.mt_note'
        )
        
        # Mostrar notificación
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'title': _('Generación Completada'),
                'message': '\n'.join(message_parts),
                'type': 'success' if not errors else 'warning',
                'sticky': True,
            }
        )
        
        # Abrir vista de sesiones generadas
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'benglish.class.session',
            'view_mode': 'calendar,list,form',
            'domain': [('subject_id', '=', self.group_id.subject_id.id), ('campus_id', '=', self.campus_id.id)],
            'name': _('Sesiones de %s') % self.group_id.name,
            'target': 'current',
        }
