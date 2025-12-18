# -*- coding: utf-8 -*-

from odoo import models, fields, api, osv
from datetime import datetime, timedelta, date, time
from odoo.exceptions import AccessError, UserError, ValidationError

class ResPartnerEconomicActivity(models.Model):

    _name = 'res.partner.economic.activity'

    code = fields.Char(string='Codigo')
    name = fields.Char('Actividad Eco.')
