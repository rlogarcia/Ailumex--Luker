# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class WhatsAppController(http.Controller):

    @http.route(
        ["/whatsapp/webhook", "/whatsapp/webhook/<int:gateway_id>"],
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
    )
    def webhook(self, gateway_id=None, **kwargs):
        """Webhook to receive WhatsApp messages and status updates

        This is a compatibility route. The main route is /gateway/whatsapp/<token>/update
        managed by mail_gateway module.
        """
        try:
            # Handle GET request (webhook verification)
            if request.httprequest.method == "GET":
                _logger.info(f"WhatsApp webhook verification GET request: {kwargs}")

                # Meta/WhatsApp verification
                hub_mode = kwargs.get("hub.mode")
                hub_verify_token = kwargs.get("hub.verify_token")
                hub_challenge = kwargs.get("hub.challenge")

                _logger.info(f"Verification - mode: {hub_mode}, token: {hub_verify_token}, challenge: {hub_challenge}")

                # El token debe ser "odoo" según tu configuración en Meta
                VERIFY_TOKEN = "odoo"
                
                if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
                    _logger.info("Webhook verification SUCCESS - returning challenge")
                    response = request.make_response(hub_challenge)
                    response.status_code = 200
                    return response
                else:
                    _logger.warning(f"Webhook verification FAILED - expected token: {VERIFY_TOKEN}, got: {hub_verify_token}")
                    response = request.make_response("Invalid verification token")
                    response.status_code = 403
                    return response

            # Handle POST request (incoming messages)
            data = (
                json.loads(request.httprequest.data.decode("utf-8"))
                if request.httprequest.data
                else {}
            )
            _logger.info(f"WhatsApp webhook received POST: {data}")

            # Try to find gateway by ID or get default
            Gateway = request.env["mail.gateway"].sudo()

            if gateway_id:
                gateway = Gateway.browse(gateway_id)
            else:
                # Get default WhatsApp gateway
                gateway = Gateway.search([("gateway_type", "=", "whatsapp")], limit=1)

            if not gateway.exists():
                _logger.warning("No gateway found for WhatsApp webhook")
                return request.make_json_response(
                    {"status": "error", "message": "Gateway not found"}, status=404
                )

            # Delegate to mail_gateway_whatsapp for processing
            result = self._process_whatsapp_webhook(gateway, data)

            return request.make_json_response(result)

        except Exception as e:
            _logger.error(f"WhatsApp webhook error: {str(e)}", exc_info=True)
            return request.make_json_response(
                {"status": "error", "message": str(e)}, status=500
            )

    def _process_whatsapp_webhook(self, gateway, data):
        """Process WhatsApp webhook data using mail_gateway system"""
        try:
            # Use mail.gateway.whatsapp to process the webhook
            whatsapp_gateway = request.env["mail.gateway.whatsapp"].sudo()

            # Process the webhook data using the standard mail_gateway method
            whatsapp_gateway._receive_update(gateway, data)

            # Also handle CRM-specific logic
            self._handle_crm_integration(gateway, data)

            return {"status": "success"}

        except Exception as e:
            _logger.error(f"Error processing WhatsApp webhook: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def _handle_crm_integration(self, gateway, data):
        """Handle CRM-specific integration for WhatsApp messages"""
        try:
            # Process entries for CRM integration
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    if change.get("field") != "messages":
                        continue

                    for message in change["value"].get("messages", []):
                        phone = message.get("from")
                        message_text = message.get("text", {}).get("body", "")

                        if not phone:
                            continue

                        # Find or create lead
                        self._find_or_create_lead(phone, message_text, gateway)

        except Exception as e:
            _logger.warning(f"CRM integration warning: {str(e)}")

    def _find_or_create_lead(self, phone, message_text, gateway):
        """Find existing lead or create interaction record"""
        Lead = request.env["crm.lead"].sudo()

        # Search for lead by phone
        lead = Lead.search(
            ["|", ("phone", "ilike", phone), ("mobile", "ilike", phone)], limit=1
        )

        if lead:
            # Log interaction in lead
            lead.message_post(
                body=f"WhatsApp recibido: {message_text}",
                subject="WhatsApp Received",
                message_type="comment",
            )
            _logger.info(f"WhatsApp message logged for lead {lead.id}")
        else:
            _logger.info(f"No lead found for phone {phone}")

    @http.route("/whatsapp/n8n/incoming", type="json", auth="public", methods=["POST"], csrf=False)
    def n8n_incoming_message(self, **kwargs):
        """Recibir mensajes de WhatsApp desde n8n"""
        try:
            phone = kwargs.get("phone")
            message = kwargs.get("message")
            sender_name = kwargs.get("name", "")
            
            _logger.info(f"Mensaje de n8n - Phone: {phone}, Message: {message}")
            
            if not phone or not message:
                return {"success": False, "error": "Phone and message required"}
            
            # Buscar o crear lead
            Lead = request.env["crm.lead"].sudo()
            lead = Lead.search(["|", ("phone", "ilike", phone), ("mobile", "ilike", phone)], limit=1)
            
            if not lead:
                # Crear nuevo lead
                lead = Lead.create({
                    "name": sender_name or f"WhatsApp Lead - {phone}",
                    "phone": phone,
                    "type": "lead",
                    "description": f"Contacto inicial por WhatsApp: {message}",
                })
                _logger.info(f"Nuevo lead creado: {lead.id}")
            
            # Registrar mensaje en el lead
            lead.message_post(
                body=f"<p><strong>WhatsApp recibido:</strong></p><p>{message}</p>",
                subject="Mensaje WhatsApp",
                message_type="comment",
            )
            
            return {
                "success": True,
                "lead_id": lead.id,
                "lead_name": lead.name,
            }
            
        except Exception as e:
            _logger.error(f"Error procesando mensaje de n8n: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    @http.route("/whatsapp/send", type="json", auth="user", methods=["POST"])
    def send_message(self, **kwargs):
        """API endpoint to send WhatsApp message"""
        try:
            lead_id = kwargs.get("lead_id")
            phone = kwargs.get("phone")
            message = kwargs.get("message")
            gateway_id = kwargs.get("gateway_id")

            if not all([phone, message, gateway_id]):
                return {"success": False, "error": "Missing required parameters"}

            # Create and send message
            whatsapp_msg = request.env["whatsapp.message"].create(
                {
                    "name": f"WhatsApp to {phone}",
                    "lead_id": lead_id,
                    "phone": phone,
                    "message": message,
                    "gateway_id": gateway_id,
                    "direction": "outgoing",
                }
            )

            whatsapp_msg.action_send()

            return {
                "success": True,
                "message_id": whatsapp_msg.id,
                "state": whatsapp_msg.state,
            }

        except Exception as e:
            _logger.error(f"Error sending WhatsApp: {str(e)}")
            return {"success": False, "error": str(e)}
