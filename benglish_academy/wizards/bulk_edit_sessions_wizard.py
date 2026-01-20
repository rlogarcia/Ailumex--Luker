# -*- coding: utf-8 -*-
"""Wizard para edición masiva de sesiones."""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta


class BulkEditSessionsWizard(models.TransientModel):
    """Wizard para editar múltiples sesiones simultáneamente."""
    
    _name = 'benglish.bulk.edit.sessions.wizard'
    _description = 'Asistente de Edición Masiva de Sesiones'

    session_ids = fields.Many2many(
        comodel_name='benglish.class.session',
        string='Sesiones a Editar',
        required=True
    )
    session_count = fields.Integer(
        string='Total Sesiones',
        compute='_compute_session_count'
    )

    # Filtros previos (opcional)
    campus_id = fields.Many2one(
        comodel_name='benglish.campus',
        string='Filtrar por Sede'
    )
    start_date = fields.Date(string='Desde')
    end_date = fields.Date(string='Hasta')

    # Acciones de edición
    action_type = fields.Selection(
        selection=[
            ('change_teacher', 'Cambiar Docente'),
            ('change_campus', 'Cambiar Sede/Aula'),
            ('shift_time', 'Desplazar Horarios'),
            ('change_mode', 'Cambiar Modalidad'),
            ('publish', 'Publicar'),
            ('unpublish', 'Despublicar'),
        ],
        string='Acción a Realizar',
        required=True
    )

    # Campos condicionales según la acción
    new_teacher_id = fields.Many2one(
        comodel_name='res.users',
        string='Nuevo Docente',
        domain="[('share', '=', False)]"
    )
    replacement_reason = fields.Text(
        string='Motivo del Reemplazo',
        help='Requerido para cambio de docente: indique licencia, vacaciones, etc.'
    )
    new_campus_id = fields.Many2one(
        comodel_name='benglish.campus',
        string='Nueva Sede'
    )
    new_subcampus_id = fields.Many2one(
        comodel_name='benglish.subcampus',
        string='Nueva Aula',
        domain="[('campus_id', '=', new_campus_id)]"
    )
    time_shift_hours = fields.Float(
        string='Desplazar Horas',
        help='Número de horas a desplazar (positivo = adelante, negativo = atrás)'
    )
    time_shift_days = fields.Integer(
        string='Desplazar Días',
        help='Número de días a desplazar las sesiones'
    )
    new_delivery_mode = fields.Selection(
        selection=[
            ('presential', 'Presencial'),
            ('virtual', 'Virtual'),
            ('hybrid', 'Híbrida'),
        ],
        string='Nueva Modalidad'
    )

    # Opciones
    skip_conflicts = fields.Boolean(
        string='Omitir Conflictos',
        default=True,
        help='Si está marcado, sesiones con conflictos se omitirán'
    )
    preview_mode = fields.Boolean(
        string='Modo Preview',
        default=False,
        help='Solo muestra qué cambios se aplicarían sin ejecutarlos'
    )

    @api.depends('session_ids')
    def _compute_session_count(self):
        for wizard in self:
            wizard.session_count = len(wizard.session_ids)

    @api.onchange('action_type')
    def _onchange_action_type(self):
        """Limpia campos no relacionados con la acción seleccionada."""
        if self.action_type != 'change_teacher':
            self.new_teacher_id = False
            self.replacement_reason = False
        if self.action_type != 'change_campus':
            self.new_campus_id = False
            self.new_subcampus_id = False
        if self.action_type != 'shift_time':
            self.time_shift_hours = 0
            self.time_shift_days = 0
        if self.action_type != 'change_mode':
            self.new_delivery_mode = False

    def action_apply(self):
        """Aplica los cambios masivos a las sesiones seleccionadas."""
        self.ensure_one()
        
        if not self.session_ids:
            raise UserError(_('No hay sesiones seleccionadas para editar.'))
        
        # Validar campos requeridos según la acción
        if self.action_type == 'change_teacher':
            if not self.new_teacher_id:
                raise UserError(_('Debe seleccionar un nuevo docente.'))
            if not self.replacement_reason:
                raise UserError(_('Debe indicar el motivo del reemplazo (T12-HU6).'))
        if self.action_type == 'change_campus' and not self.new_campus_id:
            raise UserError(_('Debe seleccionar una nueva sede.'))
        if self.action_type == 'shift_time' and self.time_shift_hours == 0 and self.time_shift_days == 0:
            raise UserError(_('Debe indicar cuántas horas o días desplazar.'))
        if self.action_type == 'change_mode' and not self.new_delivery_mode:
            raise UserError(_('Debe seleccionar una nueva modalidad.'))
        
        # Ejecutar acción
        success_count = 0
        skipped_sessions = []
        
        for session in self.session_ids:
            try:
                if self.preview_mode:
                    # Solo validar sin aplicar cambios
                    self._preview_change(session)
                else:
                    # Aplicar cambios reales
                    self._apply_change(session)
                success_count += 1
            except (ValidationError, UserError) as e:
                if self.skip_conflicts:
                    skipped_sessions.append((session.display_name, str(e)))
                else:
                    raise UserError(_(
                        'Error al editar sesión %s:\n%s'
                    ) % (session.display_name, str(e)))
        
        # Mensaje de resultado
        if self.preview_mode:
            message = _('Preview: %s sesiones serían actualizadas.') % success_count
        else:
            message = _('%s sesiones fueron actualizadas exitosamente.') % success_count
        
        if skipped_sessions:
            message += _('\n\n%s sesiones fueron omitidas por conflictos.') % len(skipped_sessions)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Edición Masiva Completada'),
                'message': message,
                'type': 'success' if not skipped_sessions else 'warning',
                'sticky': bool(skipped_sessions),
            }
        }

    def _preview_change(self, session):
        """Simula el cambio sin aplicarlo (solo validación)."""
        vals = self._prepare_values(session)
        # Simular validaciones sin guardar
        if self.action_type == 'change_teacher' and vals.get('teacher_id'):
            # Verificar solapamientos del nuevo docente
            conflicts = self.env['benglish.class.session'].search([
                ('teacher_id', '=', vals['teacher_id']),
                ('id', '!=', session.id),
                ('state', '!=', 'cancelled'),
                ('start_datetime', '<', session.end_datetime),
                ('end_datetime', '>', session.start_datetime),
            ])
            if conflicts:
                raise ValidationError(_('El nuevo docente tiene %s conflicto(s)') % len(conflicts))

    def _apply_change(self, session):
        """Aplica el cambio real a la sesión."""
        # Para cambio de docente, usar método especializado con log de auditoría 
        if self.action_type == 'change_teacher' and session.teacher_id:
            session._do_replace_teacher(
                new_teacher_id=self.new_teacher_id.id,
                reason=self.replacement_reason,
                replacement_type='massive',
                notes=f'Edición masiva de {len(self.session_ids)} sesiones'
            )
        else:
            # Para otras acciones, usar write estándar
            vals = self._prepare_values(session)
            if vals:
                session.write(vals)

    def _prepare_values(self, session):
        """Prepara los valores a actualizar según la acción."""
        vals = {}
        
        if self.action_type == 'change_teacher':
            # No usar write directo, ver _apply_change
            vals['teacher_id'] = self.new_teacher_id.id
            
        elif self.action_type == 'change_campus':
            vals['campus_id'] = self.new_campus_id.id
            if self.new_subcampus_id:
                vals['subcampus_id'] = self.new_subcampus_id.id
            else:
                vals['subcampus_id'] = False
                
        elif self.action_type == 'shift_time':
            offset = timedelta(days=self.time_shift_days, hours=self.time_shift_hours)
            vals['start_datetime'] = session.start_datetime + offset
            vals['end_datetime'] = session.end_datetime + offset
            
        elif self.action_type == 'change_mode':
            vals['delivery_mode'] = self.new_delivery_mode
            
        elif self.action_type == 'publish':
            if session.state != 'cancelled' and session.subject_id:
                vals['is_published'] = True
                vals['published_at'] = fields.Datetime.now()
                vals['published_by_id'] = self.env.user.id
            else:
                raise ValidationError(_('No se puede publicar (cancelada o sin asignatura)'))
                
        elif self.action_type == 'unpublish':
            vals['is_published'] = False
            vals['published_at'] = False
            vals['published_by_id'] = False
        
        return vals
