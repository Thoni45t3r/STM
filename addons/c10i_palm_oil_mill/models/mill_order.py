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
class MillBom(models.Model):
    _inherit = 'mrp.bom'

    product_qty = fields.Float('Quantity', default=1.0, digits=dp.get_precision('Mills Production'), required=True)
class MillBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    product_qty = fields.Float('Product Quantity', default=1.0, digits=dp.get_precision('Mills Production'), required=True)

class MillOrder(models.Model):
    _inherit = 'mrp.unbuild'
    _description = "Mill Processing Order"
    _order = 'id desc'

    date = fields.Date('Date', default=lambda self: datetime.now().strftime(DF), required=True, states={'done': [('readonly',True)]})
    mill_order = fields.Boolean('Mills Order', default=lambda self: self._context.get('mill_order', False))
    editable_produce_line_ids = fields.One2many('mill.unbuild.produce.line', 'unbuild_id', states={'done': [('readonly',True)]},
        help='This line will show you products that will be produce in this Mill Order. \n \
            It is possible to edit the quantity to be produced.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done')], string='Status', default='draft', index=True)
    need_recompute = fields.Boolean(string='Need Recompute', compute='_produce_line_check', store=True)
    product_qty = fields.Float('Quantity',required=True, states={'done': [('readonly', True)]}, default=1.0)

    @api.depends('editable_produce_line_ids.product_uom_qty')
    def _produce_line_check(self):
        for order in self:
            check = False
            for line in order.editable_produce_line_ids:
                if line.need_recompute:
                    check = True
            order.need_recompute = check

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('mill.order') or _('New')
        order = super(MillOrder, self).create(vals)
        return order

    @api.multi
    def action_confirm(self):
        check_need_recompute = self.filtered(lambda x: x.need_recompute)
        if check_need_recompute:
            raise UserError(_('Some transaction need to be recompute before confirming'))
        self.state = 'confirmed'
        self.filtered(lambda x: len(x.editable_produce_line_ids.ids)==0).generate_produce_lines()

    @api.multi
    def action_set_draft(self):
        self.state = 'draft'

    def _generate_consume_moves(self):
        moves = self.env['stock.move']
        product = self.env['product.product']
        for order in self:
            if not order.mill_order:
                continue
            if product.with_context(location=self.location_id.id, compute_child=False).browse(order.product_id.id).qty_available <= 0.0:
                raise UserError(_('Consume product quantity has to be strictly available.'))
            # this method was made to check if the consume material are all available
            
        return super(MillOrder, self)._generate_consume_moves()

    def _generate_produce_moves(self):
        moves = self.env['stock.move']
        for order in self:
            if order.mill_order:
                for line in order.editable_produce_line_ids:
                    moves += order._generate_move_from_produce_line(line)
            else:
                factor = order.product_uom_id._compute_quantity(order.product_qty, order.bom_id.product_uom_id) / order.bom_id.product_qty
                boms, lines = order.bom_id.explode(order.product_id, factor, picking_type=order.bom_id.picking_type_id)
                for line, line_data in lines:
                    moves += order._generate_move_from_bom_line(line, line_data['qty'])
        return moves

    def _generate_move_from_produce_line(self, produce_line):
        return self.env['stock.move'].create({
            'name': self.name,
            'date': self.create_date,
            'bom_line_id': produce_line.bom_line_id.id,
            'product_id': produce_line.product_id.id,
            'product_uom_qty': produce_line.product_uom_qty,
            'product_uom': produce_line.product_uom.id,
            'procure_method': 'make_to_stock',
            'location_dest_id': self.location_dest_id.id,
            'location_id': self.product_id.property_stock_production.id,
            'unbuild_id': self.id,
        })

    @api.multi
    def generate_produce_lines(self):
        produce_lines = self.env['mill.unbuild.produce.line']
        for order in self:
            for x in order.editable_produce_line_ids:
                x.unlink()
            factor = order.product_uom_id._compute_quantity(order.product_qty, order.bom_id.product_uom_id) / order.bom_id.product_qty
            boms, lines = order.bom_id.explode(order.product_id, factor, picking_type=order.bom_id.picking_type_id)
            for line, line_data in lines:
                produce_lines += order._generate_produce_line_from_bom_line(line, line_data['qty'])
        return produce_lines

    def _generate_produce_line_from_bom_line(self, bom_line, quantity):
        return self.env['mill.unbuild.produce.line'].create({
            'name': self.name,
            'bom_line_id': bom_line.id,
            'product_id': bom_line.product_id.id,
            'product_uom_qty': quantity,
            'product_uom': bom_line.product_uom_id.id,
            'unbuild_id'    : self.id,
        })

    @api.multi
    def recompute_product_lines(self):
        self.ensure_one()
        source_qty = 0.0
        for produce_line in self.editable_produce_line_ids:
            if not produce_line.calc_line:
                # source_qty = (produce_line.bom_line_id.bom_id.product_qty / produce_line.bom_line_id.product_qty) * produce_line.product_uom_qty
                source_qty = (produce_line.bom_line_id.bom_id.product_qty / produce_line.bom_line_qty) * produce_line.product_uom_qty
                break

        self.product_qty = source_qty
        factor = self.product_uom_id._compute_quantity(source_qty, self.bom_id.product_uom_id) / self.bom_id.product_qty
        boms, lines = self.bom_id.explode(self.product_id, factor, picking_type=self.bom_id.picking_type_id)
        for line, line_data in lines:
            produce_line = self.editable_produce_line_ids.filtered(lambda x: x.bom_line_id.id==line.id)
            if not produce_line:
                continue
            if produce_line.calc_line:
                produce_line.write({'product_uom_qty': (produce_line.unbuild_id.product_qty * produce_line.bom_line_qty), 'need_recompute': False})
            produce_line.write({'need_recompute': False})

    @api.multi
    def action_unbuild(self):
        self.ensure_one()
        res = super(MillOrder, self).action_unbuild()
        # FORCE UPDATE DATE. REMOVE THIS IF THIS IS NOT CORRECTLY SET
        for consume_line in self.consume_line_ids:
            consume_line.sudo().date = datetime.strptime(self.date, DF).strftime('%Y-%m-%d 12:00:00')
            if consume_line.picking_id:
                consume_line.sudo().picking_id.date_done = datetime.strptime(self.date, DF).strftime('%Y-%m-%d 12:00:00')
        for produce_line in self.produce_line_ids:
            produce_line.sudo().date = datetime.strptime(self.date, DF).strftime('%Y-%m-%d 12:00:00')
            produce_line.sudo().quant_ids.write({'in_date': datetime.strptime(self.date, DF).strftime('%Y-%m-%d 12:00:00')})
            if produce_line.picking_id:
                produce_line.sudo().picking_id.date_done = datetime.strptime(self.date, DF).strftime('%Y-%m-%d 12:00:00')
        return res

class MillOrderProduceLine(models.Model):
    _name = 'mill.unbuild.produce.line'
    _description = "Mill Produce Lines"

    name = fields.Char('Description')
    bom_line_id = fields.Many2one('mrp.bom.line', 'BoM Line')
    product_id = fields.Many2one('product.product', 'Product')
    product_uom = fields.Many2one('product.uom', 'Unit of Measure')
    bom_line_qty = fields.Float(related='bom_line_id.product_qty', string='Composition (%)', digits=dp.get_precision('Mills Production'), store=True)
    bom_line_qty_confirmed = fields.Float('Bom Qty', digits=dp.get_precision('Mills Production'))
    product_uom_qty = fields.Float('Produce Qty', digits=dp.get_precision('Mills Production UOM'))
    unbuild_id = fields.Many2one('mrp.unbuild', 'Unbuild Order')
    need_recompute = fields.Boolean('Need Recompute', default=False)
    calc_line = fields.Boolean('Calculate', default=True)

    @api.onchange('bom_line_qty', 'product_uom_qty')
    def onchange_product_needed(self):
        self.need_recompute = True
        self.bom_line_qty_confirmed = self.bom_line_qty

    @api.onchange('product_uom_qty')
    def onchange_product_uom_qty(self):
        self.calc_line = False