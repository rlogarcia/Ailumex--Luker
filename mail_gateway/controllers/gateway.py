# Copyright 2024 Dixmit
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import json
import logging

from odoo.http import Controller, request, route

from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context

_logger = logging.getLogger(__name__)


class GatewayController(Controller):
    @route(
        "/gateway/<string:usage>/<string:token>/update",
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
    )
    @add_guest_to_context
    def post_update(self, usage, token, *args, **kwargs):
        _logger.info(f"📨 Gateway webhook received: usage={usage}, token={token}, method={request.httprequest.method}")
        
        if request.httprequest.method == "GET":
            # WhatsApp/Meta webhook verification
            _logger.info(f"🔍 GET verification request - kwargs: {kwargs}")
            
            # Try to find gateway in "pending" state first (initial verification)
            bot_data = request.env["mail.gateway"]._get_gateway(
                token, gateway_type=usage, state="pending"
            )
            
            # If not found in pending, try integrated state (re-verification)
            if not bot_data:
                _logger.info(f"⚠️ Gateway not found in 'pending' state, trying 'integrated'")
                bot_data = request.env["mail.gateway"]._get_gateway(
                    token, gateway_type=usage, state="integrated"
                )
            
            # Still not found? Try direct search by webhook_key
            if not bot_data:
                _logger.info(f"⚠️ Gateway not found in cache, searching directly...")
                gateway = request.env["mail.gateway"].sudo().search([
                    ("webhook_key", "=", token),
                    ("gateway_type", "=", usage),
                ], limit=1)
                if gateway:
                    bot_data = gateway._get_gateway_data()
                    _logger.info(f"✅ Gateway found by direct search: {gateway.name}")
            
            if not bot_data:
                _logger.error(f"❌ No gateway found for token={token}, usage={usage}")
                # Return a proper 403 response instead of empty JSON
                return request.make_response(
                    "Gateway not found",
                    headers=[("Content-Type", "text/plain")],
                    status=404,
                )
            
            _logger.info(f"✅ Gateway found: bot_data={bot_data}")
            
            # Delegate to the specific gateway type handler
            result = (
                request.env[f"mail.gateway.{usage}"]
                .with_user(bot_data["webhook_user_id"])
                .with_company(bot_data["company_id"])
                ._receive_get_update(bot_data, request, **kwargs)
            )
            
            # If handler returns None, return proper error
            if result is None:
                _logger.warning("⚠️ Handler returned None, verification failed")
                return request.make_response(
                    "Verification failed",
                    headers=[("Content-Type", "text/plain")],
                    status=403,
                )
            
            return result
            
        # Handle POST request (incoming messages/events)
        bot_data = request.env["mail.gateway"]._get_gateway(
            token, gateway_type=usage, state="integrated"
        )
        if not bot_data:
            _logger.warning(
                "Gateway was not found for token %s with usage %s", token, usage
            )
            return request.make_response(
                json.dumps({}),
                [
                    ("Content-Type", "application/json"),
                ],
            )
        charset = (
            hasattr(request.httprequest, "charset")
            and request.httprequest.charset
            or "utf-8"
        )
        jsonrequest = json.loads(request.httprequest.get_data().decode(charset))
        dispatcher = (
            request.env[f"mail.gateway.{usage}"]
            .with_user(bot_data["webhook_user_id"])
            .with_context(no_gateway_notification=True)
        )
        if not dispatcher._verify_update(bot_data, jsonrequest):
            _logger.warning(
                "Message could not be verified for token %s with usage %s", token, usage
            )
            return request.make_response(
                json.dumps({}),
                [
                    ("Content-Type", "application/json"),
                ],
            )
        _logger.debug(
            "Received message for token %s with usage %s: %s",
            token,
            usage,
            json.dumps(jsonrequest),
        )
        gateway = dispatcher.env["mail.gateway"].browse(bot_data["id"])
        dispatcher._receive_update(gateway, jsonrequest)
        return request.make_response(
            json.dumps({}),
            [
                ("Content-Type", "application/json"),
            ],
        )
