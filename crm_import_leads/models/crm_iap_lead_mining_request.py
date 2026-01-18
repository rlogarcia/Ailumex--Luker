# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmIapLeadMiningRequest(models.Model):
    _inherit = 'crm.iap.lead.mining.request'

    def _default_user_id(self):
        return self.env.user if self.env.user.is_commercial_user else False

    user_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        default=_default_user_id,
        domain="[('share', '=', False), ('active', '=', True), ('is_commercial_user', '=', True)]",
    )
