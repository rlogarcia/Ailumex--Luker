# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    portal_must_change_password = fields.Boolean(
        string="Portal: Debe cambiar contraseña",
        default=False,
        help="Si está activo, el usuario deberá cambiar la contraseña al ingresar al portal.",
    )
    portal_password_changed_at = fields.Datetime(
        string="Portal: Último cambio de contraseña",
        help="Fecha del último cambio de contraseña realizado desde el portal.",
    )
