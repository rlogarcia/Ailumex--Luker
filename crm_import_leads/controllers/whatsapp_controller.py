# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class WhatsAppController(http.Controller):
    
    # ============================================================
    # EMERGENCY WEBHOOK - Ruta directa para verificación Meta
    # Esta ruta NO depende del cache y funciona inmediatamente
    # ============================================================
    @http.route(
        "/gateway/whatsapp/odoo/update",
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
    )
    def meta_webhook_direct(self, **kwargs):
        """Direct WhatsApp webhook handler - bypasses cache issues.
        
        URL: /gateway/whatsapp/odoo/update
        This matches your Meta webhook URL exactly.
        """
        try:
            # =============================================
            # HANDLE GET - Meta Webhook Verification
            # =============================================
            if request.httprequest.method == "GET":
                hub_mode = kwargs.get("hub.mode")
                hub_verify_token = kwargs.get("hub.verify_token")
                hub_challenge = kwargs.get("hub.challenge")
                
                _logger.info("=" * 60)
                _logger.info("🔍 META WEBHOOK VERIFICATION REQUEST")
                _logger.info(f"   hub.mode: {hub_mode}")
                _logger.info(f"   hub.verify_token: {hub_verify_token}")
                _logger.info(f"   hub.challenge: {hub_challenge}")
                _logger.info("=" * 60)
                
                # Validate mode
                if hub_mode != "subscribe":
                    _logger.warning(f"❌ Invalid hub.mode: {hub_mode}")
                    return request.make_response(
                        "Invalid mode",
                        headers=[("Content-Type", "text/plain")],
                        status=403
                    )
                
                # Validate challenge exists
                if not hub_challenge:
                    _logger.warning("❌ Missing hub.challenge")
                    return request.make_response(
                        "Missing challenge",
                        headers=[("Content-Type", "text/plain")],
                        status=400
                    )
                
                # Find the WhatsApp gateway
                Gateway = request.env["mail.gateway"].sudo()
                gateway = Gateway.search([
                    ("gateway_type", "=", "whatsapp")
                ], limit=1)
                
                if not gateway:
                    _logger.error("❌ No WhatsApp gateway configured in Odoo")
                    return request.make_response(
                        "No gateway configured",
                        headers=[("Content-Type", "text/plain")],
                        status=404
                    )
                
                _logger.info(f"📦 Gateway found: {gateway.name} (ID: {gateway.id})")
                _logger.info(f"   webhook_key: {gateway.webhook_key}")
                _logger.info(f"   whatsapp_security_key: {gateway.whatsapp_security_key}")
                
                # Validate verify_token against configured values
                expected_tokens = []
                if gateway.webhook_key:
                    expected_tokens.append(gateway.webhook_key)
                if hasattr(gateway, 'whatsapp_security_key') and gateway.whatsapp_security_key:
                    expected_tokens.append(gateway.whatsapp_security_key)
                
                # ALSO accept "odoo" as hardcoded fallback for emergency
                if "odoo" not in expected_tokens:
                    expected_tokens.append("odoo")
                
                _logger.info(f"   Expected tokens: {expected_tokens}")
                
                if hub_verify_token not in expected_tokens:
                    _logger.warning(f"❌ Token mismatch! Received: '{hub_verify_token}', Expected: {expected_tokens}")
                    return request.make_response(
                        "Invalid verify token",
                        headers=[("Content-Type", "text/plain")],
                        status=403
                    )
                
                # SUCCESS! Update gateway state
                try:
                    gateway.integrated_webhook_state = "integrated"
                    _logger.info("✅ Gateway state updated to 'integrated'")
                except Exception as e:
                    _logger.warning(f"⚠️ Could not update gateway state: {e}")
                
                # CRITICAL: Return challenge as plain text
                _logger.info(f"✅ VERIFICATION SUCCESS - Returning challenge: {hub_challenge}")
                
                response = request.make_response(
                    str(hub_challenge),
                    headers=[("Content-Type", "text/plain; charset=utf-8")]
                )
                response.status_code = 200
                return response
            
            # =============================================
            # HANDLE POST - Incoming Messages/Events
            # =============================================
            _logger.info("=" * 60)
            _logger.info("📨 WHATSAPP INCOMING MESSAGE (POST)")
            _logger.info("=" * 60)
            
            # Log headers for debugging
            _logger.info(f"   Headers: {dict(request.httprequest.headers)}")
            
            data = {}
            raw_data = request.httprequest.data
            if raw_data:
                try:
                    data = json.loads(raw_data.decode("utf-8"))
                    _logger.info(f"📦 Received data:\n{json.dumps(data, indent=2)}")
                except json.JSONDecodeError as e:
                    _logger.error(f"❌ Invalid JSON in POST body: {e}")
                    return request.make_response(
                        json.dumps({"status": "error", "message": "Invalid JSON"}),
                        headers=[("Content-Type", "application/json")],
                        status=400
                    )
            else:
                _logger.warning("⚠️ Empty POST body received")
                return request.make_response(
                    json.dumps({"status": "ok"}),
                    headers=[("Content-Type", "application/json")]
                )
            
            # Find gateway
            Gateway = request.env["mail.gateway"].sudo()
            gateway = Gateway.search([("gateway_type", "=", "whatsapp")], limit=1)
            
            if not gateway:
                _logger.error("❌ No WhatsApp gateway found")
                return request.make_response(
                    json.dumps({"status": "error", "message": "Gateway not found"}),
                    headers=[("Content-Type", "application/json")],
                    status=404
                )
            
            _logger.info(f"✅ Gateway: {gateway.name} (ID: {gateway.id})")
            _logger.info(f"   Members: {gateway.member_ids.mapped('name')}")
            _logger.info(f"   Webhook User: {gateway.webhook_user_id.name}")
            
            # Verify gateway has members configured
            if not gateway.member_ids:
                _logger.error("❌ CRITICAL: Gateway has NO members configured!")
                _logger.error("   Go to: Settings > Technical > Mail Gateways")
                _logger.error("   Add users in the 'Members' tab")
            
            # Process the webhook data directly (bypass signature verification for now)
            try:
                # Extract messages from Meta's webhook format
                if "entry" in data:
                    for entry in data.get("entry", []):
                        for change in entry.get("changes", []):
                            if change.get("field") == "messages":
                                value = change.get("value", {})
                                messages = value.get("messages", [])
                                statuses = value.get("statuses", [])
                                
                                _logger.info(f"📩 Found {len(messages)} messages, {len(statuses)} statuses")
                                
                                # Process incoming messages
                                for message in messages:
                                    _logger.info(f"📱 Processing message from: {message.get('from')}")
                                    _logger.info(f"   Type: {message.get('type')}")
                                    _logger.info(f"   Content: {message}")
                                    
                                    try:
                                        # Use the mail_gateway_whatsapp service with proper context
                                        whatsapp_service = (
                                            request.env["mail.gateway.whatsapp"]
                                            .sudo()
                                            .with_user(gateway.webhook_user_id.id if gateway.webhook_user_id else 1)
                                            .with_company(gateway.company_id.id if gateway.company_id else 1)
                                            .with_context(no_gateway_notification=False)
                                        )
                                        
                                        # Get or create the chat channel
                                        _logger.info(f"🔍 Getting or creating channel for: {message['from']}")
                                        chat = whatsapp_service._get_channel(
                                            gateway, 
                                            message["from"], 
                                            value, 
                                            force_create=True
                                        )
                                        
                                        if chat:
                                            _logger.info(f"💬 Chat channel created/found:")
                                            _logger.info(f"   Name: {chat.name}")
                                            _logger.info(f"   ID: {chat.id}")
                                            _logger.info(f"   Type: {chat.channel_type}")
                                            _logger.info(f"   Members: {chat.channel_member_ids.mapped('partner_id.name')}")
                                            
                                            # Process the message
                                            whatsapp_service._process_update(chat, message, value)
                                            
                                            # Ensure notifications are created
                                            chat.channel_member_ids.filtered(
                                                lambda m: not m.is_self
                                            )._set_new_message_separator()
                                            
                                            _logger.info(f"✅ Message processed and posted to channel!")
                                            
                                            # POST TO LEAD CHATTER
                                            self._post_message_to_lead_chatter(
                                                message, value, direction='incoming'
                                            )
                                        else:
                                            _logger.warning(f"⚠️ Could not get/create chat channel")
                                            
                                    except Exception as e:
                                        _logger.error(f"❌ Error processing message: {e}", exc_info=True)
                                
                                # Process status updates (delivered, read, etc.)
                                for status in statuses:
                                    _logger.info(f"📊 Status update: {status.get('status')} for {status.get('recipient_id')}")
                                    # TODO: Update message status in Odoo
                else:
                    _logger.warning(f"⚠️ Unexpected webhook format: {list(data.keys())}")
                    
            except Exception as e:
                _logger.error(f"❌ Error processing webhook: {e}", exc_info=True)
            
            # Always return 200 OK to Meta (they retry on errors)
            _logger.info("✅ Returning 200 OK to Meta")
            return request.make_response(
                json.dumps({"status": "ok"}),
                headers=[("Content-Type", "application/json")]
            )
            
        except Exception as e:
            _logger.error(f"❌ Webhook error: {str(e)}", exc_info=True)
            return request.make_response(
                json.dumps({"status": "error", "message": str(e)}),
                headers=[("Content-Type", "application/json")],
                status=500
            )

    def _post_message_to_lead_chatter(self, message, value, direction='incoming'):
        """
        Registra el mensaje de WhatsApp en el chatter del Lead correspondiente.
        Busca el lead por número de teléfono y crea uno si no existe.
        """
        try:
            phone = message.get('from', '')
            if not phone:
                return
            
            # Obtener nombre del contacto
            contact_name = phone
            for contact in value.get('contacts', []):
                if contact.get('wa_id') == phone:
                    contact_name = contact.get('profile', {}).get('name', phone)
                    break
            
            # Obtener texto del mensaje
            msg_text = ""
            msg_type = message.get('type', 'text')
            
            if msg_type == 'text':
                msg_text = message.get('text', {}).get('body', '')
            elif msg_type == 'image':
                msg_text = "📷 [Imagen recibida]"
            elif msg_type == 'audio':
                msg_text = "🎵 [Audio recibido]"
            elif msg_type == 'video':
                msg_text = "🎬 [Video recibido]"
            elif msg_type == 'document':
                doc_name = message.get('document', {}).get('filename', 'documento')
                msg_text = f"📄 [Documento: {doc_name}]"
            elif msg_type == 'location':
                msg_text = "📍 [Ubicación compartida]"
            elif msg_type == 'sticker':
                msg_text = "🎭 [Sticker]"
            else:
                msg_text = f"[Mensaje tipo: {msg_type}]"
            
            # Buscar lead por teléfono
            phone_clean = phone.lstrip('+').replace(' ', '').replace('-', '')
            
            Lead = request.env['crm.lead'].sudo()
            lead = Lead.search([
                '|', '|', '|',
                ('phone', 'ilike', phone_clean[-10:]),
                ('mobile', 'ilike', phone_clean[-10:]),
                ('partner_id.phone', 'ilike', phone_clean[-10:]),
                ('partner_id.mobile', 'ilike', phone_clean[-10:]),
            ], limit=1)
            
            if not lead:
                # Crear nuevo lead
                _logger.info(f"📝 Creating new lead for {contact_name} ({phone})")
                lead = Lead.create({
                    'name': f"{contact_name} - WhatsApp",
                    'phone': phone,
                    'contact_name': contact_name,
                    'description': 'Lead creado automáticamente desde WhatsApp',
                    'type': 'lead',
                })
            
            if lead:
                # Formato del mensaje para el chatter
                if direction == 'incoming':
                    body = f"""
                    <div style="background-color: #dcf8c6; padding: 10px; border-radius: 8px; margin: 5px 0; border-left: 4px solid #25D366;">
                        <strong>📱 WhatsApp recibido de {contact_name}</strong><br/>
                        <small style="color: #666;">Tel: {phone}</small><br/><br/>
                        <p style="margin: 0;">{msg_text}</p>
                    </div>
                    """
                else:
                    body = f"""
                    <div style="background-color: #e3f2fd; padding: 10px; border-radius: 8px; margin: 5px 0; border-left: 4px solid #1976d2;">
                        <strong>📤 WhatsApp enviado a {contact_name}</strong><br/>
                        <small style="color: #666;">Tel: {phone}</small><br/><br/>
                        <p style="margin: 0;">{msg_text}</p>
                    </div>
                    """
                
                lead.message_post(
                    body=body,
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )
                _logger.info(f"✅ Message posted to lead {lead.name} chatter")
                
        except Exception as e:
            _logger.error(f"❌ Error posting to lead chatter: {e}", exc_info=True)

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

                # Find gateway to verify token against
                Gateway = request.env["mail.gateway"].sudo()
                gateway = False
                if gateway_id:
                    gateway = Gateway.browse(gateway_id)
                else:
                    # Try to match webhook_key or whatsapp_security_key
                    if hub_verify_token:
                        gateway = Gateway.search(
                            [
                                "|",
                                ("webhook_key", "=", hub_verify_token),
                                ("whatsapp_security_key", "=", hub_verify_token),
                            ],
                            limit=1,
                        )
                    if not gateway:
                        # fallback to any whatsapp gateway
                        gateway = Gateway.search(
                            [("gateway_type", "=", "whatsapp")], limit=1
                        )

                if (
                    hub_mode == "subscribe"
                    and hub_challenge
                    and gateway
                    and gateway.exists()
                ):
                    # Accept verification only when token matches configured one (if provided)
                    if not hub_verify_token or hub_verify_token in (
                        gateway.webhook_key,
                        gateway.whatsapp_security_key,
                    ):
                        _logger.info(
                            "✅ Webhook verification successful - returning challenge"
                        )
                        return hub_challenge
                    _logger.warning("⚠️ Webhook verification token mismatch")
                    return "Forbidden"

                _logger.warning("⚠️ Webhook verification incomplete or no gateway found")
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

            # Verify POST signature (if configured) using mail.gateway.whatsapp helper
            try:
                ok_sig = True
                # If gateway has a webhook_secret, verify request signature
                # If the gateway forwarded the signature header under a different name
                # (for example when passing through a proxy), copy it into the environ
                # key that mail_gateway_whatsapp expects: HTTP_X_HUB_SIGNATURE_256
                forwarded_sig = request.httprequest.headers.get(
                    "X-Forwarded-X-Hub-Signature-256"
                ) or request.httprequest.headers.get("x-forwarded-x-hub-signature-256")
                if forwarded_sig:
                    try:
                        request.httprequest.environ["HTTP_X_HUB_SIGNATURE_256"] = (
                            forwarded_sig
                        )
                    except Exception:
                        _logger.warning(
                            "Could not copy forwarded signature into environ"
                        )

                if getattr(gateway, "webhook_secret", False):
                    ok_sig = whatsapp_service._verify_update(
                        {"webhook_secret": gateway.webhook_secret}, {}
                    )
                if not ok_sig:
                    _logger.warning("⚠️ Webhook signature verification failed")
                    return {"status": "error", "message": "Invalid signature"}

            except Exception:
                _logger.exception("Error during webhook signature verification")
                return {"status": "error", "message": "Signature verification error"}

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
