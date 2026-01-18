# -*- coding: utf-8 -*-
"""Configuración centralizada para reglas de agendamiento/cancelación."""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

PARAM_MINUTOS_AGENDAR = "benglish_academic.minutos_anticipacion_agendar"
PARAM_MINUTOS_CANCELAR = "benglish_academic.minutos_anticipacion_cancelar"
DEFAULT_MINUTOS_ANTICIPACION = 10


class BenglishAcademicSettings(models.AbstractModel):
    _name = "benglish.academic.settings"
    _description = "Configuración académica centralizada"

    @api.model
    def get_class_booking_policy(self, company_id=None):
        """Retorna la política de agendamiento/cancelación para consumir desde portal."""
        company = self.env.company
        if company_id:
            company = self.env["res.company"].browse(company_id)
            if not company.exists():
                company = self.env.company

        params = self.env["ir.config_parameter"].sudo().with_company(company)

        def _get_minutes(key):
            raw_value = params.get_param(key, DEFAULT_MINUTOS_ANTICIPACION)
            try:
                value = int(raw_value)
            except (TypeError, ValueError):
                value = DEFAULT_MINUTOS_ANTICIPACION
            if value < 0:
                return DEFAULT_MINUTOS_ANTICIPACION
            return value

        return {
            "minutos_anticipacion_agendar": _get_minutes(PARAM_MINUTOS_AGENDAR),
            "minutos_anticipacion_cancelar": _get_minutes(PARAM_MINUTOS_CANCELAR),
        }


class BenglishClassBookingSettings(models.TransientModel):
    """Configuración de parámetros de agendamiento de clases.

    Modelo independiente para evitar que aparezca en Ajustes generales de Odoo.
    Solo accesible desde: Gestión Académica > Configuración > Parametrizaciones de Clases
    """

    _name = "benglish.class.booking.settings"
    _description = "Parametrizaciones de Clases"

    minutos_anticipacion_agendar = fields.Integer(
        string="Minutos de anticipación para programar",
        default=DEFAULT_MINUTOS_ANTICIPACION,
        help="Minutos mínimos antes del inicio para permitir programar una clase.",
    )
    minutos_anticipacion_cancelar = fields.Integer(
        string="Minutos de anticipación para cancelar",
        default=DEFAULT_MINUTOS_ANTICIPACION,
        help="Minutos mínimos antes del inicio para permitir cancelar una clase.",
    )

    @api.model
    def default_get(self, fields_list):
        """Cargar valores actuales desde ir.config_parameter."""
        res = super().default_get(fields_list)
        params = self.env["ir.config_parameter"].sudo()

        if "minutos_anticipacion_agendar" in fields_list:
            raw_value = params.get_param(
                PARAM_MINUTOS_AGENDAR, DEFAULT_MINUTOS_ANTICIPACION
            )
            try:
                res["minutos_anticipacion_agendar"] = int(raw_value)
            except (TypeError, ValueError):
                res["minutos_anticipacion_agendar"] = DEFAULT_MINUTOS_ANTICIPACION

        if "minutos_anticipacion_cancelar" in fields_list:
            raw_value = params.get_param(
                PARAM_MINUTOS_CANCELAR, DEFAULT_MINUTOS_ANTICIPACION
            )
            try:
                res["minutos_anticipacion_cancelar"] = int(raw_value)
            except (TypeError, ValueError):
                res["minutos_anticipacion_cancelar"] = DEFAULT_MINUTOS_ANTICIPACION

        return res

    def execute(self):
        """Guardar los valores en ir.config_parameter."""
        self.ensure_one()
        params = self.env["ir.config_parameter"].sudo()

        params.set_param(PARAM_MINUTOS_AGENDAR, str(self.minutos_anticipacion_agendar))
        params.set_param(
            PARAM_MINUTOS_CANCELAR, str(self.minutos_anticipacion_cancelar)
        )

        return {"type": "ir.actions.act_window_close"}

    @api.constrains("minutos_anticipacion_agendar", "minutos_anticipacion_cancelar")
    def _check_minutos_anticipacion(self):
        for record in self:
            if (
                record.minutos_anticipacion_agendar is not False
                and record.minutos_anticipacion_agendar < 0
            ):
                raise ValidationError(
                    _(
                        "Los minutos de anticipación para agendar deben ser mayores o iguales a cero."
                    )
                )
            if (
                record.minutos_anticipacion_cancelar is not False
                and record.minutos_anticipacion_cancelar < 0
            ):
                raise ValidationError(
                    _(
                        "Los minutos de anticipación para cancelar deben ser mayores o iguales a cero."
                    )
                )
