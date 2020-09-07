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

class AccountSettlementAdvance(models.Model):
    _name = 'account.settlement.advance'
    _description = 'Settlement Advance'
    _inherit = ['mail.thread']
    _order = "date desc, id desc"

    @api.model
    def _default_journal(self):
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', '=', 'general'),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    @api.model
    def _get_company(self):
        return self._context.get('company_id', self.env.user.company_id.id)

    name = fields.Char(readonly=True, copy=False, default="/")
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True, readonly=True, states={'draft': [('readonly', False)]})
    employee_partner_id = fields.Many2one('res.partner', related='employee_id.address_home_id', string='Employee Partner', readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date('Settlement Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', 'Payment Journal', required=True, readonly=True, states={'draft': [('readonly', False)]}, domain="[('type', '=', 'general')]", default=_default_journal)
    move_id = fields.Many2one('account.move', 'Journal Entry', readonly=True)
    move_line_ids = fields.One2many('account.move.line', related='move_id.line_ids', string='Journal Items', readonly=True)
    memo = fields.Char('Memo', readonly=True, states={'draft': [('readonly', False)]})

    settlement_amount_total = fields.Float(compute='amount_total', string='Settlement Amount', digits=dp.get_precision('Account'))
    return_amount_total = fields.Float(compute='amount_total', string='Return Amount', digits=dp.get_precision('Account'))
    return_account_id = fields.Many2one('account.account', 'Return Account', readonly=True, states={'draft': [('readonly', False)]})
    voucher_ids = fields.Many2many('account.voucher', 'settlement_advance_account_voucher_rel', 'settlement_id', 'voucher_id', string="Payments", copy=False, readonly=True)
    has_vouchers = fields.Boolean(compute="_get_has_vouchers")
    
    settlement_line_ids = fields.One2many('account.settlement.advance.line', 'settlement_id', 'Detail Settlement', required=True, readonly=True, states={'draft': [('readonly', False)]})
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

    @api.one
    @api.depends('voucher_ids')
    def _get_has_vouchers(self):
        self.has_vouchers = bool(self.voucher_ids)

    @api.multi
    def button_vouchers(self):
        return {
            'name': _('Payments'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.voucher',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', [x.id for x in self.voucher_ids])],
        }

    @api.depends('settlement_line_ids', 'settlement_line_ids.residual', 'settlement_line_ids.amount')
    def amount_total(self):
        settle_amount = 0.0
        return_amount = 0.0
        for line in self.settlement_line_ids:
            settle_amount += line.amount
            return_amount += line.residual - line.amount

        self.settlement_amount_total = settle_amount
        self.return_amount_total = return_amount

    @api.model
    def create(self, vals):
        name = '/'
        date = vals.get('date', datetime.now().strftime('%Y-%m-%d'))
        if vals.get('journal_id', False):
            journal = self.env['account.journal'].browse(vals['journal_id'])
            if not journal.sequence_id:
                raise UserError(_('Configuration Error !'), _('The journal %s does not have a sequence, please specify one.') % journal.name)
            if not journal.sequence_id.active:
                raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % journal.name)
            name = not vals.get('name',False) and journal.with_context(ir_sequence_date=date).sequence_id.next_by_id() or vals['name']
        if name:
            vals['name'] = name
            # vals['move_name'] = name
        return super(AccountSettlementAdvance, self).create(vals)

    @api.model
    def unlink(self):
        for settle in self:
            if settle.state!='cancel':
                raise UserError(_('Deletion Error !'), _('Please Cancel before Deleting.'))
        return super(AccountSettlementAdvance, self).unlink()

    @api.model
    def _prepare_settlement_line(self, line):
        sign = 1.0
        company_currency = line.move_line_id.journal_id.company_id.currency_id
        advance_currency = line.move_line_id.currency_id or company_currency
        vals = {
            'advance_line_id': line.id,
            'move_line_id': line.move_line_id.id,
            'currency_id': advance_currency.id,
            'name': line.name or '',
        }
        # settlement_currency = self.currency_id
        vals['amount_total'] = sign * line.amount
        vals['residual'] = sign * line.residual_amount
        # else:
            # vals['amount_total'] = sign * company_currency.compute((line.debit-line.credit), payment_currency, round=False)#currency_pool.compute(cr, uid, company_currency, voucher_currency, move_line.credit or move_line.debit or 0.0, context=ctx)
            # vals['residual'] = sign * company_currency.compute(line.amount_residual, payment_currency, round=False)#currency_pool.compute(cr, uid, company_currency, voucher_currency, abs(move_line.amount_residual), context=ctx)
        return vals


    @api.multi
    def _set_outstanding_lines(self, partner_id, account_id, journal_id, date):
        AdvanceLine = self.env['account.employee.advance.line']
        self.ensure_one()
        if self.settlement_line_ids:
            self.settlement_line_ids.unlink()
        # move_lines = MoveLine.search([('account_id','=',account_id.id),('account_id.reconcile','=',True),('partner_id','=',partner_id.id),('reconciled','=',False)])
        os_lines = AdvanceLine.search([('employee_id','=',self.employee_id.id), ('move_line_id.account_id','=',account_id.id),('move_line_id.account_id.reconcile','=',True),('move_line_id.reconciled','=',False)])
        settlement_lines = self.env['account.settlement.advance.line']
        for line in os_lines:
            settle_vals = self._prepare_settlement_line(line)
            settlement_lines |= settlement_lines.new(settle_vals)
        self.settlement_line_ids = settlement_lines

    @api.multi
    def button_outstanding(self):
        for settlement in self:
            account_id = settlement.employee_partner_id.advance_account_id
            if settlement.employee_partner_id and settlement.journal_id and settlement.date:
                settlement._set_outstanding_lines(settlement.employee_partner_id, account_id, settlement.journal_id, settlement.date)

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
    def _prepare_return_move_line(self, move):
        self.ensure_one()
        company_currency = move.journal_id.company_id.currency_id
        current_currency = company_currency
        amount = self.return_amount_total
        debit = credit = 0.0
        if amount > 0.0:
            debit = amount
        else:
            credit = abs(amount)
        return {
            'move_id': move.id,
            'account_id': self.return_account_id.id,
            'partner_id': self.employee_partner_id.id,
            'name': self.name,
            'journal_id': move.journal_id.id,
            'date': move.date,
            'debit': debit,
            'credit': credit,
            'amount_currency': current_currency!=company_currency and self.return_amount_total or 0.0,
            'currency_id': current_currency!=company_currency and current_currency.id or False,
        }

    @api.multi
    def settle(self):
        '''
        Confirm the advances given in ids and create the journal entries for each of them
        '''
        MoveLine = self.env['account.move.line']
        for settlement in self:
            local_context = dict(self._context, force_company=settlement.journal_id.company_id.id)
            #validation lines
            valid = False
            for line in settlement.settlement_line_ids:
                if line.amount:
                    valid = True
            if not valid:
                raise UserError(_('There should be at least one Advance that need to be settled.'))

            if settlement.move_id:
                continue
            ctx = local_context.copy()
            ctx['date'] = settlement.date
            ctx['check_move_validity'] = False
            
            move = self.env['account.move'].create(settlement.account_move_get())
            for line in settlement.settlement_line_ids:
                if not line.amount:
                    line.unlink()
                    continue
                # if line.residual!=line.amount:
                #     raise UserError(_('This settlemenet (%s) is not Valid. Residual Amount is %s while you \
                #         were about to settle for only %s. \nSettlement Amount must be same with \
                #         Residual Amount')%(str(line.move_line_id.move_id.name),str(line.residual), str(line.amount)))
                if line.split_line_ids:
                    for split_line in line.split_line_ids:
                        move_line_vals = split_line._prepare_expense_split_move_line(line, move)
                        MoveLine.with_context(ctx).create(move_line_vals)
                else:
                    move_line_vals = line._prepare_expense_move_line(move)
                    MoveLine.with_context(ctx).create(move_line_vals)
                
                # amount_line = line.amount
                amount_line = line.residual
                new_move_line = MoveLine.with_context(ctx).create(line._prepare_settlement_move_line(move, amount_line))
                (line.move_line_id + new_move_line).reconcile()

            if settlement.return_amount_total and settlement.return_account_id:
                move_line_vals = settlement._prepare_return_move_line(move)
                MoveLine.with_context(ctx).create(move_line_vals)

            settlement.write({
                'move_id': move.id,
                'state': 'posted',
            })
            move.post()
        return True

    @api.multi
    def action_cancel(self):
        for settle in self:
            settle.move_id.line_ids.remove_move_reconcile()
            settle.move_id.button_cancel()
            settle.move_id.unlink()
            settle.state = 'cancel'

    @api.multi
    def action_draft(self):
        for settle in self:
            settle.state = 'draft'

    @api.multi
    def _prepare_voucher(self, payment_date, journal_id):
        self.ensure_one()
        voucher_type = self.return_amount_total < 0 and 'purchase' or 'sale'
        journal = self.env['account.journal'].browse(journal_id)
        account_id = False
        if voucher_type=='purchase' and journal.default_credit_account_id:
            account_id = journal.default_credit_account_id.id
        elif voucher_type=='sale' and journal.default_debit_account_id:
            account_id = journal.default_debit_account_id.id

        if not account_id:
            raise UserError(_('Configuration Error !'), _('The journal %s does not Defautl Debit/Credit Account, please specify one.') % journal.name)

        return {
            'voucher_type': voucher_type,
            'partner_id': self.employee_partner_id.id,
            'name': self.name,
            'date': payment_date,
            'account_date': payment_date,
            'company_id': self.company_id.id,
            'pay_now': 'pay_now',
            'account_id': account_id,
            'journal_id': journal_id,
        }

    @api.multi
    def _prepare_voucher_line(self, voucher_id):
        self.ensure_one()
        return {
            'voucher_id': voucher_id,
            'name': self.name,
            'price_unit': abs(self.return_amount_total),
            'quantity': 1.0,
            'account_id': self.return_account_id.id,
        }

    @api.multi
    def action_create_return_payment(self, payment_date, journal_id):
        Voucher = self.env['account.voucher']
        VoucherLine = self.env['account.voucher.line']
        res = []
        for settlement in self:
            if not settlement.return_amount_total:
                continue
            voucher_vals = settlement._prepare_voucher(payment_date, journal_id)
            voucher = Voucher.create(voucher_vals)

            voucher_line_vals = self._prepare_voucher_line(voucher.id)
            voucher_line = VoucherLine.create(voucher_line_vals)

            settlement.write({'voucher_ids': [(4, voucher.id)]})
            res.append(voucher.id)
        return res

class SplitSettlementAdvanceLine(models.Model):
    _name = 'split.settlement.advance.line'
    _description = 'Split Settlement Advance'

    settlement_line_id = fields.Many2one('account.settlement.advance.line', 'Linked Settlement Line', ondelete='cascade')
    account_id = fields.Many2one('account.account', 'Account')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    name = fields.Char('Description')
    amount = fields.Float('Settlement Amount', digits=dp.get_precision('Account'))

    def _prepare_expense_split_move_line(self, settlement_line, move):
        company_currency = move.journal_id.company_id.currency_id
        current_currency = company_currency
        debit = credit = 0.0
        amount = current_currency!=company_currency and \
            current_currency.with_context({'date': move.date}).compute(self.amount, company_currency) \
            or self.amount
        sign = 1
        if settlement_line.residual>0.0:
            if amount>0.0:
                debit = amount
            else:
                credit = abs(amount)
        else:
            sign = -1
            if amount>0.0:
                credit = amount
            else:
                debit = abs(amount)
        return {
            'move_id': move.id,
            'account_id': self.account_id.id,
            'analytic_account_id': self.analytic_account_id.id,
            'partner_id': settlement_line.move_line_id.partner_id.id,
            'name': self.name,
            'journal_id': move.journal_id.id,
            'date': move.date,
            'debit': debit,
            'credit': credit,
            'amount_currency': current_currency!=company_currency and sign*self.amount or 0.0,
            'currency_id': current_currency!=company_currency and current_currency.id or False,
        }


class AccountSettlementAdvanceLine(models.Model):
    _name = 'account.settlement.advance.line'
    _description = 'Detail Settlement Advance'

    settlement_id = fields.Many2one('account.settlement.advance', 'Settlement Ref', required=True, ondelete='cascade')
    name = fields.Char('Description')
    advance_line_id = fields.Many2one('account.employee.advance.line', 'Advance', ondelete='cascade')
    move_line_id = fields.Many2one('account.move.line', 'Move Line', required=False, ondelete='cascade')
    account_id = fields.Many2one('account.account', 'Account')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    currency_id = fields.Many2one('res.currency', 'Currency')
    amount_total = fields.Float('Original Amount', required=True, digits=dp.get_precision('Account'))
    residual = fields.Float('Residual Amount', required=True, digits=dp.get_precision('Account'))
    amount = fields.Float('Settlement Amount', digits=dp.get_precision('Account'))
    split_line_ids = fields.One2many('split.settlement.advance.line', 'settlement_line_id', 'Split Settlement')
    return_amount = fields.Float(compute='_return_amount', string='Return Amount', digits=dp.get_precision('Account'))

    @api.depends('residual', 'amount')
    def _return_amount(self):
        self.return_amount = self.residual - self.amount

    @api.onchange('split_line_ids', 'account_id')
    def onchange_split_line(self):
        if self.split_line_ids:
            self.account_id = False
            total = 0.0
            for line in self.split_line_ids:
                total+= line.amount
            self.amount = total

    def _prepare_expense_move_line(self, move):
        company_currency = move.journal_id.company_id.currency_id
        current_currency = company_currency
        debit = credit = 0.0
        amount = current_currency!=company_currency and \
            current_currency.with_context({'date': move.date}).compute(self.amount, company_currency) \
            or self.amount
        sign = 1
        if self.residual>0.0:
            if amount>0.0:
                debit = amount
            else:
                credit = abs(amount)
        else:
            sign = -1
            if amount>0.0:
                credit = amount
            else:
                debit = abs(amount)
        return {
            'move_id': move.id,
            'account_id': self.account_id.id,
            'analytic_account_id': self.analytic_account_id.id,
            'partner_id': self.move_line_id.partner_id.id,
            'name': self.name,
            'journal_id': move.journal_id.id,
            'date': move.date,
            'debit': debit,
            'credit': credit,
            'amount_currency': current_currency!=company_currency and sign*self.amount or 0.0,
            'currency_id': current_currency!=company_currency and current_currency.id or False,
        }

    def _prepare_settlement_move_line(self, move, amount_line):
        company_currency = move.journal_id.company_id.currency_id
        current_currency = company_currency
        debit = credit = 0.0
        amount = current_currency!=company_currency and \
            current_currency.with_context({'date': move.date}).compute(amount_line, company_currency) \
            or amount_line
        sign = 1
        if self.residual>0.0:
            sign = -1
            if amount>0.0:
                credit = amount
            else:
                debit = abs(amount)
        else:
            if amount>0.0:
                debit = amount
            else:
                credit = abs(amount)
        return {
            'move_id': move.id,
            'account_id': self.move_line_id.account_id.id,
            'partner_id': self.move_line_id.partner_id.id,
            'name': self.name,
            'journal_id': move.journal_id.id,
            'date': move.date,
            'debit': debit,
            'credit': credit,
            'amount_currency': current_currency!=company_currency and amount_line or 0.0,
            'currency_id': current_currency!=company_currency and current_currency.id or False,
        }