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
    'name': 'Palm Oil Mills',
    'depends': ['base', 'c10i_base', 'mrp', 'c10i_stock_manual_valuation'],
    'description': """
        Palm Oil Mills
    """,
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'category'  : 'Manufacture',
    'sequence'  : 32,
    'license'   : 'AGPL-3',
    'data': [
        'data/ir_sequence.xml',
        'data/data_mills.xml',
        'security/mill_security.xml',
        'security/ir.model.access.csv',
        'views/menuitems.xml',
        'views/account_location_views.xml',
        'views/mrp_workcenter_views.xml',
        'views/mill_order_views.xml',
        'views/mill_valuation_views.xml',
        'views/mill_project_views.xml',
    ],
    'installable': True,
    'application': True,
}
