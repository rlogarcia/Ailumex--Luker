# -*- coding: utf-8 -*-
"""
Wizard para cambiar el estado del estudiante (ciclo de vida).
"""

from odoo import api, fields, models, _
from markupsafe import Markup
from odoo.exceptions import UserError, ValidationError


class StudentChangeLifecycleStateWizard(models.TransientModel):
    _name = "benglish.student.change.lifecycle.state.wizard"
    _description = "Wizard para Cambiar Estado del Estudiante"

    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        required=True,
        readonly=True,
    )
    student_name = fields.Char(
        related="student_id.name",
        string="Nombre del Estudiante",
        readonly=True,
    )
    estado_actual = fields.Selection(
        selection=lambda self: self._get_student_state_selection(),
        string="Estado Actual",
        readonly=True,
    )
    estado_nuevo = fields.Selection(
        selection=lambda self: self._get_student_state_selection(),
        string="Nuevo Estado",
        required=True,
    )

    estados_permitidos = fields.Char(
        compute="_compute_estados_permitidos",
        string="Estados Permitidos",
    )
    hay_transiciones = fields.Boolean(
        compute="_compute_estados_permitidos",
        string="Hay Transiciones Definidas",
    )

    transicion_id = fields.Many2one(
        comodel_name="benglish.student.lifecycle.transition",
        compute="_compute_transicion_info",
        string="Transición",
    )
    requiere_motivo = fields.Boolean(
        compute="_compute_transicion_info",
        string="Requiere Motivo",
    )
    mensaje_confirmacion = fields.Text(
        compute="_compute_transicion_info",
        string="Mensaje de Confirmación",
    )
    profile_state_id = fields.Many2one(
        comodel_name="benglish.student.profile.state",
        compute="_compute_transicion_info",
        string="Estado de Perfil Aplicado",
        readonly=True,
    )

    motivo = fields.Text(
        string="Motivo del Cambio",
        help="Explique la razón del cambio de estado.",
    )
    notas = fields.Text(
        string="Notas Adicionales",
        help="Observaciones adicionales (opcional).",
    )

    @api.model
    def _get_student_state_selection(self):
        selection = self.env["benglish.student"]._fields["state"].selection
        return (
            selection(self.env["benglish.student"])
            if callable(selection)
            else selection
        )

    def _get_state_label(self, state_code):
        selection = dict(self._get_student_state_selection())
        return selection.get(state_code, state_code or "")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        student_id = res.get("student_id")
        if student_id and not res.get("estado_actual"):
            student = self.env["benglish.student"].browse(student_id)
            res["estado_actual"] = student.state
        return res

    @api.depends("estado_actual")
    def _compute_estados_permitidos(self):
        Transition = self.env["benglish.student.lifecycle.transition"]
        for wizard in self:
            if wizard.estado_actual:
                estados = Transition.get_estados_destino_permitidos(
                    wizard.estado_actual
                )
                wizard.hay_transiciones = bool(estados)
            else:
                estados = [
                    state for state, _label in self._get_student_state_selection()
                ]
                wizard.hay_transiciones = True
            wizard.estados_permitidos = ", ".join(
                self._get_state_label(state) for state in estados
            )

    @api.depends("estado_actual", "estado_nuevo")
    def _compute_transicion_info(self):
        Transition = self.env["benglish.student.lifecycle.transition"]
        for wizard in self:
            if wizard.estado_actual and wizard.estado_nuevo:
                transicion = Transition.search(
                    [
                        ("state_from", "=", wizard.estado_actual),
                        ("state_to", "=", wizard.estado_nuevo),
                        ("active", "=", True),
                    ],
                    limit=1,
                )
                wizard.transicion_id = transicion
                wizard.requiere_motivo = (
                    transicion.requires_reason if transicion else False
                )
                wizard.mensaje_confirmacion = (
                    transicion.confirmation_message if transicion else ""
                )
                wizard.profile_state_id = (
                    transicion.profile_state_id if transicion else False
                )
            else:
                wizard.transicion_id = False
                wizard.requiere_motivo = False
                wizard.mensaje_confirmacion = ""
                wizard.profile_state_id = False

    def action_confirmar(self):
        self.ensure_one()
        if not self.estado_nuevo:
            raise UserError(_("Debe seleccionar un nuevo estado."))

        Transition = self.env["benglish.student.lifecycle.transition"]
        valida, mensaje, transicion = Transition.validar_transicion(
            self.estado_actual, self.estado_nuevo
        )
        if not valida:
            raise ValidationError(
                _("Transición de estado no permitida:\n" "De: %s\nA: %s\n\n%s")
                % (
                    self._get_state_label(self.estado_actual),
                    self._get_state_label(self.estado_nuevo),
                    mensaje,
                )
            )

        if transicion and transicion.requires_reason and not self.motivo:
            raise ValidationError(
                _("Esta transición requiere indicar un motivo para continuar.")
            )

        vals = {"state": self.estado_nuevo}
        if self.estado_nuevo == "withdrawn":
            if self.motivo:
                vals["withdrawal_reason"] = self.motivo
            vals["withdrawal_date"] = fields.Date.context_today(self)
        if transicion and transicion.profile_state_id:
            vals["profile_state_id"] = transicion.profile_state_id.id
            if self.motivo:
                vals["motivo_bloqueo"] = self.motivo

        ctx = {
            "motivo_cambio_estado": self.motivo,
            "origen_cambio_estado": "wizard",
            "origen_edicion": "wizard",
        }
        if transicion and transicion.profile_state_id:
            ctx["skip_profile_transition_validation"] = True

        self.student_id.with_context(**ctx).write(vals)

        body_html = _(
            "<strong>Cambio de Estado del Estudiante</strong><br/>"
            "<ul>"
            "<li>Estado anterior: %s</li>"
            "<li>Nuevo estado: %s</li>"
            "<li>Motivo: %s</li>"
            "<li>Realizado por: %s</li>"
            "</ul>"
        ) % (
            self._get_state_label(self.estado_actual),
            self._get_state_label(self.estado_nuevo),
            self.motivo or _("No especificado"),
            self.env.user.name,
        )

        # Mark the body as safe HTML so mail.thread won't escape it
        self.student_id.message_post(
            body=Markup(body_html),
        )

        return {"type": "ir.actions.act_window_close"}

    def action_cancelar(self):
        return {"type": "ir.actions.act_window_close"}
