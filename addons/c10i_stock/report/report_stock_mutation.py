# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
from odoo.addons.jasper_reports import JasperDataParser
from odoo.addons.jasper_reports import jasper_report

class jasper_report_stock_mutation(JasperDataParser.JasperDataParser):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_report_stock_mutation, self).__init__(cr, uid, ids, data, context)

    def generate_data_source(self, cr, uid, ids, data, context):
        return 'parameters'

    def generate_parameters(self, cr, uid, ids, data, context):
        return {
                'from_date'     : str(data['form']['from_date']),
                'to_date'       : str(data['form']['to_date']),
                'username'      : str(data['form']['username']),
                'location_id'   : data['form']['location_id'][0],
                'product_id'    : str(data['form']['product_id']),
                'show_value'    : data['cost'],
                'company_id'    : data['form']['company_id'][0],
                }

    def generate_properties(self, cr, uid, ids, data, context):
        return {}

    def generate_output(self,cr, uid, ids, data, context):
        return data['form']['report_type']
    
    def generate_records(self, cr, uid, ids, data, context):
        return {}

jasper_report.ReportJasper('report.report_stock_mutation', 'wizard.report.stock.mutation', parser=jasper_report_stock_mutation,)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
