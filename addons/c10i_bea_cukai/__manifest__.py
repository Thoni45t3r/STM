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
    'name'          : "Bea Cukai of Consult10 Indonesia",
    'version'       : '1.0.1.1',
    'category'      : 'C10i Module',
    'description'   : "Bea Cukai",
    'summary'       : """
                        Bea Cukai Module modified by Consult10 Indonesia to localization use in Indonesia
                        """,
    'author'        : "Deby Wahyu Kurdian @Konsaltén Indonesia (Consult10 Indonesia)",
    'website'       : "www.consult10indonesia.com",
    'license'       : 'AGPL-3',
    'depends'       : ['base', 'c10i_base', 'stock', 'c10i_stock', 'stock_account', 'sale', 'c10i_purchase', 'c10i_account_faktur_pajak'],
    'data'          : [
                        'security/bea_cukai_security.xml',
                        'security/ir.model.access.csv',
                        'data/product_type.xml',
                        'data/user_data.xml',
                        'views/bea_cukai_views.xml',
                        'views/sale_views.xml',
                        'views/stock_views.xml',
                        'views/purchase_views.xml',
                        'views/other_stock_views.xml',
                        'views/stock_location_views.xml',
                        'views/product_category_views.xml',
                        'wizard/wizard_stock_mutation_views.xml',
                        'wizard/wizard_report_stock_cukai_views.xml',
    ],
    'qweb'          : [
    ],
    'installable'   : True,
    'application'   : True,
}