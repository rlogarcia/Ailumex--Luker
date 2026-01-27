# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    """
    Extiende discuss.channel para vincular canales de WhatsApp con leads del CRM.

    HU-WA-06: Vincular conversación y chatter
    """

    _inherit = "discuss.channel"

    lead_id = fields.Many2one(
        "crm.lead",
        string="Lead/Oportunidad",
        ondelete="set null",
        help="Lead del CRM vinculado a esta conversación de WhatsApp",
    )
    lead_count = fields.Integer(
        string="Leads relacionados",
        compute="_compute_lead_count",
    )

    @api.depends("lead_id")
    def _compute_lead_count(self):
        """Cuenta los leads vinculados (máximo 1)"""
        for channel in self:
            channel.lead_count = 1 if channel.lead_id else 0

    def action_view_lead(self):
        """Abre el lead vinculado desde el canal"""
        self.ensure_one()
        if not self.lead_id:
            raise UserError(_("No hay lead vinculado a esta conversación"))

        return {
            "name": _("Lead"),
            "type": "ir.actions.act_window",
            "res_model": "crm.lead",
            "res_id": self.lead_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def _link_or_create_lead(self):
        """
        HU-WA-05: Crear lead automático si no existe
        HU-WA-04: Deduplicación por número WhatsApp

        Busca o crea un lead asociado a este canal de WhatsApp.
        """
        self.ensure_one()

        if self.channel_type != "gateway" or not self.gateway_id:
            return False

        if self.gateway_id.gateway_type != "whatsapp":
            return False

        if self.lead_id:
            return self.lead_id

        # Normalizar número de teléfono
        phone_raw = self.gateway_channel_token
        phone_normalized = self._normalize_phone_number(phone_raw)

        if not phone_normalized:
            _logger.warning(f"No se pudo normalizar el número: {phone_raw}")
            return False

        # HU-WA-04: Buscar lead existente (deduplicación)
        lead = self._find_existing_lead(phone_normalized)

        # HU-WA-05: Crear lead si no existe
        if not lead:
            lead = self._create_lead_from_whatsapp(phone_normalized, phone_raw)

        # Vincular canal con lead
        self.lead_id = lead.id

        # Registrar en chatter del lead
        lead.message_post(
            body=_(
                f"<p>Conversación de WhatsApp iniciada.</p>"
                f"<p>Número: {phone_raw}</p>"
                f"<p>Canal: {self.name}</p>"
            ),
            subject="WhatsApp Connected",
            message_type="notification",
        )

        return lead

    def _normalize_phone_number(self, phone):
        """
        HU-WA-04: Normalización a formato E.164

        Convierte números en diferentes formatos al estándar E.164.
        Ejemplos:
        - +57 301 234 5678 → +573012345678
        - 3012345678 → +573012345678
        - (301) 234-5678 → +573012345678
        """
        if not phone:
            return False

        try:
            import phonenumbers

            # Intentar parsear el número
            # Asumir Colombia (CO) como país por defecto si no tiene código de país
            parsed = phonenumbers.parse(phone, "CO")

            # Validar que sea un número válido
            if not phonenumbers.is_valid_number(parsed):
                _logger.warning(f"Número inválido: {phone}")
                return False

            # Formatear a E.164
            normalized = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )

            return normalized

        except Exception as e:
            _logger.error(f"Error normalizando número {phone}: {str(e)}")
            return False

    def _find_existing_lead(self, phone_normalized):
        """
        HU-WA-04: Buscar lead existente por número normalizado

        Busca en los campos phone y mobile del lead.
        """
        Lead = self.env["crm.lead"]

        # Buscar por número exacto (normalizado)
        lead = Lead.search(
            [
                "|",
                ("phone", "=", phone_normalized),
                ("mobile", "=", phone_normalized),
                ("type", "=", "lead"),  # Solo leads, no oportunidades cerradas
            ],
            limit=1,
        )

        return lead

    def _create_lead_from_whatsapp(self, phone_normalized, phone_raw):
        """
        HU-WA-05: Crear lead automático desde WhatsApp
        HU-WA-07: Asignar a asesor comercial desde HR

        Crea un nuevo lead con:
        - Nombre descriptivo
        - Número normalizado
        - Fuente "WhatsApp Línea Marketing" (bloqueada)
        - Etapa "Nuevo"
        - Actividad "Llamar inmediato"
        - Asignación automática a asesor
        """
        Lead = self.env["crm.lead"]

        # Obtener fuente UTM de WhatsApp (creada en data/)
        whatsapp_source = self.env.ref(
            "crm_whatsapp_gateway.utm_source_whatsapp_marketing",
            raise_if_not_found=False,
        )

        # Obtener etapa "Nuevo" del pipeline de Marketing
        new_stage = self.env["crm.stage"].search(
            [
                ("name", "=ilike", "Nuevo"),
                ("team_id.name", "=ilike", "Marketing"),
            ],
            limit=1,
        )

        if not new_stage:
            # Fallback: primera etapa disponible
            new_stage = self.env["crm.stage"].search([], limit=1)

        # Obtener nombre del contacto si está disponible en el canal
        contact_name = self.name if self.name != phone_raw else False

        # Crear lead
        lead_vals = {
            "name": contact_name or f"WhatsApp - {phone_raw}",
            "type": "lead",
            "mobile": phone_normalized,
            "phone": phone_normalized,
            "source_id": whatsapp_source.id if whatsapp_source else False,
            "stage_id": new_stage.id if new_stage else False,
            "description": f"Lead creado automáticamente desde WhatsApp.\nNúmero: {phone_raw}",
        }

        lead = Lead.create(lead_vals)

        # HU-WA-07: Asignar a asesor comercial
        self._assign_to_commercial_user(lead)

        # HU-WA-08: Crear actividad "Llamar inmediato"
        self._create_immediate_call_activity(lead)

        _logger.info(
            f"Lead {lead.id} creado desde WhatsApp: {phone_raw} → {phone_normalized}"
        )

        return lead

    def _assign_to_commercial_user(self, lead):
        """
        HU-WA-07: Asignación del lead al asesor desde Empleados (HR)

        Implementa round-robin simple:
        1. Obtiene empleados con rol_comercial = 'asesor'
        2. Filtra solo activos con usuario asignado
        3. Rota entre ellos usando parámetro del sistema
        """
        Employee = self.env["hr.employee"]
        IrConfigParameter = self.env["ir.config_parameter"].sudo()

        # Buscar asesores comerciales activos
        asesores = Employee.search(
            [
                ("rol_comercial", "=", "asesor"),
                ("active", "=", True),
                ("user_id", "!=", False),
            ]
        )

        if not asesores:
            _logger.warning("No hay asesores comerciales activos. Lead sin asignar.")
            return False

        # Obtener último asesor asignado
        last_assigned_id = IrConfigParameter.get_param(
            "crm.whatsapp.last_assigned_employee_id", "0"
        )

        # Calcular siguiente asesor (round-robin)
        current_index = 0
        if last_assigned_id != "0":
            try:
                last_assigned_id = int(last_assigned_id)
                if last_assigned_id in asesores.ids:
                    current_index = asesores.ids.index(last_assigned_id)
                    current_index = (current_index + 1) % len(asesores)
            except (ValueError, IndexError):
                current_index = 0

        # Asignar al siguiente asesor
        assigned_employee = asesores[current_index]
        lead.user_id = assigned_employee.user_id.id

        # Guardar último asignado
        IrConfigParameter.set_param(
            "crm.whatsapp.last_assigned_employee_id",
            str(assigned_employee.id),
        )

        _logger.info(
            f"Lead {lead.id} asignado a {assigned_employee.name} (round-robin)"
        )

        return assigned_employee

    def _create_immediate_call_activity(self, lead):
        """
        HU-WA-08: Crear actividad automática "Llamar inmediato"

        Se ejecuta cuando se crea un lead desde WhatsApp.
        """
        ActivityType = self.env["mail.activity.type"]

        # Buscar tipo de actividad "Llamar"
        call_activity_type = ActivityType.search(
            [("name", "=ilike", "llamada")], limit=1
        )

        if not call_activity_type:
            # Fallback: primer tipo de actividad disponible
            call_activity_type = ActivityType.search([], limit=1)

        if not call_activity_type:
            _logger.warning("No se pudo crear actividad: no hay tipos disponibles")
            return False

        # Crear actividad
        lead.activity_schedule(
            activity_type_id=call_activity_type.id,
            summary="Llamar inmediato - Lead desde WhatsApp",
            note="Este lead se generó automáticamente desde un mensaje de WhatsApp. "
            "Contactar lo antes posible para dar seguimiento.",
            user_id=lead.user_id.id if lead.user_id else self.env.user.id,
        )

        return True

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create para detectar nuevos canales de WhatsApp
        y vincularlos automáticamente con leads.
        """
        channels = super().create(vals_list)

        # Procesar solo canales de WhatsApp gateway
        whatsapp_channels = channels.filtered(
            lambda c: c.channel_type == "gateway"
            and c.gateway_id
            and c.gateway_id.gateway_type == "whatsapp"
        )

        # Vincular o crear leads automáticamente
        for channel in whatsapp_channels:
            try:
                channel._link_or_create_lead()
            except Exception as e:
                _logger.error(f"Error vinculando canal {channel.id} con lead: {str(e)}")

        return channels

    def message_post(self, **kwargs):
        """
        Override message_post para replicar mensajes en el chatter del lead.

        HU-WA-06: Vincular conversación y chatter
        """
        message = super().message_post(**kwargs)

        # Si este canal está vinculado a un lead, copiar el mensaje al chatter
        if (
            self.channel_type == "gateway"
            and self.gateway_id
            and self.gateway_id.gateway_type == "whatsapp"
            and self.lead_id
        ):
            try:
                # Evitar recursión
                if not self.env.context.get("skip_lead_chatter_sync"):
                    self.lead_id.with_context(skip_lead_chatter_sync=True).message_post(
                        body=message.body,
                        subject=f"WhatsApp: {message.subject or ''}",
                        message_type="comment",
                        subtype_xmlid="mail.mt_comment",
                    )
            except Exception as e:
                _logger.warning(
                    f"Error sincronizando mensaje al lead {self.lead_id.id}: {str(e)}"
                )

        return message
