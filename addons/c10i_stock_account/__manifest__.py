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
    'name'      : 'WMS Accounting of Consult10 Indonesia',
    'version'   : '1.0.1.1',
    'category'  : 'Warehouse',
    'description': """
WMS Accounting module
======================
This module makes the link between the 'stock' and 'account' modules.

Key Features
------------
* Connection between Stock Move and Journal.

    """,
    'summary'   : """
                    Inventory Management Module modified by Consult10 Indonesia to localization use in Indonesia
                    """,
    'author'    : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "www.consult10indonesia.com",
    'license'   : 'AGPL-3',
    'depends'   : ['base', 'stock', 'account', 'c10i_base', 'c10i_account', 'c10i_stock'],
    'data': [
                'security/ir.model.access.csv',
                'views/account_move_line_view.xml',
                'views/stock_move_view.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
}
