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

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.multi
    def _create_payment_entry_multi(self, amount, invoice, move, line):
        if line.move_line_id.currency_id!=self.company_id.currency_id and line.move_line_id.account_id.currency_revaluation:
            if not line.payment_id.company_id.currency_exchange_journal_id:
                raise UserError(_("You should configure the 'Exchange Rate Journal' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not line.payment_id.company_id.income_currency_exchange_account_id.id:
                raise UserError(_("You should configure the 'Gain Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not line.payment_id.company_id.expense_currency_exchange_account_id.id:
                raise UserError(_("You should configure the 'Loss Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            move_line_reval, move_line_reval_ct = line.move_line_id.compute_revaluations(self.payment_date)
            if move_line_reval and move_line_reval_ct:
                move_line_reval.update({'payment_id': self.id})
                move_line_reval_ct.update({'payment_id': self.id})
                new_reval_move = self.env['account.move'].create({'journal_id': self.company_id.currency_exchange_journal_id.id,
                    'date': self.payment_date, 'line_ids': [(0,0,move_line_reval), (0,0,move_line_reval_ct)]})
                new_reval_move.post()
        
        super(AccountPayment, self)._create_payment_entry_multi(amount, invoice, move, line)

        if line.move_line_id.full_reconcile_id:
            reval_moves = line.move_line_id.unrealized_forex_line_ids.mapped('move_id')
            reval_moves.with_context(skip_full_reconcile_check='amount_currency_excluded').reverse_moves()

# class AccountPaymentLine(models.Model):
#     _inherit = 'account.payment.line'
    
#     @api.model
#     def reconcile_payment_line(self, counterpart_lines, writeoff_account=False, writeoff_journal=False):
#         self.ensure_one()
#         if self.move_line_id.unrealized_forex_line_ids:
#             to_reconcile = self.env['account.move.line']
#             to_reconcile |= self.move_line_id
#             for x in self.move_line_id.unrealized_forex_line_ids:
#                 to_reconcile |= x
#             for move_line in counterpart_lines:
#                 to_reconcile |= move_line
#             print ">>>>>>>>>>>>>>>>>>>>>>>", to_reconcile
#             to_reconcile.reconcile(writeoff_account, writeoff_journal)
#             print ">>>>>>>>>>>>>>>>>>>>>>>", asd
#         else:
#             super(AccountPaymentLine, self).reconcile_payment_line(counterpart_lines, writeoff_account, writeoff_journal)