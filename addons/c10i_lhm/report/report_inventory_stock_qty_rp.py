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


class jasper_report_inventory_stock_qty_rp(JasperDataParser.JasperDataParser):
	def __init__(self, cr, uid, ids, data, context):
		super(jasper_report_inventory_stock_qty_rp, self).__init__(cr, uid, ids, data, context)
	
	def generate_data_source(self, cr, uid, ids, data, context):
		return 'parameters'
	
	def generate_parameters(self, cr, uid, ids, data, context):
		return {
			'from_date': data['form']['from_date'],
			'to_date': data['form']['to_date'],
			'operating_unit_ids': str(data['form']['operating_unit_ids']),
		}
	
	def generate_properties(self, cr, uid, ids, data, context):
		return {}
	
	def generate_output(self, cr, uid, ids, data, context):
		return data['form']['report_type']
	
	def generate_records(self, cr, uid, ids, data, context):
		return {}


jasper_report.ReportJasper('report.report_inventory_stock_qty_rp', 'wizard.report.inventory',
						   parser=jasper_report_inventory_stock_qty_rp, )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
