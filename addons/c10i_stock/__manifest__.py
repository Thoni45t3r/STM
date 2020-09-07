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
    'name'      : 'Inventory Management Module of Consult10 Indonesia',
    'version'   : '1.0.1.1',
    'category'  : 'Inventory Management',
    'description': "-",
    'summary'   : """
                    Inventory Management Module modified by Consult10 Indonesia to localization use in Indonesia
                    """,
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'license'   : 'AGPL-3',
    'depends'   : ['base', 'c10i_base', 'stock'],
    'data': [
        'wizard/wizard_report_stock_card_views.xml',
        'wizard/wizard_report_stock_mutation_views.xml',
        'views/stock_picking_view.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
}
