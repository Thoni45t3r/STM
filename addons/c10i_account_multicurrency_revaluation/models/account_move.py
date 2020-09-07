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


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _reconcile_reversed_pair(self, move, reversed_move):
        context = self._context
        amls_to_reconcile = (move.line_ids + reversed_move.line_ids).filtered(lambda x: not x.reconciled)
        accounts_reconcilable = amls_to_reconcile.mapped('account_id').filtered(lambda a: a.reconcile)
        for account in accounts_reconcilable:
            amls_for_account = amls_to_reconcile.filtered(lambda l: l.account_id.id == account.id)
            print ">>>>>>>>>>>>>>>>>>>>>>>>>llll", amls_for_account
            print ">>>>>>>>>>>>>>>>>>>>>>>>>RECONCILE REVERSE", context.get('skip_full_reconcile_check')
            amls_for_account.with_context(context).reconcile()
            amls_to_reconcile = amls_to_reconcile - amls_for_account

    @api.multi
    def _reverse_move(self, date=None, journal_id=None):
        self.ensure_one()
        context = self._context
        reversed_move = self.copy(default={
            'date': date,
            'journal_id': journal_id.id if journal_id else self.journal_id.id,
            'ref': _('reversal of: ') + self.name})
        for acm_line in reversed_move.line_ids.with_context(check_move_validity=False):
            acm_line.write({
                'debit': acm_line.credit,
                'credit': acm_line.debit,
                'amount_currency': -acm_line.amount_currency
            })
        self.with_context(context)._reconcile_reversed_pair(self, reversed_move)
        # print ".................", asd
        return reversed_move

    @api.multi
    def reverse_moves(self, date=None, journal_id=None):
        date = date or fields.Date.today()
        reversed_moves = self.env['account.move']
        context = self._context
        for ac_move in self:
            print ".....................", ac_move.name
            reversed_move = ac_move.with_context(context)._reverse_move(date=date,
                                                  journal_id=journal_id)
            reversed_moves |= reversed_move
        if reversed_moves:
            reversed_moves._post_validate()
            reversed_moves.post()
            return [x.id for x in reversed_moves]
        return []

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    src_move_line_id = fields.Many2one('account.move.line', 'Source Forex Revaluation')
    unrealized_forex_line_ids = fields.One2many('account.move.line', 'src_move_line_id', 'Unrealized Forex')
    gl_foreign_balance = fields.Float('Aggregated Amount curency')
    gl_balance = fields.Float('Aggregated Amount')
    gl_revaluated_balance = fields.Float('Revaluated Amount')
    gl_currency_rate = fields.Float('Currency rate')

    @api.multi
    def compute_revaluations(self, revaluation_date, rate_date=False):
        self.ensure_one()
        context = self._context.copy()
        Currency = self.env['res.currency']
        rate_date = rate_date or revaluation_date
        if self.account_id.user_type_id.type not in ('receivable','payable') or not self.currency_id:
            return {}, {}
        ctx_rate = context
        ctx_rate['date'] = rate_date
        company = self.journal_id.company_id or self.env.user.company_id
        cp_currency = company.currency_id
        line_currency = Currency.with_context(ctx_rate).browse(self.currency_id.id)

        foreign_balance = self.amount_residual_currency
        balance = self.amount_residual
        unrealized_gain_loss = 0.0
        ctx_rate['revaluation'] = True
        adjusted_balance = line_currency.with_context(ctx_rate).compute(foreign_balance, cp_currency)
        unrealized_gain_loss = adjusted_balance - balance
        adj_balance = line_currency.round(unrealized_gain_loss)
        if not adj_balance:
            return {}, {}
        if not (company.revaluation_gain_account_id or company.revaluation_loss_account_id):
            raise UserError(_("No revaluation account are defined"
                  " for your company.\n"
                  "You must specify at least one provision account or"
                  " a couple of provision account."))
        # prepare dict moves
        label = "Currency Revaluation : %s"%(line_currency.rate)
        line_reval = {
            'name': label,
            'partner_id': self.partner_id and self.partner_id.id or False,
            'account_id': self.account_id.id,
            'debit': 0.0,
            'credit': 0.0,
            'currency_id': self.currency_id.id,
            'amount_currency': 0.0,
            'gl_balance' : self.amount_residual,
            'gl_currency_rate' : line_currency.rate,
            'gl_foreign_balance' : self.amount_residual_currency,
            'gl_revaluated_balance' : adj_balance,
        }

        line_reval_ct = line_reval.copy()
        if adj_balance >= 0.01:
            line_reval['debit']= adj_balance
            line_reval_ct['account_id'] = company.revaluation_gain_account_id.id
            line_reval_ct['credit'] = adj_balance
            line_reval_ct['name'] = 'Gain Income from Revaluation'
        elif adj_balance <= -0.01:
            line_reval['credit']= abs(adj_balance)
            line_reval_ct['account_id'] = company.revaluation_loss_account_id.id
            line_reval_ct['debit'] = abs(adj_balance)
            line_reval_ct['name'] = 'Loss Expense from Revaluation'
        line_reval.update({'src_move_line_id': self.id})
        return line_reval, line_reval_ct