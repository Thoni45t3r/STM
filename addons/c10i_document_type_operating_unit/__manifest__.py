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
    'name'          : "Document Type Operating Unit of Consult10 Indonesia",
    'version'       : '1.0.1.1',
    'category'      : 'C10i Module',
    'summary'       : "Document Type Operating Unit",
    'author'        : "Deby Wahyu Kurdian @Konsaltén Indonesia (Consult10 Indonesia)",
    'website'       : "www.consult10indonesia.com",
    'license'       : 'AGPL-3',
    'depends'       : ['base', 'c10i_base', 'stock', 'c10i_stock', 'stock_account', 'c10i_stock_account',
                       'sale', 'c10i_sale', 'purchase', 'c10i_purchase', 'c10i_purchase_request', 'c10i_document_type',
                       'purchase_request_operating_unit', 'purchase_operating_unit'],
    'data'          : [
    ],
    'qweb'          : [
    ],
    'installable'   : True,
    'application'   : True,
    'description'   : """For Operating Unit""",
}