# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

{
    'name'      : "Plantation - Laporan Harian Mandor",
    'category'  : 'Plantation',
    'version'   : '0.1',
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'license'   : 'AGPL-3',
    'depends'   : ['base', 'c10i_base', 'c10i_hr', 'purchase',
                    'account_cost_center', 'account_asset',
                    'account_parent', 'account_period', 'operating_unit',
                    'stock', 'stock_account', 
                    'account','c10i_account', 
                    'c10i_employee_advance', 'c10i_employee_advance_operating_unit'
                   ],
    'summary'   : """
                        Modul Laporan Harian Mandor (LHM) - Odoo 10
                    """,
    'description'   : """
                        Modul Laporan Harian Mandor (LHM) yaitu laporan progress fisik dan biaya untuk penggajian karyawan di lapangan.
                    """,
    'data'      : [
                    'security/plantation_security.xml',
                    'security/ir.model.access.csv',
                    'data/res_doc_type_data.xml',
                    'data/location_type_data.xml',
                    'data/product_data.xml',
                    'data/ir_sequence_data.xml',
                    'data/ir_cron_data.xml',
                    'data/user_data.xml',
                    'data/operating_unit_data.xml',
                    'data/stock_data.xml',
                    'data/running_sequence_data.xml',
                    'data/allowance_type_data.xml',
                    'wizard/wizard_move_employee_views.xml',
                    'views/hr_views.xml',
                    'wizard/wizard_add_employee_views.xml',
                    'wizard/wizard_salary_bill_views.xml',
                    'views/res_views.xml',
                    'views/account_cost_center_views.xml',
                    'views/lhm_views.xml',
                    'views/product_views.xml',
                    'views/res_partner_views.xml',
                    'views/stock_views.xml',
                    'views/account_views.xml',
                    'views/plantation_salary_views.xml',
                    'views/report_invoice.xml',
                    'views/account_report.xml',
                    'views/running_account_views.xml',
                    'views/report_costing_views.xml',
                    'views/account_voucher_views.xml',
                    'views/account_payment_views.xml',
                    'wizard/stock_backorder_confirmation_views.xml',
                    'wizard/wizard_nab_generate_invoice_views.xml',
                    'wizard/wizard_report_produksi_views.xml',
                    'wizard/wizard_report_progres_kerja_views.xml',
                    'wizard/wizard_report_export_data_views.xml',
                    'wizard/wizard_report_monitor_views.xml',
                    'wizard/wizard_report_invoice_view.xml',
                    'views/account_invoice_view.xml',
                    'wizard/wizard_report_stock_picking_view.xml',
                    'views/stock_picking_view.xml',
                    'wizard/wizard_report_inventory_view.xml',
                    'wizard/wizard_report_cash_bank_view.xml',
                    'wizard/wizard_contractor_bill_views.xml',
                    'wizard/wizard_plasma_bill_views.xml',
                    'wizard/wizard_running_account_report_views.xml',
                    'wizard/wizard_create_contractor_book_views.xml',
                    'wizard/lhm_state_views.xml',
    ],
    'demo': [
    ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
}
