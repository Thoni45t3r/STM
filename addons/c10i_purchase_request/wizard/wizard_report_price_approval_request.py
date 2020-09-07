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

class wizard_report_price_approval_request(models.TransientModel):
    _name           = "wizard.report.price.approval.request"
    _description    = "Report Price Approval Request"
    
    report_type             = fields.Selection(JasperDataParser.REPORT_TYPE, string="Document Type", default=lambda *a: 'xlsx')
    company_id              = fields.Many2one(comodel_name='res.company', string="Company", default=lambda self: self.env['res.company']._company_default_get('account.account'))
    purchase_request_ids    = fields.Many2many(comodel_name='purchase.request', string='Purchase Request')
    
    @api.multi
    def create_report(self):
        data = self.read()[-1]
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : 'report_price_approval_request',
            'datas': {
                    'model'         :'wizard.report.price.approval.request',
                    'id'            : self._context.get('active_ids') and self._context.get('active_ids')[0] or  self.id,
                    'ids'           : self._context.get('active_ids') and self._context.get('active_ids') or[],
                    'report_type'   : data['report_type'],
                    'company_name'  : str(self.company_id.name),
                    'form'          : data
                },
            'nodestroy'     : False
            }
wizard_report_price_approval_request()