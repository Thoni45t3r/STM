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
    'name': "Asset Purchase",
    'depends': ['account_asset', 'purchase', 'stock_account', 'c10i_account_asset', 'c10i_base'],
    'description': """
Asset Purchase
==============
Asset Purchase enabled you to create a purchase order of a specific asset products.
    """,
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'category'  : 'Accounting',
    'data': [
        # 'security/ir.model.access.csv',
        'views/product_view.xml',
        'views/account_asset_views.xml',
        'wizard/wizard_asset_addition_view.xml',
    ],
'application': True,
}