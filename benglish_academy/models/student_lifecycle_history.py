# -*- coding: utf-8 -*-
"""
Historial de cambios de estado del estudiante (ciclo de vida).
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StudentLifecycleHistory(models.Model):
    _name = "benglish.student.lifecycle.history"
    _description = "Historial de Estado del Estudiante"
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
    estado_anterior = fields.Selection(
        selection=lambda self: self._get_student_state_selection(),
        string="Estado Anterior",
    )
    estado_nuevo = fields.Selection(
        selection=lambda self: self._get_student_state_selection(),
        string="Estado Nuevo",
    )
    transicion_id = fields.Many2one(
        comodel_name="benglish.student.lifecycle.transition",
        string="Transición",
        ondelete="set null",
    )
    motivo = fields.Text(
        string="Motivo",
        help="Motivo o justificación del cambio de estado.",
    )
    origen = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("wizard", "Wizard"),
            ("matricula", "Matrícula"),
            ("importacion", "Importación"),
            ("sistema", "Sistema"),
        ],
        string="Origen",
        required=True,
        default="manual",
        readonly=True,
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

    @api.model
    def _get_student_state_selection(self):
        selection = self.env["benglish.student"]._fields["state"].selection
        return selection(self.env["benglish.student"]) if callable(selection) else selection

    def _get_state_label(self, state_code):
        selection = dict(self._get_student_state_selection())
        return selection.get(state_code, state_code or "")

    @api.depends("student_id.name", "estado_anterior", "estado_nuevo", "change_date")
    def _compute_display_name(self):
        for record in self:
            student = record.student_id.name if record.student_id else _("Estudiante")
            estado_anterior = self._get_state_label(record.estado_anterior) or _("Sin estado")
            estado_nuevo = self._get_state_label(record.estado_nuevo) or _("Sin estado")
            fecha = fields.Datetime.to_string(record.change_date) if record.change_date else ""
            record.display_name = f"{student}: {estado_anterior} → {estado_nuevo} ({fecha})"

    @api.model
    def registrar_cambio(
        self,
        student,
        estado_anterior,
        estado_nuevo,
        motivo=None,
        origen="manual",
        transicion=None,
    ):
        """Crea un registro de historial de estado del estudiante."""
        student_id = getattr(student, "id", student)
        transicion_id = getattr(transicion, "id", transicion) or False

        if not student_id:
            return False

        return self.create(
            {
                "student_id": student_id,
                "estado_anterior": estado_anterior,
                "estado_nuevo": estado_nuevo,
                "transicion_id": transicion_id,
                "motivo": motivo,
                "origen": origen or "manual",
            }
        )

    def write(self, vals):
        raise UserError(_("Los registros de historial no pueden modificarse."))

    def unlink(self):
        if not self.env.user.has_group("base.group_system"):
            raise UserError(
                _("Los registros de auditoría solo pueden ser eliminados por administradores.")
            )
        return super().unlink()
