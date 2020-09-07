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
    'name'          : "Sales Module of Consult10 Indonesia",
    'version'       : '1.0.1.1',
    'category'      : 'C10i Module',
    'description'   : "Sale Order",
    'summary'       : """
                        Sales Module modified by Consult10 Indonesia to localization use in Indonesia
                        """,
    'author'        : "Deby Wahyu Kurdian @Konsaltén Indonesia (Consult10 Indonesia)",
    'website'       : "www.consult10indonesia.com",
    'license'       : 'AGPL-3',
    'depends'       : ['base', 'c10i_base', 'sale', 'account', 'c10i_account', 'sale_stock'],
    'data'          : [
                        'views/sale_views.xml',
    ],
    'qweb'          : [
    ],
    'installable'   : True,
    'application'   : True,
}