# -*- coding: utf-8 -*-
from odoo import http

# class ResPartnerExtCoMhel(http.Controller):
#     @http.route('/ox_res_partner_ext_co/ox_res_partner_ext_co/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ox_res_partner_ext_co/ox_res_partner_ext_co/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ox_res_partner_ext_co.listing', {
#             'root': '/ox_res_partner_ext_co/ox_res_partner_ext_co',
#             'objects': http.request.env['ox_res_partner_ext_co.ox_res_partner_ext_co'].search([]),
#         })

#     @http.route('/ox_res_partner_ext_co/ox_res_partner_ext_co/objects/<model("ox_res_partner_ext_co.ox_res_partner_ext_co"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ox_res_partner_ext_co.object', {
#             'object': obj
#         })