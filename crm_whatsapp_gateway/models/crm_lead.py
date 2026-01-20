# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    """
    Extiende crm.lead para integración con WhatsApp Gateway.

    Vincula leads con canales de discusión de WhatsApp.
    """

    _inherit = "crm.lead"

    gateway_channel_id = fields.Many2one(
        "discuss.channel",
        string="Canal WhatsApp",
        ondelete="set null",
        help="Canal de WhatsApp vinculado a este lead",
        domain=[("channel_type", "=", "gateway")],
    )

    whatsapp_phone = fields.Char(
        string="WhatsApp",
        compute="_compute_whatsapp_phone",
        store=True,
        help="Número de WhatsApp normalizado (E.164)",
    )

    has_whatsapp = fields.Boolean(
        string="Tiene WhatsApp",
        compute="_compute_has_whatsapp",
        search="_search_has_whatsapp",
        help="Indica si este lead tiene una conversación de WhatsApp activa",
    )

    @api.depends("mobile", "phone")
    def _compute_whatsapp_phone(self):
        """Usar mobile o phone como número de WhatsApp"""
        for lead in self:
            lead.whatsapp_phone = lead.mobile or lead.phone or False

    @api.depends("gateway_channel_id")
    def _compute_has_whatsapp(self):
        """Indica si hay canal de WhatsApp vinculado"""
        for lead in self:
            lead.has_whatsapp = bool(lead.gateway_channel_id)

    def _search_has_whatsapp(self, operator, value):
        """Búsqueda por campo computed has_whatsapp"""
        if operator == "=" and value:
            return [("gateway_channel_id", "!=", False)]
        elif operator == "=" and not value:
            return [("gateway_channel_id", "=", False)]
        elif operator == "!=" and value:
            return [("gateway_channel_id", "=", False)]
        else:
            return [("gateway_channel_id", "!=", False)]

    def action_open_whatsapp_chat(self):
        """
        Abre el canal de WhatsApp desde el lead.

        Si no existe canal, permite crear uno buscando al partner.
        """
        self.ensure_one()

        if not self.gateway_channel_id:
            # Buscar canal por número de teléfono
            channel = self._find_whatsapp_channel()

            if channel:
                self.gateway_channel_id = channel.id
            else:
                # No hay canal, informar al usuario
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("WhatsApp no disponible"),
                        "message": _(
                            "No se encontró una conversación de WhatsApp para este lead. "
                            "El cliente debe iniciar la conversación primero."
                        ),
                        "type": "warning",
                        "sticky": False,
                    },
                }

        # Abrir canal de WhatsApp
        return {
            "name": _("WhatsApp Chat"),
            "type": "ir.actions.act_window",
            "res_model": "discuss.channel",
            "res_id": self.gateway_channel_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def _find_whatsapp_channel(self):
        """
        Busca un canal de WhatsApp existente para este lead.

        Busca por número de teléfono normalizado.
        """
        if not self.whatsapp_phone:
            return False

        # Normalizar número
        normalized = self._normalize_phone_number(self.whatsapp_phone)

        if not normalized:
            return False

        # Buscar canal por gateway_channel_token
        Channel = self.env["discuss.channel"]
        channel = Channel.search(
            [
                ("channel_type", "=", "gateway"),
                ("gateway_channel_token", "=", normalized),
            ],
            limit=1,
        )

        return channel

    def _normalize_phone_number(self, phone):
        """
        Normaliza número a formato E.164.

        Reutiliza la lógica del canal.
        """
        if not phone:
            return False

        try:
            import phonenumbers

            parsed = phonenumbers.parse(phone, "CO")

            if not phonenumbers.is_valid_number(parsed):
                return False

            normalized = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )

            return normalized

        except Exception as e:
            _logger.error(f"Error normalizando número {phone}: {str(e)}")
            return False

    def action_send_whatsapp_message(self):
        """
        Abre el composer de WhatsApp desde el lead.

        Usa el wizard de mail_gateway para enviar mensaje.
        """
        self.ensure_one()

        # Verificar que exista canal de WhatsApp
        if not self.gateway_channel_id:
            # Intentar encontrar canal
            channel = self._find_whatsapp_channel()
            if channel:
                self.gateway_channel_id = channel.id
            else:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("WhatsApp no disponible"),
                        "message": _(
                            "No se puede enviar mensaje. El cliente debe iniciar "
                            "la conversación por WhatsApp primero."
                        ),
                        "type": "warning",
                        "sticky": False,
                    },
                }

        # Abrir composer de WhatsApp
        return {
            "name": _("Enviar WhatsApp"),
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.gateway.message",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_model": "discuss.channel",
                "default_res_id": self.gateway_channel_id.id,
                "default_composition_mode": "comment",
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create para vincular automáticamente con canales de WhatsApp.
        """
        leads = super().create(vals_list)

        # Intentar vincular con canales existentes
        for lead in leads:
            if lead.whatsapp_phone and not lead.gateway_channel_id:
                try:
                    channel = lead._find_whatsapp_channel()
                    if channel:
                        lead.gateway_channel_id = channel.id
                        # Vincular el lead en el canal también
                        if not channel.lead_id:
                            channel.lead_id = lead.id
                except Exception as e:
                    _logger.warning(
                        f"Error vinculando lead {lead.id} con canal WhatsApp: {str(e)}"
                    )

        return leads

    def write(self, vals):
        """
        Override write para mantener sincronización con canales.
        """
        res = super().write(vals)

        # Si se actualiza el teléfono, re-vincular canal
        if "mobile" in vals or "phone" in vals:
            for lead in self:
                if not lead.gateway_channel_id and lead.whatsapp_phone:
                    try:
                        channel = lead._find_whatsapp_channel()
                        if channel:
                            lead.gateway_channel_id = channel.id
                            if not channel.lead_id:
                                channel.lead_id = lead.id
                    except Exception as e:
                        _logger.warning(f"Error re-vinculando lead {lead.id}: {str(e)}")

        return res
