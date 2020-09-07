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
import odoo
from odoo import report
from odoo.addons.c10i_account.report.report_general_ledger_account import jasper_report_general_ledger_account

class jasper_report_general_ledger_account_ou(jasper_report_general_ledger_account):
    def __init__(self, cr, uid, ids, data, context):
        super(jasper_report_general_ledger_account_ou, self).__init__(cr, uid, ids, data, context)

    def generate_data_source(self, cr, uid, ids, data, context):
        return 'parameters'

    def generate_parameters(self, cr, uid, ids, data, context):
        return {
                'from_date'     : data['form']['from_date'],
                'to_date'       : data['form']['to_date'],
                'account_ids'   : str(data['form']['account_ids']),
                'target_move'   : str(data['target_move']),
                'operating_unit_ids': str(data['form']['operating_unit_ids']),
                }

    def generate_properties(self, cr, uid, ids, data, context):
        return {}

    def generate_output(self,cr, uid, ids, data, context):
        return data['form']['report_type']
    
    def generate_records(self, cr, uid, ids, data, context):
        return {}
del odoo.report.interface.report_int._reports['report.report_general_ledger_account']
del odoo.report.interface.report_int._reports['report.report_general_ledger_account_xls']

jasper_report.ReportJasper('report.report_general_ledger_account', 'wizard.general.ledger.account', parser=jasper_report_general_ledger_account_ou,)
jasper_report.ReportJasper('report.report_general_ledger_account_xls', 'wizard.general.ledger.account', parser=jasper_report_general_ledger_account_ou,)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: