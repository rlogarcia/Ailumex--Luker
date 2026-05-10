# -*- coding: utf-8 -*-
# Catálogo configurable de roles operativos SISPAR
from odoo import models, fields


class LukerOperationRol(models.Model):
    _name        = 'luker.operation.rol'
    _description = 'Rol Operativo SISPAR'
    _order       = 'sequence, nom_rol'
    _rec_name    = 'nom_rol'

    nom_rol     = fields.Char(string='Nombre del rol', required=True)
    cod_rol     = fields.Char(string='Código', required=True)
    descripcion = fields.Text(string='Descripción')
    sequence    = fields.Integer(string='Secuencia', default=10)
    activo      = fields.Boolean(string='Activo', default=True)

    # Permisos operativos
    puede_aplicar    = fields.Boolean(string='Puede aplicar instrumentos', default=False)
    puede_supervisar = fields.Boolean(string='Puede supervisar aplicadores', default=False)
    puede_coordinar  = fields.Boolean(string='Puede coordinar campañas', default=False)

    _sql_constraints = [
        ('cod_rol_unique', 'UNIQUE(cod_rol)', 'El código del rol debe ser único.'),
    ]
