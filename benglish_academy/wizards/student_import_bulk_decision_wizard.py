# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError


class StudentImportBulkDecisionWizard(models.TransientModel):
    _name = "benglish.student.import.bulk.decision.wizard"
    _description = "Cambio masivo de decisiones en importación"

    batch_id = fields.Many2one(
        "benglish.student.import.batch", string="Batch", required=True
    )
    decision = fields.Selection(
        [
            ("create", "Crear"),
            ("update", "Actualizar"),
            ("ignore", "Ignorar"),
            ("pending", "Pendiente"),
        ],
        string="Decisión",
        required=True,
        default="create",
    )
    apply_to = fields.Selection(
        [
            ("all", "Todas las líneas"),
            ("pending", "Solo pendientes"),
            ("duplicates", "Solo duplicadas"),
            ("errors", "Solo con errores"),
            ("valid", "Solo válidas"),
        ],
        string="Aplicar a",
        required=True,
        default="pending",
    )
    use_existing_student = fields.Boolean(
        string="Usar estudiante existente detectado",
        default=True,
        help="Solo aplica cuando la decision es Actualizar.",
    )

    def _get_target_lines(self):
        lines = self.batch_id.line_ids
        if self.apply_to == "pending":
            lines = lines.filtered(lambda l: l.action_decision == "pending")
        elif self.apply_to == "duplicates":
            lines = lines.filtered(lambda l: l.duplicate_scope != "none")
        elif self.apply_to == "errors":
            lines = lines.filtered(lambda l: l.validation_state == "error")
        elif self.apply_to == "valid":
            lines = lines.filtered(lambda l: l.validation_state == "ok")
        return lines

    def action_apply(self):
        self.ensure_one()
        batch = self.batch_id
        lines = self._get_target_lines()
        if not lines:
            raise UserError(_("No hay líneas que cumplan el filtro seleccionado."))

        keys = set(lines.mapped("identity_key"))

        if self.decision == "update":
            if not self.use_existing_student:
                raise UserError(
                    _("Debe seleccionar el estudiante objetivo manualmente por línea.")
                )
            invalid_lines = lines.filtered(lambda l: not l.existing_student_id)
            if invalid_lines:
                raise UserError(
                    _(
                        "Hay %s líneas sin estudiante existente detectado. "
                        "No se puede aplicar 'Actualizar' en bloque."
                    )
                    % len(invalid_lines)
                )
            for line in lines:
                line.with_context(skip_import_recompute=True).write(
                    {
                        "action_decision": "update",
                        "target_student_id": line.existing_student_id.id,
                    }
                )
        else:
            lines.with_context(skip_import_recompute=True).write(
                {
                    "action_decision": self.decision,
                    "target_student_id": False,
                }
            )

        batch.with_context(skip_import_recompute=True)._recompute_decision_conflicts(
            keys
        )
        batch._log(
            "info",
            _("Decisión masiva aplicada: %s en %s líneas.")
            % (self.decision, len(lines)),
        )
        return batch.action_open_form()
