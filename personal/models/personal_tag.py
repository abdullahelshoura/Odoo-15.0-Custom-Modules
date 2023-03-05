from odoo import api, fields, models, _


class PersonalTag(models.Model):
    _name = 'personal.tag'
    _description = 'Personal Tags'

    name = fields.Char(string='Name', required=True)
    color = fields.Integer(string='Color')

