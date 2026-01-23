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

        This route receives webhooks from Meta/WhatsApp Business API and:
        1. Creates discuss.channel for inbox display (via mail_gateway_whatsapp)
        2. Logs interactions in CRM leads (via CRM integration)

        For proper inbox display, ensure:
        - Gateway has member_ids configured (users who see messages)
        - Gateway webhook_secret is configured for signature verification
        """
        try:
            # Handle GET request (webhook verification)
            if request.httprequest.method == "GET":
                _logger.info(
                    f"🔍 WhatsApp webhook verification GET request - gateway_id: {gateway_id}"
                )

                # Meta/WhatsApp verification
                hub_mode = kwargs.get("hub.mode")
                hub_verify_token = kwargs.get("hub.verify_token")
                hub_challenge = kwargs.get("hub.challenge")

                _logger.info(f"  hub.mode: {hub_mode}")
                _logger.info(f"  hub.verify_token: {hub_verify_token}")
                _logger.info(f"  hub.challenge: {hub_challenge}")

                if hub_mode == "subscribe" and hub_challenge:
                    _logger.info(
                        "✅ Webhook verification successful - returning challenge"
                    )
                    return hub_challenge

                _logger.warning("⚠️ Webhook verification incomplete")
                return "OK"

            # Handle POST request (incoming messages)
            data = (
                json.loads(request.httprequest.data.decode("utf-8"))
                if request.httprequest.data
                else {}
            )
            _logger.info(
                f"📨 WhatsApp webhook received POST data: {json.dumps(data, indent=2)}"
            )

            # Try to find gateway by ID or get default
            Gateway = request.env["mail.gateway"].sudo()

            if gateway_id:
                gateway = Gateway.browse(gateway_id)
                _logger.info(f"🔍 Looking for gateway by ID: {gateway_id}")
            else:
                # Get default WhatsApp gateway
                gateway = Gateway.search([("gateway_type", "=", "whatsapp")], limit=1)
                _logger.info(f"🔍 Looking for default WhatsApp gateway")

            if not gateway.exists():
                _logger.error("❌ No gateway found for WhatsApp webhook")
                return request.make_json_response(
                    {"status": "error", "message": "Gateway not found"}, status=404
                )

            _logger.info(f"✅ Gateway found: {gateway.name} (ID: {gateway.id})")
            _logger.info(f"   Gateway type: {gateway.gateway_type}")
            _logger.info(f"   Members: {gateway.member_ids.mapped('name')}")
            _logger.info(f"   Webhook state: {gateway.integrated_webhook_state}")

            # Delegate to mail_gateway_whatsapp for processing
            result = self._process_whatsapp_webhook(gateway, data)

            _logger.info(f"✅ Webhook processing completed: {result}")
            return request.make_json_response(result)

        except Exception as e:
            _logger.error(f"❌ WhatsApp webhook error: {str(e)}", exc_info=True)
            return request.make_json_response(
                {"status": "error", "message": str(e)}, status=500
            )

    def _process_whatsapp_webhook(self, gateway, data):
        """Process WhatsApp webhook data using mail_gateway system

        This method:
        1. Delegates to OCA mail_gateway_whatsapp to create discuss.channel and show in inbox
        2. Additionally logs the interaction in CRM leads for business logic

        Returns:
            dict: Status of processing
        """
        try:
            _logger.info(f"🔄 Processing webhook with mail.gateway.whatsapp...")

            # CRITICAL: Use the correct method from mail.gateway.whatsapp
            # The _receive_update method is called with the gateway user context
            whatsapp_service = (
                request.env["mail.gateway.whatsapp"]
                .sudo()
                .with_user(gateway.webhook_user_id.id)
                .with_context(no_gateway_notification=False)
            )

            # Process the webhook data using the standard mail_gateway method
            # This will:
            # - Create or find discuss.channel
            # - Post message to channel
            # - Create notifications
            # - Show in inbox for members
            whatsapp_service._receive_update(gateway, data)

            _logger.info(f"✅ mail.gateway.whatsapp processing completed")

            # Also handle CRM-specific logic (log in lead chatter)
            self._handle_crm_integration(gateway, data)

            return {
                "status": "success",
                "message": "Message processed and displayed in inbox",
            }

        except Exception as e:
            _logger.error(
                f"❌ Error processing WhatsApp webhook: {str(e)}", exc_info=True
            )
            return {"status": "error", "message": str(e)}

    def _handle_crm_integration(self, gateway, data):
        """Handle CRM-specific integration for WhatsApp messages

        This logs the WhatsApp interaction in the lead's chatter for business tracking,
        in addition to showing in the inbox (handled by mail_gateway_whatsapp).
        """
        try:
            _logger.info(f"🔄 Processing CRM integration...")

            # Process entries for CRM integration
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    if change.get("field") != "messages":
                        continue

                    messages = change["value"].get("messages", [])
                    _logger.info(f"   Found {len(messages)} messages to process")

                    for message in messages:
                        phone = message.get("from")
                        message_text = message.get("text", {}).get("body", "")

                        if not phone:
                            _logger.warning(
                                f"   ⚠️ Message without 'from' number, skipping"
                            )
                            continue

                        _logger.info(f"   📞 Processing message from: {phone}")
                        _logger.info(f"   💬 Message text: {message_text}")

                        # Find or create lead
                        self._find_or_create_lead(phone, message_text, gateway)

            _logger.info(f"✅ CRM integration completed")

        except Exception as e:
            _logger.warning(
                f"⚠️ CRM integration warning (non-critical): {str(e)}", exc_info=True
            )

    def _find_or_create_lead(self, phone, message_text, gateway):
        """Find existing lead and log interaction in chatter

        This logs the WhatsApp message in the lead's chatter for business tracking.
        The message also appears in inbox via the discuss.channel created by mail_gateway_whatsapp.
        """
        Lead = request.env["crm.lead"].sudo()

        # Normalize phone number for search (remove + and spaces)
        normalized_phone = phone.replace("+", "").replace(" ", "").replace("-", "")

        # Search for lead by phone (multiple patterns)
        lead = Lead.search(
            [
                "|",
                "|",
                ("phone", "ilike", phone),
                ("mobile", "ilike", phone),
                "|",
                ("phone", "ilike", normalized_phone),
                ("mobile", "ilike", normalized_phone),
            ],
            limit=1,
        )

        if lead:
            # Log interaction in lead chatter
            lead.message_post(
                body=f"<p>📱 <strong>WhatsApp recibido</strong></p><p>{message_text}</p>",
                subject="WhatsApp Received",
                message_type="comment",
            )
            _logger.info(
                f"   ✅ WhatsApp message logged in lead: {lead.name} (ID: {lead.id})"
            )
        else:
            _logger.info(
                f"   ℹ️ No lead found for phone {phone} (normalized: {normalized_phone})"
            )

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
