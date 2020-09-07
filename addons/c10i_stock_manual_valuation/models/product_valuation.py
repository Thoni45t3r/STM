# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

import calendar
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero
from odoo.addons import decimal_precision as dp
import time

class ProductValuation(models.Model):
    _name = 'product.valuation'
    _description = "Product Manual Periodic Valuation"
    _inherit = ['mail.thread']

    name = fields.Char('No', default='New Valuation', readonly=True, states={'draft': [('readonly', False)]})
    date_start = fields.Date('Start Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    date_stop = fields.Date('End Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', 'Valuation Journal', domain="[('type','=','general')]", required=True, readonly=True, states={'draft': [('readonly', False)]})
    product_id = fields.Many2one('product.product', 'Product', domain="[('categ_id.property_valuation','=','manual_periodic')]", required=True, readonly=True, states={'draft': [('readonly', False)]})
    move_ids = fields.Many2many('account.move', string='Journal Entries')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Posted')], string='Status', default='draft', index=True)

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.name = 'Valuation %s'%self.product_id.name
        else:
            self.name = 'New Valuation'

        if self.product_id and self.product_id.categ_id.property_stock_journal:
            self.journal_id = self.product_id.categ_id.property_stock_journal.id
        else:
            self.journal_id = False

        if self.product_id and self.product_id.cost_account_ids:
            self.product_cost_account_ids = map(lambda x: (4, x.id), self.product_id.cost_account_ids)
        elif self.product_id and self.product_id.categ_id.cost_account_categ_ids:
            self.product_cost_account_ids = map(lambda x: (4, x.id), self.product_id.categ_id.cost_account_categ_ids)
        else:
            self.product_cost_account_ids = []

        if self.product_id and self.product_id.cost_location_ids:
            self.product_cost_location_ids = map(lambda x: (4, x.id), self.product_id.cost_location_ids)
        elif self.product_id and self.product_id.categ_id.cost_location_categ_ids:
            self.product_cost_location_ids = map(lambda x: (4, x.id), self.product_id.categ_id.cost_location_categ_ids)
        else:
            self.product_cost_location_ids = []

    @api.multi
    def compute_product_value(self):
        self.ensure_one()
        AccountMove = self.env['account.move']
        AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False)
        MoveLine = self.env['stock.move']
        
        default_domain = [('date','>=',self.date_start),('date','<=',self.date_stop)]
        product = self.product_id
        #1. Select Opening Balance, both Qty and Value
        domain1 = default_domain[:]
        opening_account = product.property_stock_account_output or product.categ_id.property_stock_account_output_categ_id
        if not opening_account:
            raise ValidationError(_('Stock Output Account not Found. Please define it in Product Category or Product'))
        domain1.extend([('account_id','=',opening_account.id),
            ('product_id','=',product.id)])
        move_opening_bal = AccountMoveLine.search(domain1, limit=1)
        opening_qty = opening_value = 0.0
        if move_opening_bal:
            opening_qty = move_opening_bal.quantity
            opening_value = move_opening_bal.debit - move_opening_bal.credit
        print ".....................opening", opening_qty, opening_value
        #2. Select Purchase Movement, both Qty and Value
        purchase_qty = purchase_value = 0.0
        domain2 = default_domain[:]
        purchase_account = product.purchase_account_id or product.categ_id.purchase_account_categ_id
        if not purchase_account:
            raise ValidationError(_('Purchase Account not Found. Please define it in Product Category or Product'))
        domain2.extend([('account_id','=',purchase_account.id),
            ('product_id','=',product.id)])
        move_purchase = AccountMoveLine.search(domain2)
        if move_purchase:
            purchase_qty = move_purchase.quantity
            purchase_value = move_purchase.debit - move_purchase.credit
        print ".....................purchase", purchase_qty, purchase_value
        #3. Select Other Cost
        domain3 = default_domain[:]
        cost_accounts = product.cost_account_ids or product.categ_id.cost_account_categ_ids
        cost_account_locations = product.cost_location_ids or product.categ_id.cost_location_categ_ids
        if cost_accounts and cost_account_locations:
            domain3.extend(['|',('account_id','in',cost_accounts.ids),
                ('account_location_id','in',cost_account_locations.ids)])
            move_other_cost = AccountMoveLine.search(domain3)
        elif cost_accounts:
            domain3.append(('account_id','in',cost_accounts.ids))
            move_other_cost = AccountMoveLine.search(domain3)
        elif cost_account_locations:
            domain3.append(('account_location_id','in',cost_account_locations.ids))
            move_other_cost = AccountMoveLine.search(domain3)
        else:
            move_other_cost = []
        other_cost_amount = move_other_cost and sum(move_other_cost.mapped('balance')) or 0.0
        
        #4. Compute Average Price of all available product
        qty_available = opening_qty + purchase_qty
        value_available = opening_value + purchase_value + other_cost_amount
        avg_price = qty_available!=0.0 and value_available/qty_available or 0.0
        print ".....................q available", qty_available
        print ".....................v available", value_available
        print ".....................pruce", avg_price

        #5. Select Sale Product
        qty_sale = 0.0
        domain_sale = default_domain[:]
        sales_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
        if not sales_account:
            raise ValidationError(_('Stock Income Account not Found. Please define it in Product Category or Product'))
        domain_sale.extend([('product_id','=',product.id),
            ('account_id','=',sales_account.id)])
        move_sales = AccountMoveLine.search(domain_sale)
        if move_sales:
            qty_sale = sum(move_sales.mapped('quantity'))
        print ".....................sale", qty_sale
        #6. Compute Closing Balance
        qty_closing = qty_available - qty_sale
        value_closing = qty_closing * avg_price
        print ".....................closing", qty_closing
        print ".....................value closing", value_closing

        #7. Create Closing Entry at the end of the date
        valuation_account = product.categ_id.property_stock_valuation_account_id
        if not valuation_account:
            raise ValidationError(_('Stock Valuation Account not Found. Please define it in Product Category'))
        input_account = product.categ_id.stock_counterpart_valuation_account_categ_id
        if not input_account:
            raise ValidationError(_('Counterpart Valuation Account not Found. Please define it in Product Category or Product'))
        closing_move = AccountMove.create({
            'date': self.date_stop,
            'journal_id': self.journal_id.id,
            })
        move_line_dict = {
            'date': self.date_stop,
            'journal_id': self.journal_id.id,
            'name': 'Valuation %s'%product.name,
            'account_id': valuation_account.id,
            'product_id': product.id,
            'debit': value_closing, 
            'credit': 0.0,
            'price_unit': avg_price,
            'quantity': qty_closing,
            'move_id': closing_move.id
        }
        AccountMoveLine.create(move_line_dict)
        
        ct_move_line_dict = move_line_dict.copy()
        ct_move_line_dict['debit'] = 0.0
        ct_move_line_dict['credit'] = value_closing
        ct_move_line_dict['account_id'] = input_account.id
        AccountMoveLine.create(ct_move_line_dict)

        #8. Create Reclass Closing Entry at the begining of the next period
        opening_move = AccountMove.create({
            'date': (datetime.strptime(self.date_stop, DF) + \
                    relativedelta(days=+1)).strftime(DF),
            'journal_id': self.journal_id.id,
            })
        move_line_dict = {
            'date': (datetime.strptime(self.date_stop, DF) + \
                    relativedelta(days=+1)).strftime(DF),
            'journal_id': self.journal_id.id,
            'name': 'Reclass Valua Closing as Opening',
            'account_id': opening_account.id,
            'product_id': product.id,
            'debit': value_closing, 
            'credit': 0.0,
            'price_unit': avg_price,
            'quantity': qty_closing,
            'move_id': opening_move.id
        }
        AccountMoveLine.create(move_line_dict)
        
        ct_move_line_dict = move_line_dict.copy()
        ct_move_line_dict['debit'] = 0.0
        ct_move_line_dict['credit'] = value_closing
        ct_move_line_dict['account_id'] = valuation_account.id
        AccountMoveLine.create(ct_move_line_dict)

        self.move_ids = [(4,closing_move.id),(4,opening_move.id)]
        return (value_available - value_closing)

    @api.multi
    def post(self):
        for valuation in self:
            valuation.compute_product_value()
            valuation.state = 'done'
        return True

    @api.multi
    def cancel(self):
        for valuation in self:
            for move in valuation.move_ids:
                move.unlink()
            valuation.state = 'draft'