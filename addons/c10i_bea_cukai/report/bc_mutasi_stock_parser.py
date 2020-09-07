# -*- encoding: utf-8 -*-
##############################################################################
#                                                                            #
#   --- Deby Wahyu Kurdian ---                                               #
#                                                                            #
##############################################################################

from odoo.addons.jasper_reports import JasperDataParser
from odoo.addons.jasper_reports import jasper_report
import odoo.tools


class jasper_beacukai_laporan_mutasi(JasperDataParser.JasperDataParser):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_beacukai_laporan_mutasi, self).__init__(cr, uid, ids, data, context)

    def generate_data_source(self, cr, uid, ids, data, context):
        return 'parameters'

    def generate_parameters(self, cr, uid, ids, data, context):
        return {
                'date_start'    : str(data['date_start']),
                'date_stop'     : str(data['date_stop']),
                'company_id'    : int(data['company_id']),
                'company_name'  : str(data['company_name']),
                'wizard_id'     : int(data['wizard_id']),
                'product_type'  : str(data['product_type']),
                # 'suffix_report' : " " + str(data['name'])
        }

    def generate_properties(self, cr, uid, ids, data, context):
        return {}

    def generate_output(self,cr, uid, ids, data, context):
        return data['report_type']

    def generate_records(self, cr, uid, ids, data, context):
        return {}

jasper_report.ReportJasper('report.beacukai_laporan_mutasi', 'beacukai.stock.mutation', parser=jasper_beacukai_laporan_mutasi,)
jasper_report.ReportJasper('report.beacukai_laporan_mutasi_xls', 'beacukai.stock.mutation', parser=jasper_beacukai_laporan_mutasi,)

class jasper_beacukai_laporan_wip(JasperDataParser.JasperDataParser):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_beacukai_laporan_wip, self).__init__(cr, uid, ids, data, context)

    def generate_data_source(self, cr, uid, ids, data, context):
        return 'parameters'

    def generate_parameters(self, cr, uid, ids, data, context):
        return {
                'date_start'    : str(data['date_start']),
                'date_stop'     : str(data['date_stop']),
                'company_id'    : int(data['company_id']),
                'company_name'  : str(data['company_name']),
                'wizard_id'     : int(data['wizard_id']),
                # 'suffix_report' : " " + str(data['name'])
        }

    def generate_properties(self, cr, uid, ids, data, context):
        return {}

    def generate_output(self,cr, uid, ids, data, context):
        return data['report_type']

    def generate_records(self, cr, uid, ids, data, context):
        return {}

jasper_report.ReportJasper('report.beacukai_laporan_wip', 'beacukai.stock.wip', parser=jasper_beacukai_laporan_wip,)
jasper_report.ReportJasper('report.beacukai_laporan_wip_xls', 'beacukai.stock.wip', parser=jasper_beacukai_laporan_wip,)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: