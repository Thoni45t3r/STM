# -*- coding: utf-8 -*-
from odoo import http

# class AdhProcurement(http.Controller):
#     @http.route('/adh_procurement/adh_procurement/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/adh_procurement/adh_procurement/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('adh_procurement.listing', {
#             'root': '/adh_procurement/adh_procurement',
#             'objects': http.request.env['adh_procurement.adh_procurement'].search([]),
#         })

#     @http.route('/adh_procurement/adh_procurement/objects/<model("adh_procurement.adh_procurement"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('adh_procurement.object', {
#             'object': obj
#         })