# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from collections import OrderedDict, defaultdict
from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp

class StockPicking(models.Model):
    _inherit        = 'stock.picking'

    @api.model
    def default_get(self, fields):
        res = super(StockPicking, self).default_get(fields)
        picking_type_ids    = self.env['stock.picking.type'].search([('skb', '=', True),('return_picking_type_id','!=',False)])
        if res.get('skb', False):
            res['picking_type_id'] = picking_type_ids[-1].id if picking_type_ids else False
        return res

    skb                             = fields.Boolean('SKB', readonly=True)
    bpb_number                      = fields.Char('NO. BPB')
    organization_type               = fields.Selection([('afdeling', 'Tanaman'), ('division', 'Non Tanaman')], string='Departemen Type', default='afdeling')
    afdeling_id                     = fields.Many2one(comodel_name="res.afdeling", string="Departemen", ondelete="restrict")
    division_id                     = fields.Many2one(comodel_name="hr.division", string="Departemen", ondelete="restrict")
    employee_id                     = fields.Many2one(comodel_name="hr.employee", string="Employee", ondelete="restrict")

class StockMove(models.Model):
    _inherit        = 'stock.move'

    plantation_location_type_id     = fields.Many2one(comodel_name="lhm.location.type", string="Tipe Lokasi", ondelete="restrict")
    plantation_location_id          = fields.Many2one(comodel_name="lhm.location", string="Lokasi", ondelete="restrict")
    plantation_activity_id          = fields.Many2one(comodel_name="lhm.activity", string="Aktivitas", ondelete="restrict")
    plantation_activity_name        = fields.Char(related="plantation_activity_id.name", string="Nama Aktivitas", ondelete="restrict")
    account_id                      = fields.Many2one(comodel_name="account.account", string="Allocation", ondelete="restrict")
    skb                             = fields.Boolean(related="picking_id.skb", string="SKB", store=True)
    plantation_validator            = fields.Boolean("Plantation Validator", related="plantation_location_type_id.no_line")
    product_uom_qty                 = fields.Float('Quantity', digits=dp.get_precision('Product Unit of Measure'), default=0.0,
                                                                    required=True, states={'done': [('readonly', True)]},
                                                                    help="This is the quantity of products from an inventory "
                                                                        "point of view. For moves in the state 'done', this is the "
                                                                        "quantity of products that were actually moved. For other "
                                                                        "moves, this is the quantity of product that is planned to "
                                                                        "be moved. Lowering this quantity does not generate a "
                                                                        "backorder. Changing this quantity on assigned moves affects "
                                                                        "the product reservation, and should be done with care.")
    lhm_material_ids                = fields.One2many('lhm.transaction.material.line', 'move_id', ' LHM Realisation')
    lhm_contractor_material_ids     = fields.One2many('lhm.contractor.material.line', 'move_id', ' Contractor Realisation')
    plantation_material_allocation  = fields.Float(compute='_get_plantation_material', string='Allocated to Plantation Material', store=True)
    pending_material_allocation     = fields.Float(compute='_get_plantation_material', string='Pending Plantation Allocation', store=True)

    @api.depends('lhm_material_ids', 'lhm_material_ids.realization', \
            'lhm_contractor_material_ids', 'lhm_contractor_material_ids.realization')
    def _get_plantation_material(self):
        for move in self:
            allocated = sum(move.sudo().lhm_material_ids.mapped('realization')) + sum(move.sudo().lhm_contractor_material_ids.mapped('realization'))
            move.plantation_material_allocation = allocated
            move.pending_material_allocation = move.product_uom_qty - allocated

    @api.onchange('plantation_location_type_id')
    def _onchange_plantation_location_type_id(self):
        if self.plantation_location_type_id:
            self.plantation_location_id = False
            self.plantation_activity_id = False
            if self.plantation_location_type_id.no_line and (self.plantation_location_type_id.general_charge or self.plantation_location_type_id.indirect):
                self.account_id = False
            else:
                self.account_id = self.plantation_location_type_id.account_id and self.plantation_location_type_id.account_id.id or False

    @api.onchange('plantation_location_id')
    def _onchange_plantation_location_id(self):
        if self.plantation_location_id:
            self.plantation_activity_id = False

    @api.onchange('product_id')
    def onchange_product_id(self):
        product                 = self.product_id.with_context(lang=self.partner_id.lang or self.env.user.lang)
        self.name               = product.partner_ref
        self.product_uom        = product.uom_id.id
        self.product_uom_qty    = 0.0
        return {'domain': {'product_uom': [('category_id', '=', product.uom_id.category_id.id)]}}

    @api.onchange('plantation_activity_id')
    def _onchange_plantation_activity_id(self):
        if self.plantation_activity_id and (self.plantation_location_type_id.general_charge or self.plantation_location_type_id.indirect):
            self.account_id = self.plantation_activity_id.account_id and self.plantation_activity_id.account_id.id or False

    @api.multi
    def product_price_update_before_done(self):
        tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        for move in self.filtered(lambda move: move.location_id.usage in ('supplier', 'production') and move.product_id.cost_method == 'average'):
            product_tot_qty_available = move.product_id.qty_available + tmpl_dict[move.product_id.id]

            # if the incoming move is for a purchase order with foreign currency, need to call this to get the same value that the quant will use.
            if product_tot_qty_available <= 0:
                new_std_price = move.get_price_unit()
            else:
                # Get the standard price
                amount_unit = std_price_update.get((move.company_id.id, move.product_id.id)) or move.product_id.standard_price
                if move.product_id.capitalized_tax_id:
                    total_taxes = 0
                    for taxes in move.product_id.capitalized_tax_id:
                        if taxes:
                            total_taxes = total_taxes + (taxes.amount * (((move.get_price_unit() * move.product_qty)) /100))
                    new_std_price = ((amount_unit * product_tot_qty_available) + ((move.get_price_unit() + (total_taxes/move.product_qty)) * move.product_qty)) / (product_tot_qty_available + move.product_qty)
                else:
                    new_std_price = ((amount_unit * product_tot_qty_available) + (move.get_price_unit() * move.product_qty)) / (product_tot_qty_available + move.product_qty)

            tmpl_dict[move.product_id.id] += move.product_qty
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            move.product_id.with_context(force_company=move.company_id.id).sudo().write({'standard_price': new_std_price})
            std_price_update[move.company_id.id, move.product_id.id] = new_std_price

    @api.model
    def _prepare_account_move_line(self, qty, cost, credit_account_id,
                                   debit_account_id):
        res = super(StockMove, self)._prepare_account_move_line(
            qty, cost, credit_account_id, debit_account_id)
        if res:
            debit_line_vals = res[0][2]
            credit_line_vals = res[1][2]

            if self.plantation_location_type_id:
                debit_line_vals.update({'plantation_location_type_id': self.plantation_location_type_id.id})
                credit_line_vals.update({'plantation_location_type_id': self.plantation_location_type_id.id})
            if self.plantation_location_id:
                debit_line_vals.update({'plantation_location_id': self.plantation_location_id.id})
                credit_line_vals.update({'plantation_location_id': self.plantation_location_id.id})
            if self.plantation_activity_id:
                debit_line_vals.update({'plantation_activity_id': self.plantation_activity_id.id})
                credit_line_vals.update({'plantation_activity_id': self.plantation_activity_id.id})
            
            return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
        return res

class StockPickingType(models.Model):
    _inherit        = 'stock.picking.type'

    skb             = fields.Boolean("Is SKB?")
    code            = fields.Selection([('incoming', 'Vendors'),
                             ('outgoing', 'Customers'),
                             ('internal', 'Internal'),
                             ('plantation', 'Plantation'), ('plantation_return', 'Plantation Return')], 'Type of Operation', required=True)

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _account_entry_move(self, move):
        company_from = move.company_id
        if move.product_id.type != 'product' or move.product_id.valuation != 'real_time':
            # no stock valuation for consumable products
            return False
        if any(quant.owner_id or quant.qty <= 0 for quant in self):
            # if the quant isn't owned by the company, we don't make any valuation en
            # we don't make any stock valuation for negative quants because the valuation is already made for the counterpart.
            # At that time the valuation will be made at the product cost price and afterward there will be new accounting entries
            # to make the adjustments when we know the real cost price.
            return False

        if company_from and move.picking_id.picking_type_id.code == 'plantation':
            journal_id, acc_src, acc_dest, acc_valuation = move._get_accounting_data_for_valuation()
            if move.account_id:
                if acc_dest != move.account_id.id:
                    acc_dest = move.account_id.id
            self.with_context(force_company=company_from.id)._create_account_move_line(move, acc_valuation, acc_dest, journal_id)
        elif company_from and move.picking_id.picking_type_id.code == 'plantation_return':
            journal_id, acc_src, acc_dest, acc_valuation = move._get_accounting_data_for_valuation()
            if move.account_id:
                if acc_src != move.account_id.id:
                    acc_src = move.account_id.id
            self.with_context(force_company=company_from.id)._create_account_move_line(move, acc_src, acc_valuation, journal_id)
        else:
            return super(StockQuant, self)._account_entry_move(move)

    def _create_account_move_line(self, move, credit_account_id, debit_account_id, journal_id):
        # group quants by cost
        quant_cost_qty = defaultdict(lambda: 0.0)
        for quant in self:
            quant_cost_qty[quant.cost] += quant.qty

        AccountMove = self.env['account.move']
        for cost, qty in quant_cost_qty.iteritems():
            move_lines = move._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id)
            if move_lines:
                date                = self._context.get('force_period_date', fields.Date.context_today(self))
                new_account_move    = AccountMove.create({
                    'journal_id'    : journal_id,
                    'line_ids'      : move_lines,
                    'date'          : date,
                    'ref'           : move.picking_id.name})
                if move.product_id.capitalized_tax_id and move.location_id.usage == 'supplier':
                    total_taxes = 0
                    for taxes in move.product_id.capitalized_tax_id:
                        if taxes:
                            total_taxes = total_taxes + (taxes.amount * (((move.get_price_unit() * move.product_qty)) / 100))
                    if new_account_move:
                        for move_line in new_account_move.line_ids:
                            if move_line and move_line.debit > 0:
                                move_line.write({'debit': move_line.debit + total_taxes})
                            elif move_line and move_line.credit > 0:
                                move_line.write({'credit': move_line.credit + total_taxes})
                new_account_move.post()