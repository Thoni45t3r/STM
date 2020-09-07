# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2017 Alphasoft
#    (<http://www.alphasoft.co.id>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Landed Costs Avg',
    'version': '10.0.0.1.0',
    'author': "Ade Anshori",
    'sequence': 1,
    'website': 'http://www.adeanshori.com',
    'license': 'AGPL-3',
    'category': 'Purchasing',
    'summary': 'Purchase Landed Costs Average Price of a module by Ade Anshori.',
    'depends': ['product',
                'purchase',
                'stock_account',
                'c10i_base',
                'c10i_stock',
                ],
    'description': """
Module based on Ade Anshori
=====================================================
* Landed cost by weight or volume
* Landed Cost on Purchase for same Vendor (apply to cost product)
* Landed Cost on Third Parties Forwarder make new invoice (apply to cost product and incoming shippment)
* Account landed cost must be Allow Reconciliation    
* Generate Vendor Bills and automatic reconcile between landed cost & invoice (Account must be same)
* Set Product for Landed Cost and Account must be Accrue (for reconcile), don't set income or expense
""",
    'demo': [],
    'test': [],
    'data': [
            "security/purchase_security.xml",
            'security/ir.model.access.csv',
            "data/landed_cost_data.xml",
            "views/product_view.xml",
            "views/purchase_view.xml",
            "views/landed_cost_views.xml",
            "views/invoice_view.xml",
            "views/stock_view.xml",
            'views/res_config_views.xml',
            "report/report_view.xml",
     ],
    'css': [],
    'js': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
