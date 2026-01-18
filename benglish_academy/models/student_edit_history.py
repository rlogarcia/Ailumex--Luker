# -*- coding: utf-8 -*-
"""
Historial de ediciones del estudiante con detalle por campo.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StudentEditHistory(models.Model):
    _name = "benglish.student.edit.history"
    _description = "Historial de Ediciones del Estudiante"
    _order = "change_date desc, id desc"
    _rec_name = "display_name"

    display_name = fields.Char(
        compute="_compute_display_name",
    )

    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Usuario",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )
    change_date = fields.Datetime(
        string="Fecha",
        required=True,
        default=fields.Datetime.now,
        readonly=True,
        index=True,
    )
    origin = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("wizard", "Wizard"),
            ("importacion", "Importación"),
            ("sistema", "Sistema"),
        ],
        string="Origen",
        required=True,
        default="manual",
        readonly=True,
    )
    note = fields.Text(
        string="Notas",
        help="Observaciones adicionales sobre la edición.",
    )
    line_ids = fields.One2many(
        comodel_name="benglish.student.edit.history.line",
        inverse_name="history_id",
        string="Cambios",
        readonly=True,
    )
    change_count = fields.Integer(
        string="Total de Cambios",
        compute="_compute_change_count",
    )

    @api.depends("student_id.name", "change_date")
    def _compute_display_name(self):
        for record in self:
            student = record.student_id.name if record.student_id else _("Estudiante")
            fecha = fields.Datetime.to_string(record.change_date) if record.change_date else ""
            record.display_name = f"{student} ({fecha})"

    @api.depends("line_ids")
    def _compute_change_count(self):
        for record in self:
            record.change_count = len(record.line_ids)

    def write(self, vals):
        raise UserError(_("Los registros de historial no pueden modificarse."))

    def unlink(self):
        if not self.env.user.has_group("base.group_system"):
            raise UserError(
                _("Los registros de auditoría solo pueden ser eliminados por administradores.")
            )
        return super().unlink()


class StudentEditHistoryLine(models.Model):
    _name = "benglish.student.edit.history.line"
    _description = "Detalle de Edición del Estudiante"
    _order = "id"

    history_id = fields.Many2one(
        comodel_name="benglish.student.edit.history",
        string="Historial",
        required=True,
        ondelete="cascade",
        index=True,
    )
    field_name = fields.Char(
        string="Campo",
        required=True,
    )
    field_label = fields.Char(
        string="Etiqueta",
        required=True,
    )
    old_value = fields.Text(
        string="Valor Anterior",
    )
    new_value = fields.Text(
        string="Valor Nuevo",
    )

    def write(self, vals):
        raise UserError(_("Los registros de historial no pueden modificarse."))

    def unlink(self):
        if not self.env.user.has_group("base.group_system"):
            raise UserError(
                _("Los registros de auditoría solo pueden ser eliminados por administradores.")
            )
        return super().unlink()
