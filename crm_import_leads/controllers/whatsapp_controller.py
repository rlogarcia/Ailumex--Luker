# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class WhatsAppController(http.Controller):

    @http.route(
        "/whatsapp/webhook/<int:gateway_id>",
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
    )
    def webhook(self, gateway_id, **kwargs):
        """Webhook to receive WhatsApp messages and status updates"""
        try:
            # Handle GET request (webhook verification)
            if request.httprequest.method == "GET":
                _logger.info(
                    f"WhatsApp webhook verification GET request for gateway {gateway_id}"
                )
                # Meta/WhatsApp verification
                hub_mode = kwargs.get("hub.mode")
                hub_verify_token = kwargs.get("hub.verify_token")
                hub_challenge = kwargs.get("hub.challenge")

                if hub_mode == "subscribe":
                    gateway = request.env["whatsapp.gateway"].sudo().browse(gateway_id)
                    if gateway.exists() and hub_verify_token == gateway.verify_token:
                        _logger.info(
                            f"Webhook verified successfully for gateway {gateway_id}"
                        )
                        return hub_challenge or "OK"
                    else:
                        _logger.warning(
                            f"Webhook verification failed for gateway {gateway_id}"
                        )
                        return request.make_response("Verification failed", status=403)

                return "OK"

            # Handle POST request (incoming messages)
            data = (
                json.loads(request.httprequest.data.decode("utf-8"))
                if request.httprequest.data
                else {}
            )
            _logger.info(f"WhatsApp webhook received POST: {data}")

            # Parse webhook based on provider
            gateway = request.env["whatsapp.gateway"].sudo().browse(gateway_id)

            if not gateway.exists():
                return request.make_json_response(
                    {"status": "error", "message": "Gateway not found"}, status=404
                )

            # Handle incoming message
            if data.get("type") == "message":
                self._handle_incoming_message(gateway, data)

            # Handle status update
            elif data.get("type") == "status":
                self._handle_status_update(data)

            return request.make_json_response({"status": "success"})

        except Exception as e:
            _logger.error(f"WhatsApp webhook error: {str(e)}", exc_info=True)
            return request.make_json_response(
                {"status": "error", "message": str(e)}, status=500
            )

    def _handle_incoming_message(self, gateway, data):
        """Handle incoming WhatsApp message"""
        phone = data.get("from")
        message_text = data.get("message", {}).get("text", "")
        external_id = data.get("message_id")

        # Find lead by phone
        Lead = request.env["crm.lead"].sudo()
        lead = Lead.search(
            ["|", ("phone", "ilike", phone), ("mobile", "ilike", phone)], limit=1
        )

        # Create message record
        whatsapp_msg = (
            request.env["whatsapp.message"]
            .sudo()
            .create(
                {
                    "name": f"WhatsApp from {phone}",
                    "lead_id": lead.id if lead else False,
                    "phone": phone,
                    "message": message_text,
                    "direction": "incoming",
                    "state": "delivered",
                    "gateway_id": gateway.id,
                    "external_id": external_id,
                }
            )
        )

        # Log in lead chatter
        if lead:
            lead.message_post(
                body=f"WhatsApp recibido de {phone}: {message_text}",
                subject="WhatsApp Received",
                message_type="comment",
            )

    def _handle_status_update(self, data):
        """Handle message status update"""
        external_id = data.get("message_id")
        status = data.get("status")  # sent, delivered, read, failed

        if external_id and status:
            message = (
                request.env["whatsapp.message"]
                .sudo()
                .search([("external_id", "=", external_id)], limit=1)
            )

            if message:
                message.update_status(external_id, status)

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
