# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime


class WhatsAppMessage(models.Model):
    _name = 'whatsapp.message'
    _description = 'WhatsApp Message'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Subject', required=True, tracking=True)
    lead_id = fields.Many2one('crm.lead', string='Lead/Opportunity', ondelete='cascade', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Contact', tracking=True)
    phone = fields.Char('Phone Number', required=True, tracking=True)
    message = fields.Text('Message', required=True, tracking=True)
    direction = fields.Selection([
        ('outgoing', 'Outgoing'),
        ('incoming', 'Incoming')
    ], string='Direction', default='outgoing', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed')
    ], string='Status', default='draft', required=True, tracking=True)
    template_id = fields.Many2one('whatsapp.template', string='Template')
    gateway_id = fields.Many2one('whatsapp.gateway', string='Gateway', required=True)
    external_id = fields.Char('External Message ID', help='ID from WhatsApp API')
    error_message = fields.Text('Error Message')
    sent_date = fields.Datetime('Sent Date')
    delivered_date = fields.Datetime('Delivered Date')
    read_date = fields.Datetime('Read Date')

    def action_send(self):
        """Send WhatsApp message via gateway"""
        for rec in self:
            if rec.state != 'draft':
                continue
            
            try:
                # Call gateway to send message
                result = rec.gateway_id.send_message(
                    phone=rec.phone,
                    message=rec.message
                )
                
                if result.get('success'):
                    rec.write({
                        'state': 'sent',
                        'sent_date': fields.Datetime.now(),
                        'external_id': result.get('message_id')
                    })
                    
                    # Log in chatter if related to lead
                    if rec.lead_id:
                        rec.lead_id.message_post(
                            body=f"WhatsApp enviado a {rec.phone}: {rec.message}",
                            subject="WhatsApp Sent",
                            message_type='comment'
                        )
                else:
                    rec.write({
                        'state': 'failed',
                        'error_message': result.get('error', 'Unknown error')
                    })
            except Exception as e:
                rec.write({
                    'state': 'failed',
                    'error_message': str(e)
                })

    def update_status(self, external_id, status):
        """Update message status from webhook"""
        message = self.search([('external_id', '=', external_id)], limit=1)
        if message:
            vals = {'state': status}
            if status == 'delivered':
                vals['delivered_date'] = fields.Datetime.now()
            elif status == 'read':
                vals['read_date'] = fields.Datetime.now()
            message.write(vals)

    def action_view_lead(self):
        """Open related lead"""
        self.ensure_one()
        return {
            'name': 'Lead',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class WhatsAppTemplate(models.Model):
    _name = 'whatsapp.template'
    _description = 'WhatsApp Message Template'
    _order = 'name'

    name = fields.Char('Template Name', required=True)
    code = fields.Char('Code', help='Unique code for template')
    message = fields.Text('Message Template', required=True, help='Use {{field_name}} for variables')
    active = fields.Boolean('Active', default=True)
    template_type = fields.Selection([
        ('welcome', 'Welcome'),
        ('followup', 'Follow Up'),
        ('reminder', 'Reminder'),
        ('custom', 'Custom')
    ], string='Type', default='custom')
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Template code must be unique!')
    ]

    def render_template(self, lead):
        """Render template with lead data"""
        self.ensure_one()
        message = self.message
        
        # Replace variables
        replacements = {
            '{{name}}': lead.contact_name or lead.partner_id.name or '',
            '{{company}}': lead.partner_name or '',
            '{{email}}': lead.email_from or '',
            '{{phone}}': lead.phone or lead.mobile or '',
            '{{user}}': lead.user_id.name or '',
        }
        
        for key, value in replacements.items():
            message = message.replace(key, value)
        
        return message


class WhatsAppGateway(models.Model):
    _name = 'whatsapp.gateway'
    _description = 'WhatsApp Gateway Configuration'

    name = fields.Char('Gateway Name', required=True)
    provider = fields.Selection([
        ('twilio', 'Twilio'),
        ('whatsapp_business', 'WhatsApp Business API'),
        ('custom', 'Custom API')
    ], string='Provider', required=True, default='twilio')
    api_url = fields.Char('API URL', required=True)
    api_key = fields.Char('API Key')
    api_secret = fields.Char('API Secret')
    phone_number = fields.Char('WhatsApp Number', help='Your WhatsApp business number')
    active = fields.Boolean('Active', default=True)
    webhook_url = fields.Char('Webhook URL', compute='_compute_webhook_url')

    def _compute_webhook_url(self):
        """Compute webhook URL without depending on id field"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec._origin.id:
                rec.webhook_url = f"{base_url}/whatsapp/webhook/{rec._origin.id}"
            else:
                rec.webhook_url = ''

    def send_message(self, phone, message):
        """Send message via gateway API"""
        self.ensure_one()
        
        if not self.active:
            return {'success': False, 'error': 'Gateway is not active'}
        
        try:
            import requests
            
            if self.provider == 'twilio':
                return self._send_twilio(phone, message)
            elif self.provider == 'whatsapp_business':
                return self._send_whatsapp_business(phone, message)
            else:
                return self._send_custom(phone, message)
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _send_twilio(self, phone, message):
        """Send via Twilio API"""
        import requests
        from requests.auth import HTTPBasicAuth
        
        url = f"{self.api_url}/Messages.json"
        auth = HTTPBasicAuth(self.api_key, self.api_secret)
        
        data = {
            'From': f'whatsapp:{self.phone_number}',
            'To': f'whatsapp:{phone}',
            'Body': message
        }
        
        response = requests.post(url, data=data, auth=auth)
        
        if response.status_code == 201:
            result = response.json()
            return {
                'success': True,
                'message_id': result.get('sid')
            }
        else:
            return {
                'success': False,
                'error': response.text
            }

    def _send_whatsapp_business(self, phone, message):
        """Send via WhatsApp Business API"""
        import requests
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'messaging_product': 'whatsapp',
            'to': phone,
            'type': 'text',
            'text': {'body': message}
        }
        
        response = requests.post(self.api_url, json=data, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'message_id': result.get('messages', [{}])[0].get('id')
            }
        else:
            return {
                'success': False,
                'error': response.text
            }

    def _send_custom(self, phone, message):
        """Send via custom API"""
        import requests
        
        headers = {'Authorization': f'Bearer {self.api_key}'}
        data = {
            'phone': phone,
            'message': message,
            'api_secret': self.api_secret
        }
        
        response = requests.post(self.api_url, json=data, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'message_id': result.get('message_id')
            }
        else:
            return {
                'success': False,
                'error': response.text
            }
