# -*- coding: utf-8 -*-
# STUB TEMPORAL — Solo existe para permitir la desinstalación limpia.
# Odoo tiene en ir.model.data referencias a 'luker.identity.type' de versiones anteriores.
# Este stub permite que el proceso de uninstall pueda eliminar esos registros sin error.
# Una vez desinstalado e instalado limpio, este archivo puede eliminarse.
from odoo import models, fields


class LukerIdentityTypeStub(models.Model):
    _name        = 'luker.identity.type'
    _description = 'Stub — Tipo de Identidad (legacy, para desinstalación)'

    name             = fields.Char(string='Nombre')
    code             = fields.Char(string='Código')
    sequence         = fields.Integer(string='Secuencia', default=10)
    can_be_primary   = fields.Boolean(string='Puede ser primaria', default=True)
    active           = fields.Boolean(string='Activo', default=True)
