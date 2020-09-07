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
    'name': 'Invoice Advance with Operating Unit',
    'depends': ['account_operating_unit', 'c10i_account_invoice_advance'],
    'description': """
===========================
 Invoice Advance
===========================
""",
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'category'  : 'Accounting',
    'sequence'  : 32,
    'license'   : 'AGPL-3',
    'data': [
        'security/advance_security.xml',
        'views/account_invoice_advance_views.xml',
    ],
    'installable': True,
    'application': True,
}
