# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StudentImportConfirmWizard(models.TransientModel):
    _name = "benglish.student.import.confirm.wizard"
    _description = "Confirmación de importación de estudiantes"

    batch_id = fields.Many2one(
        "benglish.student.import.batch", string="Batch", required=True
    )
    confirm = fields.Boolean(string="Confirmo la importación", default=False)

    line_count = fields.Integer(compute="_compute_counts", string="Total de líneas")
    create_count = fields.Integer(compute="_compute_counts", string="Crear")
    update_count = fields.Integer(compute="_compute_counts", string="Actualizar")
    ignore_count = fields.Integer(compute="_compute_counts", string="Ignorar")
    pending_count = fields.Integer(compute="_compute_counts", string="Pendientes")
    error_count = fields.Integer(compute="_compute_counts", string="Errores")

    @api.depends(
        "batch_id",
        "batch_id.line_ids",
        "batch_id.line_ids.action_decision",
        "batch_id.line_ids.validation_state",
    )
    def _compute_counts(self):
        for wizard in self:
            lines = wizard.batch_id.line_ids
            wizard.line_count = len(lines)
            wizard.create_count = len(
                lines.filtered(lambda l: l.action_decision == "create")
            )
            wizard.update_count = len(
                lines.filtered(lambda l: l.action_decision == "update")
            )
            wizard.ignore_count = len(
                lines.filtered(lambda l: l.action_decision == "ignore")
            )
            wizard.pending_count = len(
                lines.filtered(lambda l: l.action_decision == "pending")
            )
            wizard.error_count = len(
                lines.filtered(lambda l: l.validation_state == "error")
            )

    def action_confirm_import(self):
        self.ensure_one()
        if not self.confirm:
            raise UserError(_("Debe confirmar la importación para continuar."))
        self.batch_id.action_import()
        return self.batch_id.action_open_form()
