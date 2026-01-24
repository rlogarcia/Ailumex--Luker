# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CourtesySettings(models.TransientModel):
    _name = "benglish.courtesy.settings"
    _description = "Configuración Planes Cortesía"

    courtesy_inactivity_cancel_days = fields.Integer(
        string="Días de Inactividad para Cancelación",
        default=21,
        help="Número de días sin actividad antes de cancelar automáticamente una cortesía.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        icp = self.env["ir.config_parameter"].sudo()
        res.update(
            {
                "courtesy_inactivity_cancel_days": int(
                    icp.get_param(
                        "benglish_academy.courtesy_inactivity_cancel_days", 21
                    )
                ),
            }
        )
        return res

    def _set_params(self):
        icp = self.env["ir.config_parameter"].sudo()
        for rec in self:
            icp.set_param(
                "benglish_academy.courtesy_inactivity_cancel_days",
                rec.courtesy_inactivity_cancel_days or 0,
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._set_params()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._set_params()
        return res

    @api.constrains("courtesy_inactivity_cancel_days")
    def _check_courtesy_days(self):
        for record in self:
            if record.courtesy_inactivity_cancel_days <= 0:
                raise ValidationError(
                    "Los días de cancelación deben ser mayores a cero."
                )
