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

class AccountInvoice(models.Model):
    _inherit        = "account.invoice"

    @api.multi
    def print_report_invoice(self):
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : 'report_nota_invoice',
            'datas'         : {
                'model'         : 'account.invoice',
                'id'            : self.id,
                'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or [],
                'name'          : self.number or "Report Nota Invoice",
                },
            'nodestroy'     : False
        }

class AccountTax(models.Model):
    _inherit    = "account.tax"

    report_name = fields.Char("Name Reporting")

class AccountJournal(models.Model):
    _inherit = "account.journal"

    receipt_sequence = fields.Boolean('Dedicated Cash/Bank Receipt Sequence', 
        help="Check this box if you don't want to share the same sequence for "
            "payment and receipt made from this journal", default=False)
    receipt_sequence_id = fields.Many2one('ir.sequence', string='Receipt Entry Sequence',
        help="This field contains the information related to the numbering of the journal"
            " entries of this journal.", required=False, copy=False)

    @api.model
    def _get_sequence_prefix(self, code, refund=False, receipt=False):
        prefix = code.upper()
        if refund:
            prefix = 'R' + prefix
        elif receipt:
            prefix = 'IN' + prefix
        return prefix + '/%(range_year)s/'

    @api.model
    def _create_sequence(self, vals, refund=False, receipt=False):
        """ Create new no_gap entry sequence for every new Journal"""
        prefix = self._get_sequence_prefix(vals['code'], refund, receipt)
        seq = {
            'name': refund and vals['name'] + _(': Refund') or vals['name'],
            'implementation': 'no_gap',
            'prefix': prefix,
            'padding': 4,
            'number_increment': 1,
            'use_date_range': True,
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        return self.env['ir.sequence'].create(seq)

    @api.model
    def create(self, vals):
        if vals.get('type') in ('cash', 'bank') and vals.get('receipt_sequence') and not vals.get('refund_sequence_id'):
            vals.update({'receipt_sequence_id': self.sudo()._create_sequence(vals, receipt=True).id})
        journal = super(AccountJournal, self).create(vals)
        return journal

    @api.multi
    def write(self, vals):
        result = super(AccountJournal, self).write(vals)
        if vals.get('receipt_sequence'):
            for journal in self.filtered(lambda j: j.type in ('cash', 'bank') and not j.receipt_sequence_id):
                journal_vals = {
                    'name': journal.name,
                    'company_id': journal.company_id.id,
                    'code': journal.code
                }
                journal.receipt_sequence_id = self.sudo()._create_sequence(journal_vals, receipt=True).id
        return result
