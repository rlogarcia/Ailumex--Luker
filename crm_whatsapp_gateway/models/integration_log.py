# -*- coding: utf-8 -*-
from odoo import models, fields, api


class IntegrationLog(models.Model):
    _name = "integration.log"
    _description = "Integration Log"
    _rec_name = "summary"

    summary = fields.Char(string="Summary", required=True)
    model_name = fields.Char(string="Model")
    res_id = fields.Integer(string="Record ID")
    method = fields.Char(string="Method")
    level = fields.Selection(
        [("info", "Info"), ("warning", "Warning"), ("error", "Error")], default="error"
    )
    error = fields.Text(string="Error")
    data = fields.Text(string="Data")
    create_date = fields.Datetime(string="Created On", readonly=True)
    user_id = fields.Many2one(
        "res.users", string="User", default=lambda self: self.env.uid
    )
