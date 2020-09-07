# -*- encoding: utf-8 -*-
##############################################################################
#                                                                            #
#   --- Deby Wahyu Kurdian ---                                               #
#                                                                            #
##############################################################################

from odoo.addons.jasper_reports import JasperDataParser
from odoo.addons.jasper_reports import jasper_report
import odoo.tools


class jasper_report_invoice(JasperDataParser.JasperDataParser):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_report_invoice, self).__init__(cr, uid, ids, data, context)

    def generate_data_source(self, cr, uid, ids, data, context):
        return 'parameters'

    def generate_parameters(self, cr, uid, ids, data, context):
        rootpath = odoo.tools.config.addons_data_dir
        return {
                'id'        : int(ids[0]) or 1,
                'rootpath': rootpath
                }

    def generate_properties(self, cr, uid, ids, data, context):
        return {}

    def generate_output(self,cr, uid, ids, data, context):
        return data['form']['report_type']
    
    def generate_records(self, cr, uid, ids, data, context):
        return {}

jasper_report.ReportJasper('report.report_invoice_a4', 'wizard.report.invoice', parser=jasper_report_invoice,)
jasper_report.ReportJasper('report.report_invoice_kwitansi_a42', 'wizard.report.invoice', parser=jasper_report_invoice,)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
