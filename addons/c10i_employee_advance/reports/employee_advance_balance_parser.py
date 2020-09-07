# -*- encoding: utf-8 -*-
##############################################################################
#                                                                            #
#   --- Hendra Saputra ---                                                   #
#                                                                            #
##############################################################################

from odoo.addons.jasper_reports import JasperDataParser
from odoo.addons.jasper_reports import jasper_report
import odoo.tools


class jasper_employee_advance_balance(JasperDataParser.JasperDataParser):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_employee_advance_balance, self).__init__(cr, uid, ids, data, context)

    def generate_data_source(self, cr, uid, ids, data, context):
        return 'parameters'

    def generate_parameters(self, cr, uid, ids, data, context):
        return data['form']

    def generate_properties(self, cr, uid, ids, data, context):
        return {}

    def generate_output(self,cr, uid, ids, data, context):
        return data['report_type']

    def generate_records(self, cr, uid, ids, data, context):
        return {}

jasper_report.ReportJasper('report.employee_advance_balance', 'wizard.employee.advance.balance', parser=jasper_employee_advance_balance,)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
