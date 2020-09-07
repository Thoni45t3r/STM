# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   @modified Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

from odoo.addons.jasper_reports import JasperDataParser
from odoo.addons.jasper_reports import jasper_report

class jasper_voucher_payment_employee_advance(JasperDataParser.JasperDataParser):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_voucher_payment_employee_advance, self).__init__(cr, uid, ids, data, context)
    
    def generate_data_source(self, cr, uid, ids, data, context):
        return 'parameters'
    
    def generate_parameters(self, cr, uid, ids, data, context):
        return {'id': int(data['id'])}
    
    def generate_properties(self, cr, uid, ids, data, context):
        return {}
    
    def generate_output(self, cr, uid, ids, data, context):
        return data['report_type']
    
    def generate_records(self, cr, uid, ids, data, context):
        return {}


jasper_report.ReportJasper('report.voucher_payment_employee_advance', 'account.employee.advance',
                           parser=jasper_voucher_payment_employee_advance, )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: