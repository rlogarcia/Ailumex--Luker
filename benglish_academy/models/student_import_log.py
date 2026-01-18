# -*- coding: utf-8 -*-

from odoo import fields, models


class StudentImportLog(models.Model):
    _name = "benglish.student.import.log"
    _description = "Log técnico de importación de estudiantes"
    _order = "create_date desc, id desc"

    batch_id = fields.Many2one(
        "benglish.student.import.batch",
        string="Batch",
        required=True,
        ondelete="cascade",
        index=True,
    )
    line_id = fields.Many2one(
        "benglish.student.import.line",
        string="Línea",
        ondelete="set null",
    )
    level = fields.Selection(
        [
            ("info", "Info"),
            ("warning", "Advertencia"),
            ("error", "Error"),
        ],
        string="Nivel",
        default="info",
        required=True,
    )
    message = fields.Char(string="Mensaje", required=True)
    details = fields.Text(string="Detalle")
