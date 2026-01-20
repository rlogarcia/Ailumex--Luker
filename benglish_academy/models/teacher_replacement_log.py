# -*- coding: utf-8 -*-
"""Modelo de auditoría para reemplazos de docente"""

from odoo import api, fields, models, _


class TeacherReplacementLog(models.Model):
    """
    Registro de auditoría para cada reemplazo de docente.
    Mantiene historial completo de cambios con trazabilidad.
    """
    _name = 'benglish.teacher.replacement.log'
    _description = 'Log de Reemplazo de Docente'
    _order = 'replaced_at desc, id desc'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Nombre',
        compute='_compute_display_name',
        store=True
    )

    # Sesión afectada
    session_id = fields.Many2one(
        comodel_name='benglish.class.session',
        string='Sesión',
        required=True,
        ondelete='cascade',
        index=True
    )
    subject_id = fields.Many2one(
        comodel_name='benglish.subject',
        string='Asignatura',
        related='session_id.subject_id',
        store=True,
        readonly=True
    )
    campus_id = fields.Many2one(
        comodel_name='benglish.campus',
        string='Sede',
        related='session_id.campus_id',
        store=True,
        readonly=True
    )

    # Fechas de la sesión (para contexto)
    session_start_datetime = fields.Datetime(
        string='Inicio de Sesión',
        related='session_id.start_datetime',
        store=True,
        readonly=True
    )
    session_end_datetime = fields.Datetime(
        string='Fin de Sesión',
        related='session_id.end_datetime',
        store=True,
        readonly=True
    )

    # Docentes involucrados
    original_teacher_id = fields.Many2one(
        comodel_name='res.users',
        string='Docente Anterior',
        required=True,
        domain="[('share', '=', False)]",
        ondelete='restrict'
    )
    new_teacher_id = fields.Many2one(
        comodel_name='res.users',
        string='Docente Nuevo',
        required=True,
        domain="[('share', '=', False)]",
        ondelete='restrict'
    )

    # Motivo y contexto
    replacement_reason = fields.Text(
        string='Motivo del Reemplazo',
        required=True,
        help='Razón por la cual se realizó el reemplazo (ej: licencia médica, vacaciones, emergencia)'
    )
    replacement_type = fields.Selection(
        selection=[
            ('single', 'Sesión individual'),
            ('future', 'Serie futura'),
            ('all', 'Todas las sesiones'),
            ('massive', 'Edición masiva'),
        ],
        string='Tipo de Reemplazo',
        default='single',
        required=True,
        help='Alcance del reemplazo realizado'
    )

    # Auditoría
    replaced_at = fields.Datetime(
        string='Fecha del Reemplazo',
        required=True,
        default=fields.Datetime.now,
        readonly=True,
        index=True
    )
    replaced_by_id = fields.Many2one(
        comodel_name='res.users',
        string='Reemplazado Por',
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        ondelete='restrict'
    )

    # Información adicional
    notes = fields.Text(
        string='Notas Adicionales',
        help='Comentarios o información complementaria sobre el reemplazo'
    )

    @api.depends('session_id', 'original_teacher_id', 'new_teacher_id', 'replaced_at')
    def _compute_display_name(self):
        """Genera un nombre descriptivo para el log."""
        for record in self:
            parts = []
            if record.session_id and record.session_id.display_name:
                parts.append(record.session_id.display_name)
            if record.original_teacher_id and record.new_teacher_id:
                parts.append(
                    f"{record.original_teacher_id.name} → {record.new_teacher_id.name}"
                )
            if record.replaced_at:
                date_str = fields.Datetime.to_string(record.replaced_at)
                parts.append(date_str[:16])  # YYYY-MM-DD HH:MM
            record.display_name = ' | '.join(parts) if parts else _('Reemplazo de Docente')

    @api.model
    def create_log(self, session_id, original_teacher_id, new_teacher_id, reason, 
                   replacement_type='single', notes=None):
        """
        Crea un registro de log de reemplazo.
        
        Args:
            session_id: ID de la sesión afectada
            original_teacher_id: ID del docente anterior
            new_teacher_id: ID del docente nuevo
            reason: Motivo del reemplazo
            replacement_type: Tipo de reemplazo ('single', 'future', 'all', 'massive')
            notes: Notas adicionales opcionales
        
        Returns:
            Registro creado de benglish.teacher.replacement.log
        """
        return self.create({
            'session_id': session_id,
            'original_teacher_id': original_teacher_id,
            'new_teacher_id': new_teacher_id,
            'replacement_reason': reason,
            'replacement_type': replacement_type,
            'notes': notes,
        })

    def action_view_session(self):
        """Abre la sesión relacionada."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sesión'),
            'res_model': 'benglish.class.session',
            'res_id': self.session_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
