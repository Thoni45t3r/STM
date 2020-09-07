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
from odoo.tools import float_compare, float_is_zero
import urllib3
import odoo.addons.decimal_precision as dp
from lxml import etree

# from faktur_pajak import KODE_TRANSAKSI_FAKTUR_PAJAK

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 
            'company_id', 'date_invoice', 'type', 'register_advance_ids.amount')
    def _compute_amount(self):
        res = super(AccountInvoice, self)._compute_amount()
        round_curr = self.currency_id.round
        advance_total = sum(round_curr(line.amount) for line in self.register_advance_ids)
        self.amount_untaxed = self.amount_untaxed - advance_total
        self.amount_total = self.amount_total - advance_total
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
        return res

    amount_untaxed = fields.Monetary(string='Untaxed Amount',
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_total = fields.Monetary(string='Total',
        store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Monetary(string='Total',
        store=True, readonly=True, compute='_compute_amount')
    amount_total_signed = fields.Monetary(string='Total in Invoice Currency', currency_field='currency_id',
        store=True, readonly=True, compute='_compute_amount',
        help="Total amount in the currency of the invoice, negative for credit notes.")
    amount_total_company_signed = fields.Monetary(string='Total in Company Currency', currency_field='company_currency_id',
        store=True, readonly=True, compute='_compute_amount',
        help="Total amount in the currency of the company, negative for credit notes.")
    register_advance_ids = fields.One2many('account.invoice.register.advance', 'invoice_id', 
        string='Register Advance', readonly=True, states={'draft': [('readonly', False)]}, copy=False)

    @api.multi
    def advance_outstanding(self):
        self.ensure_one()
        if self.type=='in_invoice':
            advance_type = 'in_advance'
        elif self.type=='out_invoice':
            advance_type = 'out_advance'
        else:
            return False

        advance_line = self.env['account.invoice.advance.line'].search([
            ('invoice_id.partner_id','=',self.partner_id.id),('invoice_id.type','=',advance_type),
            ('reconciled','=',False)])
        company_currency = self.journal_id.company_id.currency_id
        invoice_currenct = self.currency_id
        advance_lines = []
        for line in advance_line:
            vals = {
                'invoice_id': self.id,
                'advance_line_id': line.id,
                'amount_total': line.price_subtotal,
                'residual': line.residual,
                'amount': line.residual,
            }
            advance_lines.append(vals)
        self.register_advance_ids = list(map(lambda x: (0,0,x), advance_lines))
        # Compute Taxes
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.tax_line_ids.filtered('manual')
        for tax in taxes_grouped.values():
            tax_lines += tax_lines.new(tax)
        self.tax_line_ids = tax_lines

    @api.onchange('register_advance_ids')
    def _onchange_register_advance_ids(self):
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.tax_line_ids.filtered('manual')
        for tax in taxes_grouped.values():
            tax_lines += tax_lines.new(tax)
        self.tax_line_ids = tax_lines
        return

    @api.multi
    def get_taxes_values(self):
        tax_grouped = super(AccountInvoice, self).get_taxes_values()
        for rline in self.register_advance_ids:
            line = rline.advance_line_id
            price_unit = line.price_unit
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, False, self.partner_id)['taxes']
            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

                if key not in tax_grouped:
                    tax_grouped[key] = -1*val
                else:
                    tax_grouped[key]['amount'] += -1*val['amount']
                    tax_grouped[key]['base'] += -1*val['base']
        return tax_grouped

    @api.model
    def invoice_line_move_line_get(self):
        res = super(AccountInvoice, self).invoice_line_move_line_get()
        for line in self.register_advance_ids:
            if line.amount<=0:
                continue
            move_line_dict = {
                'advl_id': line.id,
                'type': 'advance',
                'name': line.invoice_id.number or 'Advance',
                'price_unit': -1*line.amount,
                'quantity': 1.0,
                'price': -1*line.amount,
                'account_id': line.move_line_id.account_id.id,
                'product_id': False,
                'uom_id': False,
                'account_analytic_id': False,
                'tax_ids': [],
                'invoice_id': self.id,
                'analytic_tag_ids': [],
            }
            res.append(move_line_dict)
        return res

    @api.model
    def line_get_convert(self, line, part):
        res = super(AccountInvoice, self).line_get_convert(line, part)
        res.update({'invline': line.get('advl_id') and self.env['account.invoice.register.advance'].browse(line['advl_id']) or False,
            'inv_line_type': line['type']})
        return res

    # BUAT REVAL ATAS PENERIMAAN BARANG
    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_move = self.env['account.move']
        account_move_line = self.env['account.move.line']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise UserError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            iml = inv.invoice_line_move_line_get()
            iml += inv.tax_line_move_line_get()

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, iml)

            name = inv.name or '/'
            if inv.payment_term_id:
                totlines = inv.with_context(ctx).payment_term_id.with_context(currency_id=company_currency.id).compute(total, inv.date_invoice)[0]
                res_amount_currency = total_currency
                ctx['date'] = inv._get_currency_rate_date()
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice_id': inv.id
                })
            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            line = inv.finalize_invoice_move_lines(line)

            date = inv.date or inv.date_invoice
            move_vals = {
                'ref': inv.reference,
                # 'line_ids': line,
                'journal_id': journal.id,
                'date': date,
                'narration': inv.comment,
            }
            ctx['company_id'] = inv.company_id.id
            ctx['invoice'] = inv
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)

            for i, c, move_val in line:
                move_val.update({'move_id': move.id})
                new_move_line = account_move_line.with_context(check_move_validity=False).create(move_val)
                if move_val['inv_line_type']=='advance' and move_val.get('invline') \
                        and move_val['invline'].move_line_id:
                    (new_move_line + move_val['invline'].move_line_id).reconcile()
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
        return True


class AccountInvoiceRegisterAdvance(models.Model):
    _name = 'account.invoice.register.advance'
    _description = 'Register Advance'
    
    @api.one
    @api.depends('advance_line_id', 'amount', 'invoice_id.date', 'invoice_id.currency_id')
    def _compute_payment_difference(self):
        self.payment_difference = self.residual - self.amount

    invoice_id = fields.Many2one('account.invoice', 'Invoice', ondelete='cascade', required=True)
    advance_line_id = fields.Many2one('account.invoice.advance.line', 'Advance Line', ondelete='restrict', required=True)
    invoice_advance_id = fields.Many2one('account.invoice.advance', related='advance_line_id.invoice_id', string='Invoice Advance', readonly=True)
    move_line_id = fields.Many2one('account.move.line', related='advance_line_id.move_line_id', string='Advance Line', readonly=True)
    currency_id = fields.Many2one('res.currency', related='invoice_advance_id.currency_id', string='Currency', readonly=True)
    date = fields.Date(related='move_line_id.move_id.date', string='Date', readonly=True)
    amount_total = fields.Float('Original Amount', required=True, digits=dp.get_precision('Account'), readonly=True)
    residual = fields.Float('Outstanding Amount', required=True, digits=dp.get_precision('Account'), readonly=True)
    amount = fields.Float('Allocation', required=True, digits=dp.get_precision('Account'))
    payment_difference = fields.Monetary(compute='_compute_payment_difference', string='Payment Difference', readonly=True, store=True)
    writeoff_account_id = fields.Many2one('account.account', string="Write-off Account", domain=[('deprecated', '=', False)], copy=False)