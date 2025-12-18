# -*- coding: utf-8 -*-

from odoo import models, fields, api, osv
from datetime import datetime, timedelta, date, time
from odoo.exceptions import AccessError, UserError, ValidationError


class ResCountryStateExt(models.Model):

    _inherit = 'res.country.state'
    city_ids = fields.One2many('res.city', 'state_id', string='Ciudades', readonly=False)
    

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            # Be sure name_search is symetric to name_get
            name = name.split(' / ')[-1]
            args = ['|', ('name', operator, name), ('code', operator, name)] + args
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)