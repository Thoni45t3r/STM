# -*- encoding: utf-8 -*-
##############################################################################
#                                                                            #
#   --- Deby Wahyu Kurdian ---                                               #
#                                                                            #
##############################################################################
import time
import calendar
from odoo.addons.jasper_reports import JasperDataParser
from odoo.addons.jasper_reports import jasper_report

class jasper_report_progres_kerja_harian_material_detail_xls(JasperDataParser.JasperDataParser):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_report_progres_kerja_harian_material_detail_xls, self).__init__(cr, uid, ids, data, context)

    def generate_data_source(self, cr, uid, ids, data, context):
        return 'parameters'

    def generate_parameters(self, cr, uid, ids, data, context):
        return {
                'date_start'    : str(data['form']['date_start']),
                'date_end'      : str(data['form']['date_end']),
                'group_ids'     : str(data['form']['group_ids']),
                'listing'       : str(data['listing']),
                'username'      : str(data['user_print']),
                'company_id'    : int(data['form']['company_id'][0]),
                'suffix_report' : str(" - " + str(data['form']['date_end']))
        }

    def generate_properties(self, cr, uid, ids, data, context):
        return {}

    def generate_output(self,cr, uid, ids, data, context):
        return str(data['report_type'])
    
    def generate_records(self, cr, uid, ids, data, context):
        return {}

jasper_report.ReportJasper('report.report_progres_kerja_harian_material_detail', 'wizard.report.progres.kerja.material.detail', parser=jasper_report_progres_kerja_harian_material_detail_xls,)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
