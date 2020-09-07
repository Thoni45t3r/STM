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

class jasper_purchase_received_register(JasperDataParser.JasperDataParser):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_purchase_received_register, self).__init__(cr, uid, ids, data, context)

    def generate_data_source(self, cr, uid, ids, data, context):
        return 'parameters'

    def generate_parameters(self, cr, uid, ids, data, context):
        params = {
                'company_name': data['form']['company_id'][1],
                'currency_name': data['form']['currency_name'],
                'date_start' : str(data['form']['date_start']),
                'date_stop' : str(data['form']['date_stop']),
                }
        return params

    def generate_properties(self, cr, uid, ids, data, context):
        return {}

    def generate_output(self,cr, uid, ids, data, context):
        return data['form']['report_type']
    
    def generate_records(self, cr, uid, ids, data, context):
        return {}

jasper_report.ReportJasper('report.report_purchase_received_register', 'wizard.purchase.received.register', parser=jasper_purchase_received_register,)
jasper_report.ReportJasper('report.report_purchase_received_register_xls', 'wizard.purchase.received.register', parser=jasper_purchase_received_register,)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
