from odoo import models, fields, api


class PersonDepends(models.Model):
    _name = 'person.depends'
    _description = 'Personal Dependency'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', tracking=True)
    ref = fields.Char(string='Reference', tracking=True)
    age = fields.Integer(string='Age', tracking=True)
    relationship = fields.Char(string='Relationship', required=True)
    person_id = fields.Many2one('personal.info', string='Depends To', tracking=True, required=True)
    person_gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender', related='person_id.gender')


    @api.model
    def create(self, vals):
        vals['ref'] = self.env['ir.sequence'].next_by_code('person.depends')
        return super(PersonDepends, self).create(vals)
