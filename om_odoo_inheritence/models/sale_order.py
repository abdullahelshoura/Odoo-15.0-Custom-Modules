from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    confirmed_user_id = fields.Many2one('res.users',string="Confirmed User")

    #Inherit function method
    def action_confirm(self):
        # Super built in function to inherit
        # the function action_confirm()
        # from a model SaleOrder in sale module
        super(SaleOrder,self).action_confirm()
        self.confirmed_user_id = self.env.user.id