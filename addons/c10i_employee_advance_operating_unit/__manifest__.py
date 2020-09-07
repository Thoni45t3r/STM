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
    'name': 'Employee Advance & Settelement with Operating Unit',
    'depends': ['c10i_employee_advance', 'account_operating_unit', 'account_voucher_operating_unit'],
    'description': """
        Pemberlakuan filter Operating Unit per Transaksi
    """,
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'category'  : 'Accounting',
    'sequence'  : 32,
    'license'   : 'AGPL-3',
    'data': [
        'views/employee_advance_views.xml',
        'views/settlement_advance_views.xml',
        'security/employee_advance_security.xml'
    ],
    'installable': True,
    'application': True,
}
