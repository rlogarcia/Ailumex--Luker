# -*- coding: utf-8 -*-

from odoo import models, fields, api, osv
from datetime import datetime, timedelta, date, time
from odoo.exceptions import AccessError, UserError, ValidationError

class ResPartnerBankExt(models.Model):

    _inherit = 'res.partner.bank'

    type_account = fields.Selection([('Ahorros', 'Ahorros'), ('Corriente', 'Corriente')], string='Tipo cuenta')
