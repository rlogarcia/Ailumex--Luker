# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    """
    Extiende hr.employee para soporte de asignación WhatsApp.

    Usa la infraestructura existente de crm_import_leads (rol_comercial).
    """

    _inherit = "hr.employee"

    @api.model
    def get_next_whatsapp_assignee(self):
        """
        Obtiene el siguiente asesor comercial para asignación round-robin.

        HU-WA-07: Asignación del lead al asesor desde Empleados (HR)

        Este método es llamado desde discuss.channel al crear leads.
        """
        # Buscar asesores activos
        asesores = self.search(
            [
                ("rol_comercial", "=", "asesor"),
                ("active", "=", True),
                ("user_id", "!=", False),
            ]
        )

        if not asesores:
            _logger.warning("No hay asesores comerciales activos disponibles")
            return False

        # Obtener último asignado
        IrConfigParameter = self.env["ir.config_parameter"].sudo()
        last_assigned_id = IrConfigParameter.get_param(
            "crm.whatsapp.last_assigned_employee_id", "0"
        )

        # Calcular siguiente
        current_index = 0
        if last_assigned_id != "0":
            try:
                last_assigned_id = int(last_assigned_id)
                if last_assigned_id in asesores.ids:
                    current_index = asesores.ids.index(last_assigned_id)
                    current_index = (current_index + 1) % len(asesores)
            except (ValueError, IndexError):
                current_index = 0

        # Retornar siguiente asesor
        next_asesor = asesores[current_index]

        # Guardar como último asignado
        IrConfigParameter.set_param(
            "crm.whatsapp.last_assigned_employee_id",
            str(next_asesor.id),
        )

        return next_asesor
