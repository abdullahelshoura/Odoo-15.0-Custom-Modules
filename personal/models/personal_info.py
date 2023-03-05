from datetime import date
from odoo import models, fields, api, _
from dateutil import relativedelta
from odoo.exceptions import UserError, ValidationError


class PersonalInfo(models.Model):
    _name = 'personal.info'
    _description = 'Personal Information'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {"res.partner": "partner_id"}

    partner_id = fields.Many2one('res.partner', string='Partner ID', required=True, ondelete='cascade')
    ref = fields.Char(string='Reference', tracking=True)
    birthdate = fields.Date(string="Date Of Birth", tracking=True)
    age = fields.Integer(string='Age', compute='_compute_age', inverse='_compute_age_inverse', search='_search_age',
                         tracking=True)
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender', tracking=True)
    tags = fields.Many2many('personal.tag', string="Custom Tags")
    debt = fields.Float(string='Debt')
    total_orders_amount = fields.Float(compute='_compute_total_orders_amount')
    total_amount = fields.Float(compute='_compute_total_amount')
    state = fields.Selection([
        ('sale_order', 'Sale Order'),
        ('done', 'Done')], default='sale_order', string="Status", required=True)
    debit_account_id = fields.Many2one('account.account', string='Debit account',
                                       domain="[('deprecated', '=', False), ('is_off_balance', '=', False)]")
    credit_account_id = fields.Many2one('account.account', string='Credit account',
                                        domain="[('deprecated', '=', False), ('is_off_balance', '=', False)]")

    journal_id = fields.Integer(string='Journal', default='1')
    depends_ids = fields.One2many('person.depends', 'person_id', string='Person Dependency')
    hide_depends_age = fields.Boolean(string='Hide Depends Ages')
    @api.model
    def create(self, vals):
        vals['ref'] = self.env['ir.sequence'].next_by_code('personal.info')
        return super(PersonalInfo, self).create(vals)

    @api.depends('birthdate')
    def _compute_age(self):
        for rec in self:
            today = date.today()
            if rec.birthdate:
                rec.age = today.year - rec.birthdate.year
            else:
                rec.age = 0

    @api.depends('age')
    def _compute_age_inverse(self):
        today = date.today()
        for rec in self:
            rec.birthdate = today - relativedelta.relativedelta(years=rec.age)

    def _search_age(self, operator, value):
        birthdate = date.today() - relativedelta.relativedelta(years=value)
        start_of_year = birthdate.replace(day=1, month=1)
        end_of_year = birthdate.replace(day=31, month=12)
        return [('birthdate', '>=', start_of_year), ('birthdate', '<=', end_of_year)]

    def action_view_orders(self):
        # action = self.env.ref('sale.action_orders').read()[0]
        # action['domain'] = [('partner_id.id', '=', self.partner_id.id)]
        # return action
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Orders',

            'res_model': 'sale.order',
            'view_type': 'form',
            'domain': [('partner_id.id', '=', self.partner_id.id)],
            'view_mode': 'tree,form',
            'target': 'current',
        }

    @api.depends('debt', 'total_amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.debt + rec.total_orders_amount

    def _compute_total_orders_amount(self):
        orders = self.env['sale.order'].search([('partner_id.id', '=', self.partner_id.id)])
        total = 0.0
        for order in orders:
            total = total + order.amount_total
        self.total_orders_amount = total

    def action_sale_order(self):
        for rec in self:
            rec.state = 'sale_order'

    def create_journal(self, adjustment_type=None):
        cid = self.env.company.id
        for rec in self:
            rec.state = 'done'

        debit_vals = {
            'name': self.partner_id.name + ' / Purchases',
            'debit': abs(self.total_amount),
            'credit': 0.0,
            'partner_id': self.partner_id.id,
            'ref': self.ref,
            'account_id': self.debit_account_id.id,
            'tax_line_id': adjustment_type == 'debit' and self.tax_id.id or False,
        }
        credit_vals = {
            'name': self.partner_id.name + ' / Purchases',
            'debit': 0.0,
            'credit': abs(self.total_amount),
            'partner_id': self.partner_id.id,
            'ref': self.ref,
            'account_id': self.credit_account_id.id,
            'tax_line_id': adjustment_type == 'credit' and self.tax_id.id or False,
        }
        vals = {
            'journal_id': self.journal_id,
            'date': date.today(),
            'state': 'draft',
            'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
        }
        move = self.env['account.move'].create(vals)
        return move


        #
    def return_journal(self):

        return {
            'type': 'ir.actions.act_window',
            'name': self.partner_id.name+' Journals',
            'res_model': 'account.move.line',
            'view_type': 'form',
            'domain': [('partner_id.id', '=', self.partner_id.id)],
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def cancel_journal(self):
        action = self.env.ref('personal.cancel_journal_action_window').read()[0]
        for rec in self:
            rec.state = 'sale_order'
        return action


