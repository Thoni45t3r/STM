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
    'name': 'Transporter Charges',
    # 'depends': ['c10i_base', 'mrp', 'c10i_account', 'c10i_account_location', 'c10i_stock_manual_valuation'],
    'depends': ['c10i_base', 'c10i_account', 'c10i_stock'],
    'description': """
        Transporter Charges
    """,
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'category'  : 'Manufacture',
    'sequence'  : 32,
    'license'   : 'AGPL-3',
    'data': [
        # 'data/ir_sequence.xml',
        # 'security/transport_security.xml',
        # 'security/ir.model.access.csv',
        # 'views/menuitems.xml',
        'views/stock_views.xml',
        'views/transport_cost_views.xml',
        'views/stock_incoterm_views.xml',
    ],
    'installable': True,
    'application': True,
}
