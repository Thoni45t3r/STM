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

class WizardInvoiceAdvanceBalance(models.TransientModel):
    _name = 'wizard.invoice.advance.balance'
    _description = 'Unadjusted Advance'

    advance_type = fields.Selection([('out_advance', 'Customer Invoice Advance'), ('in_advance', 'Vendor Bill Advance')], string='Advance Type', required=True)
    as_of_date = fields.Date('As of Date', required=True, default=lambda self:time.strftime('%Y-%m-%d'))
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id.id, required=True)

    @api.multi
    def print_report(self):
        self.ensure_one()
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : 'invoice_advance_balance',
            'datas'         : {
                'model'         : 'wizard.invoice.advance.balance',
                'id'            : self.id,
                'ids'           : [self.id],
                'report_type'   : 'xlsx',
                'form'          : {
                        'advance_type': self.advance_type,
                        'as_of_date': self.as_of_date,
                        'company_id': self.company_id.id,
                        'company_name': self.company_id.name,
                    },
                },
            'nodestroy': False
        }