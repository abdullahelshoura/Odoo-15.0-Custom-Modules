# -*- coding: utf-8 -*-
# from odoo import http


# class Abdullah(http.Controller):
#     @http.route('/abdullah/abdullah', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/abdullah/abdullah/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('abdullah.listing', {
#             'root': '/abdullah/abdullah',
#             'objects': http.request.env['abdullah.abdullah'].search([]),
#         })

#     @http.route('/abdullah/abdullah/objects/<model("abdullah.abdullah"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('abdullah.object', {
#             'object': obj
#         })
