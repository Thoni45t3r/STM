# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from odoo import models, fields, api, _
from odoo.addons.jasper_reports import JasperDataParser
from odoo.addons.jasper_reports import jasper_report
import time

class wizard_report_asset(models.TransientModel):
    _name           = "wizard.report.asset"
    _description    = "Report Assets"
    
    report_type     = fields.Selection(JasperDataParser.REPORT_TYPE, string="Document Type", default=lambda *a: 'pdf')
    to_date         = fields.Date(string="Per Tanggal", default=lambda *a: time.strftime('%Y-%m-%d'))
    company_id      = fields.Many2one(comodel_name='res.company', string="Company", default=lambda self: self.env.user.company_id)
    
    @api.multi
    def create_report(self):
        data = self.read()[-1]
        name = 'report_asset'
        if data['report_type'] in ['xls', 'xlsx']:
            name = 'report_asset_xls'
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : name,
            'datas': {
                    'model'         :'wizard.report.asset',
                    'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or  self.id,
                    'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or[],
                    'report_type'   : data['report_type'],
                    'form'          : data
                },
            'nodestroy'     : False
            }
wizard_report_asset()