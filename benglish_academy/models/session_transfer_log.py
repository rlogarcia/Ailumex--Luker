# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SessionTransferLog(models.Model):
    _name = "benglish.session.transfer.log"
    _description = "Log de Traslado de Estudiantes"
    _order = "transfer_at desc, id desc"
    _rec_name = "display_name"

    display_name = fields.Char(
        string="Nombre",
        compute="_compute_display_name",
        store=True,
    )
    transfer_at = fields.Datetime(
        string="Fecha",
        required=True,
        default=fields.Datetime.now,
        readonly=True,
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Usuario",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        ondelete="restrict",
    )
    source_session_id = fields.Many2one(
        comodel_name="benglish.academic.session",
        string="Sesion Origen",
        ondelete="set null",
        index=True,
    )
    destination_session_id = fields.Many2one(
        comodel_name="benglish.academic.session",
        string="Sesion Destino",
        ondelete="set null",
        index=True,
    )
    source_session_code = fields.Char(string="Codigo Origen", readonly=True)
    destination_session_code = fields.Char(string="Codigo Destino", readonly=True)
    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        ondelete="set null",
        index=True,
    )
    transfer_type = fields.Selection(
        selection=[
            ("single", "Individual"),
            ("bulk", "Masivo"),
        ],
        string="Tipo",
        required=True,
    )
    reason = fields.Text(string="Motivo")
    result = fields.Selection(
        selection=[
            ("success", "Exitoso"),
            ("skipped", "Omitido"),
            ("failed", "Fallido"),
        ],
        string="Resultado",
        required=True,
    )
    message = fields.Text(string="Detalle")
    batch_id = fields.Char(string="Lote", readonly=True, index=True)

    @api.depends(
        "student_id",
        "source_session_code",
        "destination_session_code",
        "transfer_at",
    )
    def _compute_display_name(self):
        for record in self:
            parts = []
            if record.student_id:
                parts.append(record.student_id.name)
            if record.source_session_code or record.destination_session_code:
                parts.append(
                    "%s -> %s"
                    % (record.source_session_code or "-", record.destination_session_code or "-")
                )
            if record.transfer_at:
                parts.append(fields.Datetime.to_string(record.transfer_at)[:16])
            record.display_name = " | ".join(parts) if parts else _("Traslado")
