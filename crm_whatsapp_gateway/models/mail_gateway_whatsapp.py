# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class MailGatewayWhatsapp(models.AbstractModel):
    """
    Extiende mail.gateway.whatsapp para integrar con CRM.

    Hook en el procesamiento de mensajes para vincular automáticamente
    con leads del CRM.
    """

    _inherit = "mail.gateway.whatsapp"

    def _process_update(self, chat, message, value):
        """
        Override para vincular canal con lead después de procesar mensaje.

        HU-WA-05: Crear lead automático si no existe
        HU-WA-06: Vincular conversación y chatter
        """
        # Procesar mensaje normalmente (OCA)
        res = super()._process_update(chat, message, value)

        # Vincular con lead si no está vinculado
        if chat and not chat.lead_id:
            try:
                chat._link_or_create_lead()
            except Exception as e:
                _logger.error(f"Error vinculando canal {chat.id} con lead: {str(e)}")

        return res


class MailNotification(models.Model):
    """
    Extiende mail.notification para manejar reintentos de WhatsApp.

    HU-WA-10: Manejo de errores y reintentos
    """

    _inherit = "mail.notification"

    def send_gateway(self):
        """
        Override para capturar fallos y añadir a cola de reintentos.
        """
        for notification in self:
            try:
                # Intentar envío normal
                super(MailNotification, notification).send_gateway()

            except Exception as e:
                # El envío falló, añadir a cola de reintentos
                _logger.warning(
                    f"Fallo al enviar notificación {notification.id}: {str(e)}. "
                    "Añadiendo a cola de reintentos."
                )

                # Solo añadir a cola si es de WhatsApp
                if (
                    notification.notification_type == "gateway"
                    and notification.gateway_type == "whatsapp"
                ):
                    self.env["whatsapp.message.queue"].create_from_notification(
                        notification
                    )
                else:
                    # Re-lanzar excepción para otros tipos
                    raise
