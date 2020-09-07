# -*- coding: utf-8 -*-
######################################################################################################
#
#   Odoo, Open Source Management Solution
#   Copyright (C) 2018  Dion Martin @Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   Copyright (C) 2018  Konsaltén Indonesia (Consult10 Indonesia) <www.consult10indonesia.com>
#   @author Dion Martin Hamonangan <kepengen.ganteng@gmail.com>
#   @modified Deby Wahyu Kurdian <deby.wahyu.kurdian@gmail.com>
#   For more details, check COPYRIGHT and LICENSE files
#
######################################################################################################
{
    'name'      : "Purchase Request & Procurement of Consult10 Indonesia",
    'version'   : '1.0.1.1',
    'category'  : 'C10i Module',
    'description' : "Purchase Request",
    'summary'   : """
                    Purchase Module modified by Consult10 Indonesia to localization use in Indonesia
                    """,
    'author'    : "Dion Martin H. @Konsaltén Indonesia (Consult10 Indonesia)",
    'website'   : "http://www.yourcompany.com",
    'website'   : "www.consult10indonesia.com",
    'license'   : 'AGPL-3',
    'depends'   : ['base', 'c10i_base', 'purchase', 'c10i_purchase', 'stock'],
    'data'      : [
                    'security/purchase_request.xml',
                    'security/ir.model.access.csv',
                    'wizard/wizard_purchase_request_to_rfq_view.xml',
                    'wizard/wizard_purchase_request_to_purchase_view.xml',
                    'wizard/wizard_rfq_to_purchase_view.xml',
                    'wizard/wizard_report_price_approval_request_view.xml',
                    'views/purchase_view.xml',
                    'views/purchase_request_view.xml',
                    'views/purchase_rfq_view.xml',
                    'data/purchase_request_data.xml',
                    'data/purchase_rfq_data.xml',
                    'data/purchase_data.xml',
                    'wizard/wizard_pending_purchase_request_views.xml',
                    'report/report_views.xml',
    ],
    'qweb'          : [
    ],
    'installable'   : True,
    'application'   : True,
}