# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError


class StudentImportWizard(models.TransientModel):
    _name = "benglish.student.import.wizard"
    _description = "Wizard de importación de estudiantes"

    file_data = fields.Binary(string="Archivo XLSX", required=True)
    file_name = fields.Char(string="Nombre del archivo", required=True)
    extra_column_policy = fields.Selection(
        [
            ("reject", "Rechazar"),
            ("ignore", "Ignorar"),
            ("allow", "Permitir"),
        ],
        string="Política de columnas extra",
        default="reject",
        required=True,
    )
    enforce_column_order = fields.Boolean(
        string="Validar el orden de columnas", default=False
    )
    identity_field = fields.Selection(
        [("student_id_number", "Documento de identidad")],
        string="Campo de identidad",
        default="student_id_number",
        required=True,
    )

    def action_create_batch(self):
        self.ensure_one()
        if not self.file_data or not self.file_name:
            raise UserError(_("Debe cargar un archivo XLSX."))

        batch = self.env["benglish.student.import.batch"].create(
            {
                "file_name": self.file_name,
                "file_data": self.file_data,
                "extra_column_policy": self.extra_column_policy,
                "enforce_column_order": self.enforce_column_order,
                "identity_field": self.identity_field,
            }
        )
        batch.action_validate_file()
        return batch.action_open_form()
