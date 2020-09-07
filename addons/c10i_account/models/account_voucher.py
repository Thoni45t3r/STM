# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
from odoo import fields, models, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from datetime import datetime


class AccountVoucher(models.Model):
    _name    = "account.voucher"
    _description = 'Accounting Voucher'
    _inherit = ['account.voucher', 'mail.thread', 'ir.needaction_mixin']

    @api.model
    def _default_journal(self):
        voucher_type = self._context.get('voucher_type', 'sale')
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', ('cash','bank')),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    #added by deby
    check_number    = fields.Char("No. Giro")
    check_date      = fields.Date("Tanggal Giro")
    # ------------------ #
    journal_id = fields.Many2one('account.journal', 'Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]}, default=_default_journal)
    number = fields.Char(readonly=False, copy=False)
    account_id = fields.Many2one('account.account', 'Account', required=True, readonly=True, domain="[('deprecated', '=', False)]")
    # , states={'draft': [('readonly', False)]}
    #voucher_type = fields.Selection([('sale', 'Receipt'), ('purchase', 'Payment')], string='Type', required=True, readonly=True, states={'draft': [('readonly', False)]}, oldname="type", default='sale')
    voucher_type = fields.Selection([
        ('sale', 'Receive'),
        ('purchase', 'Payment'),
        ], string='Type', default='purchase', readonly=True, states={'draft': [('readonly', False)]}, oldname="type")
    transaction_type = fields.Selection([('expedition', 'Expedition'), ('regular', 'Regular'),('disposal','Asset Disposal')], string='Transaction Type', readonly=True, states={'draft': [('readonly', False)]})
    statement_line_id = fields.Many2one('account.bank.statement.line', string='Statement Line')
    #===========================================================================
    journal_report_type    = fields.Selection([
                            ('sale', 'Sale'),
                            ('purchase', 'Purchase'),
                            ('cash', 'Cash'),
                            ('bank', 'Bank'),
                            ('general', 'Miscellaneous'),
                        ], required=True, related="journal_id.type", store=False, readonly=True,
                        help="Select 'Sale' for customer invoices journals.\n"\
                        "Select 'Purchase' for vendor bills journals.\n"\
                        "Select 'Cash' or 'Bank' for journals that are used in customer or vendor payments.\n"\
                        "Select 'General' for miscellaneous operations journals.")

    @api.model
    def create(self, vals):
        journal = self.env['account.journal'].browse(vals['journal_id'])
        if journal.sequence_id:
            if not journal.sequence_id.active:
                raise UserError(_('Please activate the sequence of selected journal !'))
        else:
            raise UserError(_('Please define a sequence on the journal.'))
        if journal.type in ('cash','bank') and journal.receipt_sequence:
            if journal.receipt_sequence_id:
                if not journal.receipt_sequence_id:
                    raise UserError(_('Please activate the Receipt Sequence of selected journal !'))
            else:
                raise UserError(_('Please define a Receipt Sequence on the journal.'))
        date = vals.get('date', datetime.now().strftime('%Y-%m-%d'))
        if vals.get('voucher_type', 'purchase')=='sale' and journal.receipt_sequence:
            vals['number'] = not vals.get('number',False) and journal.receipt_sequence_id.with_context(ir_sequence_date=date).next_by_id() or vals['number']
        else:
            vals['number'] = not vals.get('number',False) and journal.sequence_id.with_context(ir_sequence_date=date).next_by_id() or vals['number']
        return super(AccountVoucher, self).create(vals)

    @api.multi
    def write(self, update_vals):
        # UNCOMMENT THIS IF YOU WANT YOUR JOURNAL TO BE EDITABLE
        # BUT THERE IS A POSSIBIILTY THAT YOU WILL FIND A MISSING JOURNAL NUMBER
        # BECAUSE OF THE OTHER TRANSACTION MISTAKE
        # if 'journal_id' in update_vals and 'number' not in update_vals:
        #     journal = self.env['account.journal'].browse(update_vals['journal_id'])
        #     if journal.sequence_id:
        #         if not journal.sequence_id.active:
        #             raise UserError(_('Please activate the sequence of selected journal !'))
        #     else:
        #         raise UserError(_('Please define a sequence on the journal.'))
        #     date = update_vals.get('date', self.date)
        #     update_vals['number'] = journal.sequence_id.with_context(ir_sequence_date=date).next_by_id()
        if 'number' in update_vals:
            if self.statement_line_id:
                self.statement_line_id.name = update_vals['number']
        return super(AccountVoucher, self).write(update_vals)

    @api.onchange('partner_id', 'pay_now', 'journal_id')
    def onchange_partner_id(self):
        #print "==onchange_partner_id==",self.pay_now,self.voucher_type
        if self.pay_now == 'pay_now':
            if self.journal_id.type in ('sale','purchase'):
                liq_journal = self.env['account.journal'].search([('type','not in',['sale','purchase'])], limit=1)
                self.account_id = liq_journal.default_debit_account_id \
                    if self.voucher_type == 'sale' else liq_journal.default_credit_account_id
            else:
                self.account_id = self.journal_id.default_debit_account_id \
                    if self.voucher_type == 'sale' else self.journal_id.default_credit_account_id
        else:
            if self.partner_id:
                self.account_id = self.partner_id.property_account_receivable_id \
                    if self.voucher_type == 'sale' else self.partner_id.property_account_payable_id
            elif self.journal_id.type not in ('sale','purchase'):
                self.account_id = False
            else:
                self.account_id = self.journal_id.default_debit_account_id \
                    if self.voucher_type == 'sale' else self.journal_id.default_credit_account_id

    @api.multi
    def _action_statement_line_create(self):
        for voucher in self:
            Statement = self.env['account.bank.statement']
            StatementLine = self.env['account.bank.statement.line']
            statement_id = Statement.search([('journal_id','=',voucher.journal_id.id),
                                             ('date','=',voucher.date)], limit=1)
            if not statement_id:
                statement_id = Statement.with_context({'journal_id': voucher.journal_id.id}).create({'journal_id': voucher.journal_id.id, 'date': voucher.date})
            elif statement_id.state=='confirm':
                raise UserError(_("Your %s is already Validated. It means you have closed your Statement at this Payment Date (%s).\n \
                    Please Re-Open it first before Creating a new Entry") % (voucher.journal_id.type=='bank' and 'Bank Statement' or 'Cash Register', voucher.date))
            statement_line_id = StatementLine.create({
                'statement_id': statement_id.id,
                'voucher_id': voucher.id,
                'date': voucher.date,
                'name': voucher.name or 'Direct Payment %s'%voucher.number, 
                'partner_id': voucher.partner_id and voucher.partner_id.id or False,
                'ref': voucher.number or '',
                'amount': voucher.voucher_type == 'sale' and voucher.amount or -voucher.amount,
            })
            voucher.write({'statement_line_id': statement_line_id.id})
        return True

    @api.multi
    def proforma_voucher(self):
        result = super(AccountVoucher, self).proforma_voucher()
        self._action_statement_line_create()
        return result
    
    @api.multi
    def cancel_voucher(self):
        result = super(AccountVoucher, self).cancel_voucher()
        for voucher in self:
            if voucher.statement_line_id and voucher.statement_line_id.state == 'confirm':
                raise UserError(_("Please set the bank statement to New before canceling."))
            voucher.statement_line_id.unlink()
        return result

    @api.multi
    def first_move_line_get(self, move_id, company_currency, current_currency):
        move_line = super(AccountVoucher, self).first_move_line_get(move_id, company_currency, current_currency)
        if self.partner_id.commercial_partner_id.id == self.company_id.id:
            move_line.update({'partner_id': self.partner_id.id})
        return move_line

    @api.multi
    def voucher_move_line_create(self, line_total, move_id, company_currency, current_currency):
        '''
        Create one account move line, on the given account move, per voucher line where amount is not 0.0.
        It returns Tuple with tot_line what is total of difference between debit and credit and
        a list of lists with ids to be reconciled with this format (total_deb_cred,list_of_lists).

        :param voucher_id: Voucher id what we are working with
        :param line_total: Amount of the first line, which correspond to the amount we should totally split among all voucher lines.
        :param move_id: Account move wher those lines will be joined.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: Tuple build as (remaining amount not allocated on voucher lines, list of account_move_line created in this method)
        :rtype: tuple(float, list of int)
        '''
        for line in self.line_ids:
            #create one move line per voucher line where amount is not 0.0
            if not line.price_subtotal:
                continue
            # convert the amount set on the voucher line into the currency of the voucher's company
            # this calls res_curreny.compute() with the right context,
            # so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
            debit = credit = 0.0
            amount = self._convert_amount(line.price_unit*line.quantity)
            if self.voucher_type == 'sale':
                if amount < 0.0:
                    debit = abs(amount)
                else:
                    credit = amount
            elif self.voucher_type == 'purchase':
                if amount < 0.0:
                    credit = abs(amount)
                else:
                    debit = amount
            sign = debit - credit < 0 and -1 or 1

            move_line = {
                'journal_id': self.journal_id.id,
                'name': line.name or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'partner_id': self.partner_id.commercial_partner_id.id,
                'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                'quantity': 1,
                'debit': debit,
                'credit': credit,
                'date': self.account_date,
                'tax_ids': [(4,t.id) for t in line.tax_ids],
                # 'amount_currency': line.price_subtotal if current_currency != company_currency else 0.0,
                'amount_currency': sign*line.price_subtotal if current_currency != company_currency else 0.0,
                'currency_id': company_currency != current_currency and current_currency or False,
                'payment_id': self._context.get('payment_id'),
            }
            self.env['account.move.line'].with_context(apply_taxes=True).create(move_line)
            line_total += (debit - credit)
        return line_total

    @api.model
    def balancing_move_line_create(self, amount, move_id):
        debit = credit = 0.0
        if amount < 0:
            debit = abs(amount)
            account_id = self.company_id.currency_exchange_journal_id.default_debit_account_id.id
        else:
            credit = amount
            account_id = self.company_id.currency_exchange_journal_id.default_credit_account_id.id
        if not account_id:
            raise UserError(_('Configuration Error !'), _('You need to define Expense/Income Account in Configuration'))
        move_line = {
            'journal_id': self.journal_id.id,
            'name': 'Rounding Difference',
            'account_id': account_id,
            'move_id': move_id,
            'partner_id': self.partner_id.commercial_partner_id.id,
            'debit': debit,
            'credit': credit,
            'date': self.account_date,
            'amount_currency': 0.0,
            'currency_id': False,
            'payment_id': self._context.get('payment_id'),
        }
        self.env['account.move.line'].create(move_line)

    @api.multi
    def voucher_pay_now_payment_create(self):
        if self.voucher_type == 'sale':
            payment_methods = self.journal_id.inbound_payment_method_ids
            payment_type = 'inbound'
            partner_type = 'customer'
            sequence_code = 'account.payment.customer.invoice'
        else:
            payment_methods = self.journal_id.outbound_payment_method_ids
            payment_type = 'outbound'
            partner_type = 'supplier'
            sequence_code = 'account.payment.supplier.invoice'
        # name = self.env['ir.sequence'].with_context(ir_sequence_date=self.date).next_by_code(sequence_code)
        # REMOVE THIS BECAUSE WE ARE USING DIFFERENT SOURCE OF NUMBER
        name = self.number
        partner_id = self.partner_id.commercial_partner_id.id
        if self.partner_id.commercial_partner_id.id == self.company_id.id:
            partner_id = self.partner_id.id
        return {
            'name': name,
            'payment_type': 'direct_payment',
            # 'payment_type': payment_type,
            'payment_method_id': payment_methods and payment_methods[0].id or False,
            'partner_type': partner_type,
            'partner_id': partner_id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'payment_date': self.date,
            'journal_id': self.payment_journal_id.id,
            'company_id': self.company_id.id,
            'communication': self.name,
            'state': 'reconciled',
        }

    @api.multi
    def action_move_line_create(self):
        '''
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        for voucher in self:
            local_context = dict(self._context, force_company=voucher.journal_id.company_id.id)
            if voucher.move_id:
                continue
            company_currency = voucher.journal_id.company_id.currency_id.id
            current_currency = voucher.currency_id.id or company_currency
            # we select the context to use accordingly if it's a multicurrency case or not
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = local_context.copy()
            ctx['date'] = voucher.account_date
            ctx['check_move_validity'] = False
            # Create a payment to allow the reconciliation when pay_now = 'pay_now'.
            if self.pay_now == 'pay_now' and self.amount > 0:
                ctx['payment_id'] = self.env['account.payment'].create(self.voucher_pay_now_payment_create()).id
            # Create the account move record.
            move = self.env['account.move'].create(voucher.account_move_get())
            # Get the name of the account_move just created
            # Create the first line of the voucher
            move_line = self.env['account.move.line'].with_context(ctx).create(voucher.with_context(ctx).first_move_line_get(move.id, company_currency, current_currency))
            line_total = move_line.debit - move_line.credit
            if voucher.voucher_type == 'sale':
                line_total = line_total - voucher._convert_amount(voucher.tax_amount)
            elif voucher.voucher_type == 'purchase':
                line_total = line_total + voucher._convert_amount(voucher.tax_amount)
            # Create one move line per voucher line where amount is not 0.0
            line_total = voucher.with_context(ctx).voucher_move_line_create(line_total, move.id, company_currency, current_currency)
            if voucher.journal_id.company_id.currency_id.round(line_total)!=0.0:
                voucher.with_context(ctx).balancing_move_line_create(voucher.journal_id.company_id.currency_id.round(line_total), move.id)

            # Add tax correction to move line if any tax correction specified
            if voucher.tax_correction != 0.0:
                tax_move_line = self.env['account.move.line'].search([('move_id', '=', move.id), ('tax_line_id', '!=', False)], limit=1)
                if len(tax_move_line):
                    tax_move_line.write({'debit': tax_move_line.debit + voucher.tax_correction if tax_move_line.debit > 0 else 0,
                        'credit': tax_move_line.credit + voucher.tax_correction if tax_move_line.credit > 0 else 0})

            # We post the voucher.
            voucher.write({
                'move_id': move.id,
                'state': 'posted',
                'number': move.name
            })
            move.post()
        return True

    @api.multi
    def create_report(self):
        report_name = 'report_voucher_cash_bank'
        return {
                'type'          : 'ir.actions.report.xml',
                'report_name'   : report_name,
                'datas'         : {
                    'model'         : 'account.voucher',
                    'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or self.id,
                    'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or [],
                    'name'          : (self.journal_report_type.capitalize() + " - " + self.number)or "---",
                    },
                'nodestroy'     : False
        }
    
class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'
    
    voucher_id = fields.Many2one('account.voucher', string='Direct Payment')
