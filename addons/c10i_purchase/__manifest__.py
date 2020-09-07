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
    'name'          : 'Purchase',
    'depends'       : ['base', 'c10i_base', 'purchase', 'c10i_stock_account', 'c10i_account'],
    'version'       : '1.0.1.1',
    'category'      : 'C10i Module',
    'summary'       : """
                        Purchase Module modified by Consult10 Indonesia to localization use in Indonesia
                        """,
    'description'   : """
Purchase
========

Module Customization for Purchasing in Indonesian.

Preference:
-----------

* Add new feature of Delivery Address and Invoice Address in Purchase Order
* Customize Purchase Reporting 
                            """,
    'author'        : "Konsaltén Indonesia (Consult10 Indonesia)",
    'website'       : "www.consult10indonesia.com",
    'license'       : 'AGPL-3',
    'data'          : [
                        'security/ir.model.access.csv',
                        'views/purchase_views.xml',
                        'views/res_company_views.xml',
                        'wizard/wizard_pending_purchase_order_views.xml',
                        'wizard/wizard_purchase_received_register_views.xml',
                        'report/report_views.xml',
                    ],
    'installable'   : True,
    'application'   : True,
}
