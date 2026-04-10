# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartnerDiscapacidad(models.Model):

    _name = 'res.partner.discapacidad'
    _description = 'Tipo de Discapacidad'
    _order = 'codigo'

    codigo = fields.Char('Código', required=True)
    tipo = fields.Char('Tipo', required=True)
    name = fields.Char('Nombre', required=True)
