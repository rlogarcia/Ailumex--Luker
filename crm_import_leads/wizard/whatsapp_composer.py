# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WhatsAppComposer(models.TransientModel):
    _name = 'whatsapp.composer'
    _description = 'WhatsApp Message Composer'

    lead_id = fields.Many2one('crm.lead', string='Lead/Opportunity', required=True)
    partner_id = fields.Many2one('res.partner', string='Contact')
    phone = fields.Char('Phone Number', required=True)
    template_id = fields.Many2one('whatsapp.template', string='Use Template')
    message = fields.Text('Message', required=True)
    gateway_id = fields.Many2one('whatsapp.gateway', string='Gateway', required=True,
                                  domain=[('active', '=', True)])

    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Load template message"""
        if self.template_id and self.lead_id:
            self.message = self.template_id.render_template(self.lead_id)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Update phone from partner"""
        if self.partner_id:
            self.phone = self.partner_id.mobile or self.partner_id.phone

    def action_send(self):
        """Send WhatsApp message and log in chatter"""
        self.ensure_one()
        
        if not self.phone:
            raise UserError(_('Please provide a phone number'))
        
        # Create WhatsApp message record
        message = self.env['whatsapp.message'].create({
            'name': f"WhatsApp to {self.partner_id.name or self.phone}",
            'lead_id': self.lead_id.id,
            'partner_id': self.partner_id.id,
            'phone': self.phone,
            'message': self.message,
            'template_id': self.template_id.id,
            'gateway_id': self.gateway_id.id,
            'direction': 'outgoing',
            'state': 'draft',
        })
        
        # Send message
        message.action_send()
        
        return {'type': 'ir.actions.act_window_close'}
