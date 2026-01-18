# -*- coding: utf-8 -*-
"""Wizard para reemplazar docente con alcance temporal y registro de auditoría."""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ReplaceTeacherWizard(models.TransientModel):
    """
    Wizard para reemplazar el docente de una o varias sesiones.
    Soporta reemplazo con alcance temporal: individual, futuras o todas.
    """
    
    _name = 'benglish.replace.teacher.wizard'
    _description = 'Asistente de Reemplazo de Docente'

    # Sesión/sesiones origen
    session_id = fields.Many2one(
        comodel_name='benglish.class.session',
        string='Sesión de Referencia',
        help='Sesión desde la cual se inicia el reemplazo'
    )
    session_ids = fields.Many2many(
        comodel_name='benglish.class.session',
        string='Sesiones Seleccionadas',
        help='Sesiones seleccionadas para reemplazo masivo'
    )
    subject_id = fields.Many2one(
        comodel_name='benglish.subject',
        string='Asignatura',
        related='session_id.subject_id',
        readonly=True,
        store=False
    )

    # Docentes
    original_teacher_id = fields.Many2one(
        comodel_name='res.users',
        string='Docente Actual',
        readonly=True,
        domain="[('share', '=', False)]"
    )
    new_teacher_id = fields.Many2one(
        comodel_name='res.users',
        string='Nuevo Docente',
        required=True,
        domain="[('share', '=', False)]",
        help='Seleccione el docente que reemplazará al actual'
    )
    
    # Alcance temporal (T12)
    replacement_scope = fields.Selection(
        selection=[
            ('single', 'Solo esta sesión'),
            ('future', 'Esta sesión y todas las futuras de la misma asignatura'),
            ('all', 'Todas las sesiones de la asignatura (pasadas y futuras)'),
            ('selected', 'Solo sesiones seleccionadas (múltiples)'),
        ],
        string='Alcance del Reemplazo',
        default='single',
        required=True,
        help='Define qué sesiones serán afectadas por el reemplazo'
    )
    effective_date = fields.Datetime(
        string='Fecha Efectiva',
        help='Para alcance "futuras": reemplazar desde esta fecha en adelante'
    )
    sessions_to_replace_count = fields.Integer(
        string='Sesiones a Afectar',
        compute='_compute_sessions_to_replace',
        help='Número de sesiones que serán reemplazadas'
    )
    
    # Motivo y notas
    replacement_reason = fields.Text(
        string='Motivo del Reemplazo',
        required=True,
        help='Indique por qué se reemplaza al docente (ej: licencia médica, vacaciones, emergencia)'
    )
    notes = fields.Text(
        string='Notas Adicionales',
        help='Información complementaria sobre el reemplazo'
    )
    
    # Validaciones
    check_conflicts = fields.Boolean(
        string='Verificar Conflictos de Horario',
        default=True,
        help='Si está marcado, valida que el nuevo docente no tenga solapamientos'
    )
    conflict_warning = fields.Text(
        string='Advertencia de Conflictos',
        compute='_compute_conflict_warning',
        readonly=True
    )
    skip_conflicts = fields.Boolean(
        string='Omitir Sesiones con Conflictos',
        default=False,
        help='Si hay conflictos, omite esas sesiones y continúa con las demás'
    )

    @api.depends('replacement_scope', 'session_id', 'session_ids', 'effective_date', 'subject_id')
    def _compute_sessions_to_replace(self):
        """Calcula el número de sesiones que serán afectadas."""
        for wizard in self:
            sessions = wizard._get_sessions_to_replace()
            wizard.sessions_to_replace_count = len(sessions)

    @api.depends('new_teacher_id', 'replacement_scope', 'session_id', 'session_ids', 'effective_date')
    def _compute_conflict_warning(self):
        """Verifica si el nuevo docente tiene conflictos de horario."""
        for wizard in self:
            wizard.conflict_warning = False
            if not wizard.new_teacher_id or not wizard.check_conflicts:
                continue
            
            sessions = wizard._get_sessions_to_replace()
            conflicts = []
            conflict_count = 0
            
            for session in sessions:
                if not session.start_datetime or not session.end_datetime:
                    continue
                # Buscar sesiones del nuevo docente en ese horario
                conflicting = self.env['benglish.class.session'].search([
                    ('teacher_id', '=', wizard.new_teacher_id.id),
                    ('state', '!=', 'cancelled'),
                    ('id', '!=', session.id),
                    ('start_datetime', '<', session.end_datetime),
                    ('end_datetime', '>', session.start_datetime),
                ])
                if conflicting:
                    conflict_count += 1
                    if len(conflicts) < 5:
                        conflicts.append(
                            f"• {session.display_name[:60]}: {len(conflicting)} conflicto(s)"
                        )
            
            if conflicts:
                wizard.conflict_warning = f"⚠️ {conflict_count} CONFLICTOS DETECTADOS:\n" + "\n".join(conflicts)
                if conflict_count > 5:
                    wizard.conflict_warning += f"\n... y {conflict_count - 5} más."
                if wizard.skip_conflicts:
                    wizard.conflict_warning += "\n\n✓ Las sesiones con conflictos serán omitidas."

    @api.onchange('replacement_scope', 'session_id')
    def _onchange_replacement_scope(self):
        """Actualiza la fecha efectiva según el alcance."""
        if self.replacement_scope == 'future' and self.session_id:
            self.effective_date = self.session_id.start_datetime
        elif self.replacement_scope in ('single', 'all', 'selected'):
            self.effective_date = False

    def _get_sessions_to_replace(self):
        """
        Obtiene las sesiones que serán reemplazadas según el alcance.
        
        Returns:
            recordset de benglish.class.session
        """
        self.ensure_one()
        
        if self.replacement_scope == 'selected':
            return self.session_ids
        
        if not self.session_id:
            return self.env['benglish.class.session']
        
        if self.replacement_scope == 'single':
            return self.session_id
        
        # Para 'future' y 'all', buscar sesiones de la misma asignatura y docente
        domain = [
            ('subject_id', '=', self.session_id.subject_id.id),
            ('teacher_id', '=', self.original_teacher_id.id),
            ('state', '!=', 'cancelled'),
        ]
        
        if self.replacement_scope == 'future':
            effective = self.effective_date or self.session_id.start_datetime
            domain.append(('start_datetime', '>=', effective))
        
        return self.env['benglish.class.session'].search(domain, order='start_datetime asc')

    def action_replace(self):
        """Ejecuta el reemplazo de docente con alcance temporal."""
        self.ensure_one()
        
        # Validar que hay un docente nuevo diferente
        if self.new_teacher_id == self.original_teacher_id:
            raise UserError(_('El nuevo docente debe ser diferente al actual.'))
        
        # Obtener sesiones a reemplazar
        sessions = self._get_sessions_to_replace()
        if not sessions:
            raise UserError(_('No hay sesiones para reemplazar con los criterios seleccionados.'))
        
        # Validar conflictos si está habilitado y no se permiten
        if self.check_conflicts and self.conflict_warning and not self.skip_conflicts:
            raise UserError(_(
                'El nuevo docente tiene conflictos de horario:\n\n%s\n\n'
                'Active "Omitir Sesiones con Conflictos" para continuar, '
                'o desactive "Verificar Conflictos" para forzar el reemplazo.'
            ) % self.conflict_warning)
        
        # Determinar tipo de reemplazo para el log
        replacement_type_map = {
            'single': 'single',
            'future': 'future',
            'all': 'all',
            'selected': 'massive',
        }
        replacement_type = replacement_type_map.get(self.replacement_scope, 'single')
        
        # Ejecutar reemplazo
        success_count = 0
        skipped_count = 0
        error_count = 0
        
        for session in sessions:
            try:
                # Verificar conflictos individuales si se deben omitir
                if self.check_conflicts and self.skip_conflicts:
                    conflicting = self.env['benglish.class.session'].search_count([
                        ('teacher_id', '=', self.new_teacher_id.id),
                        ('state', '!=', 'cancelled'),
                        ('id', '!=', session.id),
                        ('start_datetime', '<', session.end_datetime),
                        ('end_datetime', '>', session.start_datetime),
                    ])
                    if conflicting:
                        skipped_count += 1
                        continue
                
                # Ejecutar reemplazo con log de auditoría
                session._do_replace_teacher(
                    new_teacher_id=self.new_teacher_id.id,
                    reason=self.replacement_reason,
                    replacement_type=replacement_type,
                    notes=self.notes
                )
                success_count += 1
                
            except (ValidationError, UserError) as e:
                error_count += 1
                if len(sessions) == 1:
                    raise
                # Para operaciones masivas, registrar error y continuar
                session.message_post(
                    body=_('Error al reemplazar docente: %s') % str(e),
                    message_type='notification'
                )
        
        # Mensaje de resultado
        message_parts = [_('%s sesión(es) reemplazada(s) exitosamente.') % success_count]
        if skipped_count:
            message_parts.append(_('%s omitida(s) por conflictos.') % skipped_count)
        if error_count:
            message_parts.append(_('%s con errores.') % error_count)
        
        # Mostrar notificación
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'title': _('Reemplazo Completado'),
                'message': ' '.join(message_parts),
                'type': 'success' if success_count > 0 else 'warning',
                'sticky': False,
            }
        )
        
        # Cerrar wizard y refrescar vista
        return {'type': 'ir.actions.act_window_close'}
