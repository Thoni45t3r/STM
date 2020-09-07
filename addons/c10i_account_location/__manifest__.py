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
    'name': 'Account Location',
    'depends': ['c10i_base', 'account', 'c10i_account', 'c10i_employee_advance', 'account_cost_center', 'account_voucher'],
    'description': """
        Account Location Type
        Account Location
    """,
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'category'  : 'Accounting',
    'sequence'  : 32,
    'license'   : 'AGPL-3',
    'data': [
        # 'data/ir_sequence.xml',
        'security/location_security.xml',
        'security/ir.model.access.csv',
        'views/account_location_views.xml',
        'views/account_cost_center_views.xml',
        'views/account_move_views.xml',
        'views/account_invoice_views.xml',
        'views/account_voucher_views.xml',
        'views/settlement_advance_views.xml',
    ],
    'installable': True,
    'application': True,
}
