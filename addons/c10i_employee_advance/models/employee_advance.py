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
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools import float_compare, float_is_zero
import odoo.addons.decimal_precision as dp

class AccountEmployeeAdvance(models.Model):
    _name = 'account.employee.advance'
    _description = 'Employee Advance'
    _inherit = ['mail.thread']
    _order = "date desc, id desc"

    @api.model
    def _default_journal(self):
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', ['bank','cash']),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    @api.model
    def _get_company(self):
        return self._context.get('company_id', self.env.user.company_id.id)

    name = fields.Char(readonly=True, copy=False, default="/")
    partner_id = fields.Many2one('res.partner', 'Vendor', readonly=True, states={'draft': [('readonly', False)]}, domain="[('supplier', '=', True)]")
    employee_id = fields.Many2one('hr.employee', 'Default Employee', readonly=True, states={'draft': [('readonly', False)]})
    employee_partner_id = fields.Many2one('res.partner', related='employee_id.address_home_id', string='Default Partner', readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date('Accounting Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', 'Payment Journal', required=True, readonly=True, states={'draft': [('readonly', False)]}, domain="[('type', 'in', ['cash', 'bank'])]", default=_default_journal)
    payment_id = fields.Many2one('account.payment', 'Payment ID')
    move_id = fields.Many2one('account.move', 'Journal Entry', readonly=True)
    move_line_ids = fields.One2many('account.move.line', related='move_id.line_ids', string='Journal Items', readonly=True)
    amount_total = fields.Float('Amount to Pay', compute='_amount_total', store=True, digits=dp.get_precision('Account'))
    memo = fields.Char('Memo', readonly=True, states={'draft': [('readonly', False)]})
    rounding_account_id = fields.Many2one('account.account', 'Rounding Account', readonly=True, states={'draft': [('readonly', False)]})
    
    line_ids = fields.One2many('account.employee.advance.line', 'advance_id', 'Detail Advance', required=True, readonly=True, states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', 'Company',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        related='journal_id.company_id', default=lambda self: self._get_company())
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('posted', 'Posted')
        ], 'Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed advance.\n"
             " * The 'Posted' status is used when user create advance,a advance number is generated and advance entries are created in account.\n"
             " * The 'Cancelled' status is used when user cancel advance.")
    statement_line_id = fields.Many2one('account.bank.statement.line', string='Statement Line')

    @api.depends('line_ids', 'line_ids.amount', 'state')
    def _amount_total(self):
        for adv in self:
            total = 0.0
            for line in adv.line_ids:
                total += line.amount
            adv.amount_total = total

    @api.model
    def create(self, vals):
        name = '/'
        date = vals.get('date', datetime.now().strftime('%Y-%m-%d'))
        if vals.get('journal_id', False):
            journal = self.env['account.journal'].browse(vals['journal_id'])
            if journal.sequence_id:
                if not journal.sequence_id.active:
                    raise UserError(_('The sequence of journal %s is deactivated.') % journal.name)
            else:
                raise UserError(_('The journal %s does not have a sequence, please specify one.') % journal.name)
            name = not vals.get('name',False) and journal.with_context(ir_sequence_date=date).sequence_id.next_by_id() or vals['name']
        if name:
            vals['name'] = name
            # vals['move_name'] = name
        return super(AccountEmployeeAdvance, self).create(vals)

    @api.multi
    def unlink(self):
        for adv in self:
            if adv.state!='cancel':
                raise UserError(_('Please Cancel before Deleting.'))
        return super(AccountEmployeeAdvance, self).unlink()

    @api.multi
    def advance_payment_create(self, current_currency_id):
        self.ensure_one()
        payment_methods = self.journal_id.outbound_payment_method_ids
        payment_type = 'outbound'
        partner_type = 'supplier'
        # sequence_code = 'account.payment.supplier.invoice'
        # name = self.env['ir.sequence'].with_context(ir_sequence_date=self.date).next_by_code(sequence_code)
        return {
            'name': self.name,
            'payment_type': payment_type,
            'payment_method_id': payment_methods and payment_methods[0].id or False,
            'partner_type': partner_type,
            'partner_id': self.partner_id and self.partner_id.commercial_partner_id.id or False,
            'amount': self.amount_total,
            'currency_id': current_currency_id,
            'payment_date': self.date,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'communication': self.name,
            'state': 'reconciled',
        }

    @api.multi
    def account_move_get(self):
        if self.name:
            name = self.name
        elif self.journal_id.sequence_id:
            if not self.journal_id.sequence_id.active:
                raise UserError(_('Please activate the sequence of selected journal !'))
            name = self.journal_id.sequence_id.with_context(ir_sequence_date=self.date).next_by_id()
        else:
            raise UserError(_('Please define a sequence on the journal.'))

        move = {
            'name': name,
            'journal_id': self.journal_id.id,
            'narration': self.memo,
            'date': self.date,
            # 'ref': self.reference,
        }
        return move

    @api.multi
    def _convert_amount(self, amount):
        for adv in self:
            current_currency = adv.journal_id.currency_id and adv.journal_id.currency_id or adv.company_id.currency_id
            return current_currency.compute(amount, adv.company_id.currency_id)

    @api.multi
    def advance_move_line_create(self, line_total, move_id, company_currency, current_currency):
        for line in self.line_ids:
            #create one move line per voucher line where amount is not 0.0
            if not line.amount:
                continue
            # check advance account
            if not line.employee_partner_id.advance_account_id:
                raise UserError(_('Employee %s doesnt have Advance Account configured in its data.\nPlease fill Advance Account first.') % line.employee_id.address_home_id.name)
            # convert the amount set on the voucher line into the currency of the voucher's company
            # this calls res_curreny.compute() with the right context,
            # so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
            amount = self._convert_amount(line.amount)
            move_line = line.with_context(self._context)._prepare_move_line(amount)
            move_line.update({
                'move_id': move_id,
                'amount_currency': self.amount if current_currency != company_currency else 0.0,
                'currency_id': company_currency != current_currency and current_currency or False,
            })
            line_total += (move_line['debit'] - move_line['credit'])
            move_line_id = self.env['account.move.line'].with_context(self._context).create(move_line)
            line.write({'move_line_id': move_line_id.id})
        return line_total

    @api.multi
    def first_move_line_get(self, move_id, company_currency, current_currency):
        debit = credit = 0.0
        credit = self._convert_amount(self.amount_total)
        if debit < 0.0: debit = 0.0
        if credit < 0.0: credit = 0.0
        sign = debit - credit < 0 and -1 or 1
        #set the first line of the voucher
        move_line = {
                'name': self.memo or 'Advance Payment',
                'debit': debit,
                'credit': credit,
                'account_id': self.journal_id.default_credit_account_id.id,
                'move_id': move_id,
                'journal_id': self.journal_id.id,
                'partner_id': self.partner_id.commercial_partner_id.id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': (sign * abs(self.amount_total)  # amount < 0 for refunds
                    if company_currency != current_currency else 0.0),
                'date': self.date,
                'payment_id': self._context.get('payment_id'),
            }
        return move_line

    @api.multi
    def rounding_move_line_create(self, difference_amount, move_id, company_currency, current_currency):
        debit = credit = 0.0
        if difference_amount < 0:
            debit = abs(difference_amount)
        else:
            credit = difference_amount
        if debit < 0.0: debit = 0.0
        if credit < 0.0: credit = 0.0
        #set the first line of the voucher
        if not self.rounding_account_id:
            raise UserError(_('We find the Journal Entry is not Balance with difference amount %s. Please fill Rounding Account to alocate this difference')%str(difference_amount))
        move_line = {
                'name': _('Rounding Amount'),
                'debit': debit,
                'credit': credit,
                'account_id': self.rounding_account_id.id,
                'move_id': move_id,
                'journal_id': self.journal_id.id,
                'partner_id': self.partner_id.commercial_partner_id.id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': 0.0,
                'date': self.date,
                'payment_id': self._context.get('payment_id'),
            }
        return move_line

    @api.multi
    def _prepare_statement_basic_line_entry(self, statement):
        self.ensure_one()
        values = {
            'statement_id': statement.id,
            'date': self.date,
            'name': self.name or '/', 
            'partner_id': self.partner_id.id,
            'ref': datetime.strptime(self.date, '%Y-%m-%d').strftime('%d/%m/%y'),
            'amount': -1*self.amount_total,
        }
        return values

    @api.multi
    def post(self):
        '''
        Confirm the advances given in ids and create the journal entries for each of them
        '''
        for advance in self:
            local_context = dict(self._context, force_company=advance.journal_id.company_id.id)
            if advance.move_id:
                continue
            company_currency = advance.journal_id.company_id.currency_id.id
            current_currency = advance.journal_id.currency_id and advance.journal_id.currency_id.id or company_currency
            # we select the context to use accordingly if it's a multicurrency case or not
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = local_context.copy()
            ctx['date'] = advance.date
            ctx['check_move_validity'] = False
            # Create Payment for Bank/Cash Reconciliation
            if advance.payment_id and self.amount_total > 0:
                advance.payment_id.write(self.advance_payment_create(current_currency))
                ctx['payment_id'] = advance.payment_id.id
            elif self.amount_total > 0:
                ctx['payment_id'] = self.env['account.payment'].create(self.advance_payment_create(current_currency)).id
            # Create the account move record
            move = self.env['account.move'].create(advance.account_move_get())
            # Create the cash/bank line of the advance
            move_line = self.env['account.move.line'].with_context(ctx).create(advance.with_context(ctx).first_move_line_get(move.id, company_currency, current_currency))
            line_total = move_line.debit - move_line.credit
            # Create one move line per advance line where amount is not 0.0
            line_total = advance.with_context(ctx).advance_move_line_create(line_total, move.id, company_currency, current_currency)
            # Check if line_total is not 0, then we will create rounding entry
            if line_total:
                advance.with_context(ctx).rounding_move_line_create(line_total, move.id, company_currency, current_currency)
            # Create Bank Statement / Cash Register
            # REMOVE THIS IF YOU DIDNT NEED IT 
            Statement = self.env['account.bank.statement']
            StatementLine = self.env['account.bank.statement.line']
            statement_brw = Statement.search([('journal_id','=',advance.journal_id.id),
                                             ('date','>=',advance.date),
                                             ('date','<=',advance.date)], limit=1)
            if not statement_brw:
                statement_brw = Statement.with_context({'journal_id': advance.journal_id.id}).create({'journal_id': advance.journal_id.id, 'date': advance.date})
            statement_line = StatementLine.create(advance._prepare_statement_basic_line_entry(statement_brw))
            # We post the advance.
            advance.write({
                'move_id': move.id,
                'state': 'posted',
                'payment_id': ctx.get('payment_id',False),
                'statement_line_id': statement_line.id
                # 'move_name': move.name
            })
            move.post()
        return True

    @api.multi
    def action_cancel(self):
        for adv in self:
            if adv.statement_line_id and adv.statement_line_id.statement_id.state=='confirm':
                raise UserError(_("Please set the bank statement to New before canceling this Advance."))
            settlement_ids = self.env['account.settlement.advance.line'].search([('advance_line_id','in',adv.line_ids.ids),('settlement_id.move_id','!=',False)])
            if settlement_ids:
                raise UserError(_('This Advance have already settled (%s).\n \
                    Please Cancel it before Canceling this transaction.') % \
                    str(", ".join(settlement_ids.mapped('settlement_id').mapped('name'))))
            
            for move_line in adv.move_id.line_ids:
                if move_line.statement_id and move_line.statement_id.state!='open':
                    raise UserError(_('This payment have already reconciled on Bank Statement.\nPlease Cancel Statement %s before Canceling this transaction.') % move_line.statement_id.name)
            adv.statement_line_id.unlink()
            adv.move_id.line_ids.remove_move_reconcile()
            adv.move_id.button_cancel()
            for payment in adv.move_id.line_ids.mapped('payment_id'):
                payment.cancel()
                payment.write({'move_name': False})
                payment.unlink()
            adv.move_id.unlink()
            adv.state = 'cancel'

    @api.multi
    def action_draft(self):
        for adv in self:
            adv.state = 'draft'

    @api.multi
    def print_voucher(self):
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : 'voucher_payment_employee_advance',
            'datas'         : {
                'model'         : 'account.employee.advance',
                'id'            : self.id,
                'ids'           : [self.id],
                'report_type'   : 'pdf',
                'form'          : {},
                },
            'nodestroy': False
        }

class AccountEmployeeAdvanceLine(models.Model):
    _name = 'account.employee.advance.line'
    _description = 'Detail Employee Advance'

    @api.one
    @api.depends('advance_id.state', 'amount', 'move_line_id.amount_residual', 'move_line_id.currency_id')
    def _residual_amount(self):
        currency_id = self.advance_id.journal_id.currency_id or self.advance_id.company_id.currency_id
        residual = 0.0
        residual_company_signed = 0.0
    
        line = self.move_line_id
        residual_company_signed = line.amount_residual
        if line.currency_id and line.currency_id.id == currency_id.id:
            residual = line.amount_residual_currency if line.currency_id else line.amount_residual
        else:
            from_currency = (line.currency_id and line.currency_id.with_context(date=line.date)) or line.company_id.currency_id.with_context(date=line.date)
            residual = from_currency.compute(line.amount_residual, currency_id)
        
        self.residual_company_signed = abs(residual_company_signed)
        self.residual_signed = abs(residual)
        self.residual = abs(residual)
        self.residual_amount = abs(residual)
        # digits_rounding_precision = self.currency_id.rounding

    advance_id = fields.Many2one('account.employee.advance', 'Advance Ref', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True, default=lambda self: self._context.get('employee_id', False))
    employee_partner_id = fields.Many2one('res.partner', related='employee_id.address_home_id', string='Default Partner', required=True)
    name = fields.Char('Description', required=True)
    amount = fields.Float('Amount', required=True, digits=dp.get_precision('Account'))
    move_line_id = fields.Many2one('account.move.line', 'Journal Item')
    residual_amount = fields.Float(compute='_residual_amount', string='Residual Amount', digits=dp.get_precision('Account'))
    # settlement_id = fields.Many2one('account.settlement.advance', 'Settlement')

    @api.multi
    def _prepare_move_line(self, amount):
        self.ensure_one()
        return {
                'journal_id': self.advance_id.journal_id.id,
                'name': self.name or '/',
                'account_id': self.employee_partner_id.advance_account_id.id,
                'partner_id': self.employee_partner_id.id,
                # 'analytic_account_id': self.account_analytic_id and self.account_analytic_id.id or False,
                'analytic_account_id': False,
                'quantity': 1,
                'debit': abs(amount) if amount>0 else 0.0,
                'credit': abs(amount) if amount<0 else 0.0,
                'date': self.advance_id.date,
                'payment_id': self._context.get('payment_id'),
            }