# -*- coding: utf-8 -*-

from odoo import models, fields, api, osv
from datetime import datetime, timedelta, date, time
from odoo.exceptions import AccessError, UserError, ValidationError

class ResPartnerSociety(models.Model):

    _name = 'res.partner.society'

    name = fields.Char('Tipo Sociedad')
