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

class wizard_trial_balance_10c(models.TransientModel):
    _name           = "wizard.trial.balance.10c"
    _description    = "Report General Ledger By Account"
    
    report_type         = fields.Selection(JasperDataParser.REPORT_TYPE, string="Document Type", default=lambda *a: 'xlsx')
    from_date           = fields.Date(string="From", default=lambda *a: time.strftime('%Y-%m-%d'))
    to_date             = fields.Date(string="To", default=lambda *a: time.strftime('%Y-%m-%d'))
    company_id          = fields.Many2one(comodel_name='res.company', string="Company", default=lambda self: self.env['res.company']._company_default_get('account.account'))
    target_move = fields.Selection([('posted','Posted Entries'),('all','All Entries')], 'Target Move', default='posted', required=True)

    @api.multi
    def create_report(self):
        data        = self.read()[-1]
        name        = 'report_trial_balance_10c'

        if self.target_move=='posted':
            target_move_query = "am1.state='posted'"
        else:
            target_move_query = "am1.state in ('draft','posted')"
        data.update({'target_move': target_move_query})
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : name,
            'datas': {
                    'model'         :'wizard.trial.balance.10c',
                    'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or  self.id,
                    'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or[],
                    'report_type'   : data['report_type'],
                    'form'          : data
                },
            'nodestroy'     : False
            }
wizard_trial_balance_10c()