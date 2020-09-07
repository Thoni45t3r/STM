# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from odoo import api, fields, models
from odoo.addons.jasper_reports import JasperDataParser
from datetime import datetime
from dateutil.relativedelta import relativedelta

class AccountingReport(models.TransientModel):
    _inherit = "accounting.report"
    
    report_type     = fields.Selection(JasperDataParser.REPORT_TYPE, string="Document Type", default=lambda *a: 'xlsx')

    def _print_report(self, data):
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move'])[0]
        used_context = {}
        used_context['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        used_context['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        used_context['date_from'] = data['form']['date_from'] or False
        used_context['date_to'] = data['form']['date_to'] or False
        used_context['strict_range'] = True if used_context['date_from'] else False
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')
        data['form'].update(self.read(['date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp', 'account_report_id', 'enable_filter', 'label_filter', 'target_move', 'report_type', 'company_id'])[0])
        if data['form'].get('enable_filter'):
            report_name = 'accounting_report_jasper_comp'
        elif data['form'].get('date_from'):
            report_name = 'accounting_report_jasper_4c'
        else:
            report_name = 'accounting_report_jasper'
        # report_name = 'accounting_report_jasper'
        # if data['report_type'] in ['xls', 'xlsx']:
        #     report_name = report_name + '_xls'
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : report_name,
            'data': {
                    'model'         :'accounting.report',
                    'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or  self.id,
                    'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or[],
                    'report_type'   : data['form']['report_type'],
                    'form'          : data['form']
                },
            'datas': {
                    'model'         :'accounting.report',
                    'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or  self.id,
                    'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or[],
                    'report_type'   : data['form']['report_type'],
                    'form'          : data['form']
                },
            'nodestroy'     : False
            }

class AccountLegalReport(models.TransientModel):
    _name = 'account.legal.report'
    _description = 'Legal Report'

    type = fields.Selection([('balance_sheet', 'Balance Sheet'),('profit_loss', 'Profit and Loss')], required=True, default=lambda self: self._context.get('type','balance_sheet'))
    date_start = fields.Date('Date Start', required=True)
    date_stop = fields.Date('Date Stop', required=True)
    target_move = fields.Selection([('posted','Posted Entries'),('all','All Entries')], 'Target Move', default='posted', required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id.id, required=True)

    @api.multi
    def print_report(self):
        self.ensure_one()
        if self.type=='balance_sheet':
            report_name = 'account_report_balance_sheet'
        else:
            report_name = 'account_report_profit_loss'

        if self.target_move=='posted':
            target_move_query = "am1.state='posted'"
        else:
            target_move_query = "am1.state in ('draft','posted')"
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : report_name,
            'datas'         : {
                'model'         : 'account.legal.report',
                'id'            : self.id,
                'ids'           : [self.id],
                'report_type'   : 'xlsx',
                'form'          : {
                        'target_move': target_move_query,
                        'date_start': self.date_start,
                        'date_stop': self.date_stop,
                        'year_start': (datetime.strptime(self.date_start, '%Y-%m-%d') + relativedelta(month=1, day=1)).strftime('%Y-%m-%d'),
                        'company_id': self.company_id.id,
                        'company_name': self.company_id.name,
                    },
                },
            'nodestroy': False
        }