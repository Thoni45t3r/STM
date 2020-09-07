# -*- encoding: utf-8 -*-
##############################################################################
#                                                                            #
#   --- Deby Wahyu Kurdian ---                                               #
#                                                                            #
##############################################################################

from odoo.addons.jasper_reports import JasperDataParser
from odoo.addons.jasper_reports import jasper_report
import odoo.tools


class jasper_report_stock_cukai(JasperDataParser.JasperDataParser):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_report_stock_cukai, self).__init__(cr, uid, ids, data, context)

    def generate_data_source(self, cr, uid, ids, data, context):
        return 'parameters'

    def generate_parameters(self, cr, uid, ids, data, context):
        return {
                'id'            : int(data['id']),
                # 'suffix_report' : " " + str(data['name'])
        }

    def generate_properties(self, cr, uid, ids, data, context):
        return {}

    def generate_output(self,cr, uid, ids, data, context):
        return data['report_type']

    def generate_records(self, cr, uid, ids, data, context):
        return {}

jasper_report.ReportJasper('report.report_stock_cukai', 'wizard.report.stock.cukai', parser=jasper_report_stock_cukai,)
jasper_report.ReportJasper('report.report_stock_cukai_xls', 'wizard.report.stock.cukai', parser=jasper_report_stock_cukai,)
jasper_report.ReportJasper('report.report_stock_cukai_production', 'wizard.report.stock.cukai.production', parser=jasper_report_stock_cukai,)
jasper_report.ReportJasper('report.report_stock_cukai_production_xls', 'wizard.report.stock.cukai.production', parser=jasper_report_stock_cukai,)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: