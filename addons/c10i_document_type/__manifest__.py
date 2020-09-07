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
    'name'          : "Document Type of Consult10 Indonesia",
    'version'       : '1.0.1.1',
    'category'      : 'C10i Module',
    'summary'       : "Document Type",
    'author'        : "Deby Wahyu Kurdian @Konsaltén Indonesia (Consult10 Indonesia)",
    'website'       : "www.consult10indonesia.com",
    'license'       : 'AGPL-3',
    'depends'       : ['base', 'c10i_base', 'stock', 'c10i_stock', 'stock_account', 'c10i_stock_account',
                       'sale', 'c10i_sale', 'purchase', 'c10i_purchase', 'c10i_purchase_request',
                       'c10i_account_invoice_advance', 'account', 'c10i_account', 'sales_team'],
    'data'          : [
        'security/ir.model.access.csv',
        'security/document_type_security.xml',
        'wizard/wizard_purchase_request_to_purchase_view.xml',
        'wizard/wizard_rfq_to_purchase_view.xml',
        'views/res_document_type_views.xml',
        'views/purchase_views.xml',
        'views/sale_views.xml',
        'views/purchase_request_views.xml',
        'views/purchase_rfq_views.xml',
    ],
    'qweb'          : [
    ],
    'installable'   : True,
    'application'   : True,
    'description'   : """
Document Type Module modified by Consult10 Indonesia to localization use in Indonesia
=====================================================================================

This application is used to set the default and custom settings for other modules.

All Setting:

* **C10i** -> **Document Type**
* **Sales** -> **Configuration** ->**Document Type**
* **Purchases** -> **Configuration** ->**Document Type**

Preferences:
------------------------------------------------------

* Create Down Payment in Purchase and Sales
* Has default setting for Invoicing, Shipping, Sales, Purchase
* Sale and Purchase can choose **Document Type**
* Purchase Request can choose **Document Type**
* Purchase RFQ can choose **Document Type**
""",
}