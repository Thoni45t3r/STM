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

class WizardEmployeeAdvanceBalance(models.TransientModel):
    _name = 'wizard.employee.advance.balance'
    _description = 'Unsettled Employee Advance'

    as_of_date = fields.Date('As of Date', required=True, default=lambda self:time.strftime('%Y-%m-%d'))
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id.id, required=True)

    @api.multi
    def print_report(self):
        self.ensure_one()
        return {
            'type'          : 'ir.actions.report.xml',
            'report_name'   : 'employee_advance_balance',
            'datas'         : {
                'model'         : 'wizard.employee.advance.balance',
                'id'            : self.id,
                'ids'           : [self.id],
                'report_type'   : 'xlsx',
                'form'          : {
                        'as_of_date': self.as_of_date,
                        'company_id': self.company_id.id,
                        'company_name': self.company_id.name,
                    },
                },
            'nodestroy': False
        }