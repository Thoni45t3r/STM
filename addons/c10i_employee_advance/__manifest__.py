# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Hendra Saputra <hendrasaputra0501@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################

{
    'name': 'Employee Advance & Settelement',
    'depends': ['c10i_base', 'c10i_hr', 'account', 'account_voucher'],
    'description': """
    Menu ini menyediakan fitur untuk pencatatan
    - Advance Employee: (untuk Perjalanan dinas, Agenda tertentu, dll)
    - Settelemt Advance: (untuk pencatatan Realisasi Advance yg diajukan)
    """,
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'category'  : 'Accounting',
    'sequence'  : 32,
    'license'   : 'AGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'wizard/return_payment_view.xml',
        'wizard/wizard_employee_advance_balance_views.xml',
        'reports/report_views.xml',
        'views/partner_views.xml',
        'views/hr_views.xml',
        'views/employee_advance_views.xml',
        'views/settlement_advance_views.xml',
    ],
    'installable': True,
    'application': True,
}
