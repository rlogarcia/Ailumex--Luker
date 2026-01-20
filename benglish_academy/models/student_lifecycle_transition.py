# -*- coding: utf-8 -*-
"""
Transiciones válidas para el estado del estudiante (ciclo de vida).
"""

from odoo import api, fields, models, _


class StudentLifecycleTransition(models.Model):
    _name = "benglish.student.lifecycle.transition"
    _description = "Transición de Estado del Estudiante"
    _order = "state_from, sequence"
    _rec_name = "display_name"

    display_name = fields.Char(
        compute="_compute_display_name",
        store=True,
    )

    state_from = fields.Selection(
        selection=lambda self: self._get_student_state_selection(),
        string="Estado Origen",
        required=True,
        index=True,
    )
    state_to = fields.Selection(
        selection=lambda self: self._get_student_state_selection(),
        string="Estado Destino",
        required=True,
        index=True,
    )
    sequence = fields.Integer(
        string="Secuencia",
        default=10,
        help="Orden de aparición en listas.",
    )
    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Transiciones inactivas no serán permitidas.",
    )
    requires_reason = fields.Boolean(
        string="Requiere Motivo",
        default=False,
        help="Si está activo, se debe indicar un motivo para realizar esta transición.",
    )
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="benglish_lifecycle_transition_group_rel",
        column1="transition_id",
        column2="group_id",
        string="Grupos Permitidos",
        help="Si se define, solo estos grupos pueden ejecutar la transición.",
    )
    description = fields.Text(
        string="Descripción",
        help="Descripción del propósito de esta transición.",
    )
    confirmation_message = fields.Text(
        string="Mensaje de Confirmación",
        help="Mensaje que se muestra al usuario antes de confirmar la transición.",
    )
    profile_state_id = fields.Many2one(
        comodel_name="benglish.student.profile.state",
        string="Estado de Perfil",
        help=(
            "Estado de perfil que se asignará automáticamente al estudiante al "
            "ejecutar esta transición. Controla los permisos del portal."
        ),
    )

    _sql_constraints = [
        (
            "unique_transition",
            "UNIQUE(state_from, state_to)",
            "Ya existe una transición entre estos estados.",
        ),
        (
            "no_self_transition",
            "CHECK(state_from != state_to)",
            "No se puede crear una transición de un estado a sí mismo.",
        ),
    ]

    @api.model
    def _get_student_state_selection(self):
        selection = self.env["benglish.student"]._fields["state"].selection
        return selection(self.env["benglish.student"]) if callable(selection) else selection

    def _get_state_label(self, state_code):
        selection = dict(self._get_student_state_selection())
        return selection.get(state_code, state_code or "")

    @api.depends("state_from", "state_to")
    def _compute_display_name(self):
        for record in self:
            if record.state_from and record.state_to:
                record.display_name = (
                    f"{self._get_state_label(record.state_from)} → "
                    f"{self._get_state_label(record.state_to)}"
                )
            else:
                record.display_name = _("Nueva Transición")

    def puede_transicionar(self, user=None):
        """Valida si el usuario puede ejecutar la transición."""
        self.ensure_one()
        user = user or self.env.user

        if not self.active:
            return (False, _("Esta transición no está activa."))

        if self.group_ids:
            if not (user.groups_id & self.group_ids):
                return (False, _("No tiene permisos para realizar esta transición."))

        return (True, _("Transición permitida."))

    @api.model
    def get_transiciones_permitidas(self, state_from, user=None):
        """Retorna transiciones permitidas desde un estado origen."""
        user = user or self.env.user
        transiciones = self.search(
            [
                ("state_from", "=", state_from),
                ("active", "=", True),
            ]
        )

        permitidas = self.env["benglish.student.lifecycle.transition"]
        for trans in transiciones:
            puede, _ = trans.puede_transicionar(user)
            if puede:
                permitidas |= trans
        return permitidas

    @api.model
    def get_estados_destino_permitidos(self, state_from, user=None):
        transiciones = self.get_transiciones_permitidas(state_from, user=user)
        return transiciones.mapped("state_to")

    @api.model
    def validar_transicion(self, state_from, state_to, user=None):
        user = user or self.env.user

        transicion = self.search(
            [
                ("state_from", "=", state_from),
                ("state_to", "=", state_to),
                ("active", "=", True),
            ],
            limit=1,
        )

        if not transicion:
            inactiva = self.search(
                [
                    ("state_from", "=", state_from),
                    ("state_to", "=", state_to),
                    ("active", "=", False),
                ],
                limit=1,
            )
            if inactiva:
                return (False, _("Esta transición existe pero está desactivada."), False)
            return (False, _("No existe una transición válida entre estos estados."), False)

        puede, mensaje = transicion.puede_transicionar(user)
        if not puede:
            return (False, mensaje, False)

        return (True, mensaje, transicion)
