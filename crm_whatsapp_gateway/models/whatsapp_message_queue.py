# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class WhatsappMessageQueue(models.Model):
    """
    HU-WA-10: Manejo de errores y reintentos

    Cola de reintentos para mensajes de WhatsApp fallidos.
    Implementa backoff exponencial: 1min, 5min, 15min
    """

    _name = "whatsapp.message.queue"
    _description = "Cola de reintentos WhatsApp"
    _order = "next_retry asc, id asc"

    notification_id = fields.Many2one(
        "mail.notification",
        string="Notificación",
        required=True,
        ondelete="cascade",
        help="Notificación de mail_gateway que falló",
    )

    message_id = fields.Many2one(
        "mail.message",
        string="Mensaje",
        related="notification_id.mail_message_id",
        store=True,
        readonly=True,
    )

    channel_id = fields.Many2one(
        "discuss.channel",
        string="Canal",
        related="notification_id.gateway_channel_id",
        store=True,
        readonly=True,
    )

    retry_count = fields.Integer(
        string="Intentos",
        default=0,
        help="Número de reintentos realizados",
    )

    max_retries = fields.Integer(
        string="Máximo de intentos",
        default=3,
        help="Número máximo de reintentos antes de marcar como fallido permanente",
    )

    next_retry = fields.Datetime(
        string="Próximo intento",
        help="Fecha y hora del próximo intento de envío",
    )

    error_log = fields.Text(
        string="Log de errores",
        help="Historial de errores de cada intento",
    )

    state = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("processing", "Procesando"),
            ("failed", "Fallido permanente"),
            ("success", "Exitoso"),
        ],
        string="Estado",
        default="pending",
        required=True,
    )

    lead_id = fields.Many2one(
        "crm.lead",
        string="Lead relacionado",
        compute="_compute_lead_id",
        store=True,
    )

    @api.depends("channel_id", "channel_id.lead_id")
    def _compute_lead_id(self):
        """Obtiene el lead relacionado desde el canal"""
        for queue in self:
            queue.lead_id = queue.channel_id.lead_id.id if queue.channel_id else False

    def action_retry_now(self):
        """Botón manual para reintentar inmediatamente"""
        self.ensure_one()

        if self.state == "success":
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Ya enviado"),
                    "message": _("Este mensaje ya fue enviado exitosamente."),
                    "type": "info",
                },
            }

        if self.state == "failed":
            # Resetear para permitir reintento manual
            self.write(
                {
                    "state": "pending",
                    "retry_count": 0,
                    "next_retry": fields.Datetime.now(),
                }
            )

        # Ejecutar reintento
        self._retry_send()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Reintento ejecutado"),
                "message": _("Se ha intentado reenviar el mensaje."),
                "type": "success" if self.state == "success" else "warning",
            },
        }

    def _retry_send(self):
        """
        Reintenta enviar el mensaje usando el sistema de notificaciones OCA.
        """
        self.ensure_one()

        if self.state not in ("pending", "processing"):
            return False

        # Marcar como procesando
        self.state = "processing"

        try:
            # Intentar enviar usando el sistema OCA
            self.notification_id.send_gateway()

            # Si llegamos aquí, el envío fue exitoso
            self.write(
                {
                    "state": "success",
                    "error_log": (self.error_log or "")
                    + f"\n[{fields.Datetime.now()}] Enviado exitosamente después de {self.retry_count} intentos.",
                }
            )

            _logger.info(
                f"Mensaje {self.message_id.id} enviado exitosamente después "
                f"de {self.retry_count} reintentos"
            )

            return True

        except Exception as e:
            # El envío falló
            self.retry_count += 1
            error_msg = f"\n[{fields.Datetime.now()}] Intento {self.retry_count} fallido: {str(e)}"
            self.error_log = (self.error_log or "") + error_msg

            if self.retry_count >= self.max_retries:
                # Se alcanzó el máximo de reintentos
                self.state = "failed"
                self._alert_admin()

                _logger.error(
                    f"Mensaje {self.message_id.id} falló permanentemente "
                    f"después de {self.retry_count} intentos: {str(e)}"
                )
            else:
                # Programar siguiente reintento con backoff exponencial
                # 1min (60s), 5min (300s), 15min (900s)
                delays = [60, 300, 900]
                delay_seconds = delays[min(self.retry_count - 1, len(delays) - 1)]

                self.write(
                    {
                        "state": "pending",
                        "next_retry": fields.Datetime.now()
                        + timedelta(seconds=delay_seconds),
                    }
                )

                _logger.warning(
                    f"Mensaje {self.message_id.id} falló (intento {self.retry_count}). "
                    f"Próximo intento en {delay_seconds}s"
                )

            return False

    def _alert_admin(self):
        """
        Envía alerta al administrador cuando un mensaje falla permanentemente.
        """
        self.ensure_one()

        # Buscar usuarios administradores del gateway
        admin_users = self.env["res.users"].browse()
        try:
            gateway_group = self.env.ref("mail_gateway.gateway_admin")
        except Exception:
            gateway_group = None

        if gateway_group:
            admin_users = self.env["res.users"].search(
                [("groups_id", "in", [gateway_group.id])]
            )

        if not admin_users:
            # Fallback: buscar usuario admin por login o usar el usuario actual
            admin_users = (
                self.env["res.users"].search([("login", "=", "admin")], limit=1)
                or self.env.user
            )

        # Crear mensaje interno para administradores
        body = _(
            f"<p><strong>⚠️ Mensaje de WhatsApp fallido permanentemente</strong></p>"
            f"<ul>"
            f"<li><strong>Canal:</strong> {self.channel_id.name if self.channel_id else 'N/A'}</li>"
            f"<li><strong>Lead:</strong> {self.lead_id.name if self.lead_id else 'N/A'}</li>"
            f"<li><strong>Intentos:</strong> {self.retry_count} / {self.max_retries}</li>"
            f"<li><strong>Último error:</strong> {self.error_log[-200:] if self.error_log else 'N/A'}</li>"
            f"</ul>"
            f"<p>Por favor, revise la configuración del gateway de WhatsApp.</p>"
        )

        # Enviar notificación interna
        partner_ids = admin_users.mapped("partner_id").ids
        if not partner_ids:
            partner_ids = self.env.user.partner_id.ids

        self.env["mail.thread"].sudo().message_notify(
            partner_ids=partner_ids,
            body=body,
            subject=_("WhatsApp: Mensaje fallido permanentemente"),
            message_type="notification",
        )

    @api.model
    def _cron_retry_failed_messages(self):
        """
        Cron que reintenta mensajes fallidos periódicamente.

        Se ejecuta cada 5 minutos según configuración en data/cron_data.xml
        """
        # Buscar mensajes pendientes cuya hora de reintento ya pasó
        pending_messages = self.search(
            [("state", "=", "pending"), ("next_retry", "<=", fields.Datetime.now())]
        )

        _logger.info(
            f"Cron WhatsApp: {len(pending_messages)} mensajes pendientes de reintento"
        )

        for queue in pending_messages:
            # Saltar si ya alcanzó el máximo de reintentos
            if queue.retry_count >= queue.max_retries:
                continue

            try:
                queue._retry_send()
                # Commit después de cada reintento para no bloquear la cola
                try:
                    self.env.cr.commit()
                except Exception:
                    # Commit puede fallar en algunos entornos; seguir intentando
                    pass
            except Exception as e:
                _logger.error(
                    f"Error en cron de reintentos WhatsApp para mensaje {queue.id}: {str(e)}"
                )
                try:
                    self.env.cr.rollback()
                except Exception:
                    pass

    @api.model
    def create_from_notification(self, notification):
        """
        Crea entrada en cola desde una notificación fallida.

        Llamado automáticamente cuando falla un envío de WhatsApp.
        """
        # Verificar que no exista ya en cola
        existing = self.search(
            [
                ("notification_id", "=", notification.id),
                ("state", "in", ["pending", "processing"]),
            ],
            limit=1,
        )

        if existing:
            return existing

        # Crear nueva entrada en cola
        return self.create(
            {
                "notification_id": notification.id,
                "retry_count": 0,
                "next_retry": fields.Datetime.now()
                + timedelta(seconds=60),  # Primer reintento en 1 minuto
                "state": "pending",
                "error_log": f"[{fields.Datetime.now()}] Mensaje añadido a cola de reintentos.",
            }
        )
