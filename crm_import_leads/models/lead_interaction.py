from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import format_datetime
import logging

_logger = logging.getLogger(__name__)


class LeadInteraction(models.Model):
    """Modelo para registrar interacciones con leads (llamadas, emails, reuniones, etc.)"""
    _name = 'lead.interaction'
    _description = 'Interacción con Lead'
    _order = 'date desc'

    # Campos principales
    lead_id = fields.Many2one(
        'crm.lead',
        string='Lead',
        required=True,
        ondelete='cascade',
        help='Lead asociado a esta interacción'
    )
    
    date = fields.Datetime(
        string='Fecha y Hora',
        default=fields.Datetime.now,
        required=True,
        help='Fecha y hora de la interacción'
    )

    timeline_end = fields.Datetime(
        string='Fin estimado',
        compute='_compute_timeline_end',
        store=True,
        help='Fecha de finalización para representar la interacción en la línea de tiempo'
    )
    
    type = fields.Selection([
        ('call', 'Llamada'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Correo'),
        ('meeting', 'Reunión'),
        ('sms', 'SMS'),
        ('note', 'Nota'),
        ('other', 'Otro'),
    ], string='Tipo de Contacto', required=True, default='call',
       help='Tipo de interacción realizada')
    
    result = fields.Selection([
        ('contacted', 'Contactado'),
        ('no_answer', 'Sin respuesta'),
        ('follow_up', 'Seguimiento'),
        ('meeting_scheduled', 'Reunión programada'),
        ('interested', 'Interesado'),
        ('not_interested', 'No interesado'),
        ('callback', 'Devolver llamada'),
        ('pending', 'Pendiente'),
    ], string='Resultado', required=True, default='pending',
       help='Resultado de la interacción')
    
    notes = fields.Text(
        string='Observaciones',
        help='Notas detalladas de la interacción'
    )
    
    # Campos de auditoría
    user_id = fields.Many2one(
        'res.users',
        string='Registrado por',
        default=lambda self: self.env.user,
        readonly=True,
        help='Usuario que registró la interacción'
    )
    
    create_date = fields.Datetime(readonly=True)
    write_date = fields.Datetime(readonly=True)
    
    # Campos computados para vista kanban
    type_display = fields.Char(
        string='Tipo',
        compute='_compute_type_display',
        help='Visualización del tipo de interacción'
    )
    
    result_display = fields.Char(
        string='Resultado',
        compute='_compute_result_display',
        help='Visualización del resultado'
    )
    
    days_ago = fields.Char(
        string='Hace',
        compute='_compute_days_ago',
        help='Cuántos días hace de la interacción'
    )

    @api.depends('type')
    def _compute_type_display(self):
        """Convierte el tipo en un icono + texto"""
        type_icons = {
            'call': '📞 Llamada',
            'whatsapp': '💬 WhatsApp',
            'email': '📧 Correo',
            'meeting': '📅 Reunión',
            'sms': '💭 SMS',
            'note': '📝 Nota',
            'other': '🔔 Otro',
        }
        for interaction in self:
            interaction.type_display = type_icons.get(interaction.type, interaction.type)

    @api.depends('result')
    def _compute_result_display(self):
        """Convierte el resultado en un icono + texto"""
        result_icons = {
            'contacted': '✅ Contactado',
            'no_answer': '❌ Sin respuesta',
            'follow_up': '⏰ Seguimiento',
            'meeting_scheduled': '📅 Reunión programada',
            'interested': '🎯 Interesado',
            'not_interested': '🚫 No interesado',
            'callback': '📱 Devolver llamada',
            'pending': '⏳ Pendiente',
        }
        for interaction in self:
            interaction.result_display = result_icons.get(interaction.result, interaction.result)

    @api.depends('date')
    def _compute_days_ago(self):
        """Calcula cuántos días hace de la interacción"""
        now = fields.Datetime.now()
        for interaction in self:
            if not interaction.date:
                interaction.days_ago = 'N/A'
                continue
            
            delta = now - interaction.date
            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            
            if days > 0:
                interaction.days_ago = f'Hace {days}d'
            elif hours > 0:
                interaction.days_ago = f'Hace {hours}h'
            elif minutes > 0:
                interaction.days_ago = f'Hace {minutes}m'
            else:
                interaction.days_ago = 'Ahora mismo'

    @api.depends('date')
    def _compute_timeline_end(self):
        """Define un rango mínimo para representar la interacción en la vista timeline"""
        for interaction in self:
            interaction.timeline_end = interaction.date + timedelta(hours=1) if interaction.date else interaction.date

    def action_view_lead(self):
        """Navega al lead asociado"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Override create para log"""
        records = super().create(vals_list)
        for record in records:
            _logger.info(f'Interacción creada: {record.type_display} con lead {record.lead_id.name}')
        return records

    def write(self, vals):
        """Override write para log"""
        result = super().write(vals)
        for record in self:
            _logger.info(f'Interacción actualizada: {record.type_display} para lead {record.lead_id.name}')
        return result

    def unlink(self):
        """Override unlink para log"""
        for record in self:
            _logger.info(f'Interacción eliminada: {record.type_display} de lead {record.lead_id.name}')
        return super().unlink()
