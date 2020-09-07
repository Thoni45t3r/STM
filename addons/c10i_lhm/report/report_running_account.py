# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from odoo.addons.jasper_reports import JasperDataParser
from odoo.addons.jasper_reports import jasper_report
from datetime import datetime, timedelta
from odoo import models, api, fields
import time
import base64
import os
import math

class jasper_running_account_report(JasperDataParser.JasperDataParser):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_running_account_report, self).__init__(cr, uid, ids, data, context)

    def generate_data_source(self, cr, uid, ids, data, context):
        return 'parameters'

    def generate_parameters(self, cr, uid, ids, data, context):
        print ">>>>>>>>>>>>>>>>>>>>>>dalem", data
        return {
            'company_name' : data['form']['company_id'][1],
            'period_name' : data['form']['account_period_id'][1],
            'account_period_id' : data['form']['account_period_id'][0],
        }

    def generate_properties(self, cr, uid, ids, data, context):
        return {}

    def generate_output(self,cr, uid, ids, data, context):
        return data['form']['report_type']
    
    @api.model
    def generate_records(self, cr, uid, ids, data, context):
        # running_lines = self.env['running.account.line'].search([('running_account_id.account_period_id','=',data['form']['account_period_id'][0])])
        res = {}
        # utilities = list(set([x.utility_id for x in running_line]))
        # for util in sorted(utilities, lambda x: (x.location_type_id.code=='WS' and 1 or (x.location_type_id.code=='VH' and 2 or (x.location_type_id.code=='MA' and 3 or 4)))):
        #     util_running_lines = running_lines.filtered(lambda x: x.utility_id.id==util.id)
        #     for activity in list(set([x.activity_id for x in util_running_lines])):
        #         lines = util_running_lines.filtered(lambda x: x.activity_id.id==activity.id)
        #         data = {
        #             'location': util.location_type_id.code,
        #             'code': util.code,
        #             'activity_code': activity.code,
        #             'activity': activity.name,
        #             'amount': sum(lines.map('total'))
        #         }
        #         res.append(data)
        #         print ">>>>>>>>>>>>>>>>", data
        return res

jasper_report.ReportJasper('report.running_account_report', 'wizard.running.account.report', parser=jasper_running_account_report,)
jasper_report.ReportJasper('report.running_account_report_xls', 'wizard.running.account.report', parser=jasper_running_account_report,)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: