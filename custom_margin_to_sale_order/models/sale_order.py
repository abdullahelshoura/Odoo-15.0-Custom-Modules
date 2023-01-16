from odoo import api, fields, models
import json
import odoo.addons.decimal_precision as dp
from odoo.addons.account.models.account_move import AccountMoveLine

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('order_line.tax_id', 'order_line.price_unit', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals_json(self):
        def compute_taxes(order_line):
            price = order_line.price_unit * (1 + ((order_line.margin or 0.0 ) / 100.0) - (order_line.discount or 0.0) / 100.0)
            order = order_line.order_id
            return order_line.tax_id._origin.compute_all(price, order.currency_id, order_line.product_uom_qty,
                                                         product=order_line.product_id,
                                                         partner=order.partner_shipping_id)

        account_move = self.env['account.move']
        for order in self:
            tax_lines_data = account_move._prepare_tax_lines_data_for_totals_from_object(order.order_line,
                                                                                         compute_taxes)
            tax_totals = account_move._get_tax_totals(order.partner_id, tax_lines_data, order.amount_total,
                                                      order.amount_untaxed, order.currency_id)
            order.tax_totals_json = json.dumps(tax_totals)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    discount_amount = fields.Float(compute='_compute_discount_amount', inverse='_onchange_discount', store=True)
    margin = fields.Float(string='Margin (%)', digits='Margin', default=0.0)

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id','margin')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            if line.product_uom_qty and line.margin:
                price = price + ((line.margin / 100) * line.price_unit)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                    'account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])

    @api.depends('discount', 'price_unit')
    def _compute_discount_amount(self):
        for rec in self:
            rec.discount_amount = (rec.discount / 100) * rec.price_unit

    @api.onchange('product_id', 'price_unit', 'product_uom', 'product_uom_qty', 'tax_id','discount_amount')
    def _onchange_discount(self):
        for rec in self:
            if rec.product_id:
                rec.discount = ((rec.discount_amount / (
                            (rec.price_unit or 1.0) * rec.product_uom_qty)) * 100)
    def _prepare_invoice_line(self,**optional_values):
        res = super(SaleOrderLine,self)._prepare_invoice_line()
        res['margin'] = self.margin
        return res


class AccountMove(models.Model):
    _inherit = 'account.move'
    def _recompute_tax_lines(self, recompute_tax_base_amount=False, tax_rep_lines_to_recompute=None):
        """ Compute the dynamic tax lines of the journal entry.

        :param recompute_tax_base_amount: Flag forcing only the recomputation of the `tax_base_amount` field.
        """
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            ''' Serialize the dictionary values to be used in the taxes_map.
            :param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
            :return: A string representing the values.
            '''
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            ''' Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            '''
            move = base_line.move_id

            if move.is_invoice(include_receipts=True):
                handle_price_include = True
                sign = -1 if move.is_inbound() else 1
                quantity = base_line.quantity
                is_refund = move.move_type in ('out_refund', 'in_refund')
                price_unit_wo_discount = sign * base_line.price_unit * (1 + ((base_line.margin or 0.0)/100.0) - (base_line.discount / 100.0))
            else:
                handle_price_include = False
                quantity = 1.0
                tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
                is_refund = (tax_type == 'sale' and base_line.debit) or (tax_type == 'purchase' and base_line.credit)
                price_unit_wo_discount = base_line.amount_currency

            return base_line.tax_ids._origin.with_context(force_sign=move._get_tax_force_sign()).compute_all(
                price_unit_wo_discount,
                currency=base_line.currency_id,
                quantity=quantity,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=is_refund,
                handle_price_include=handle_price_include,
                include_caba_tags=move.always_tax_exigible,
            )

        taxes_map = {}

        # ==== Add tax lines ====
        to_remove = self.env['account.move.line']
        for line in self.line_ids.filtered('tax_repartition_line_id'):
            grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
            grouping_key = _serialize_tax_grouping_key(grouping_dict)
            if grouping_key in taxes_map:
                # A line with the same key does already exist, we only need one
                # to modify it; we have to drop this one.
                to_remove += line
            else:
                taxes_map[grouping_key] = {
                    'tax_line': line,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                }
        if not recompute_tax_base_amount:
            self.line_ids -= to_remove

        # ==== Mount base lines ====
        for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
            # Don't call compute_all if there is no tax.
            if not line.tax_ids:
                if not recompute_tax_base_amount:
                    line.tax_tag_ids = [(5, 0, 0)]
                continue

            compute_all_vals = _compute_base_line_taxes(line)

            # Assign tags on base line
            if not recompute_tax_base_amount:
                line.tax_tag_ids = compute_all_vals['base_tags'] or [(5, 0, 0)]

            for tax_vals in compute_all_vals['taxes']:
                grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)

                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

                taxes_map_entry = taxes_map.setdefault(grouping_key, {
                    'tax_line': None,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                })
                taxes_map_entry['amount'] += tax_vals['amount']
                taxes_map_entry['tax_base_amount'] += self._get_base_amount_to_display(tax_vals['base'], tax_repartition_line, tax_vals['group'])
                taxes_map_entry['grouping_dict'] = grouping_dict

        # ==== Pre-process taxes_map ====
        taxes_map = self._preprocess_taxes_map(taxes_map)

        # ==== Process taxes_map ====
        for taxes_map_entry in taxes_map.values():
            # The tax line is no longer used in any base lines, drop it.
            if taxes_map_entry['tax_line'] and not taxes_map_entry['grouping_dict']:
                if not recompute_tax_base_amount:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            currency = self.env['res.currency'].browse(taxes_map_entry['grouping_dict']['currency_id'])

            # Don't create tax lines with zero balance.
            if currency.is_zero(taxes_map_entry['amount']):
                if taxes_map_entry['tax_line'] and not recompute_tax_base_amount:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            # tax_base_amount field is expressed using the company currency.
            tax_base_amount = currency._convert(taxes_map_entry['tax_base_amount'], self.company_currency_id, self.company_id, self.date or fields.Date.context_today(self))

            # Recompute only the tax_base_amount.
            if recompute_tax_base_amount:
                if taxes_map_entry['tax_line']:
                    taxes_map_entry['tax_line'].tax_base_amount = tax_base_amount
                continue

            balance = currency._convert(
                taxes_map_entry['amount'],
                self.company_currency_id,
                self.company_id,
                self.date or fields.Date.context_today(self),
            )
            to_write_on_line = {
                'amount_currency': taxes_map_entry['amount'],
                'currency_id': taxes_map_entry['grouping_dict']['currency_id'],
                'debit': balance > 0.0 and balance or 0.0,
                'credit': balance < 0.0 and -balance or 0.0,
                'tax_base_amount': tax_base_amount,
            }

            if taxes_map_entry['tax_line']:
                # Update an existing tax line.
                if tax_rep_lines_to_recompute and taxes_map_entry['tax_line'].tax_repartition_line_id not in tax_rep_lines_to_recompute:
                    continue

                taxes_map_entry['tax_line'].update(to_write_on_line)
            else:
                # Create a new tax line.
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)

                if tax_rep_lines_to_recompute and tax_repartition_line not in tax_rep_lines_to_recompute:
                    continue

                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                taxes_map_entry['tax_line'] = create_method({
                    **to_write_on_line,
                    'name': tax.name,
                    'move_id': self.id,
                    'company_id': self.company_id.id,
                    'company_currency_id': self.company_currency_id.id,
                    'tax_base_amount': tax_base_amount,
                    'exclude_from_invoice_tab': True,
                    **taxes_map_entry['grouping_dict'],
                })

            if in_draft_mode:
                taxes_map_entry['tax_line'].update(taxes_map_entry['tax_line']._get_fields_onchange_balance(force_computation=True))



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    discount_amount = fields.Float(compute='_compute_discount_amount', inverse='_onchange_discount', store=True)
    margin = fields.Float(string='Margin (%)', digits='Margin',default=0.0)

    @api.depends('discount', 'price_unit')
    def _compute_discount_amount(self):
        for rec in self:
            rec.discount_amount = (rec.discount / 100) * rec.price_unit

    @api.onchange('product_id', 'price_unit', 'quantity', 'discount_amount')
    def _onchange_discount(self):
        for rec in self:
            if rec.product_id:
                rec.discount = ((rec.discount_amount / (
                        (rec.price_unit or 1.0) * rec.quantity)) * 100)

    def _get_price_total_and_subtotal(self, price_unit=None, quantity=None, discount=None, margin=None, currency=None, product=None, partner=None, taxes=None, move_type=None):
        self.ensure_one()
        return self._get_price_total_and_subtotal_model(
            price_unit=self.price_unit if price_unit is None else price_unit,
            quantity=self.quantity if quantity is None else quantity,
            discount=self.discount if discount is None else discount,
            margin=self.margin if margin is None else margin,
            currency=self.currency_id if currency is None else currency,
            product=self.product_id if product is None else product,
            partner=self.partner_id if partner is None else partner,
            taxes=self.tax_ids if taxes is None else taxes,
            move_type=self.move_id.move_type if move_type is None else move_type,
        )
    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, margin, currency, product, partner, taxes, move_type):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param currency:    The line's currency.
        :param product:     The line's product.
        :param partner:     The line's partner.
        :param taxes:       The applied taxes.
        :param move_type:   The type of the move.
        :return:            A dictionary containing 'price_subtotal' & 'price_total'.
        '''
        res = {}
        # Compute 'price_subtotal'.
        line_discount_price_unit = price_unit * (1 - (discount / 100.0))
        if quantity and margin:
            line_discount_price_unit = line_discount_price_unit + (price_unit*margin/100.0)
        subtotal = quantity * line_discount_price_unit
        # Compute 'price_total'.
        if taxes:
            taxes_res = taxes._origin.with_context(force_sign=1).compute_all(line_discount_price_unit,
                                                                             quantity=quantity, currency=currency,
                                                                             product=product, partner=partner,
                                                                             is_refund=move_type in (
                                                                             'out_refund', 'in_refund'))
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        # In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'margin', 'tax_ids')

        for vals in vals_list:
            move = self.env['account.move'].browse(vals['move_id'])
            vals.setdefault('company_currency_id',
                            move.company_id.currency_id.id)  # important to bypass the ORM limitation where monetary fields are not rounded; more info in the commit message

            # Ensure balance == amount_currency in case of missing currency or same currency as the one from the
            # company.
            currency_id = vals.get('currency_id') or move.company_id.currency_id.id
            if currency_id == move.company_id.currency_id.id:
                balance = vals.get('debit', 0.0) - vals.get('credit', 0.0)
                vals.update({
                    'currency_id': currency_id,
                    'amount_currency': balance,
                })
            else:
                vals['amount_currency'] = vals.get('amount_currency', 0.0)

            if move.is_invoice(include_receipts=True):
                currency = move.currency_id
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                taxes = self.new({'tax_ids': vals.get('tax_ids', [])}).tax_ids
                tax_ids = set(taxes.ids)
                taxes = self.env['account.tax'].browse(tax_ids)

                # Ensure consistency between accounting & business fields.
                # As we can't express such synchronization as computed fields without cycling, we need to do it both
                # in onchange and in create/write. So, if something changed in accounting [resp. business] fields,
                # business [resp. accounting] fields are recomputed.
                if any(vals.get(field) for field in ACCOUNTING_FIELDS):
                    price_subtotal = self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        vals.get('margin',0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.move_type,
                    ).get('price_subtotal', 0.0)
                    vals.update(self._get_fields_onchange_balance_model(
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        vals['amount_currency'],
                        move.move_type,
                        currency,
                        taxes,
                        price_subtotal
                    ))
                    vals.update(self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        vals.get('margin', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.move_type,
                    ))
                elif any(vals.get(field) for field in BUSINESS_FIELDS):
                    vals.update(self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        vals.get('margin', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.move_type,
                    ))
                    vals.update(self._get_fields_onchange_subtotal_model(
                        vals['price_subtotal'],
                        move.move_type,
                        currency,
                        move.company_id,
                        move.date,
                    ))

        lines = models.Model.create(self, vals_list)

        moves = lines.mapped('move_id')
        if self._context.get('check_move_validity', True):
            moves._check_balanced()
        moves.filtered(lambda m: m.state == 'posted')._check_fiscalyear_lock_date()
        lines.filtered(lambda l: l.parent_state == 'posted')._check_tax_lock_date()
        moves._synchronize_business_models({'line_ids'})

        return lines





