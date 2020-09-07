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

class StockTransportCost(models.Model):
    _name = 'stock.transport.cost'
    _description = "Transport Cost"
    _inherit = ['mail.thread']
    _order = 'id desc'

    date_start = fields.Date('From Date', required=True, readonly=True, states={'draft': [('readonly','=',True)]})
    date_stop = fields.Date('To Date', required=True, readonly=True, states={'draft': [('readonly','=',True)]})
    transporter_id = fields.Many2one('res.partner', 'Transporter', readonly=True, states={'draft': [('readonly','=',True)]}, required=True)
    picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type', domain=[('code','in',['incoming','outgoing'])], readonly=True, states={'draft': [('readonly','=',True)]})
    picking_ids = fields.One2many('stock.picking', 'transport_cost_id', string='Pickings', readonly=True, states={'draft': [('readonly','=',True)]})
    cost_line_ids = fields.One2many('stock.transport.cost.line', 'cost_id', string='Cost Lines', readonly=True, states={'draft': [('readonly','=',True)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done')], string='Status', default='draft', index=True)

    journal_id = fields.Many2one('account.journal', 'Journal', required=True, readonly=True, states={'draft': [('readonly','=',True)]}, domain=[('type','=','purchase')])
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, readonly=True, states={'draft': [('readonly','=',True)]}, default=lambda self: self.env.user.company_id.currency_id.id)
    company_id = fields.Many2one('res.company', 'Company', required=True, readonly=True, states={'draft': [('readonly','=',True)]}, default=lambda self: self.env.user.company_id.id)
    invoice_ids = fields.Many2many('account.invoice', 'Invoices', readonly=True)
    # service_order_id = fields.Many2one('purchase.order', 'Surat Perintah Kerja', readonly=True, states={'draft': [('readonly','=',True)]}, domain=[('type','=','purchase')])

    # @api.model
    # def create(self, vals):
    #     if not vals.get('name'):
    #         vals['name'] = self.env['ir.sequence'].next_by_code('mill.order') or _('New')
    #     order = super(MillOrder, self).create(vals)
    #     return order

    @api.multi
    def action_confirm(self):
        self.state = 'confirmed'
        for x in self.filtered(lambda x: len(x.cost_line_ids.ids)==0):
            x.generate_cost_lines()

    @api.multi
    def action_set_draft(self):
        self.state = 'draft'

    @api.multi
    def generate_cost_lines(self):
        self.ensure_one()
        for x in self.cost_line_ids:
            x.unlink()
        cost_line = self.env['stock.transport.cost.line']
        default_domain = [('date_done','>=', datetime.strptime(self.date_start, DF).strftime(DF+' 00:00:00')), \
            ('date_done','<=', datetime.strptime(self.date_stop, DF).strftime(DF+' 23:59:59')),
            ('state','=','done'), ('incoterm_id.transport_cost','=',True)]
        if self.picking_type_id:
            default_domain.append(('picking_type_id','=',self.picking_type_id.id))
        else:
            default_domain.append(('picking_type_id.code','in',['incoming','outgoing']))
        
        if self.transporter_id:
            default_domain.append(('transporter_id','=',self.transporter_id.id))
        else:
            default_domain.append(('transporter_id','!=',False))

        pickings = self.env['stock.picking'].search(default_domain)
        total_net_weight = 0.0
        for transporter in pickings.mapped('transporter_id'):
            for incoterm in pickings.filtered(lambda x: x.transporter_id.id==transporter.id).mapped('incoterm_id'):
                total_net_weight = 0.0
                for pick in pickings.filtered(lambda x: x.transporter_id.id==transporter.id and x.incoterm_id.id==incoterm.id):
                    total_net_weight += sum(pick.move_lines.mapped('net_weight'))
                vals = {
                    'cost_id': self.id,
                    'incoterm_id': incoterm.id,
                    'transporter_id': transporter.id,
                    'quantity': total_net_weight,
                    'price_unit': 0.0,
                }
                cost_line.create(vals)
        self.picking_ids = [(6,0,pickings.ids)]
        return True

    @api.multi
    def create_invoice(self):
        self.ensure_one()
        Invoice = self.env['account.invoice']
        InvoiceLine = self.env['account.invoice.line']

        res = []
        for partner in self.cost_line_ids.mapped('transporter_id'):
            invoice_vals = {
                'journal_id': self.journal_id.id,
                'date_invoice': self.date_stop,
                'partner_id': partner.id,
                'account_id': partner.property_account_payable_id.id,
                'company_id': self.company_id.id,
                'currency_id': self.currency_id.id,
            }
            invoice = Invoice.create(invoice_vals)
            for line in self.cost_line_ids.filtered(lambda x: x.transporter_id.id==partner.id):
                invoice_line_vals = {
                    'invoice_id': invoice.id,
                    'product_id': False,
                    'uom_id': False,
                    'account_id': line.incoterm_id.account_id.id,
                    'name': 'Transport Charges %s - %s'%(self.date_start, self.date_stop),
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                }
                InvoiceLine.create(invoice_line_vals)

            res.append(invoice)

        # Necessary to force computation of taxes. In account_invoice, they are triggered
        # by onchanges, which are not triggered when doing a create.
        for inv in res:
            inv.compute_taxes()
            inv.message_post('This invoice has been created from Buku Kontraktor')

        self.write({
            'invoice_ids': [(6, 0, [x.id for x in res])],
            'state': 'done'})
        # Redirect to show Invoice
        action = self.env.ref('account.action_invoice_tree2').read()[0]
        action['domain'] = [('id','in',[x.id for x in res])]
        return action

    @api.multi
    def post(self):
        self.ensure_one()
        Entry = self.env['account.move']
        JournalItem = self.env['account.move.line']

        move_lines = []
        for partner in self.cost_line_ids.mapped('transporter_id'):
            # move = Entry.create(move_vals)
            move_line_vals = (0,0,{
                    'product_id': False,
                    'uom_id': False,
                    'partner_id': partner.id,
                    'account_id': partner.property_account_payable_id.id,
                    # 'account_id': partner.account_payable_contractor_id.id,
                    'name': 'Transport Charges %s - %s'%(self.date_start, self.date_stop),
                    # 'quantity': line.quantity,
                    # 'price_unit': line.price_unit,
                    'debit': 0.0,
                    'credit': sum(self.cost_line_ids.filtered(lambda x: x.transporter_id.id==partner.id).mapped('amount')),
                    'journal_id': self.journal_id.id,
                    'date': self.date_stop,
                })
            move_lines.append(move_line_vals)
            for line in self.cost_line_ids.filtered(lambda x: x.transporter_id.id==partner.id):
                move_line_vals = (0,0,{
                    'product_id': False,
                    'uom_id': False,
                    'account_id': line.incoterm_id.account_id.id,
                    'name': 'Transport Charges %s - %s'%(self.date_start, self.date_stop),
                    'quantity': line.quantity,
                    # 'price_unit': line.price_unit,
                    'debit': line.amount,
                    'credit': 0.0,
                    'journal_id': self.journal_id.id,
                    'date': self.date_stop,
                })
                move_lines.append(move_line_vals)

        if not move_lines:
            return False
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.date_stop,
            'company_id': self.company_id.id,
            'line_ids': move_lines,
        }
        move = Entry.create(move_vals)
        move.post()
        return self.write({'state': 'done'})


class StockTransportCostLine(models.Model):
    _name = 'stock.transport.cost.line'
    _description = "Transport Lines"

    incoterm_id = fields.Many2one('stock.incoterms', 'Incoterms', required=True)
    transporter_id = fields.Many2one('res.partner', 'Transporter', required=True)
    quantity = fields.Float('Total Weight', required=True, digits=dp.get_precision('Product Unit of Measure'))
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Account'))
    amount = fields.Float(string='Subtotal', compute='_compute_line', store=True)
    cost_id = fields.Many2one('stock.transport.cost', 'Cost Ref')

    @api.multi
    @api.depends('quantity', 'price_unit')
    def _compute_line(self):
        for line in self:
            line.amount = line.quantity * line.price_unit