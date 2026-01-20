# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class WhatsAppController(http.Controller):

    @http.route('/whatsapp/webhook/<int:gateway_id>', type='json', auth='public', methods=['POST'], csrf=False)
    def webhook(self, gateway_id, **kwargs):
        """Webhook to receive WhatsApp messages and status updates"""
        try:
            data = request.jsonrequest
            _logger.info(f"WhatsApp webhook received: {data}")
            
            # Parse webhook based on provider
            gateway = request.env['whatsapp.gateway'].sudo().browse(gateway_id)
            
            if not gateway.exists():
                return {'status': 'error', 'message': 'Gateway not found'}
            
            # Handle incoming message
            if data.get('type') == 'message':
                self._handle_incoming_message(gateway, data)
            
            # Handle status update
            elif data.get('type') == 'status':
                self._handle_status_update(data)
            
            return {'status': 'success'}
            
        except Exception as e:
            _logger.error(f"WhatsApp webhook error: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _handle_incoming_message(self, gateway, data):
        """Handle incoming WhatsApp message"""
        phone = data.get('from')
        message_text = data.get('message', {}).get('text', '')
        external_id = data.get('message_id')
        
        # Find lead by phone
        Lead = request.env['crm.lead'].sudo()
        lead = Lead.search([
            '|', ('phone', 'ilike', phone),
            ('mobile', 'ilike', phone)
        ], limit=1)
        
        # Create message record
        whatsapp_msg = request.env['whatsapp.message'].sudo().create({
            'name': f"WhatsApp from {phone}",
            'lead_id': lead.id if lead else False,
            'phone': phone,
            'message': message_text,
            'direction': 'incoming',
            'state': 'delivered',
            'gateway_id': gateway.id,
            'external_id': external_id,
        })
        
        # Log in lead chatter
        if lead:
            lead.message_post(
                body=f"WhatsApp recibido de {phone}: {message_text}",
                subject="WhatsApp Received",
                message_type='comment'
            )

    def _handle_status_update(self, data):
        """Handle message status update"""
        external_id = data.get('message_id')
        status = data.get('status')  # sent, delivered, read, failed
        
        if external_id and status:
            message = request.env['whatsapp.message'].sudo().search([
                ('external_id', '=', external_id)
            ], limit=1)
            
            if message:
                message.update_status(external_id, status)

    @http.route('/whatsapp/send', type='json', auth='user', methods=['POST'])
    def send_message(self, **kwargs):
        """API endpoint to send WhatsApp message"""
        try:
            lead_id = kwargs.get('lead_id')
            phone = kwargs.get('phone')
            message = kwargs.get('message')
            gateway_id = kwargs.get('gateway_id')
            
            if not all([phone, message, gateway_id]):
                return {'success': False, 'error': 'Missing required parameters'}
            
            # Create and send message
            whatsapp_msg = request.env['whatsapp.message'].create({
                'name': f"WhatsApp to {phone}",
                'lead_id': lead_id,
                'phone': phone,
                'message': message,
                'gateway_id': gateway_id,
                'direction': 'outgoing',
            })
            
            whatsapp_msg.action_send()
            
            return {
                'success': True,
                'message_id': whatsapp_msg.id,
                'state': whatsapp_msg.state
            }
            
        except Exception as e:
            _logger.error(f"Error sending WhatsApp: {str(e)}")
            return {'success': False, 'error': str(e)}
