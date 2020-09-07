# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo import api, fields, models, _
from datetime import datetime
import time

class WizardCashBankBook(models.TransientModel):
    _name = 'wizard.cash.bank.book'
    _description = 'Cash/Bank Book'

    date_start = fields.Date('Date From', required=True, default=lambda self:time.strftime('%Y-%m-%d'))
    date_stop = fields.Date('Date To', required=True, default=lambda self:time.strftime('%Y-%m-%d'))
    journal_id = fields.Many2one('account.journal', string='Journal', domain=[('type','in',['cash','bank'])], required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id.id, required=True)

    @api.multi
    def print_report(self):
        self.ensure_one()
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : 'cash_bank_book_gl',
            'datas'         : {
                'model'         : 'wizard.cash.bank.book',
                'id'            : self.id,
                'ids'           : [self.id],
                'report_type'   : 'xlsx',
                'form'          : {
                        'date_start': self.date_start,
                        'date_stop': self.date_stop,
                        'journal_id': self.journal_id.id,
                        'journal_name': self.journal_id.name,
                        'company_id': self.company_id.id,
                        'company_name': self.company_id.name,
                    },
                },
            'nodestroy': False
        }