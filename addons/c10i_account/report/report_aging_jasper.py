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

class jasper_report_aging(JasperDataParser.JasperDataParser):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_report_aging, self).__init__(cr, uid, ids, data, context)

    def generate_data_source(self, cr, uid, ids, data, context):
        return 'parameters'

    def generate_parameters(self, cr, uid, ids, data, context):
        return {
                'from_date'     : data['form']['from_date'],
                'usia'          : data['form']['usia'],
                'Partner_type'  : data['form']['Partner_type'],
                'company_id'    : data['form']['company'][0],
                'invoice'       : data['form']['invoice'],
                'journal'       : str(data['form']['journal']),
                'partner'       : str(data['form']['partner']),
                }

    def generate_properties(self, cr, uid, ids, data, context):
        return {}

    def generate_output(self,cr, uid, ids, data, context):
        return data['form']['report_type']
    
    def generate_records(self, cr, uid, ids, data, context):
        return {}

jasper_report.ReportJasper('report.report_aging', 'report.aging', parser=jasper_report_aging,)
jasper_report.ReportJasper('report.report_aging_xls', 'report.aging', parser=jasper_report_aging,)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
