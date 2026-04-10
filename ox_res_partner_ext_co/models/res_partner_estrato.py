# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartnerEstrato(models.Model):

    _name = 'res.partner.estrato'
    _description = 'Estrato Socioeconómico'
    _order = 'codigo'

    codigo = fields.Char('Código', required=True)
    name = fields.Char('Nombre', required=True)
    descripcion = fields.Text('Descripción')
