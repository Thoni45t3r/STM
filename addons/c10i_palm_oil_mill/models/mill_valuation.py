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

class MillValuationCategory(models.Model):
    _name = 'mill.valuation.category'
    _description = "Cost Category"
    
    name = fields.Char('Name', required=True)
    bom_id = fields.Many2one('mrp.bom', 'Bill of Material', required=True)
    journal_id = fields.Many2one('account.journal', 'Journal', domain="[('type','=','general')]", required=True)
    production_cost_account_ids = fields.Many2many('account.account', 'mill_costing_account_rel', 'mill_costing_categ_id', 'account_id', string='Production Cost Account')
    production_cost_location_ids = fields.Many2many('account.location', 'mill_costing_account_location_rel', 'mill_costing_categ_id', 'account_location_id', string='Production Cost Account Location')
    active = fields.Boolean("Active", default=True)

    @api.onchange('bom_id')
    def onchange_product(self):
        if self.bom_id and self.bom_id.product_id and self.bom_id.product_id.categ_id and self.bom_id.product_id.categ_id.property_stock_journal:
            self.journal_id = self.bom_id.product_id.categ_id.property_stock_journal.id
        else:
            self.journal_id = False

class MillValuation(models.Model):
    _name = 'mill.valuation'
    _description = "Mill Valuation"
    _inherit = ['mail.thread']

    @api.model
    def _get_last_valuation(self):
        last_valuation = self.search([('id','>',0),('state','=','done')], order="date_stop desc", limit=1)
        if last_valuation:
            date_start = datetime.strptime(last_valuation.date_stop, DF) + relativedelta(days=+1)
            return date_start.strftime(DF)
        else:
            return (datetime.now() + relativedelta(month=1, day=1)).strftime(DF)

    name = fields.Char('No', default='New Valuation', readonly=True, states={'draft': [('readonly', False)],'need_sale_price': [('readonly', False)]})
    date_start = fields.Date('Start Date', required=True, readonly=True, states={'draft': [('readonly', False)],'need_sale_price': [('readonly', False)]}, default=_get_last_valuation)
    date_stop = fields.Date('As of Date', required=True, readonly=True, states={'draft': [('readonly', False)],'need_sale_price': [('readonly', False)]}, default=lambda self: datetime.now().strftime(DF))
    valuation_categ_id = fields.Many2one('mill.valuation.category', 'Category', required=True, readonly=True, states={'draft': [('readonly', False)],'need_sale_price': [('readonly', False)]})
    bom_id = fields.Many2one('mrp.bom', related='valuation_categ_id.bom_id', string='Bill of Material', required=True, readonly=True, states={'draft': [('readonly', False)],'need_sale_price': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', 'Journal', domain="[('type','=','general')]", required=True, readonly=True, states={'draft': [('readonly', False)],'need_sale_price': [('readonly', False)]})
    production_cost_account_ids = fields.Many2many('account.account', string='Production Cost Account', readonly=False, states={'draft': [('readonly', False)],'need_sale_price': [('readonly', False)]})
    production_cost_location_ids = fields.Many2many('account.location', string='Production Cost Account Location', readonly=False, states={'draft': [('readonly', False)],'need_sale_price': [('readonly', False)]})
    consume_product_lines = fields.One2many('mill.valuation.consume.line', 'valuation_id', 'Consume Lines', readonly=True, states={'draft': [('readonly', False)],'need_sale_price': [('readonly', False)]})
    produce_product_lines = fields.One2many('mill.valuation.produce.line', 'valuation_id', 'Produce Lines', readonly=True, states={'draft': [('readonly', False)],'need_sale_price': [('readonly', False)]})
    move_ids = fields.Many2many('account.move', string='Journal Entries')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('need_sale_price', 'Sale Price Confirmation'),
        ('done', 'Done')], string='Status', default='draft', index=True)

    @api.onchange('date_stop')
    def onchange_date_stop(self):
        if self.date_stop < self.date_start:
            self.date_stop = datetime.now().strftime(DF)
            return {'warning': {
                    'title': _('Wrong Entry'),
                    'message': _('Last Valuation was made at %s. \
                        You cannot create valuation again for \
                        the previous date of the last valuation')%(datetime.strptime(self.date_start, DF) + \
                                        relativedelta(days=-1)).strftime('%d/%m/%Y'),
                    }
            }
        elif self.date_stop > datetime.now().strftime(DF):
            self.date_stop = datetime.now().strftime(DF)
            return {
                'warning': {
                    'title': _('Wrong Entry'),
                    'message': _('You cannot create valuation greater than todays date'),
                    }
                }


    @api.onchange('valuation_categ_id')
    def onchange_product(self):
        if self.valuation_categ_id:
            self.name = 'Valuation %s'%self.valuation_categ_id.name
        else:
            self.name = 'New Valuation'

        if self.valuation_categ_id and self.valuation_categ_id.journal_id:
            self.journal_id = self.valuation_categ_id.journal_id.id
        else:
            self.journal_id = False

        if self.valuation_categ_id.production_cost_account_ids:
            # self.production_cost_account_ids = map(lambda x: (4, x.id), self.valuation_categ_id.production_cost_account_ids)
            self.production_cost_account_ids = [(6,0,self.valuation_categ_id.production_cost_account_ids.ids)]
        else:
            self.production_cost_account_ids = []

        if self.valuation_categ_id.production_cost_location_ids:
            self.production_cost_location_ids = map(lambda x: (4, x.id), self.valuation_categ_id.production_cost_location_ids)
        else:
            self.production_cost_location_ids = []

    @api.model
    def create(self, vals):
        if 'production_cost_account_ids' in vals.keys():
            to_be_added = []
            for item in vals['production_cost_account_ids']:
                if item[0]==1:
                    to_be_added.append(item[1])
                elif item[0]==6:
                    to_be_added.extend(item[2])
            if to_be_added:
                vals['production_cost_account_ids'] = [(6,0, to_be_added)]
        return super(MillValuation, self).create(vals)

    @api.multi
    def compute_consume_product_value(self):
        self.ensure_one()
        AccountMove = self.env['account.move']
        AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False)
        MoveLine = self.env['stock.move']
        
        default_domain = [('date','>=',self.date_start),('date','<=',self.date_stop)]
        product = self.valuation_categ_id.bom_id.product_id
        consume_line_dict = {
            'valuation_id': self.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'sale_qty': 0.0, 'sale_value': 0.0, 'sale_price':0.0,
        }
        #1. Select Opening Balance, both Qty and Value
        domain1 = default_domain[:]
        opening_account = product.property_stock_account_output or product.categ_id.property_stock_account_output_categ_id
        if not opening_account:
            raise ValidationError(_('Stock Prev. Balance Account not Found. Please define it in Product Category or Product %s')%product.name)
        domain1.extend([('account_id','=',opening_account.id),
            ('product_id','=',product.id)])
        move_opening_bal = AccountMoveLine.search(domain1, limit=1)
        opening_qty = opening_value = 0.0
        if move_opening_bal:
            opening_qty = move_opening_bal.quantity
            opening_value = move_opening_bal.debit - move_opening_bal.credit
        consume_line_dict.update({'opening_qty': opening_qty})
        #2. Select Purchase Movement, both Qty and Value
        purchase_qty = purchase_value = 0.0
        domain2 = default_domain[:]
        purchase_account = product.purchase_account_id or product.categ_id.purchase_account_categ_id
        if not purchase_account:
            raise ValidationError(_('Purchase Account not Found. Please define it in Product Category or Product%s')%product.name)
        domain2.extend([('account_id','=',purchase_account.id),
            ('product_id','=',product.id)])
        move_purchase = AccountMoveLine.search(domain2)
        if move_purchase:
            purchase_qty = sum(move_purchase.mapped('quantity'))
            purchase_value = sum(move_purchase.mapped('debit')) - sum(move_purchase.mapped('credit'))
        consume_line_dict.update({'purchase_qty': purchase_qty})
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

        #5. Select Consumed Product
        consume_qty = 0.0
        consume_lines = MoveLine.search([('consume_unbuild_id','!=',False), 
            ('consume_unbuild_id.product_id','=',product.id),
            ('product_id','=',product.id),
            # ('consume_unbuild_id.date','>=',self.date_start),
            ('date','>=',self.date_start),
            # ('consume_unbuild_id.date','<=',self.date_stop),
            ('date','<=',self.date_stop),
            ('state','=','done'),
            ])
        if consume_lines:
            consume_qty = sum(consume_lines.mapped('product_uom_qty'))
        consume_line_dict.update({'consume_qty': consume_qty})
        #6. Compute Closing Balance
        qty_closing = qty_available - consume_qty
        value_closing = qty_closing * avg_price

        #7. Create Closing Entry at the end of the date
        valuation_account = product.categ_id.property_stock_valuation_account_id
        if not valuation_account:
            raise ValidationError(_('Stock Valuation Account not Found. Please define it in Product Category %s')%product.name)
        input_account = product.categ_id.stock_counterpart_valuation_account_categ_id
        if not input_account:
            raise ValidationError(_('Counterpart Valuation Account not Found. Please define it in Product Category or Product%s')%product.name)
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
            'name': 'Reclass Value Closing as Opening',
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

        current_consume_line = False
        for consume_line in self.consume_product_lines:
            if consume_line.product_id.id == product.id:
                current_consume_line = consume_line
        if not current_consume_line:
            self.env['mill.valuation.consume.line'].create(consume_line_dict)
        else:
            current_consume_line.write(consume_line_dict)
        self.move_ids = [(4,closing_move.id),(4,opening_move.id)]
        return (value_available - value_closing)

    @api.multi
    def create_move_produce_product_value(self, amount_cogm):
        self.ensure_one()
        AccountMove = self.env['account.move']
        AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False)
        MoveLine = self.env['stock.move']
        
        default_domain = [('date','>=',self.date_start),('date','<=',self.date_stop)]

        #1. Select Sales (Sale Qty, Sales Value, and Average Sale Price) and Production (Produce Qty)
        produce_products = {}
        for produce_line in self.produce_product_lines:
            if produce_line.product_id not in produce_products.keys():
                produce_products.update({produce_line.product_id: {
                    'produce_line': produce_line,
                    'sale_price': produce_line.sale_price,
                    }})
        biggest_sale_price_product = False
        biggest_sale_price = 0.0
        found_empty_sale = False
        for produce_product in self.bom_id.mapped('bom_line_ids.product_id'):
            product = produce_product
            produce_product_line_dict = {
                'valuation_id': self.id,
                'product_id': product.id,
                'product_uom': product.uom_id.id,
            }
            if product not in produce_products.keys():
                produce_products.update({product: {}})

            #1.1. Select all Sales Journal from Produce Product to get average sale price
            avg_sale_price = sales_qty = sales_value = qty_produce = 0.0
            domain_sale = default_domain[:]

            sales_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
            if not sales_account:
                raise ValidationError(_('Stock Income Account not Found. Please define it in Product Category or Product'))
            domain_sale.extend([('product_id','=',produce_product.id),
                ('account_id','=',sales_account.id)])
            move_sales = AccountMoveLine.search(domain_sale)
            if move_sales:
                sales_qty = sum(move_sales.mapped('quantity'))
                sales_value = -1* (sum(move_sales.mapped('debit')) - sum(move_sales.mapped('credit')))
                avg_sale_price = abs(sales_qty and sales_value / sales_qty or 0.0)
            else:
                avg_sale_price = produce_products[product].get('sale_price',0.0)
            produce_product_line_dict.update({
                'sale_qty': sales_qty,
                'sale_value': sales_value,
                'sale_price': abs(avg_sale_price),
                })

            if not avg_sale_price:
                found_empty_sale = True
                if not produce_products[product].get('produce_line',False):
                    self.env['mill.valuation.produce.line'].create(produce_product_line_dict)
                else:
                    produce_products[product]['produce_line'].write(produce_product_line_dict)
                continue

            if abs(avg_sale_price) > biggest_sale_price:
                biggest_sale_price = abs(avg_sale_price)
                biggest_sale_price_product = produce_product
            if not biggest_sale_price_product:
                biggest_sale_price = abs(avg_sale_price) or 1.0
                biggest_sale_price_product = produce_product
            #1.2. Compute Production Value of each produce product
            produce_lines = MoveLine.search([('unbuild_id','!=',False), 
                ('product_id','=',product.id),
                # ('unbuild_id.date','>=',self.date_start),
                ('date','>=',self.date_start),
                # ('unbuild_id.date','<=',self.date_stop),
                ('date','<=',self.date_stop),
                ('state','=','done'),
                ])
            if produce_lines:
                qty_produce = sum(produce_lines.mapped('product_uom_qty'))
                produce_product_line_dict.update({'produce_qty': qty_produce})

            if not produce_products[product].get('produce_line',False):
                produce_line = self.env['mill.valuation.produce.line'].create(produce_product_line_dict)
                produce_products[product].update({'produce_line': produce_line})
            
            produce_products[product].update({
                'sale_price': abs(avg_sale_price) or 1.0,
                'sale_qty': sales_qty,
                'produce_qty': qty_produce})

        if found_empty_sale:
            self.state = 'need_sale_price'
            return False

        #2. Compute produce qty populated based on biggest sale price
        for produce_product in produce_products.keys():
            coeff_sale_price = 1
            if produce_product.id!=biggest_sale_price_product.id and produce_products[biggest_sale_price_product]['sale_price']!=0:
                coeff_sale_price = produce_products[produce_product]['sale_price'] / produce_products[biggest_sale_price_product]['sale_price']
            populated_produce_qty = coeff_sale_price * produce_products[produce_product]['produce_qty']
            produce_products[produce_product].update({
                'populated_produce_qty': populated_produce_qty,
                })
        for produce_product in self.bom_id.mapped('bom_line_ids.product_id'):
            product = produce_product

            #3. Select Opening Balance, both Qty and Value
            domain1 = default_domain[:]
            opening_account = product.property_stock_account_output or product.categ_id.property_stock_account_output_categ_id
            if not opening_account:
                raise ValidationError(_('Stock Prev. Balance Account not Found. Please define it in Product Category or Product'))
            domain1.extend([('account_id','=',opening_account.id),
                ('product_id','=',product.id)])
            move_opening_bal = AccountMoveLine.search(domain1, limit=1)
            opening_qty = opening_value = 0.0
            if move_opening_bal:
                opening_qty = move_opening_bal.quantity
                opening_value = move_opening_bal.debit - move_opening_bal.credit

            #4. Compute COGM of each finish goods
            produce_qty = produce_products[product]['produce_qty']
            populated_produce_qty = produce_products[product]['populated_produce_qty']
            total_populated_produce_qty = sum([x['populated_produce_qty'] for x in produce_products.values()])
            if not total_populated_produce_qty and not produce_qty:
                continue
            produce_value = ((populated_produce_qty / total_populated_produce_qty) * amount_cogm)
            produce_price_unit =  produce_value / produce_qty

            #5. Select Purchase Movement, both Qty and Value
            purchase_qty = purchase_value = 0.0
            domain2 = default_domain[:]
            purchase_account = product.purchase_account_id or product.categ_id.purchase_account_categ_id
            if not purchase_account:
                raise ValidationError(_('Purchase Account not Found. Please define it in Product Category or Product'))
            domain2.extend([('account_id','=',purchase_account.id),
                ('product_id','=',product.id)])
            move_purchase = AccountMoveLine.search(domain2)
            if move_purchase:
                purchase_qty = sum(move_purchase.mapped('quantity'))
                purchase_value = sum(move_purchase.mapped('debit')) - sum(move_purchase.mapped('credit'))

            #6. Compute Average Price of all available product
            value_available = opening_value + purchase_value + produce_value
            qty_available = opening_qty + purchase_qty + produce_qty
            avg_price = qty_available and value_available/qty_available or 0.0

            #7. Take Sales Qty
            sale_qty = produce_products[product]['sale_qty']
            #7. Compute Closing Balance : Qty and Value
            qty_closing = qty_available - sale_qty
            value_closing = qty_closing * avg_price

            produce_products[product]['produce_line'].write({
                'opening_qty': opening_qty,
                'produce_qty': produce_qty,
                'purchase_qty': purchase_qty,
                })

            if not round(qty_closing,2):
                continue
            #8. Create Closing Entry at the end of the date
            valuation_account = product.categ_id.property_stock_valuation_account_id
            if not valuation_account:
                raise ValidationError(_('Stock Valuation Account not Found. Please define it in Product Category or Product'))
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
                'name': 'Reclass Value Closing as Opening',
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
            # produce_products[product]['produce_line'].write(produce_product_line_dict)
        return True

    @api.multi
    def post(self):
        self.with_context(from_post=True).filtered(lambda x: x.move_ids).cancel()
        for mill_valuation in self:
            #1. Compute and create journal for raw material consume value
            consume_value = mill_valuation.compute_consume_product_value()

            #2. Select other consume value from salary or factory overhead cost
            domain = [('date','>=',mill_valuation.date_start),('date','<=',mill_valuation.date_stop)]
            cost_accounts = mill_valuation.production_cost_account_ids
            cost_account_locations = mill_valuation.production_cost_location_ids
            if cost_accounts and cost_account_locations:
                domain.extend(['|',('account_id','in',cost_accounts.ids),
                    ('account_location_id','in',cost_account_locations.ids)])
                move_other_cost = self.env['account.move.line'].search(domain)
            elif cost_accounts:
                domain.append(('account_id','in',cost_accounts.ids))
                move_other_cost = self.env['account.move.line'].search(domain)
            elif cost_account_locations:
                domain.append(('account_location_id','in',cost_account_locations.ids))
                move_other_cost = self.env['account.move.line'].search(domain)
            else:
                move_other_cost = []
            other_consume_value = move_other_cost and sum(move_other_cost.mapped('balance')) or 0.0
            cogm_amt = consume_value + other_consume_value

            #3. Compute Produce Product Valuation and create journal
            check_res = mill_valuation.create_move_produce_product_value(cogm_amt)
            if not check_res:
                # if check return False, then there could be uncompleted information that need to be used
                # in Valuation Computation. One of it is Sale Price that need to be input manually.
                # so we will skip this valuation
                continue
            mill_valuation.state = 'done'
        return True

    @api.multi
    def cancel(self):
        for order in self:
            for move in order.move_ids:
                move.unlink()
            if not self._context.get('from_post'):
                for consume_line in order.consume_product_lines:
                    consume_line.unlink()
                for produce_line in order.produce_product_lines:
                    produce_line.unlink()
            order.state = 'draft'

class MillValuationConsumeLine(models.Model):
    _name = 'mill.valuation.consume.line'

    product_id = fields.Many2one('product.product', 'Product')
    product_uom = fields.Many2one('product.uom', 'UoM')
    opening_qty = fields.Float('Opening Qty', digits=dp.get_precision('Product Unit of Measure'))
    purchase_qty = fields.Float('Purchase Qty', digits=dp.get_precision('Product Unit of Measure'))
    sale_qty = fields.Float('Sale Qty', digits=dp.get_precision('Product Unit of Measure'))
    sale_value = fields.Float('Sale Value', digits=dp.get_precision('Account'))
    sale_price = fields.Float('Sale Price', digits=dp.get_precision('Product Price'))
    consume_qty = fields.Float('Consume Qty', digits=dp.get_precision('Product Unit of Measure'))
    valuation_id = fields.Many2one('mill.valuation', 'Valuation')

class MillValuationConsumeLine(models.Model):
    _name = 'mill.valuation.produce.line'

    product_id = fields.Many2one('product.product', 'Product')
    product_uom = fields.Many2one('product.uom', 'UoM')
    opening_qty = fields.Float('Opening Qty', digits=dp.get_precision('Product Unit of Measure'))
    purchase_qty = fields.Float('Purchase Qty', digits=dp.get_precision('Product Unit of Measure'))
    sale_qty = fields.Float('Sale Qty', digits=dp.get_precision('Product Unit of Measure'))
    sale_value = fields.Float('Sale Value', digits=dp.get_precision('Account'))
    sale_price = fields.Float('Sale Price', digits=dp.get_precision('Product Price'))
    produce_qty = fields.Float('Produce Qty', digits=dp.get_precision('Product Unit of Measure'))
    valuation_id = fields.Many2one('mill.valuation', 'Valuation')