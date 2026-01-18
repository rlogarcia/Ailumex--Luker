# -*- coding: utf-8 -*-
"""
Historial de cambios de estado de perfil del estudiante.
Mantiene trazabilidad completa de cada transición de perfil.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StudentProfileStateHistory(models.Model):
    _name = "benglish.student.state.history"
    _description = "Historial de Estado de Perfil del Estudiante"
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
    estado_anterior_id = fields.Many2one(
        comodel_name="benglish.student.profile.state",
        string="Estado Anterior",
        ondelete="set null",
    )
    estado_nuevo_id = fields.Many2one(
        comodel_name="benglish.student.profile.state",
        string="Estado Nuevo",
        ondelete="set null",
    )
    transicion_id = fields.Many2one(
        comodel_name="benglish.student.state.transition",
        string="Transición",
        ondelete="set null",
    )
    motivo = fields.Text(
        string="Motivo",
        help="Motivo o justificación del cambio de estado de perfil.",
    )
    origen = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("wizard", "Wizard"),
            ("automatico", "Automático"),
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

    @api.depends("student_id.name", "estado_anterior_id.name", "estado_nuevo_id.name", "change_date")
    def _compute_display_name(self):
        for record in self:
            student = record.student_id.name if record.student_id else _("Estudiante")
            estado_anterior = record.estado_anterior_id.name or _("Sin estado")
            estado_nuevo = record.estado_nuevo_id.name or _("Sin estado")
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
        """Crea un registro de historial de estado de perfil."""
        student_id = getattr(student, "id", student)
        estado_anterior_id = getattr(estado_anterior, "id", estado_anterior) or False
        estado_nuevo_id = getattr(estado_nuevo, "id", estado_nuevo) or False
        transicion_id = getattr(transicion, "id", transicion) or False

        if not student_id:
            return False

        return self.create(
            {
                "student_id": student_id,
                "estado_anterior_id": estado_anterior_id,
                "estado_nuevo_id": estado_nuevo_id,
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
