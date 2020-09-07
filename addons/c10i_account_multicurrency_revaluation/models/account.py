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

class AccountAccount(models.Model):
    _inherit = 'account.account'

    currency_revaluation = fields.Boolean("Allow Currency Revaluation", default=False)

    _sql_mapping = {
        'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as "
                   "balance",
        'debit': "COALESCE(SUM(l.debit), 0) as debit",
        'credit': "COALESCE(SUM(l.credit), 0) as credit",
        'foreign_balance': "COALESCE(SUM(l.amount_currency), 0) as foreign_"
                           "balance",
    }

    @api.multi
    def _foreign_currency_query(self, revaluation_date):
        context = self._context
        tables, lines_where_clause, lines_where_clause_params = self.env['account.move.line'].with_context(context)._query_get()
        where_clause = (lines_where_clause and " AND " or "")+" AND ".join(lines_where_clause)
        query = ("SELECT l.account_id as id, l.currency_id, " +
                 ', '.join(self._sql_mapping.values()) +
                 " FROM account_move_line l "
                 " WHERE l.account_id IN %s AND "
                 " l.date <= %s AND "
                 " l.currency_id IS NOT NULL "
                 + lines_where_clause +
                 " GROUP BY l.account_id, l.currency_id")
        params = [tuple(self.ids), revaluation_date] + lines_where_clause_params
        return query, params

    def foreign_currency_balance(self, revaluation_date):
        context = self._context
        accounts = {}

        # compute for each account the balance/debit/credit from the move lines
        ctx_query = context.copy()
        query, params = self.with_context(ctx_query)._foreign_currency_query(revaluation_date)
        self.env.cr.execute(query, params)

        lines = self.env.cr.dictfetchall()
        for line in lines:
            # generate a tree
            # - account_id
            # -- currency_id
            # --- partner_id
            # ----- balances
            account_id, currency_id = line['id'], line['currency_id']

            accounts.setdefault(account_id, {})
            accounts[account_id].setdefault(currency_id, {})
            accounts[account_id][currency_id] = line

        return accounts