# -*- coding: utf-8 -*-
"""Wizard para elegir el ID a asignar al crear una encuesta."""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SurveyCodeSelectionWizard(models.TransientModel):
    _name = "survey.code.selection.wizard"
    _description = "Selección de ID para encuesta"

    code_source = fields.Selection(
        selection=[
            ("available", "Usar un ID liberado"),
            ("new", "Generar el siguiente consecutivo"),
        ],
        string="Opción",
        required=True,
        default="available",
    )
    available_code_id = fields.Many2one(
        "survey.code.available",
        string="ID liberado",
        help="Selecciona uno de los IDs que se liberaron previamente.",
    )
    new_code_number = fields.Integer(string="Número consecutivo", readonly=True)
    new_code_label = fields.Char(string="ID consecutivo", readonly=True)
    has_available_codes = fields.Boolean(string="Hay IDs liberados", readonly=True)

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        available_ids = self.env.context.get("available_code_ids", [])
        available_codes = self.env["survey.code.available"].browse(available_ids)
        new_code_number = self.env.context.get("new_code_number")
        new_code_label = self.env.context.get("new_code_label")

        result.setdefault("has_available_codes", bool(available_codes))
        if available_codes:
            result.setdefault("available_code_id", available_codes[:1].id)
        else:
            result.setdefault("code_source", "new")

        if new_code_number:
            result.setdefault("new_code_number", new_code_number)
        if new_code_label:
            result.setdefault("new_code_label", new_code_label)
        return result

    def action_confirm(self):
        self.ensure_one()
        ctx = dict(self.env.context or {})
        ctx.pop("available_code_ids", None)
        ctx.pop("new_code_number", None)
        ctx.pop("new_code_label", None)
        ctx.pop("force_code_selection", None)

        selected_number = None
        selected_code_value = None
        selected_code_id = None

        if self.code_source == "available":
            if not self.available_code_id:
                raise UserError(_("Selecciona un ID liberado."))
            selected_number = self.available_code_id.number
            selected_code_value = self.available_code_id.code
            selected_code_id = self.available_code_id.id
        else:
            if not self.new_code_number:
                raise UserError(_("No se pudo determinar el siguiente consecutivo."))
            selected_number = self.new_code_number
            selected_code_value = self.new_code_label or self.env["survey.survey"]._format_code(selected_number)

        ctx.update(
            {
                "skip_code_selection": True,
                "preselected_code_number": selected_number,
                "preselected_code_value": selected_code_value,
                "preselected_code_id": selected_code_id,
                "default_code": selected_code_value,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "survey.survey",
            "view_mode": "form",
            "target": "current",
            "context": ctx,
        }