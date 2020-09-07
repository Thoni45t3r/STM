# -*- encoding: utf-8 -*-
##############################################################################
#                                                                            #
#   --- Deby Wahyu Kurdian ---                                               #
#                                                                            #
##############################################################################

from odoo.addons.jasper_reports import JasperDataParser
from odoo.addons.jasper_reports import jasper_report
import odoo.tools


class jasper_cash_bank_book(JasperDataParser.JasperDataParser):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_cash_bank_book, self).__init__(cr, uid, ids, data, context)

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

jasper_report.ReportJasper('report.cash_bank_book_gl', 'wizard.cash.bank.book', parser=jasper_cash_bank_book,)
# jasper_report.ReportJasper('report.cash_bank_book_statement', 'wizard.cash.bank.book', parser=jasper_cash_bank_book,)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
