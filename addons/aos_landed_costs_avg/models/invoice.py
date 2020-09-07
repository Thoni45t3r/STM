# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, RedirectWarning, ValidationError

class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    @api.one
    @api.depends('invoice_line_ids.subtotal', 'invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id', 'date_invoice', 'type')
    def _compute_amount(self):
        #=======================================================================
        # GET UNTAXED FROM SUBTOTAL
        #=======================================================================
        self.amount_untaxed = sum(line.subtotal for line in self.invoice_line_ids)
        #=======================================================================
        # GET INLAND FROM PRICE_SUBTOTAL
        self.amount_inland_total = sum(line.inland_value for line in self.invoice_line_ids)
        #=======================================================================
        self.amount_tax = sum(line.amount for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax + self.amount_inland_total
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self.date_invoice)
            amount_total_company_signed = currency_id.compute(self.amount_total, self.company_id.currency_id)
            amount_untaxed_signed = currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign
        
    
    landed_id = fields.Many2one('avg.landed.cost', string='Landed Cost',
        readonly=True, index=True, ondelete='restrict', copy=False,
        help="Link to the automatically generated from landed cost Items.")
    amount_inland = fields.Float(string='Amount Shipping Cost', required=False,
       readonly=True, states={'draft': [('readonly', False)]})
    amount_inland_total = fields.Monetary(string='Amount Inland',
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    
    def _prepare_invoice_line_from_po_line(self, line):
        vals = super(AccountInvoice, self)._prepare_invoice_line_from_po_line(line)
        vals['weight'] = line.weight
        vals['volume'] = line.volume
        vals['tot_weight'] = line.tot_weight
        vals['tot_volume'] = line.tot_volume
        vals['discount'] = line.discount
        vals['inland_unit'] = line.inland_unit
        vals['inland_value'] = line.inland_value
        return vals
    
    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        if self.currency_id:
            for line in self.invoice_line_ids.filtered(lambda r: r.purchase_line_id):
                line.price_unit = line.purchase_id.currency_id.compute(line.purchase_line_id.price_unit, self.currency_id, round=False)
                #===============================================================
                # ADD THIS LINE TO UPDATE CURRENCY ON LANDED
                line.inland_unit = line.purchase_id.currency_id.compute(line.inland_value / (line.quantity or 1.0), self.currency_id, round=False)
                line.inland_value = line.purchase_id.currency_id.compute((line.tot_weight / (sum(li.tot_weight for li in self.invoice_line_ids) or 1.0)) * self.amount_inland, self.currency_id, round=False)
                #===============================================================
    
    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(AccountInvoice, self)._onchange_partner_id()
        if self.purchase_id.currency_id:
            self.currency_id = self.purchase_id.currency_id.id
        return res
    
    # Load all unsold PO lines
    @api.onchange('purchase_id')
    def purchase_order_change(self):
        if not self.purchase_id:
            return {}
        if not self.partner_id:
            self.partner_id = self.purchase_id.partner_id.id
        #=======================================================================
        # THIS WILL DELETE INVOICE LINES
        self.invoice_line_ids = []
        #=======================================================================
        new_lines = self.env['account.invoice.line']
        for line in self.purchase_id.order_line - self.invoice_line_ids.mapped('purchase_line_id'):
            data = self._prepare_invoice_line_from_po_line(line)
            new_line = new_lines.new(data)
            new_line._set_additional_fields(self)
            new_lines += new_line
 
        self.invoice_line_ids += new_lines
        self.currency_id = self.purchase_id.currency_id.id
        self.amount_inland = self.purchase_id.amount_inland
        #print "===amount_inland====",self.amount_inland
        self.purchase_id = self.purchase_id.id
        return {}
    
    #===========================================================================
    # change base _anglo_saxon_purchase_move_lines property_account_creditor_price_difference into gain loss account get from journal
    #===========================================================================
    @api.model
    def _anglo_saxon_purchase_move_lines(self, i_line, res):
        """Return the additional move lines for purchase invoices and refunds.
        change
        i_line: An account.invoice.line object.
        res: The move line entries produced so far by the parent move_line_get.
        'account_id': amount_diff > 0 and 
        self.company_id.currency_exchange_journal_id.default_debit_account_id.id or 
        self.company_id.currency_exchange_journal_id.default_credit_account_id.id,
        """
        inv = i_line.invoice_id
        company_currency = inv.company_id.currency_id
        if i_line.product_id and i_line.product_id.valuation == 'real_time' and i_line.product_id.type == 'product':
            # get the fiscal position
            fpos = i_line.invoice_id.fiscal_position_id
            # get the price difference account at the product
            #===================================================================
            # USE THIS IF NOT MULTICURRENCY
            #===================================================================
            acc = i_line.product_id.property_account_creditor_price_difference
            if not acc:
                # if not found on the product get the price difference account at the category
                acc = i_line.product_id.categ_id.property_account_creditor_price_difference_categ
            acc = fpos.map_account(acc).id
            #===================================================================
            # reference_account_id is the stock input account
            reference_account_id = i_line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fpos)['stock_input'].id
            diff_res = []
            # CHANGE ROUNDING      
            account_prec = 10#inv.company_id.currency_id.decimal_places
            # calculate and write down the possible price difference between invoice price and product price
            for line in res:
                if line.get('invl_id', 0) == i_line.id and reference_account_id == line['account_id']:
                    valuation_price_unit = i_line.product_id.uom_id._compute_price(i_line.product_id.standard_price, i_line.uom_id)
                    if i_line.product_id.cost_method != 'standard' and i_line.purchase_line_id:
                        #for average/fifo/lifo costing method, fetch real cost price from incomming moves
                        valuation_price_unit = i_line.purchase_line_id.product_uom._compute_price(i_line.purchase_line_id.price_unit, i_line.uom_id)
                        stock_move_obj = self.env['stock.move']
                        valuation_stock_move = stock_move_obj.search([('purchase_line_id', '=', i_line.purchase_line_id.id), ('state', '=', 'done')])
                        if valuation_stock_move:
                            valuation_price_unit_total = 0
                            valuation_total_qty = 0
                            for val_stock_move in valuation_stock_move:
                                valuation_price_unit_total += val_stock_move.price_unit * val_stock_move.product_qty
                                valuation_total_qty += val_stock_move.product_qty
                            valuation_price_unit = valuation_price_unit_total / valuation_total_qty
                            valuation_price_unit = i_line.product_id.uom_id._compute_price(valuation_price_unit, i_line.uom_id)
                    if inv.currency_id.id != company_currency.id:
                        valuation_price_unit = company_currency.with_context(date=inv.date_invoice).compute(valuation_price_unit, inv.currency_id, round=False)
                        if not inv.company_id.currency_exchange_journal_id.default_debit_account_id and not inv.company_id.currency_exchange_journal_id.default_credit_account_id:
                            raise UserError(_('You should set account debit/credit exchange gain loss on journal (%s)' % inv.company_id.currency_exchange_journal_id.name))
                    if valuation_price_unit != i_line.price_unit and line['price_unit'] == i_line.price_unit and acc:
                        # price with discount and without tax included
                        price_unit = i_line.price_unit * (1 - (i_line.discount or 0.0) / 100.0)
                        tax_ids = []
                        if line['tax_ids']:
                            #line['tax_ids'] is like [(4, tax_id, None), (4, tax_id2, None)...]
                            taxes = self.env['account.tax'].browse([x[1] for x in line['tax_ids']])
                            price_unit = taxes.compute_all(price_unit, currency=inv.currency_id, quantity=1.0)['total_excluded']
                            for tax in taxes:
                                tax_ids.append((4, tax.id, None))
                                for child in tax.children_tax_ids:
                                    if child.type_tax_use != 'none':
                                        tax_ids.append((4, child.id, None))
                        price_before = line.get('price', 0.0)
                        line.update({'price': round(valuation_price_unit * line['quantity'], account_prec)})
                        diff_res.append({
                            'type': 'src',
                            'name': i_line.name[:64],
                            'price_unit': round(price_unit - valuation_price_unit, account_prec),
                            'quantity': line['quantity'],
                            'price': round(price_before - line.get('price', 0.0), account_prec),
                            'account_id': inv.currency_id.id == company_currency.id and acc or round(price_before - line.get('price', 0.0), account_prec) > 0 and inv.company_id.currency_exchange_journal_id.default_debit_account_id.id or inv.company_id.currency_exchange_journal_id.default_credit_account_id.id,
                            'product_id': line['product_id'],
                            'uom_id': line['uom_id'],
                            'account_analytic_id': line['account_analytic_id'],
                            'tax_ids': tax_ids,
                            })
                        #=======================================================
                        # DO UPDATE STANDARD PRICE IF YOU REVISE THE PRICE
                        #=======================================================
                        if i_line.product_id.qty_available > 0:
                            standard_price = i_line.product_id.standard_price
                            qty_available = i_line.product_id.qty_available
                            valuation_current = standard_price * qty_available
                            #po line - inv line
                            valuation_diff = round(valuation_price_unit * line['quantity'], account_prec) - round(price_unit * line['quantity'], account_prec)
                            standard_price_update = (valuation_current-valuation_diff)/qty_available
                            #this is update revisi if you have difference price on po and inv per product
                            i_line.product_id.write({'standard_price': standard_price_update})
            return diff_res
        return []
    
    @api.multi
    def action_move_create(self):
        result = super(AccountInvoice, self).action_move_create()
        #===========================================================
        # LANDED ONLY FOR VENDOR BILLS && LANDED TO RECONCILED
        #===========================================================
        for inv in self:
            company_currency = inv.company_id.currency_id
            if inv.landed_id and inv.type == 'in_invoice':
                if inv.currency_id.id != company_currency.id and inv.landed_id.date != inv.date_invoice:
                    raise UserError(_('Date Landed Cost and Date Invoice must be same'))
                landed_account_ids = inv.landed_id.account_move_id.line_ids.filtered(lambda r: r.account_id == inv.invoice_line_ids.mapped('account_id'))
                invoice_account_ids = inv.move_id.line_ids.filtered(lambda r: r.account_id == inv.invoice_line_ids.mapped('account_id'))
                if landed_account_ids and invoice_account_ids:
                    (landed_account_ids+invoice_account_ids).reconcile()
        return result

class AccountInvoiceLine(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.invoice.line'
    
    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity', 'inland_value',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
        'invoice_id.date_invoice')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        inland = 0
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        if self.inland_value:
            inland = self.inland_value
        
        self.subtotal = taxes['total_excluded'] if taxes else self.quantity * price
        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else (self.quantity * price)+inland
        if self.invoice_id.currency_id and self.invoice_id.company_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.with_context(date=self.invoice_id.date_invoice).compute(price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign
        self.subtotal = self.quantity * price
    
    cost_line_ids = fields.Many2many('avg.landed.cost.lines', 
            'avg_landed_cost_line_invoice_rel', 
            'invoice_line_id', 
            'avg_line_id', string='Invoice Lines', copy=False)
    quantity = fields.Float(string='Qty', digits=dp.get_precision('Product Unit of Measure'),
        required=True, default=1)
    discount = fields.Float(string='Disc (%)', digits=dp.get_precision('Discount'),
        default=0.0)
    inland_type = fields.Selection([
            #('equal', 'Equal'),
            #('by_quantity', 'By Qty'),
            ('by_weight', 'By Weight'),
            ('by_volume', 'By Volume'),
        ], string='Shipping Cost Type', default='by_weight', required=False,
            help='''By Weight = Amount Inland / Total Weight\n
                By Volume = Amount Inland / Total Volume''')
    weight = fields.Float('Unit Weight', default=1.0, digits=dp.get_precision('Stock Weight'))
    volume = fields.Float('Unit Volume', default=1.0)
    tot_weight = fields.Float('Tot. Weight', default=0.0, digits=dp.get_precision('Stock Weight'))
    tot_volume = fields.Float('Tot. Volume', default=0.0)
    inland_unit = fields.Float(string='Unit Ship.Cost', digits=dp.get_precision('Product Price'), default=0.0)
    inland_value = fields.Float(string='Total Ship.Cost', digits=dp.get_precision('Product Price'), default=0.0)
    subtotal = fields.Monetary(string='Subtotal',
        store=True, readonly=True, compute='_compute_price')
    price_subtotal = fields.Monetary(string='Net Amount',
        store=True, readonly=True, compute='_compute_price')
    price_subtotal_signed = fields.Monetary(string='Amount Signed', currency_field='company_currency_id',
        store=True, readonly=True, compute='_compute_price',
        help="Total amount in the currency of the company, negative for credit notes.")