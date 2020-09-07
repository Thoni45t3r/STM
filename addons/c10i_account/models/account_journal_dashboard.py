# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

import json
from datetime import datetime, timedelta

from babel.dates import format_datetime, format_date

from odoo import models, api, _, fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools.misc import formatLang

class account_journal(models.Model):
    _inherit = "account.journal"

    @api.multi
    def get_journal_dashboard_datas(self):
        res = super(account_journal, self).get_journal_dashboard_datas()
        currency = self.currency_id or self.company_id.currency_id
        last_balance = 0.0
        if self.type in ['bank', 'cash']:
            # last_bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids)], order="date desc, id desc", limit=1)
            # last_balance = last_bank_stmt and last_bank_stmt[0].balance_end or 0
            self.env.cr.execute("""SELECT abs.id
                        FROM account_bank_statement abs 
                            INNER JOIN account_bank_statement_line absl ON absl.statement_id=abs.id
                            INNER JOIN account_move am ON am.statement_line_id=absl.id
                        WHERE abs.journal_id IN %s and abs.state='open'
                        GROUP BY abs.id
                        ORDER BY abs.date desc
                        LIMIT 1""", (tuple(self.ids),))
            statement_id = self.env.cr.fetchone()
            if statement_id:
                last_bank_stmt = self.env['account.bank.statement'].browse(statement_id[0])
                last_balance = last_bank_stmt.balance_start
                for line in last_bank_stmt.line_ids:
                    if not line.journal_entry_ids:
                        continue
                    last_balance += line.amount
        res.update({
            'last_balance': formatLang(self.env, currency.round(last_balance) + 0.0, currency_obj=currency),
        })
        return res 
