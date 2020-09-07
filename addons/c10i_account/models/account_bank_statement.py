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
import urllib3
from lxml import etree
import time

class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    # CUSTOM REQUIREMENT, REMOVE THIS IF THE COMPANY DOESNT NEED IT
    @api.multi
    def button_confirm_bank(self):
        for statement in self:
            check_all_line = []
            if statement.all_lines_reconciled:
                statement.write({'balance_end_real': statement.balance_end})
        # self._balance_check()
        statements = self.filtered(lambda r: r.state == 'open')
        for statement in statements:
            moves = self.env['account.move']
            for st_line in statement.line_ids:
                if st_line.account_id and not st_line.journal_entry_ids.ids:
                    st_line.fast_counterpart_creation()
                elif not st_line.journal_entry_ids.ids:
                    raise UserError(_('All the account entries lines must be processed in order to close the statement.'))
                moves = (moves | st_line.journal_entry_ids)
            if moves:
                moves.sudo().post()
            statement.message_post(body=_('Statement %s confirmed, journal items were created.') % (statement.name,))
        statements.link_bank_to_partner()
        statements.write({'state': 'confirm', 'date_done': time.strftime("%Y-%m-%d %H:%M:%S")})
    
    @api.multi
    def reconciliation_widget_preprocess(self):
        """ Get statement lines of the specified statements or all unreconciled statement lines and try to automatically reconcile them / find them a partner.
            Return ids of statement lines left to reconcile and other data for the reconciliation widget.
        """
        statements = self
        bsl_obj = self.env['account.bank.statement.line']
        # NB : The field account_id can be used at the statement line creation/import to avoid the reconciliation process on it later on,
        # this is why we filter out statements lines where account_id is set

        sql_query = """SELECT stl.id 
                        FROM account_bank_statement_line stl  
                        WHERE account_id IS NULL AND not exists (select 1 from account_move m where m.statement_line_id = stl.id)
                            AND company_id = %s
                """
        params = (self.env.user.company_id.id,)
        if statements:
            sql_query += ' AND stl.statement_id IN %s'
            params += (tuple(statements.ids),)
        sql_query += ' ORDER BY stl.id'
        self.env.cr.execute(sql_query, params)
        st_lines_left = self.env['account.bank.statement.line'].browse([line.get('id') for line in self.env.cr.dictfetchall()])

        #try to assign partner to bank_statement_line
        stl_to_assign_partner = [stl.id for stl in st_lines_left if not stl.partner_id]
        refs = list(set([st.name for st in st_lines_left if not stl.partner_id]))
        if st_lines_left and stl_to_assign_partner and refs\
           and st_lines_left[0].journal_id.default_credit_account_id\
           and st_lines_left[0].journal_id.default_debit_account_id:

            sql_query = """SELECT aml.partner_id, aml.ref, stl.id
                            FROM account_move_line aml
                                JOIN account_account acc ON acc.id = aml.account_id
                                JOIN account_bank_statement_line stl ON aml.ref = stl.name
                            WHERE (aml.company_id = %s 
                                AND aml.partner_id IS NOT NULL) 
                                AND (aml.statement_id IS NULL AND aml.account_id IN %s) 
                                AND aml.ref IN %s
                                """
            params = (self.env.user.company_id.id, (st_lines_left[0].journal_id.default_credit_account_id.id, st_lines_left[0].journal_id.default_debit_account_id.id), tuple(refs))
            if statements:
                sql_query += 'AND stl.id IN %s'
                params += (tuple(stl_to_assign_partner),)
            self.env.cr.execute(sql_query, params)
            results = self.env.cr.dictfetchall()
            st_line = self.env['account.bank.statement.line']
            for line in results:
                st_line.browse(line.get('id')).write({'partner_id': line.get('partner_id')})

        return {
            'st_lines_ids': st_lines_left.ids,
            'notifications': [],
            'statement_name': len(statements) == 1 and statements[0].name or False,
            'num_already_reconciled_lines': 0,
        }

class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def get_move_lines_for_reconciliation(self, excluded_ids=None, str=False, offset=0, limit=None, additional_domain=None, overlook_partner=False):
        """ Return account.move.line records which can be used for bank statement reconciliation.

            :param excluded_ids:
            :param str:
            :param offset:
            :param limit:
            :param additional_domain:
            :param overlook_partner:
        """
        # Blue lines = payment on bank account not assigned to a statement yet
        reconciliation_aml_accounts = [self.journal_id.default_credit_account_id.id, self.journal_id.default_debit_account_id.id]
        domain_reconciliation = ['&', '&', ('statement_id', '=', False), ('account_id', 'in', reconciliation_aml_accounts), ('payment_id','<>', False)]

        # REMOVE THIS FOR CASH BASE ACCOUNTING
        # # Black lines = unreconciled & (not linked to a payment or open balance created by statement
        # domain_matching = [('reconciled', '=', False)]
        # if self.partner_id.id or overlook_partner:
        #     domain_matching = expression.AND([domain_matching, [('account_id.internal_type', 'in', ['payable', 'receivable'])]])
        # else:
        #     # TODO : find out what use case this permits (match a check payment, registered on a journal whose account type is other instead of liquidity)
        #     domain_matching = expression.AND([domain_matching, [('account_id.reconcile', '=', True)]])

        # Let's add what applies to both
        # domain = expression.OR([domain_reconciliation, domain_matching])
        domain = expression.OR([domain_reconciliation])
        if self.partner_id.id and not overlook_partner:
            domain = expression.AND([domain, [('partner_id', '=', self.partner_id.id)]])

        # Domain factorized for all reconciliation use cases
        ctx = dict(self._context or {})
        ctx['bank_statement_line'] = self
        generic_domain = self.env['account.move.line'].with_context(ctx).domain_move_lines_for_reconciliation(excluded_ids=excluded_ids, str=str)
        domain = expression.AND([domain, generic_domain])

        # Domain from caller
        if additional_domain is None:
            additional_domain = []
        else:
            additional_domain = expression.normalize_domain(additional_domain)
        domain = expression.AND([domain, additional_domain])

        return self.env['account.move.line'].search(domain, offset=offset, limit=limit, order="date_maturity asc, id asc")

    def _get_common_sql_query(self, overlook_partner = False, excluded_ids = None, split = False):
        acc_type = "acc.internal_type IN ('payable', 'receivable')" if (self.partner_id or overlook_partner) else "acc.reconcile = true"
        select_clause = "SELECT aml.id "
        from_clause = "FROM account_move_line aml JOIN account_account acc ON acc.id = aml.account_id "
        account_clause = ''
        if self.journal_id.default_credit_account_id and self.journal_id.default_debit_account_id:
            # account_clause = "(aml.statement_id IS NULL AND aml.account_id IN %(account_payable_receivable)s AND aml.payment_id IS NOT NULL) OR"
            account_clause = "(aml.statement_id IS NULL AND aml.account_id IN %(account_payable_receivable)s AND aml.payment_id IS NOT NULL)"
        # where_clause = """WHERE aml.company_id = %(company_id)s
        #                   AND (
        #                             """ + account_clause + """
        #                             ("""+acc_type+""" AND aml.reconciled = false)
        #                   )"""
        if account_clause:
            where_clause = """WHERE aml.company_id = %(company_id)s
                          AND (
                                    """ + account_clause + """
                          )"""
        else:
            where_clause = """WHERE aml.company_id = %(company_id)s"""
        where_clause = where_clause + ' AND aml.partner_id = %(partner_id)s' if self.partner_id else where_clause
        where_clause = where_clause + ' AND aml.id NOT IN %(excluded_ids)s' if excluded_ids else where_clause
        if split:
            return select_clause, from_clause, where_clause
        return select_clause + from_clause + where_clause