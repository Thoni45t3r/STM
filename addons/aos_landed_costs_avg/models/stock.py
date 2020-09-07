# -*- coding: utf-8 -*-
import time
import logging
from datetime import datetime
from collections import defaultdict
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from collections import namedtuple
import odoo.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)


class Picking(models.Model):
    _inherit = "stock.picking"
    
    @api.multi
    @api.depends('move_lines')
    def _entry_count(self):
        for picking in self:
            res = self.env['stock.move'].search_count([('picking_id', '=', picking.id), ('move_id', '!=', False)])
            picking.entry_count = res or 0

#     @api.one
#     @api.depends('package_ids', 'weight_bulk')
#     def _compute_shipping_weight(self):
#         self.shipping_weight = sum([pack.shipping_weight for pack in self.package_ids])
            
    entry_count = fields.Integer(compute='_entry_count', string='# Stock Entries')
    force_date = fields.Datetime('Force Date')
    #shipping_weight = fields.Float("Weight for Shipping", compute='_compute_shipping_weight')
    landed_ids = fields.Many2many('avg.landed.cost', 
                                 'avg_landed_cost_stock_picking_rel', 'stock_picking_id', 'avg_landed_cost_id', 
                                 string='Landed Costs', copy=False, readonly=False)
    
    @api.multi
    def open_entries(self):
        move_ids = []
        for picking in self:
            for move in picking.move_lines:
                if move.move_id:
                    move_ids.append(move.move_id.id)
        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_ids)],
        }
    
    @api.multi
    def do_prepare_partial(self):
        super(Picking, self).do_prepare_partial()
        PackOperation = self.env['stock.pack.operation']
        for picking in self:
            existing_packages = PackOperation.search([('picking_id', '=', picking.id)])
            for pack in existing_packages:
                use_lots = ((picking.picking_type_id.use_existing_lots or picking.picking_type_id.use_create_lots) and pack.product_id.tracking != 'none') and 'yes' or 'no'
                pack.write({'use_lots': use_lots})
    
    @api.multi
    def do_new_transfer(self):
        for pick in self:
            pack_operations_delete = self.env['stock.pack.operation']
            if not pick.move_lines and not pick.pack_operation_ids:
                raise UserError(_('Please create some Initial Demand or Mark as Todo and create some Operations. '))
            # In draft or with no pack operations edited yet, ask if we can just do everything
            if pick.state == 'draft' or all([x.qty_done == 0.0 for x in pick.pack_operation_ids]):
                # If no lots when needed, raise error
                picking_type = pick.picking_type_id
                #ADD ADDITIONAL FILTER HERE
                if (picking_type.use_create_lots or picking_type.use_existing_lots):
                    for pack in pick.pack_operation_ids:
                        if pack.product_id and pack.product_id.tracking != 'none' and pack.use_lots == 'yes':
                            raise UserError(_('Some products require lots/serial numbers, so you need to specify those first!'))
                view = self.env.ref('stock.view_immediate_transfer')
                wiz = self.env['stock.immediate.transfer'].create({'pick_id': pick.id})
                # TDE FIXME: a return in a loop, what a good idea. Really.
                return {
                    'name': _('Immediate Transfer?'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.immediate.transfer',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'res_id': wiz.id,
                    'context': self.env.context,
                }

            # Check backorder should check for other barcodes
            if pick.check_backorder():
                view = self.env.ref('stock.view_backorder_confirmation')
                wiz = self.env['stock.backorder.confirmation'].create({'pick_id': pick.id})
                # TDE FIXME: same reamrk as above actually
                return {
                    'name': _('Create Backorder?'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.backorder.confirmation',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'res_id': wiz.id,
                    'context': self.env.context,
                }
            for operation in pick.pack_operation_ids:
                if operation.qty_done < 0:
                    raise UserError(_('No negative quantities allowed'))
                if operation.qty_done > 0:
                    operation.write({'product_qty': operation.qty_done})
                else:
                    pack_operations_delete |= operation
            if pack_operations_delete:
                pack_operations_delete.unlink()
        self.do_transfer()
        return
    
class Quant(models.Model):
    _inherit = "stock.quant"

    @api.model
    def quants_move(self, quants, move, location_to, location_from=False, lot_id=False, owner_id=False,
                    src_package_id=False, dest_package_id=False, entire_pack=False):
        """Moves all given stock.quant in the given destination location.  Unreserve from current move.
        :param quants: list of tuple(browse record(stock.quant) or None, quantity to move)
        :param move: browse record (stock.move)
        :param location_to: browse record (stock.location) depicting where the quants have to be moved
        :param location_from: optional browse record (stock.location) explaining where the quant has to be taken
                              (may differ from the move source location in case a removal strategy applied).
                              This parameter is only used to pass to _quant_create_from_move if a negative quant must be created
        :param lot_id: ID of the lot that must be set on the quants to move
        :param owner_id: ID of the partner that must own the quants to move
        :param src_package_id: ID of the package that contains the quants to move
        :param dest_package_id: ID of the package that must be set on the moved quant
        """
        # TDE CLEANME: use ids + quantities dict
        if location_to.usage == 'view':
            raise UserError(_('You cannot move to a location of type view %s.') % (location_to.name))
 
        quants_reconcile_sudo = self.env['stock.quant'].sudo()
        quants_move_sudo = self.env['stock.quant'].sudo()
        check_lot = False
        for quant, qty in quants:
            if not quant:
                # If quant is None, we will create a quant to move (and potentially a negative counterpart too)
                quant = self._quant_create_from_move(
                    qty, move, lot_id=lot_id, owner_id=owner_id, src_package_id=src_package_id,
                    dest_package_id=dest_package_id, force_location_from=location_from, force_location_to=location_to)
                if move.picking_id.force_date:
                    quant.write({'in_date': move.picking_id.force_date})
                check_lot = True
            else:
                _logger.info(quant)
                quant._quant_split(qty)
                _logger.info(quant)
                quants_move_sudo |= quant
            quants_reconcile_sudo |= quant
 
        if quants_move_sudo:
            moves_recompute = quants_move_sudo.filtered(lambda self: self.reservation_id != move).mapped(
                'reservation_id')
            quants_move_sudo._quant_update_from_move(move, location_to, dest_package_id, lot_id=lot_id,
                                                     entire_pack=entire_pack)
            moves_recompute.recalculate_move_state()
 
        if location_to.usage == 'internal':
            # Do manual search for quant to avoid full table scan (order by id)
            self._cr.execute("""
                SELECT 0 FROM stock_quant, stock_location WHERE product_id = %s AND stock_location.id = stock_quant.location_id AND
                ((stock_location.parent_left >= %s AND stock_location.parent_left < %s) OR stock_location.id = %s) AND qty < 0.0 LIMIT 1
            """, (move.product_id.id, location_to.parent_left, location_to.parent_right, location_to.id))
            if self._cr.fetchone():
                quants_reconcile_sudo._quant_reconcile_negative(move)
 
        # In case of serial tracking, check if the product does not exist somewhere internally already
        # Checking that a positive quant already exists in an internal location is too restrictive.
        # Indeed, if a warehouse is configured with several steps (e.g. "Pick + Pack + Ship") and
        # one step is forced (creates a quant of qty = -1.0), it is not possible afterwards to
        # correct the inventory unless the product leaves the stock.
        picking_type = move.picking_id and move.picking_id.picking_type_id or False
        if check_lot and lot_id and move.product_id.tracking == 'serial' and (
            not picking_type or (picking_type.use_create_lots or picking_type.use_existing_lots)):
            other_quants = self.search([('product_id', '=', move.product_id.id), ('lot_id', '=', lot_id),
                                        ('qty', '>', 0.0), ('location_id.usage', '=', 'internal')])
            if other_quants:
                # We raise an error if:
                # - the total quantity is strictly larger than 1.0
                # - there are more than one negative quant, to avoid situations where the user would
                #   force the quantity at several steps of the process
                if sum(other_quants.mapped('qty')) > 1.0 or len([q for q in other_quants.mapped('qty') if q < 0]) > 1:
                    lot_name = self.env['stock.production.lot'].browse(lot_id).name
                    raise UserError(_('The serial number %s is already in stock.') % lot_name + _(
                        "Otherwise make sure the right stock/owner is set."))
# 
    @api.multi
    def _quant_update_from_move(self, move, location_dest_id, dest_package_id, lot_id=False, entire_pack=False):
        vals = super(Quant, self)._quant_update_from_move(move, location_dest_id, dest_package_id, lot_id=lot_id, entire_pack=entire_pack)
        if move.picking_id.force_date:
            self.write({'in_date': move.picking_id.force_date})
            
    def _create_account_move_line(self, move, credit_account_id, debit_account_id, journal_id):
        # group quants by cost
        quant_cost_qty = defaultdict(lambda: 0.0)
        for quant in self:
            quant_cost_qty[quant.cost] += quant.qty
        AccountMove = self.env['account.move']
        for cost, qty in quant_cost_qty.iteritems():
            #print "===_create_account_move_line==",cost, qty
            move_lines = move._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id)
            #print "===_create_account_move_line==",cost, qty, move_lines
            if move_lines:
                if move.picking_id.force_date:
                    date = datetime.strptime(move.picking_id.force_date, '%Y-%m-%d %H:%M:%S')
                else:
                    date = self._context.get('force_period_date', fields.Date.context_today(self))
                new_account_move = AccountMove.create({
                    'journal_id': journal_id,
                    'line_ids': move_lines,
                    'date': date,
                    'ref': move.picking_id.name})
                new_account_move.post()
                move.write({'move_id': new_account_move.id})


class StockMove(models.Model):
    _inherit = "stock.move"
    
#     @api.depends('product_id', 'product_uom_qty', 'product_uom')
#     def _cal_move_shipweight(self):
#         for move in self:
#             shipping_weight = 0.0
#             for link in move.linked_move_operation_ids:
#                 if link.move_id.state == 'done' and link.move_id.product_id == link.operation_id.product_id:
#                     shipping_weight += link.operation_id.shipping_weight
#             move.shipping_weight = shipping_weight
#             
#     shipping_weight = fields.Float(compute='_cal_move_shipweight', string="Ship. Weight", digits=dp.get_precision('Stock Weight'), store=False)
    move_id = fields.Many2one('account.move', string='Journal Entries')
    
    @api.multi
    def check_tracking(self, pack_operation):
        #CHANGE THIS BASE DEF DONT USE SUPER
        """ Checks if serial number is assigned to stock move or not and raise an error if it had to. """
        # TDE FIXME: I cannot able to understand
        for move in self:
#             if move.picking_id and \
#                     (move.picking_id.picking_type_id.use_existing_lots or move.picking_id.picking_type_id.use_create_lots) and \
#                     move.product_id.tracking != 'none' and \
#                     not (move.restrict_lot_id or (pack_operation and (pack_operation.product_id and pack_operation.pack_lot_ids)) or (pack_operation and not pack_operation.product_id)):
            if move.picking_id and move.product_id.tracking != 'none' \
                    and (pack_operation and pack_operation.use_lots == 'yes') and \
                    not (move.restrict_lot_id or (pack_operation and (pack_operation.product_id and pack_operation.pack_lot_ids)) or (pack_operation and not pack_operation.product_id)):
                raise UserError(_('You need to provide a Lot/Serial Number for product %s') % move.product_id.name)

    @api.multi
    def action_done(self):
        res = super(StockMove, self).action_done()
        f_date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        for move in self:
            if move.picking_id.force_date:
                f_date = move.picking_id.force_date
        self.write({'state': 'done', 'date': f_date})
        return res
    
    @api.multi
    def get_price_unit(self):
        """ Force Date get_price_unit Returns the unit price to store on the quant """
        if self.purchase_line_id:
            order = self.purchase_line_id.order_id
            #if the currency of the PO is different than the company one, the price_unit on the move must be reevaluated
            #(was created at the rate of the PO confirmation, but must be valuated at the rate of stock move execution)
            if order.currency_id != self.company_id.currency_id:
                #we don't pass the move.date in the compute() for the currency rate on purpose because
                # 1) get_price_unit() is supposed to be called only through move.action_done(),
                # 2) the move hasn't yet the correct date (currently it is the expected date, after
                #    completion of action_done() it will be now() )
                price_unit = self.purchase_line_id.with_context(date=self.picking_id.force_date)._get_stock_move_price_unit()
                self.write({'price_unit': price_unit})
                return price_unit
            return self.price_unit
        return super(StockMove, self).get_price_unit()



class PackOperation(models.Model):
    _inherit = "stock.pack.operation"
    
    def _compute_tot_weight(self):
        for packop in self:
            if packop.product_id:
                packop.tot_weight = packop.product_uom_id._compute_quantity(packop.product_qty, packop.product_id.uom_id) * packop.product_id.weight
    
    @api.model
    def _get_default_prodlot(self):
        for packop in self:
            if packop.product_id:
                packop.use_lots = ((packop.picking_id.picking_type_id.use_existing_lots or packop.picking_id.picking_type_id.use_create_lots) and packop.product_id.tracking != 'none') and 'yes' or 'no'
    
    use_lots = fields.Selection([('no','No'),('yes','Yes')], string='S/N', default=_get_default_prodlot)
    tot_weight = fields.Float(compute='_compute_tot_weight', string="Tot. Weight")
    #shipping_weight = fields.Float(string='Ship. Weight', related='result_package_id.shipping_weight', help="Can be changed during the 'put in pack' to adjust the weight of the shipping.")
    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'No Tracking')], string="Tracking", related='product_id.tracking', required=False)
    
#     @api.onchange('use_lots')
#     def check_tracking_lots(self):
#         for pack in self:
#             if pack.use_lots == 'yes' and pack.picking_id.picking_type_id and pack.product_id.tracking == 'none':
#                 raise UserError(_('You need to provide a Lot/Serial Number for product %s') % pack.product_id.name)
    
    @api.one
    def _compute_location_description(self):
        if self.package_id:
            self.from_loc = '%s:%s' % (self.location_id.name, self.product_id and self.package_id.name or '')
        else:
            self.from_loc = '%s' % (self.location_id.name or '')
        if self.result_package_id:
            self.to_loc = '%s:%s' % (self.location_dest_id.name, self.result_package_id.name or '')
        else:
            self.to_loc = '%s' % (self.location_dest_id.name or '')
        
    @api.one
    def _compute_lots_visible(self):
        #ADD THE FIRST LINE FOR FIRST ARGUMENT WHEN YOU WANT TO USER LOTS OR NOT
        if self.use_lots == 'no' and self.picking_id.picking_type_id and self.product_id.tracking != 'none':
            self.lots_visible = False
        elif self.pack_lot_ids:
            self.lots_visible = True
        elif self.picking_id.picking_type_id and self.product_id.tracking != 'none':  # TDE FIXME: not sure correctly migrated
            picking = self.picking_id
            self.lots_visible = picking.picking_type_id.use_existing_lots or picking.picking_type_id.use_create_lots
        else:
            self.lots_visible = self.product_id.tracking != 'none'
            
    @api.multi
    def put_in_pack(self):
        # TDE FIXME: reclean me
        QuantPackage = self.env["stock.quant.package"]
        package = False
        for pick in self:
            operations = [x for x in pick if x.qty_done > 0 and (not x.result_package_id)]
            self = self.env['stock.pack.operation']
            for operation in operations:
                # If we haven't done all qty in operation, we have to split into 2 operation
                op = operation
                if operation.qty_done < operation.product_qty:
                    new_operation = operation.copy({'product_qty': operation.qty_done,'qty_done': operation.qty_done})

                    operation.write({'product_qty': operation.product_qty - operation.qty_done,'qty_done': 0})
                    if operation.pack_lot_ids:
                        packlots_transfer = [(4, x.id) for x in operation.pack_lot_ids]
                        new_operation.write({'pack_lot_ids': packlots_transfer})

                        # the stock.pack.operation.lot records now belong to the new, packaged stock.pack.operation
                        # we have to create new ones with new quantities for our original, unfinished stock.pack.operation
                        new_operation._copy_remaining_pack_lot_ids(operation)

                    op = new_operation
                self |= op
            if operations:
                self.check_tracking()
                package = QuantPackage.create({})
                self.write({'result_package_id': package.id})
            else:
                raise UserError(_('Please process some quantities to put in the pack first!'))
        return package
    
    