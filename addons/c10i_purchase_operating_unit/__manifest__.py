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
    "name": "Operating Unit in C10i Purchase Orders",
    "summary": "An operating unit (OU) is an organizational entity part of a "
               "company",
    "version": "10.0.1.1.1",
    "author": "Konsaltén Indonesia (Consult10 Indonesia)",
    "website": "http://www.eficent.com",
    "category": "Purchase Management",
    "depends": ["c10i_purchase", "purchase_operating_unit"],
    "license": "LGPL-3",
    "data": [
        "security/purchase_security.xml",
        "views/purchase_views.xml",
    ],
    "demo": [],
    "installable": True,
}
