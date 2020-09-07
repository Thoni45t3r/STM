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

class wizard_pending_purchase_request(models.TransientModel):
    _name           = "wizard.pending.purchase.request"
    _description    = "Pending Purchase Request"
    
    report_type     = fields.Selection(JasperDataParser.REPORT_TYPE, string="Document Type", default=lambda *a: 'pdf')
    to_date         = fields.Date("Per Tanggal", default=lambda *a: time.strftime('%Y-%m-%d'))
    company_id      = fields.Many2one('res.company', "Company", default=lambda self: self.env.user.company_id)
    
    @api.multi
    def create_report(self):
        data = self.read()[-1]
        name = 'report_pending_purchase_request'
        if data['report_type'] in ['xls', 'xlsx']:
            name = 'report_pending_purchase_request_xls'
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : name,
            'datas': {
                    'model'         :'wizard.pending.purchase.request',
                    'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or  self.id,
                    'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or[],
                    'report_type'   : data['report_type'],
                    'form'          : data
                },
            'nodestroy'     : False
            }
wizard_pending_purchase_request()