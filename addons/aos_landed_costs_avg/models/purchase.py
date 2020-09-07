# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
import odoo.addons.decimal_precision as dp
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import math

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
            
    @api.depends('order_line.price_total','order_line.subtotal')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = amount_inland_total = 0.0
            for line in order.order_line:
                amount_untaxed += line.subtotal
                amount_inland_total += line.inland_value
                # FORWARDPORT UP TO 10.0
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.taxes_id.compute_all(price, line.order_id.currency_id, line.product_qty, product=line.product_id, partner=order.order_id.partner_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_inland_total': amount_inland_total,
                'amount_total': amount_untaxed + amount_tax + amount_inland_total,
            })
            
    validator_uid = fields.Many2one('res.users', 'Validate by')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'On Progress'),
        ('done', 'Locked'),
        ('running', 'Running'),
        ('cancel', 'Cancelled')
        ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')
    inland_type = fields.Selection([
            #('equal', 'Equal'),
            #('by_quantity', 'By Qty'),
            ('by_weight', 'By Weight'),
            ('by_volume', 'By Volume'),
        ], string='Shipping Cost Type', default='by_weight', required=False, readonly=True, states={'draft': [('readonly', False)]},
            help='''Equal = Amount Inland / Total Line\n
                By Quantity = Amount Inland / Total Qty\n
                By Weight = Amount Inland / Total Weight\n
                By Volume = Amount Inland / Total Volume''')
    amount_inland = fields.Float(string='Amount Shipping Cost', required=False,
                                   readonly=True, states={'draft': [('readonly', False)]})
    amount_inland_total = fields.Monetary(string='Amount Shipping Cost', store=True, readonly=True, compute='_amount_all')
    amount_untaxed = fields.Monetary(string='Net Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')

    def get_valuation_inlands(self):
        lines = []
        for line in self.mapped('order_line'):
            #print '==get_valuation_inlands===',line.weight,line.product_id.weight
            if line.product_id.valuation != 'real_time':# or line.product_id.cost_method != 'average':
                continue
                #raise UserError(_('Product Category Setting is Invalid for (%s)\nCosting Method should Average Price\nInventory Valuation should Perpetual (automated)' % line.name))
            if line.order_id.inland_type == 'by_weight' and line.product_id.weight == 0.0:
                raise UserError(_('No Weight set for product (%s)' % line.name))
            elif line.order_id.inland_type == 'by_volume' and line.product_id.volume == 0.0:
                raise UserError(_('No Volume set for product (%s)' % line.name))
            line.weight = line.product_id.weight
            line.volume = line.product_id.volume
            #line.tot_weight = line.product_id.weight * line.product_qty
            #line.tot_volume = line.product_id.volume * line.product_qty
            lines.append({
                'weight': line.product_id.weight,
                'volume': line.product_id.volume,
                'tot_weight': line.weight * line.product_qty,
                'tot_volume': line.volume * line.product_qty,
            })

        if not lines and self.mapped('order_line'):
            raise UserError(_('No purchase line!'))
        return lines
    
    def _set_line_inlands(self):
        digits = dp.get_precision('Product Price')(self._cr)
        for purchase in self:
            total_qty = total_weight = total_ship_weight = total_volume = total_line = per_unit = value_split = 0.0
            all_val_line_values = purchase.get_valuation_inlands()
            for val_line_values in all_val_line_values:
                total_qty += val_line_values.get('quantity', 0.0)
                total_weight += val_line_values.get('tot_weight', 0.0)
                total_volume += val_line_values.get('tot_volume', 0.0)
                total_line += 1
            for line in purchase.order_line:
                if purchase.inland_type == 'by_weight' and total_weight:
                    per_unit = (purchase.amount_inland / total_weight)
                    value = line.tot_weight * per_unit
                elif purchase.inland_type == 'by_volume' and total_volume:
                    per_unit = (purchase.amount_inland / total_volume)
                    value = line.tot_volume * per_unit
                else:
                    value = (purchase.amount_inland / total_line)
                if digits:
                    value = tools.float_round(value, precision_digits=digits[1], rounding_method='UP')
                    fnc = min if purchase.amount_inland > 0 else max
                    if line.product_qty:
                        line.inland_unit = value/line.product_qty
                    line.inland_value = fnc(value, purchase.amount_inland - value_split)
                    value_split += value
                    
    @api.onchange('inland_type', 'amount_inland')
    def _onchange_purchase_inland(self):
        self._set_line_inlands()
        
    @api.multi
    def compute_inland(self):
        self._set_line_inlands()
        return

    @api.multi
    def button_approve(self, force=False):
        if self.company_id.po_double_validation == 'two_step'\
          and self.amount_total >= self.env.user.company_id.currency_id.compute(self.company_id.po_double_validation_amount, self.currency_id)\
          and not self.user_has_groups('purchase.group_purchase_manager'):
            raise UserError(_('You need purchase manager access rights to validate an order above %.2f %s.') % (self.company_id.po_double_validation_amount, self.company_id.currency_id.name))
        self.write({'state': 'purchase', 'validator_uid': self.env.uid})
        self._create_picking()
        if self.company_id.po_lock == 'lock':
            self.write({'state': 'done'})
        return {}
    
class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    _description = 'Purchase Order Line'
    
    @api.depends('product_qty', 'price_unit', 'taxes_id', 'discount', 'inland_value')
    def _compute_amount(self):
        for line in self:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.taxes_id.compute_all(price_unit, line.order_id.currency_id, line.product_qty, product=line.product_id, partner=line.order_id.partner_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'subtotal': taxes['total_excluded'],
                'price_subtotal': taxes['total_excluded']+line.inland_value,
            })
    

    @api.depends('weight', 'volume', 'product_qty')
    def _compute_weight(self):
        for line in self:
            line.tot_weight = line.product_id.weight * line.product_qty
            line.tot_volume = line.product_id.volume * line.product_qty
    
#     @api.depends('order_id.state', 'move_ids.state')
#     def _compute_ship_weight(self):
#         for line in self:
#             total = 0.0
#             for move in line.move_ids:
#                 if move.state == 'done':
#                     total += move.shipping_weight
#             line.shipping_weight = total

    sequence = fields.Integer(string='Sequence', default=10)
    product_uom = fields.Many2one('product.uom', string='UoM', required=True)
    product_qty = fields.Float(string='Order Qty', digits=dp.get_precision('Product Unit of Measure'), required=True)
    inland_type = fields.Selection([
            #('equal', 'Equal'),
            #('by_quantity', 'By Qty'),
            ('by_weight', 'By Weight'),
            ('by_volume', 'By Volume'),
        ], string='Shipping Cost Type', default='by_weight', required=False,
            help='''By Weight = Amount Inland / Total Weight\n
                By Volume = Amount Inland / Total Volume''')
    weight = fields.Float('Unit Weight', default=0.0, digits=dp.get_precision('Stock Weight'))
    volume = fields.Float('Unit Volume', default=0.0)
    tot_weight = fields.Float(compute='_compute_weight', string='Tot. Weight', default=0.0, digits=dp.get_precision('Stock Weight'))
    tot_volume = fields.Float(compute='_compute_weight', string='Tot. Volume', default=0.0)
#     shipping_weight = fields.Float(compute='_compute_ship_weight', string="Ship. Weight", digits=dp.get_precision('Stock Weight'), store=True)
    inland_unit = fields.Float(string='Unit Ship.Cost', digits=dp.get_precision('Product Price'), default=0.0, readonly=True)
    inland_value = fields.Float(string='Total Ship.Cost', digits=dp.get_precision('Product Price'), default=0.0, readonly=True)
    discount = fields.Float(string='Disc (%)', digits=dp.get_precision('Discount'), default=0.0)
    
    subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Tax', store=True)

    _sql_constraints = [
        ('discount_limit', 'CHECK (discount <= 100.0)', 'Maximum discount is 100%.'),
    ]
    
    @api.multi
    def _get_stock_move_price_unit(self):
        ''' change _get_stock_move_price_unit with context date for compute currency it will update:\
            price_unit on stock.move
            cost on stock.quant'''
        self.ensure_one()
        date = self._context.get('date')
        line = self[0]
        order = line.order_id
        price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        if line.taxes_id:
            price_unit = line.taxes_id.with_context(round=False).compute_all(
                price_unit, currency=line.order_id.currency_id, quantity=1.0, product=line.product_id, partner=line.order_id.partner_id
            )['total_excluded']
        if line.product_uom.id != line.product_id.uom_id.id:
            price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
        if order.currency_id != order.company_id.currency_id:
            price_unit = order.currency_id.with_context(date=self._context.get('date')).compute(price_unit, order.company_id.currency_id, round=False)
        return price_unit + line.inland_unit

    @api.multi
    def _prepare_stock_moves(self, picking):
        res = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
        return res
    
class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    @api.multi
    def _rfq_quantity(self):
        for template in self:
            template.rfq_qty = sum([p.rfq_qty for p in template.product_variant_ids])
        return True
    
    rfq_qty = fields.Integer(compute='_rfq_quantity', string='RFQ Stock', digits=dp.get_precision('Product Unit of Measure'))
    
class ProductProduct(models.Model):
    _inherit = "product.product"
    
    @api.multi
    def _rfq_quantity(self):
        domain = [
            ('state', 'in', ['draft','confirmed', 'approved']),
            ('product_id', 'in', self.mapped('id')),
        ]
        r = {}
        for group in self.env['purchase.report'].read_group(domain, ['product_id', 'quantity'], ['product_id']):
            r[group['product_id'][0]] = group['quantity']
        for product in self:
            product.rfq_qty = r.get(product.id, 0)
        return True
    
                
    rfq_qty = fields.Integer(compute='_rfq_quantity', string='RFQ Stock', digits=dp.get_precision('Product Unit of Measure'))
