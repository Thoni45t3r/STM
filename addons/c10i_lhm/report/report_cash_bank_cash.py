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

class jasper_report_cash_bank_cash(JasperDataParser.JasperDataParser):
	def __init__(self, cr, uid, ids, data, context):
		super(jasper_report_cash_bank_cash, self).__init__(cr, uid, ids, data, context)
	
	def generate_data_source(self, cr, uid, ids, data, context):
		return 'parameters'
	
	def generate_parameters(self, cr, uid, ids, data, context):
		return {
			'from_date': data['form']['from_date'],
			'to_date': data['form']['to_date'],
			'journal_id': data['form']['journal_id'][0],
		}
	
	def generate_properties(self, cr, uid, ids, data, context):
		return {}
	
	def generate_output(self, cr, uid, ids, data, context):
		return data['form']['report_type']
	
	def generate_records(self, cr, uid, ids, data, context):
		return {}


jasper_report.ReportJasper('report.report_cash_bank_cash_c10i', 'wizard.report.cash.bank', parser=jasper_report_cash_bank_cash, )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
