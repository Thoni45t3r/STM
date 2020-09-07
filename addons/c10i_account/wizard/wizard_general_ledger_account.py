# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from openerp import models, fields, api, _
from odoo.addons.jasper_reports import JasperDataParser
from odoo.addons.jasper_reports import jasper_report
import time

class wizard_general_ledger_account(models.TransientModel):
    _name           = "wizard.general.ledger.account"
    _description    = "Report General Ledger By Account"
    
    report_type     = fields.Selection(JasperDataParser.REPORT_TYPE, string="Document Type", default=lambda *a: 'xlsx')
    from_date       = fields.Date(string="From", default=lambda *a: time.strftime('%Y-%m-%d'))
    to_date         = fields.Date(string="To", default=lambda *a: time.strftime('%Y-%m-%d'))
    target_move     = fields.Selection([('posted', 'All Posted Entries'),
                                        ('all', 'All Entries'),
                                        ], string='Target Moves', required=True, default='posted')
    company_id      = fields.Many2one(comodel_name='res.company', string="Company", default=lambda self: self.env.user.company_id)
    account_ids     = fields.Many2many(comodel_name='account.account', string='Accounts')
    
    @api.multi
    def create_report(self):
        data = self.read()[-1]
        name = 'report_general_ledger_account'
        target = "'posted'"
        if data['report_type'] in ['xls', 'xlsx']:
            name = 'report_general_ledger_account_xls'
        if data['target_move'] == "all":
            target = "'posted','draft'"
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : name,
            'datas': {
                    'model'         :'wizard.general.ledger.account',
                    'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or  self.id,
                    'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or[],
                    'report_type'   : data['report_type'],
                    'form'          : data,
                    'target_move'   : target,
                },
            'nodestroy'     : False
            }
wizard_general_ledger_account()