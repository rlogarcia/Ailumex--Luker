# -*- coding: utf-8 -*-

from odoo import models, fields, api, osv
from datetime import datetime, timedelta, date, time
from odoo.exceptions import AccessError, UserError, ValidationError

class Ciudad(models.Model):

    _name = 'res.city'
    _description = 'Ciudad'

    name = fields.Char('Nombre ciudad', required=True)
    state_id = fields.Many2one('res.country.state', string='Departamento', required=True)
    cod_depto = fields.Char('Cod. DIAN', required=False)
    cod_ciudad = fields.Char('Cod. Ciudad', required=False)
    zipcode = fields.Char('Cod. Zip', required=False)
    image = fields.Image(required=False)
    image_2 = fields.Image(required=False)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            # Be sure name_search is symetric to name_get
            name = name.split(' / ')[-1]
            args = ['|', ('name', operator, name), ('cod_ciudad', operator, name)] + args
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)
