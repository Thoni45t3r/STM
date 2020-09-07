# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, tools, _
from odoo.addons import decimal_precision as dp
from odoo.addons.aos_landed_costs_avg.models import product
from odoo.exceptions import UserError


class AvgLandedCost(models.Model):
    _name = 'avg.landed.cost'
    _description = 'Average Landed Cost'
    _inherit = 'mail.thread'
    
    @api.model
    def _default_journal_bill(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', '=', 'purchase'),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)
    
    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', '=', 'general'),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)
    
    @api.model
    def _default_currency(self):
        journal = self._default_journal()
        return journal.currency_id or journal.company_id.currency_id or self.env.user.company_id.currency_id

    @api.depends('state', 'invoice_id')
    def _get_invoiced(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for order in self:
            if order.state == 'done' and not order.invoice_id:
                order.invoice_status = 'to invoice'
            elif order.state == 'invoiced' and order.invoice_id:
                order.invoice_status = 'invoiced'
            else:
                order.invoice_status = 'no'

    name = fields.Char('Name', default=lambda self: self.env['ir.sequence'].next_by_code('avg.landed.cost'),
                       copy=False, readonly=True, track_visibility='always')
    is_multi_partner = fields.Boolean('Multi Forwarder')
    partner_id = fields.Many2one('res.partner', string='Forwarder', required=True, 
                                 readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date('Date', default=fields.Date.context_today, copy=False, required=True, 
                       readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange')
    picking_ids = fields.Many2many('stock.picking', 
                                     'avg_landed_cost_stock_picking_rel', 'avg_landed_cost_id', 'stock_picking_id', 
                                     string='Pickings', copy=False,
                                     readonly=True, states={'draft': [('readonly', False)]})
    origin = fields.Char(string='Origin', compute='_compute_origin', store=True)
    cost_lines = fields.One2many('avg.landed.cost.lines', 'cost_id', 'Cost Lines',
                                 copy=True, readonly=True, states={'draft': [('readonly', False)]})
    valuation_adjustment_lines = fields.One2many('avg.valuation.adjustment.lines', 'cost_id', 'Valuation Adjustments',
                                                 readonly=True, states={'draft': [('readonly', False)]})
    description = fields.Text('Item Description', readonly=True, states={'draft': [('readonly', False)]})
    amount_total = fields.Float('Total', compute='_compute_total_amount', digits=0, store=True, track_visibility='always')
    state = fields.Selection([
                ('draft', 'Draft'),
                ('done', 'Posted'),
                ('invoiced', 'Invoiced'),
                ('cancel', 'Cancelled')], 'State', default='draft',
                copy=False, readonly=True, track_visibility='onchange')
    invoice_id = fields.Many2one('account.invoice', 'Invoice', copy=False, readonly=True)
    account_move_id = fields.Many2one('account.move', 'Journal Entry', copy=False, readonly=True)
    account_journal_id = fields.Many2one('account.journal', string='Valuation Journal', default=_default_journal,
                                         required=True, readonly=True, states={'draft': [('readonly', False)]},
                                         domain="[('type', '=', 'general'), ('company_id', '=', company_id)]")
    journal_id = fields.Many2one('account.journal', string='Invoice Journal', default=_default_journal_bill,
                                 readonly=True, states={'draft': [('readonly', False)]},
                                 domain="[('type', '=', 'purchase'), ('company_id', '=', company_id)]")
    currency_id = fields.Many2one('res.currency', string='Currency',
                                required=True, readonly=True, states={'draft': [('readonly', False)]},
                                default=_default_currency, track_visibility='always')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
                                required=True, readonly=True, states={'draft': [('readonly', False)]},
                                default=lambda self: self.env['res.company']._company_default_get('avg.landed.cost'))
    user_id = fields.Many2one('res.users', string='Salesperson', track_visibility='onchange',
                            readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.user)
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', oldname='payment_term')
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
                                         readonly=True, states={'draft': [('readonly', False)]})
    invoice_status = fields.Selection([('no', 'Nothing to Bill'),
                                        ('to invoice', 'Waiting Bills'),
                                        ('invoiced', 'Bills Received'),
                                        ], string='Billing Status', compute='_get_invoiced', store=True, readonly=True, copy=False, default='no')
    note = fields.Text('Terms and conditions')
    
    @api.onchange('is_multi_partner')
    def _onchange_cost_lines(self):
        for line in self.cost_lines:
            line.is_multi_partner = self.is_multi_partner
    
    @api.one
    @api.depends('cost_lines.price_unit')
    def _compute_total_amount(self):
        self.amount_total = sum(line.price_unit for line in self.cost_lines)
        
    @api.depends('picking_ids')
    def _compute_origin(self):
        origin_ids = self.mapped('picking_ids').mapped('origin')
        self.origin = ", ".join(origin_ids) or ''

    @api.multi
    def unlink(self):
        self.button_cancel()
        return super(AvgLandedCost, self).unlink()

    @api.multi
    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'done':
            return 'aos_landed_costs_avg.mt_aos_landed_cost_open'
        return super(AvgLandedCost, self)._track_subtype(init_values)
    
    @api.multi
    def action_cancel(self):
        moves = self.env['account.move']
        for cost in self:
            if cost.account_move_id:
                moves += cost.account_move_id

        # First, set the invoices as cancelled and detach the move ids
        self.write({'state': 'cancel', 'invoice_id': False, 'account_move_id': False})
        if moves:
            # second, invalidate the move(s)
            moves.button_cancel()
            # delete the move this invoice was pointing to
            # Note that the corresponding move_lines and move_reconciles
            # will be automatically deleted too
            moves.unlink()
        return True
    
    @api.multi
    def button_draft(self):
        return self.write({'state': 'draft'})
    
    @api.multi
    def button_cancel(self):
        return self.write({'state': 'cancel'})
    
    @api.multi
    def button_cancel_validated(self):
        #UPDATE AVERAGE PRODUCT BACK TO BEGINING
        for cost in self:
            if cost.invoice_id and self.filtered(lambda inv: cost.invoice_id.state not in ['proforma2', 'draft', 'open']):
                raise UserError(_("Invoice must be in draft, Pro-forma or open state in order to be cancelled."))
            #CANCEL DRAFT INVOICE
            if cost.invoice_id:
                cost.invoice_id.action_cancel()
            
            products_dict = defaultdict(lambda: 0.0)
            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                products_dict[line.product_id] += line.former_cost_per_unit
            #===========================================================
            # BACK STANDART PRICE TO BEGINNING ONLY IF LANDED POSTED
            #===========================================================
            for product, price_value in products_dict.items():
                product.sudo().write({'standard_price': product.standard_price - price_value}) 
        
        return self.action_cancel()

    @api.multi
    def button_validate(self):
        if any(cost.state != 'draft' for cost in self):
            raise UserError(_('Only draft landed costs can be validated'))
        if any(not cost.valuation_adjustment_lines for cost in self):
            raise UserError(_('No valuation adjustments lines. You should maybe recompute the landed costs.'))
        if not self._check_sum():
            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

        for cost in self:
            move = self.env['account.move'].create({
                'partner_id': cost.partner_id.id,
                'journal_id': cost.account_journal_id.id,
                'date': cost.date,
                'ref': cost.name
            })
            products_dict = defaultdict(lambda: 0.0)
            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                per_unit = line.final_cost / line.qty_available
                diff = line.former_cost_per_unit
                products_dict[line.product_id] += line.former_cost_per_unit
                # If the precision required for the variable diff is larger than the accounting
                # precision, inconsistencies between the stock valuation and the accounting entries
                # may arise.
                # For example, a landed cost of 15 divided in 13 units. If the products leave the
                # stock one unit at a time, the amount related to the landed cost will correspond to
                # round(15/13, 2)*13 = 14.95. To avoid this case, we split the quant in 12 + 1, then
                # record the difference on the new quant.
                # We need to make sure to able to extract at least one unit of the product. There is
                # an arbitrary minimum quantity set to 2.0 from which we consider we can extract a
                # unit and adapt the cost.
                curr_rounding = line.move_id.company_id.currency_id.rounding
                diff_rounded = tools.float_round(diff, precision_rounding=curr_rounding)
                diff_correct = diff_rounded
                quants = line.move_id.quant_ids.sorted(key=lambda r: r.qty, reverse=True)
                quant_correct = False
                if quants\
                        and tools.float_compare(quants[0].product_id.uom_id.rounding, 1.0, precision_digits=1) == 0\
                        and tools.float_compare(line.qty_available * diff, line.qty_available * diff_rounded, precision_rounding=curr_rounding) != 0\
                        and tools.float_compare(quants[0].qty, 2.0, precision_rounding=quants[0].product_id.uom_id.rounding) >= 0:
                    # Search for existing quant of quantity = 1.0 to avoid creating a new one
                    quant_correct = quants.filtered(lambda r: tools.float_compare(r.qty, 1.0, precision_rounding=quants[0].product_id.uom_id.rounding) == 0)
                    if not quant_correct:
                        quant_correct = quants[0]._quant_split(quants[0].qty - 1.0)
                    else:
                        quant_correct = quant_correct[0]
                        quants = quants - quant_correct
                    diff_correct += (line.qty_available * diff) - (line.qty_available * diff_rounded)
                    diff = diff_rounded
                 
                quant_dict = {}
                for quant in quants:
                    quant_dict[quant] = (quant.inventory_value/(quant.qty or 1.0)) + diff
                if quant_correct:
                    quant_dict[quant_correct] = (quant_correct.inventory_value/(quant_correct.qty or 1.0)) + diff_correct
                for quant, value in quant_dict.items():
                    quant.sudo().write({'cost': value})
                qty_out = 0
                for quant in line.move_id.quant_ids:
                    if quant.location_id.usage != 'internal':
                        qty_out += quant.qty
                
                line._create_accounting_entries(move, qty_out)
            #===================================================================
            # UPDATE STANDARD PRICE + PRICE UNIT LANDED COST VALUE
            #===================================================================
            for product, price_value in products_dict.items():
                product.sudo().write({'standard_price': product.standard_price + price_value}) 
                
            move.assert_balanced()
            cost.write({'state': 'done', 'account_move_id': move.id})
            move.post()
        return True

    def _check_sum(self):
        """ Check if each cost line its valuation lines sum to the correct amount
        and if the overall total amount is correct also """
        prec_digits = self.env['decimal.precision'].precision_get('Account')
        for landed_cost in self:
            total_amount = sum(landed_cost.valuation_adjustment_lines.mapped('additional_landed_cost'))
            if not tools.float_compare(total_amount, landed_cost.amount_total, precision_digits=prec_digits) == 0:
                return False

            val_to_cost_lines = defaultdict(lambda: 0.0)
            for val_line in landed_cost.valuation_adjustment_lines:
                val_to_cost_lines[val_line.cost_line_id] += val_line.additional_landed_cost
            if any(tools.float_compare(cost_line.price_unit, val_amount, precision_digits=prec_digits) != 0
                   for cost_line, val_amount in val_to_cost_lines.iteritems()):
                return False
        return True

    def get_valuation_lines(self):
        lines = []

        for pack in self.mapped('picking_ids').mapped('pack_operation_product_ids'):
        #for move in self.mapped('picking_ids').mapped('move_lines'):
            # it doesn't make sense to make a landed cost for a product that isn't set as being valuated in real time at real cost
            if pack.product_id.valuation != 'real_time' or pack.product_id.cost_method != 'average':
                continue
            vals = {
                'product_id': pack.product_id.id,
                'move_id': len(pack.linked_move_operation_ids) == 1 and pack.linked_move_operation_ids.move_id.id 
                           or len(pack.linked_move_operation_ids) > 1 and pack.linked_move_operation_ids[0].move_id.id or False,
                'quantity': pack.qty_done,
                'qty_available': pack.product_id.qty_available,
                'former_cost': len(pack.linked_move_operation_ids) == 1 and pack.linked_move_operation_ids.move_id.purchase_line_id 
                    and pack.linked_move_operation_ids.move_id.purchase_line_id.price_subtotal 
                    or len(pack.linked_move_operation_ids) > 1 
                        and sum([move1.move_id.purchase_line_id.price_subtotal for move1 in pack.linked_move_operation_ids])
                    or len(pack.linked_move_operation_ids) > 1 
                        and sum([move2.move_id.price_unit*pack.qty_done for move2 in pack.linked_move_operation_ids]) 
                    or 0,
                'weight': pack.product_id.weight,
                'volume': pack.product_id.volume,
                'tot_weight': pack.product_id.weight * pack.qty_done,
                'tot_volume': pack.product_id.volume * pack.product_qty
            }
            lines.append(vals)

        if not lines and self.mapped('picking_ids'):
            raise UserError(_('The selected picking does not contain any move that would be impacted by landed costs. Landed costs are only possible for products configured in real time valuation with average price costing method. Please make sure it is the case, or you selected the correct picking'))
        return lines

    @api.multi
    def compute_landed_cost(self):
        AdjustementLines = self.env['avg.valuation.adjustment.lines']
        AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()
        currency = self.currency_id or None
        
        digits = dp.get_precision('Product Price')(self._cr)
        towrite_dict = {}
        for cost in self.filtered(lambda cost: cost.picking_ids):
            total_qty = 0.0
            total_cost = 0.0
            total_weight = 0.0
            total_volume = 0.0
            total_line = 0.0
            all_val_line_values = cost.get_valuation_lines()
            for val_line_values in all_val_line_values:
                for cost_line in cost.cost_lines:
                    val_line_values.update({'cost_id': cost.id, 'cost_line_id': cost_line.id})
                    self.env['avg.valuation.adjustment.lines'].create(val_line_values)
                total_qty += val_line_values.get('quantity', 0.0)
                total_weight += val_line_values.get('tot_weight', 0.0)
                total_volume += val_line_values.get('tot_volume', 0.0)

                former_cost = val_line_values.get('former_cost', 0.0)
                # round this because former_cost on the valuation lines is also rounded
                total_cost += tools.float_round(former_cost, precision_digits=digits[1]) if digits else former_cost
                total_line += 1

            for line in cost.cost_lines:
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines:
                    value = 0.0
                    if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                        if line.split_method_avg == 'by_quantity' and total_qty:
                            per_unit = (line.price_unit / total_qty)
                            value = valuation.quantity * per_unit
                        elif line.split_method_avg == 'by_weight' and total_weight:
                            per_unit = (line.price_unit / total_weight)
                            value = valuation.tot_weight * per_unit
                        elif line.split_method_avg == 'by_volume' and total_volume:
                            per_unit = (line.price_unit / total_volume)
                            value = valuation.tot_volume * per_unit    
                        elif line.split_method_avg == 'equal':
                            value = (line.price_unit / total_line)
                        elif line.split_method_avg == 'by_current_cost_price' and total_cost:
                            per_unit = (line.price_unit / total_cost)
                            value = valuation.former_cost * per_unit
                        else:
                            value = (line.price_unit / total_line)

                        if digits:
                            value = tools.float_round(value, precision_digits=digits[1], rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value
        if towrite_dict:
            for key, value in towrite_dict.items():
                if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
                    value = self.currency_id.with_context(date=self.date).compute(value, self.company_id.currency_id)
                AdjustementLines.browse(key).write({'additional_landed_cost': value})
        return True
    
    @api.multi
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        if not self.journal_id:
            raise UserError(_('Please define an accounting landed bills journal for this company.'))
        pick_ids = self.mapped('picking_ids').mapped('name')
        origin_ids = self.mapped('picking_ids').mapped('origin')
        # Search for invoices which have been 'cancelled' (filter_refund = 'modify' in
        # 'account.invoice.refund')
        # use like as origin may contains multiple references (e.g. 'SO01, SO02')
        #refunds = invoice_ids.search([('origin', 'like', order.name)])
        #invoice_ids |= refunds.filtered(lambda r: order.name in [origin.strip() for origin in r.origin.split(',')])
        invoice_vals = {
            'name': ", ".join(origin_ids) or '',
            'origin': self.name or '',
            'date_invoice': self.date,
            'type': 'in_invoice',
            'account_id': self.partner_id.property_account_payable_id.id,
            'partner_id': self.partner_id.id,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'comment': self.note,
            'payment_term_id': self.payment_term_id.id,
            'fiscal_position_id': self.fiscal_position_id.id or self.partner_id.property_account_position_id.id,
            'company_id': self.company_id.id,
            'user_id': self.user_id and self.user_id.id,
            #'team_id': self.team_id.id
            'landed_id': self.id,
        }
        return invoice_vals        
    
    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        inv_obj = self.env['account.invoice']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        invoices = {}
        references = {}
        for cost in self:
            group_key = cost.id if grouped else (cost.partner_id.id, cost.currency_id.id)
            for line in cost.cost_lines:
                if group_key not in invoices:
                    inv_data = cost._prepare_invoice()
                    invoice = inv_obj.create(inv_data)
                    references[invoice] = cost
                    invoices[group_key] = invoice
                elif group_key in invoices:
                    vals = {}
                    if cost.name not in invoices[group_key].origin.split(', '):
                        vals['origin'] = invoices[group_key].origin + ', ' + cost.name
                    invoices[group_key].write(vals)
                if line.invoice_status == 'to invoice':
                    line.invoice_line_create(invoices[group_key].id)
            #print "===invoices==",invoices
            if references.get(invoices.get(group_key)):
                if cost not in references[invoices[group_key]]:
                    references[invoice] = references[invoice] | cost

        if not invoices:
            raise UserError(_('There is no invoicable line.'))

        for invoice in invoices.values():
            if not invoice.invoice_line_ids:
                raise UserError(_('There is no invoicable line.'))
            # Necessary to force computation of taxes. In account_invoice, they are triggered
            # by onchanges, which are not triggered when doing a create.
            invoice.compute_taxes()
            invoice.message_post_with_view('mail.message_origin_link',
                values={'self': invoice, 'origin': references[invoice]},
                subtype_id=self.env.ref('mail.mt_note').id)
            self.write({'state': 'invoiced', 'invoice_id': invoice.id})
        return [inv.id for inv in invoices.values()]


class AvgLandedCostLine(models.Model):
    _name = 'avg.landed.cost.lines'
    _description = 'Average Landed Cost Lines'
    
    @api.depends('state', 'invoice_lines', 'cost_id.invoice_id')
    def _compute_invoice_status(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            if line.state == 'done' and not line.cost_id.invoice_id:
                line.invoice_status = 'to invoice'
            elif line.state == 'invoiced' and line.invoice_lines and line.cost_id.invoice_id:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'
                
    name = fields.Char('Description')
    sequence = fields.Integer('Sequence')
    is_multi_partner = fields.Boolean('Multi Forwarder')
    partner_id = fields.Many2one('res.partner', string='Forwarder')
    cost_id = fields.Many2one(
        'avg.landed.cost', 'Landed Cost',
        required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    price_unit = fields.Float('Cost', digits=dp.get_precision('Product Price'), required=True)
    split_method_avg = fields.Selection(product.SPLIT_METHOD, string='Split Method', required=True)
    account_id = fields.Many2one('account.account', 'Account', domain=[('deprecated', '=', False)])
    invoice_lines = fields.Many2many('account.invoice.line', 'avg_landed_cost_line_invoice_rel', 'avg_line_id', 'invoice_line_id', string='Invoice Lines', copy=False)
    invoice_status = fields.Selection([
        ('upselling', 'Upselling Opportunity'),
        ('invoiced', 'Fully Invoiced'),
        ('to invoice', 'To Invoice'),
        ('no', 'Nothing to Invoice')
        ], string='Invoice Status', compute='_compute_invoice_status', store=True, readonly=True, default='no')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Posted'),
        ('invoiced', 'Invoiced'),
        ('cancel', 'Cancelled')
    ], related='cost_id.state', string='Cost Status', readonly=True, copy=False, store=True, default='draft')
    
    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id:
            self.quantity = 0.0
        self.name = self.product_id.name or ''
        self.split_method_avg = self.product_id.split_method_avg or 'by_weight'
        self.price_unit = self.product_id.standard_price or 0.0
        self.account_id = self.product_id.property_account_expense_id.id or self.product_id.categ_id.property_account_expense_categ_id.id


    @api.multi
    def _prepare_invoice_line(self):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        """
        self.ensure_one()
        res = {}
        account = self.account_id or self.product_id.property_account_expense_id or self.product_id.categ_id.property_account_expense_categ_id
        if not account:
            raise UserError(_('Please define expense account for this product: "%s" (id:%d) - or for its category: "%s".') %
                (self.product_id.name, self.product_id.id, self.product_id.categ_id.name))

        fpos = self.cost_id.fiscal_position_id or self.cost_id.partner_id.property_account_position_id
        if fpos:
            account = fpos.map_account(account)

        res = {
            'name': self.name,
            'sequence': self.sequence,
            'origin': self.cost_id.name,
            'account_id': account.id,
            'price_unit': self.price_unit,
            'quantity': 1.0,
            'product_id': self.product_id.id or False,
            #'discount': self.discount,
            #'uom_id': self.product_uom.id,
            #'layout_category_id': self.layout_category_id and self.layout_category_id.id or False,
            #'invoice_line_tax_ids': [(6, 0, self.tax_id.ids)],
            #'account_analytic_id': self.order_id.project_id.id,
            #'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
        }
        return res
    
    @api.multi
    def invoice_line_create(self, invoice_id):
        """
        Create an invoice line. The quantity to invoice can be positive (invoice) or negative
        (refund).

        :param invoice_id: integer
        :param qty: float quantity to invoice
        """
        for line in self:
            vals = line._prepare_invoice_line()
            vals.update({'invoice_id': invoice_id, 'cost_line_ids': [(6, 0, [line.id])]})
            self.env['account.invoice.line'].create(vals)    
        
class AvgAdjustmentLines(models.Model):
    _name = 'avg.valuation.adjustment.lines'
    _description = 'Average Valuation Adjustment Lines'
    
    name = fields.Char(
        'Description', compute='_compute_name', store=True)
    cost_id = fields.Many2one(
        'avg.landed.cost', 'Landed Cost',
        ondelete='cascade', required=True)
    cost_line_id = fields.Many2one(
        'avg.landed.cost.lines', 'Cost Line', readonly=True)
    move_id = fields.Many2one('stock.move', 'Stock Move', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    quantity = fields.Float('Qty Receipt', default=1.0,
        digits=dp.get_precision('Product Unit of Measure'), required=True)
    qty_available = fields.Float(
        'Qty On Hand', default=1.0,
        digits=dp.get_precision('Product Unit of Measure'), required=True)
    weight = fields.Float(
        'Weight', default=1.0,
        digits=dp.get_precision('Stock Weight'))
    tot_weight = fields.Float(
        'Tot. Weight', default=1.0,
        digits=dp.get_precision('Stock Weight'))
    volume = fields.Float(
        'Volume', default=1.0)
    tot_volume = fields.Float(
        'Tot. Volume', default=1.0)
    former_cost = fields.Float(
        'Former Cost', digits=dp.get_precision('Product Price'))
    former_cost_per_unit = fields.Float(
        'Former Cost per Unit', compute='_compute_former_cost_per_unit',
        digits=0, store=True)
    landed_cost_per_unit = fields.Float(
        'Cost per Unit', compute='_compute_landed_cost_per_unit',
        digits=0, store=True)
    additional_landed_cost = fields.Float(
        'Landed Cost', digits=dp.get_precision('Product Price'))
    final_cost = fields.Float(
        'Final Cost', compute='_compute_final_cost',
        digits=0, store=True)

    @api.one
    @api.depends('cost_line_id.name', 'product_id.code', 'product_id.name')
    def _compute_name(self):
        name = '%s - ' % (self.cost_line_id.name if self.cost_line_id else '')
        self.name = name + (self.product_id.code or self.product_id.name or '')

    @api.one
    @api.depends('former_cost','additional_landed_cost', 'qty_available')
    def _compute_former_cost_per_unit(self):
        former_cost_landed = self.additional_landed_cost * self.quantity / (self.qty_available or 1.0)
        self.former_cost_per_unit = former_cost_landed / (self.quantity or 1.0)

    @api.one
    @api.depends('additional_landed_cost', 'quantity', 'qty_available')
    def _compute_landed_cost_per_unit(self):
        self.landed_cost_per_unit = self.additional_landed_cost / (self.quantity or 1.0)

    @api.one
    @api.depends('former_cost', 'additional_landed_cost')
    def _compute_final_cost(self):
        self.final_cost = self.former_cost + self.additional_landed_cost

    def _create_accounting_entries(self, move, qty_out):
        # TDE CLEANME: product chosen for computation ?
        cost_product = self.cost_line_id.product_id
        if not cost_product:
            return False
        accounts = self.product_id.product_tmpl_id.get_product_accounts()
        debit_account_id = accounts.get('stock_valuation') and accounts['stock_valuation'].id or False
        already_out_account_id = accounts['stock_output'].id
        credit_account_id = self.cost_line_id.account_id.id or cost_product.property_account_expense_id.id or cost_product.categ_id.property_account_expense_categ_id.id

        if not credit_account_id:
            raise UserError(_('Please configure Stock Expense Account for product: %s.') % (cost_product.name))

        return self._create_account_move_line(move, credit_account_id, debit_account_id, qty_out, already_out_account_id)

    def _create_account_move_line(self, move, credit_account_id, debit_account_id, qty_out, already_out_account_id):
        """
        Generate the account.move.line values to track the landed cost.
        Afterwards, for the goods that are already out of stock, we should create the out moves
        """
        AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False, recompute=False)

        base_line = {
            'name': self.name,
            'move_id': move.id,
            'partner_id': move.partner_id and move.partner_id.id or False,
            'product_id': self.product_id.id,
            'quantity': self.qty_available,
        }
        debit_line = dict(base_line, account_id=debit_account_id)
        credit_line = dict(base_line, account_id=credit_account_id)
        diff = self.additional_landed_cost
        if diff > 0:
            debit_line['debit'] = diff
            credit_line['credit'] = diff
        else:
            # negative cost, reverse the entry
            debit_line['credit'] = -diff
            credit_line['debit'] = -diff
        AccountMoveLine.create(debit_line)
        AccountMoveLine.create(credit_line)

        # Create account move lines for quants already out of stock
        if qty_out > 0:
            debit_line = dict(base_line,
                              name=(self.name + ": " + str(qty_out) + _(' already out')),
                              quantity=qty_out,
                              account_id=already_out_account_id)
            credit_line = dict(base_line,
                               name=(self.name + ": " + str(qty_out) + _(' already out')),
                               quantity=qty_out,
                               account_id=debit_account_id)
            diff = diff * qty_out / self.quantity
            if diff > 0:
                debit_line['debit'] = diff
                credit_line['credit'] = diff
            else:
                # negative cost, reverse the entry
                debit_line['credit'] = -diff
                credit_line['debit'] = -diff
            AccountMoveLine.create(debit_line)
            AccountMoveLine.create(credit_line)

            # TDE FIXME: oh dear
            if self.env.user.company_id.anglo_saxon_accounting:
                debit_line = dict(base_line,
                                  name=(self.name + ": " + str(qty_out) + _(' already out')),
                                  quantity=qty_out,
                                  account_id=credit_account_id)
                credit_line = dict(base_line,
                                   name=(self.name + ": " + str(qty_out) + _(' already out')),
                                   quantity=qty_out,
                                   account_id=already_out_account_id)

                if diff > 0:
                    debit_line['debit'] = diff
                    credit_line['credit'] = diff
                else:
                    # negative cost, reverse the entry
                    debit_line['credit'] = -diff
                    credit_line['debit'] = -diff
                AccountMoveLine.create(debit_line)
                AccountMoveLine.create(credit_line)

        return True
