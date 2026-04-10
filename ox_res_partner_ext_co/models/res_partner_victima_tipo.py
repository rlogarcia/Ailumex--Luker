# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartnerVictimaTipo(models.Model):

    _name = 'res.partner.victima.tipo'
    _description = 'Tipo de Víctima de Conflicto Armado'
    _order = 'name'

    codigo = fields.Char('Código', required=True)
    name = fields.Char('Nombre', required=True)
    descripcion = fields.Text('Descripción')
