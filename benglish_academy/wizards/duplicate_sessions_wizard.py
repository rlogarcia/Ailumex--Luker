# -*- coding: utf-8 -*-
"""Wizard para duplicar sesiones por sede y periodo."""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta


class DuplicateSessionsWizard(models.TransientModel):
    """Wizard para duplicar sesiones de una sede/periodo a otro."""
    
    _name = 'benglish.duplicate.sessions.wizard'
    _description = 'Asistente de Duplicación de Sesiones'

    # Origen
    source_campus_id = fields.Many2one(
        comodel_name='benglish.campus',
        string='Sede Origen',
        required=True
    )
    source_start_date = fields.Date(
        string='Desde (Fecha)',
        required=True
    )
    source_end_date = fields.Date(
        string='Hasta (Fecha)',
        required=True
    )
    source_session_ids = fields.Many2many(
        comodel_name='benglish.class.session',
        relation='wizard_duplicate_source_sessions_rel',
        column1='wizard_id',
        column2='session_id',
        string='Sesiones a Duplicar',
        compute='_compute_source_sessions',
        readonly=False,
        store=True
    )
    source_session_count = fields.Integer(
        string='Total Sesiones',
        compute='_compute_source_session_count'
    )

    # Destino
    target_campus_id = fields.Many2one(
        comodel_name='benglish.campus',
        string='Sede Destino'
    )
    target_start_date = fields.Date(
        string='Nueva Fecha Inicio',
        required=True,
        help='Las sesiones se duplicarán manteniendo los mismos días/horarios desde esta fecha'
    )
    date_offset_days = fields.Integer(
        string='Desplazamiento (días)',
        compute='_compute_date_offset',
        readonly=True
    )
    
    # Opciones
    copy_published_state = fields.Boolean(
        string='Copiar Estado de Publicación',
        default=False,
        help='Si está marcado, las sesiones duplicadas heredarán el estado publicado/no publicado'
    )
    auto_adjust_teachers = fields.Boolean(
        string='Ajustar Docentes Automáticamente',
        default=False,
        help='Intenta asignar docentes de la sede destino cuando sea posible'
    )
    skip_conflicts = fields.Boolean(
        string='Omitir Conflictos',
        default=True,
        help='Si está marcado, las sesiones con conflictos de horario se omitirán en lugar de fallar'
    )

    @api.depends('source_campus_id', 'source_start_date', 'source_end_date')
    def _compute_source_sessions(self):
        """Carga las sesiones del periodo origen."""
        for wizard in self:
            if wizard.source_campus_id and wizard.source_start_date and wizard.source_end_date:
                sessions = self.env['benglish.class.session'].search([
                    ('campus_id', '=', wizard.source_campus_id.id),
                    ('start_datetime', '>=', fields.Datetime.to_datetime(wizard.source_start_date)),
                    ('start_datetime', '<=', fields.Datetime.to_datetime(wizard.source_end_date).replace(hour=23, minute=59)),
                    ('state', '!=', 'cancelled'),
                ])
                wizard.source_session_ids = sessions
            else:
                wizard.source_session_ids = False

    @api.depends('source_session_ids')
    def _compute_source_session_count(self):
        for wizard in self:
            wizard.source_session_count = len(wizard.source_session_ids)

    @api.depends('source_start_date', 'target_start_date')
    def _compute_date_offset(self):
        """Calcula cuántos días se desplazarán las sesiones."""
        for wizard in self:
            if wizard.source_start_date and wizard.target_start_date:
                delta = wizard.target_start_date - wizard.source_start_date
                wizard.date_offset_days = delta.days
            else:
                wizard.date_offset_days = 0

    @api.constrains('source_start_date', 'source_end_date')
    def _check_dates(self):
        for wizard in self:
            if wizard.source_end_date < wizard.source_start_date:
                raise ValidationError(_('La fecha de fin debe ser posterior a la fecha de inicio.'))

    def action_duplicate(self):
        """Duplica las sesiones seleccionadas."""
        self.ensure_one()
        
        if not self.source_session_ids:
            raise UserError(_('No hay sesiones para duplicar en el periodo seleccionado.'))
        
        if not self.target_start_date:
            raise UserError(_('Debe indicar la fecha de inicio para las sesiones duplicadas.'))
        
        # Preparar campus destino
        target_campus = self.target_campus_id or self.source_campus_id
        
        created_sessions = self.env['benglish.class.session']
        skipped_sessions = []
        
        for session in self.source_session_ids:
            # Calcular nuevas fechas
            offset = timedelta(days=self.date_offset_days)
            new_start = session.start_datetime + offset
            new_end = session.end_datetime + offset
            
            # Preparar valores
            vals = {
                'subject_id': session.subject_id.id,
                'campus_id': target_campus.id,
                'subcampus_id': session.subcampus_id.id if session.subcampus_id and session.subcampus_id.campus_id == target_campus else False,
                'teacher_id': session.teacher_id.id,
                'coach_id': session.coach_id.id,
                'session_type': session.session_type,
                'delivery_mode': session.delivery_mode,
                'meeting_link': session.meeting_link,
                'meeting_platform': session.meeting_platform,
                'start_datetime': new_start,
                'end_datetime': new_end,
                'notes': (session.notes or '') + f'\n[Duplicada desde sesión {session.id} el {fields.Date.today()}]',
            }
            
            # Copiar estado de publicación si se solicita
            if self.copy_published_state and session.is_published:
                vals['is_published'] = True
            
            # Intentar crear sesión
            try:
                new_session = self.env['benglish.class.session'].create(vals)
                created_sessions |= new_session
            except (ValidationError, UserError) as e:
                if self.skip_conflicts:
                    skipped_sessions.append((session.display_name, str(e)))
                else:
                    raise UserError(_(
                        'Error al duplicar sesión %s:\n%s'
                    ) % (session.display_name, str(e)))
        
        # Mensaje de resultado
        message = _('%s sesiones fueron duplicadas exitosamente.') % len(created_sessions)
        if skipped_sessions:
            message += _('\n\n%s sesiones fueron omitidas por conflictos.') % len(skipped_sessions)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Duplicación Completada'),
                'message': message,
                'type': 'success' if not skipped_sessions else 'warning',
                'sticky': bool(skipped_sessions),
            }
        }
