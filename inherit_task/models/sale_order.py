from odoo import api, fields, models
import json
import odoo.addons.decimal_precision as dp


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    discount_amount = fields.Float(string='Discount Amount')
    margin = fields.Float(string="Margin (%)")

    @api.onchange('price_unit', 'product_uom', 'product_uom_qty', 'tax_id', 'discount_amount', 'margin')
    def _onchange_discount(self):
        if self.product_id:
            self.discount = ((self.discount_amount / ((self.price_unit or 1.0) * self.product_uom_qty)) * 100) - self.margin

    def _prepare_invoice_line(self, sequence):
        res = super(SaleOrderLine, self)._prepare_invoice_line()
        res.update({'discount_amount': self.discount_amount, 'margin': self.margin,'discount_percent':(self.discount_amount/(self.price_unit or 1))*100,})

        return res




class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    margin = fields.Float(string='Margin')
    discount_amount = fields.Float(string='Discount Amount')
    discount_percent = fields.Float(string='Disc.(%)', store=True,readonly=True)
