# -*- coding: utf-8 -*-
from odoo import fields, models


class SurveyTarget(models.Model):
    _name = "survey.target"
    _description = "Público objetivo para encuestas"

    name = fields.Char(string="Nombre", required=True)
    active = fields.Boolean(string="Activo", default=True)
    target_id = fields.Many2one("survey.target", string="Público objetivo")

    def name_get(self):
        return [(rec.id, rec.name) for rec in self]
