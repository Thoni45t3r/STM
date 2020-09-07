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
    'name': 'Assets Management Custom',
    'depends': ['account_asset', 'c10i_base'],
    'description': """
Assets management customer
==========================
Solve a problem of Opening Value of Asset when implementing a new Odoo System
- unknown yet
Add a new feature of Asset Capitalization
- unknown yet
Add a new feature of Asset Disposal
- when you choose to Sell an Asset, it will create a Customer Invoice
    """,
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'category'  : 'Accounting',
    'sequence'  : 32,
    'license'   : 'AGPL-3',
    'data': [
        'wizard/asset_disposal_views.xml',
        'wizard/asset_confirm_views.xml',
        'views/account_asset_views.xml',
        'data/account_asset_data.xml',
        'wizard/wizard_report_asset_views.xml',
    ],
    'installable': True,
    'application': True,
}
