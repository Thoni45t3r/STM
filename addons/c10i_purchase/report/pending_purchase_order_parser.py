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

class jasper_pending_purchase_order(JasperDataParser.JasperDataParser):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_pending_purchase_order, self).__init__(cr, uid, ids, data, context)

    def generate_data_source(self, cr, uid, ids, data, context):
        return 'parameters'

    def generate_parameters(self, cr, uid, ids, data, context):
        params = {
                'company_name': data['form']['company_id'][1],
                'to_date' : str(data['form']['to_date']),
                }
        return params

    def generate_properties(self, cr, uid, ids, data, context):
        return {}

    def generate_output(self,cr, uid, ids, data, context):
        return data['form']['report_type']
    
    def generate_records(self, cr, uid, ids, data, context):
        return {}

jasper_report.ReportJasper('report.report_pending_purchase_order', 'wizard.pending.purchase.order', parser=jasper_pending_purchase_order,)
jasper_report.ReportJasper('report.report_pending_purchase_order_xls', 'wizard.pending.purchase.order', parser=jasper_pending_purchase_order,)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
