# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Marca si el contacto pertenece a un estudiante del sistema académico.
    is_student = fields.Boolean(string="Es Estudiante", default=False)
