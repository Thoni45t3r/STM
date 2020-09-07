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
    'name': 'Stock Manual Periodic Valuation',
    'depends': ['c10i_base', 'c10i_account', 'c10i_account_location', 'c10i_stock_account'],
    'description': """
        Stock Manual Periodic Valuation
    """,
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'category'  : 'Manufacture',
    'sequence'  : 32,
    'license'   : 'AGPL-3',
    'data': [
        'data/ir_sequence.xml',
        'security/stock_security.xml',
        'security/ir.model.access.csv',
        # 'wizard/wizard_sales_view.xml',
        'views/product_views.xml',
        'views/product_valuation_views.xml',
    ],
    'installable': True,
    'application': False,
}
